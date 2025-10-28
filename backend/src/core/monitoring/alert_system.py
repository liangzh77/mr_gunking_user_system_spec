"""
智能告警系统

提供灵活的告警规则配置、多渠道通知、告警聚合等功能
"""
import asyncio
import json
import structlog
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
import smtplib
try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
except ImportError:
    # 兼容不同Python版本
    from email.mime.text import MIMEText as MimeText
    from email.mime.multipart import MIMEMultipart as MimeMultipart
import httpx

from .health_monitor import HealthCheckResult, HealthStatus
from ...core.metrics.enhanced_metrics import metrics_collector

logger = structlog.get_logger(__name__)


class AlertSeverity(Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """告警规则"""
    id: str
    name: str
    description: str
    severity: AlertSeverity
    condition: str  # 告警条件表达式
    threshold: float
    evaluation_interval: int  # 评估间隔（秒）
    consecutive_failures: int  # 连续失败次数
    enabled: bool = True
    tags: Dict[str, str] = None
    notification_channels: List[str] = None
    cooldown_period: int = 300  # 冷却期（秒）

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.notification_channels is None:
            self.notification_channels = []


@dataclass
class Alert:
    """告警对象"""
    id: str
    rule_id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    component: str
    threshold_exceeded: Optional[str]
    current_value: float
    threshold_value: float
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    labels: Dict[str, str] = None
    annotations: Dict[str, str] = None

    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if self.annotations is None:
            self.annotations = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        if self.acknowledged_at:
            data['acknowledged_at'] = self.acknowledged_at.isoformat()
        data['severity'] = self.severity.value
        data['status'] = self.status.value
        return data


class NotificationChannel:
    """通知渠道基类"""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)

    async def send_notification(self, alert: Alert, message: str) -> bool:
        """发送通知"""
        raise NotImplementedError

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self.enabled


class EmailNotificationChannel(NotificationChannel):
    """邮件通知渠道"""

    async def send_notification(self, alert: Alert, message: str) -> bool:
        try:
            smtp_config = self.config

            # 创建邮件内容
            msg = MimeMultipart()
            msg['From'] = smtp_config['from']
            msg['To'] = ', '.join(smtp_config['to'])
            msg['Subject'] = f"[MR监控] {alert.severity.value.upper()} - {alert.title}"

            # 邮件正文
            body = f"""
告警详情：
- 告警ID: {alert.id}
- 告警标题: {alert.title}
- 告警描述: {alert.description}
- 严重级别: {alert.severity.value}
- 组件: {alert.component}
- 当前值: {alert.current_value}
- 阈值: {alert.threshold_value}
- 创建时间: {alert.created_at}
- 状态: {alert.status.value}

详细信息：
{message}

请及时处理此告警。
            """

            msg.attach(MimeText(body, 'plain', 'utf-8'))

            # 发送邮件
            with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
                if smtp_config.get('use_tls'):
                    server.starttls()
                if smtp_config.get('username') and smtp_config.get('password'):
                    server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg)

            logger.info("email_notification_sent",
                       alert_id=alert.id,
                       to=smtp_config['to'])
            return True

        except Exception as e:
            logger.error("email_notification_failed",
                        alert_id=alert.id,
                        error=str(e))
            return False


class WebhookNotificationChannel(NotificationChannel):
    """Webhook通知渠道"""

    async def send_notification(self, alert: Alert, message: str) -> bool:
        try:
            webhook_config = self.config
            webhook_url = webhook_config['url']

            # 构建webhook payload
            payload = {
                'alert_id': alert.id,
                'title': alert.title,
                'description': alert.description,
                'severity': alert.severity.value,
                'status': alert.status.value,
                'component': alert.component,
                'current_value': alert.current_value,
                'threshold_value': alert.threshold_value,
                'created_at': alert.created_at.isoformat(),
                'message': message,
                'labels': alert.labels,
                'annotations': alert.annotations
            }

            # 添加自定义字段
            if 'custom_fields' in webhook_config:
                payload.update(webhook_config['custom_fields'])

            # 发送webhook请求
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers=webhook_config.get('headers', {})
                )
                response.raise_for_status()

            logger.info("webhook_notification_sent",
                       alert_id=alert.id,
                       url=webhook_url,
                       status_code=response.status_code)
            return True

        except Exception as e:
            logger.error("webhook_notification_failed",
                        alert_id=alert.id,
                        error=str(e))
            return False


class SlackNotificationChannel(NotificationChannel):
    """Slack通知渠道"""

    async def send_notification(self, alert: Alert, message: str) -> bool:
        try:
            slack_config = self.config
            webhook_url = slack_config['webhook_url']

            # 构建Slack消息
            color_map = {
                AlertSeverity.INFO: "#36a64f",
                AlertSeverity.WARNING: "#ff9500",
                AlertSeverity.CRITICAL: "#ff0000"
            }

            slack_payload = {
                "attachments": [
                    {
                        "color": color_map.get(alert.severity, "#808080"),
                        "title": f"[{alert.severity.value.upper()}] {alert.title}",
                        "text": alert.description,
                        "fields": [
                            {
                                "title": "组件",
                                "value": alert.component,
                                "short": True
                            },
                            {
                                "title": "当前值/阈值",
                                "value": f"{alert.current_value} / {alert.threshold_value}",
                                "short": True
                            },
                            {
                                "title": "状态",
                                "value": alert.status.value,
                                "short": True
                            },
                            {
                                "title": "时间",
                                "value": alert.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                                "short": True
                            }
                        ],
                        "footer": "MR监控系统",
                        "ts": int(alert.created_at.timestamp())
                    }
                ]
            }

            # 发送Slack消息
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(webhook_url, json=slack_payload)
                response.raise_for_status()

            logger.info("slack_notification_sent",
                       alert_id=alert.id,
                       status_code=response.status_code)
            return True

        except Exception as e:
            logger.error("slack_notification_failed",
                        alert_id=alert.id,
                        error=str(e))
            return False


class AlertRuleEngine:
    """告警规则引擎"""

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.rule_states: Dict[str, Dict[str, Any]] = {}  # 规则状态

    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules[rule.id] = rule
        self.rule_states[rule.id] = {
            'consecutive_failures': 0,
            'last_evaluation': None,
            'last_alert_time': None,
            'active_alert_id': None
        }
        logger.info("alert_rule_added", rule_id=rule.id, rule_name=rule.name)

    def remove_rule(self, rule_id: str):
        """移除告警规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            if rule_id in self.rule_states:
                del self.rule_states[rule_id]
            logger.info("alert_rule_removed", rule_id=rule_id)

    def evaluate_rules(self, metrics_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """评估告警规则"""
        triggered_alerts = []

        for rule_id, rule in self.rules.items():
            if not rule.enabled:
                continue

            try:
                # 评估规则条件
                should_trigger, current_value = self._evaluate_condition(rule.condition, metrics_data)

                # 更新规则状态
                state = self.rule_states[rule_id]
                state['last_evaluation'] = datetime.now()

                if should_trigger:
                    state['consecutive_failures'] += 1

                    # 检查是否需要触发告警
                    if (state['consecutive_failures'] >= rule.consecutive_failures and
                        self._should_send_alert(rule_id, rule)):

                        triggered_alerts.append({
                            'rule_id': rule_id,
                            'rule_name': rule.name,
                            'severity': rule.severity,
                            'current_value': current_value,
                            'threshold': rule.threshold,
                            'condition': rule.condition,
                            'consecutive_failures': state['consecutive_failures']
                        })

                        state['last_alert_time'] = datetime.now()

                else:
                    # 重置失败计数
                    if state['consecutive_failures'] > 0:
                        logger.info("rule_condition_resolved",
                                   rule_id=rule_id,
                                   consecutive_failures=state['consecutive_failures'])
                    state['consecutive_failures'] = 0

            except Exception as e:
                logger.error("rule_evaluation_error",
                           rule_id=rule_id,
                           error=str(e))

        return triggered_alerts

    def _evaluate_condition(self, condition: str, metrics_data: Dict[str, Any]) -> tuple[bool, float]:
        """评估告警条件"""
        try:
            # 简单的条件评估实现
            # 支持格式: metric_name > threshold 或 metric_name < threshold

            if '>' in condition:
                metric_name, threshold = condition.split('>', 1)
                metric_name = metric_name.strip()
                threshold = float(threshold.strip())
                current_value = self._get_metric_value(metric_name, metrics_data)
                return current_value > threshold, current_value

            elif '<' in condition:
                metric_name, threshold = condition.split('<', 1)
                metric_name = metric_name.strip()
                threshold = float(threshold.strip())
                current_value = self._get_metric_value(metric_name, metrics_data)
                return current_value < threshold, current_value

            elif '==' in condition:
                metric_name, value = condition.split('==', 1)
                metric_name = metric_name.strip()
                value = value.strip().strip('"\'')
                current_value = self._get_metric_value(metric_name, metrics_data)
                return str(current_value) == value, float(current_value) if isinstance(current_value, (int, float)) else 0

            else:
                logger.warning("unsupported_condition_format", condition=condition)
                return False, 0

        except Exception as e:
            logger.error("condition_evaluation_error",
                        condition=condition,
                        error=str(e))
            return False, 0

    def _get_metric_value(self, metric_name: str, metrics_data: Dict[str, Any]) -> float:
        """获取指标值"""
        # 支持嵌套访问，如: system.cpu.usage
        keys = metric_name.split('.')
        value = metrics_data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return 0

        try:
            return float(value)
        except (ValueError, TypeError):
            return 0

    def _should_send_alert(self, rule_id: str, rule: AlertRule) -> bool:
        """检查是否应该发送告警"""
        state = self.rule_states[rule_id]

        # 检查冷却期
        if (state['last_alert_time'] and
            datetime.now() - state['last_alert_time'] < timedelta(seconds=rule.cooldown_period)):
            return False

        return True


class AlertManager:
    """告警管理器"""

    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.rule_engine = AlertRuleEngine()
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self.alert_groups: Dict[str, Set[str]] = {}  # 告警分组
        self.is_running = False
        self.evaluation_interval = 60  # 默认60秒评估一次

    def add_notification_channel(self, channel: NotificationChannel):
        """添加通知渠道"""
        self.notification_channels[channel.name] = channel
        logger.info("notification_channel_added", channel_name=channel.name)

    def remove_notification_channel(self, channel_name: str):
        """移除通知渠道"""
        if channel_name in self.notification_channels:
            del self.notification_channels[channel_name]
            logger.info("notification_channel_removed", channel_name=channel_name)

    def add_alert_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rule_engine.add_rule(rule)

    def remove_alert_rule(self, rule_id: str):
        """移除告警规则"""
        self.rule_engine.remove_rule(rule_id)

    async def create_alert(self, alert_data: Dict[str, Any]) -> Alert:
        """创建告警"""
        alert = Alert(
            id=alert_data['id'],
            rule_id=alert_data['rule_id'],
            title=alert_data['title'],
            description=alert_data['description'],
            severity=alert_data['severity'],
            status=AlertStatus.ACTIVE,
            component=alert_data['component'],
            threshold_exceeded=alert_data.get('threshold_exceeded'),
            current_value=alert_data['current_value'],
            threshold_value=alert_data['threshold'],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            labels=alert_data.get('labels', {}),
            annotations=alert_data.get('annotations', {})
        )

        self.alerts[alert.id] = alert

        # 发送通知
        await self._send_alert_notifications(alert)

        logger.info("alert_created",
                   alert_id=alert.id,
                   severity=alert.severity.value,
                   component=alert.component)

        return alert

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """确认告警"""
        if alert_id not in self.alerts:
            return False

        alert = self.alerts[alert_id]
        if alert.status != AlertStatus.ACTIVE:
            return False

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now()
        alert.updated_at = datetime.now()

        logger.info("alert_acknowledged",
                   alert_id=alert_id,
                   acknowledged_by=acknowledged_by)

        return True

    async def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        if alert_id not in self.alerts:
            return False

        alert = self.alerts[alert_id]
        if alert.status == AlertStatus.RESOLVED:
            return True

        old_status = alert.status
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()
        alert.updated_at = datetime.now()

        # 发送解决通知
        if old_status != AlertStatus.RESOLVED:
            await self._send_alert_resolved_notification(alert)

        logger.info("alert_resolved",
                   alert_id=alert_id,
                   old_status=old_status.value)

        return True

    async def suppress_alert(self, alert_id: str, duration_minutes: int = 60) -> bool:
        """抑制告警"""
        if alert_id not in self.alerts:
            return False

        alert = self.alerts[alert_id]
        alert.status = AlertStatus.SUPPRESSED
        alert.updated_at = datetime.now()

        # 设置自动恢复任务
        asyncio.create_task(self._auto_unsuppress_alert(alert_id, duration_minutes))

        logger.info("alert_suppressed",
                   alert_id=alert_id,
                   duration_minutes=duration_minutes)

        return True

    async def _auto_unsuppress_alert(self, alert_id: str, duration_minutes: int):
        """自动取消抑制"""
        await asyncio.sleep(duration_minutes * 60)

        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            if alert.status == AlertStatus.SUPPRESSED:
                alert.status = AlertStatus.ACTIVE
                alert.updated_at = datetime.now()
                logger.info("alert_unsuppressed", alert_id=alert_id)

    async def _send_alert_notifications(self, alert: Alert):
        """发送告警通知"""
        # 获取告警规则
        rule = self.rule_engine.rules.get(alert.rule_id)
        if not rule:
            return

        # 构建通知消息
        message = self._build_alert_message(alert)

        # 发送到配置的通知渠道
        for channel_name in rule.notification_channels:
            if channel_name in self.notification_channels:
                channel = self.notification_channels[channel_name]
                if channel.is_enabled():
                    try:
                        await channel.send_notification(alert, message)
                    except Exception as e:
                        logger.error("alert_notification_failed",
                                   channel_name=channel_name,
                                   alert_id=alert.id,
                                   error=str(e))

    async def _send_alert_resolved_notification(self, alert: Alert):
        """发送告警解决通知"""
        # 获取告警规则
        rule = self.rule_engine.rules.get(alert.rule_id)
        if not rule:
            return

        # 构建解决通知消息
        message = f"告警已自动解决\n告警ID: {alert.id}\n解决时间: {alert.resolved_at}"

        # 发送到配置的通知渠道
        for channel_name in rule.notification_channels:
            if channel_name in self.notification_channels:
                channel = self.notification_channels[channel_name]
                if channel.is_enabled():
                    try:
                        # 可以修改channel以支持解决通知
                        await channel.send_notification(alert, message)
                    except Exception as e:
                        logger.error("alert_resolved_notification_failed",
                                   channel_name=channel_name,
                                   alert_id=alert.id,
                                   error=str(e))

    def _build_alert_message(self, alert: Alert) -> str:
        """构建告警消息"""
        message = f"""
告警详情：
- 告警ID: {alert.id}
- 告警标题: {alert.title}
- 告警描述: {alert.description}
- 严重级别: {alert.severity.value}
- 组件: {alert.component}
- 当前值: {alert.current_value}
- 阈值: {alert.threshold_value}
- 创建时间: {alert.created_at}
- 状态: {alert.status.value}
"""

        if alert.threshold_exceeded:
            message += f"- 超阈值: {alert.threshold_exceeded}\n"

        if alert.labels:
            message += "- 标签:\n"
            for key, value in alert.labels.items():
                message += f"  {key}: {value}\n"

        return message

    async def evaluate_alert_rules(self, metrics_data: Dict[str, Any]):
        """评估告警规则"""
        try:
            triggered_alerts = self.rule_engine.evaluate_rules(metrics_data)

            for alert_data in triggered_alerts:
                # 检查是否已存在相同的活跃告警
                existing_alert = self._find_existing_alert(alert_data['rule_id'], alert_data['component'])
                if existing_alert:
                    # 更新现有告警
                    existing_alert.current_value = alert_data['current_value']
                    existing_alert.updated_at = datetime.now()
                else:
                    # 创建新告警
                    await self.create_alert({
                        'id': f"{alert_data['rule_id']}_{alert_data['component']}_{int(datetime.now().timestamp())}",
                        'rule_id': alert_data['rule_id'],
                        'title': f"{alert_data['rule_name']} - {alert_data['component']}",
                        'description': f"{alert_data['rule_name']} 触发告警",
                        'severity': alert_data['severity'],
                        'component': alert_data['component'],
                        'current_value': alert_data['current_value'],
                        'threshold': alert_data['threshold'],
                        'threshold_exceeded': f"{alert_data['condition']} (当前值: {alert_data['current_value']})",
                        'labels': {
                            'rule_name': alert_data['rule_name'],
                            'condition': alert_data['condition']
                        }
                    })

        except Exception as e:
            logger.error("alert_rules_evaluation_error", error=str(e))

    def _find_existing_alert(self, rule_id: str, component: str) -> Optional[Alert]:
        """查找现有的活跃告警"""
        for alert in self.alerts.values():
            if (alert.rule_id == rule_id and
                alert.component == component and
                alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]):
                return alert
        return None

    async def start_monitoring(self, interval: int = 60):
        """启动告警监控"""
        if self.is_running:
            return

        self.is_running = True
        self.evaluation_interval = interval

        logger.info("alert_monitoring_started", interval=interval)

        # 启动监控任务
        asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self):
        """停止告警监控"""
        self.is_running = False
        logger.info("alert_monitoring_stopped")

    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                # 获取最新的指标数据
                metrics_data = await self._collect_metrics_data()

                # 评估告警规则
                await self.evaluate_alert_rules(metrics_data)

                await asyncio.sleep(self.evaluation_interval)
            except Exception as e:
                logger.error("alert_monitoring_loop_error", error=str(e))
                await asyncio.sleep(min(self.evaluation_interval, 30))

    async def _collect_metrics_data(self) -> Dict[str, Any]:
        """收集指标数据"""
        # 这里应该从实际的监控系统获取数据
        # 目前返回模拟数据
        import random

        return {
            'system': {
                'cpu': {
                    'usage': random.uniform(20, 80)
                },
                'memory': {
                    'usage': random.uniform(30, 70)
                },
                'disk': {
                    'usage': random.uniform(40, 85)
                }
            },
            'application': {
                'active_sessions': random.randint(100, 500),
                'response_time': random.uniform(50, 300),
                'error_rate': random.uniform(0, 5),
                'throughput': random.uniform(10, 100)
            },
            'database': {
                'connection_pool_usage': random.uniform(0.5, 0.9),
                'query_time': random.uniform(10, 100),
                'active_connections': random.randint(10, 50)
            }
        }

    def get_active_alerts(self, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        alerts = []
        for alert in self.alerts.values():
            if alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
                if severity is None or alert.severity.value == severity:
                    alerts.append(alert.to_dict())

        return sorted(alerts, key=lambda x: x['created_at'], reverse=True)

    def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计"""
        stats = {
            'total_alerts': len(self.alerts),
            'active_alerts': 0,
            'acknowledged_alerts': 0,
            'resolved_alerts': 0,
            'suppressed_alerts': 0,
            'by_severity': {
                'info': 0,
                'warning': 0,
                'critical': 0
            },
            'by_component': {}
        }

        for alert in self.alerts.values():
            # 状态统计
            if alert.status == AlertStatus.ACTIVE:
                stats['active_alerts'] += 1
            elif alert.status == AlertStatus.ACKNOWLEDGED:
                stats['acknowledged_alerts'] += 1
            elif alert.status == AlertStatus.RESOLVED:
                stats['resolved_alerts'] += 1
            elif alert.status == AlertStatus.SUPPRESSED:
                stats['suppressed_alerts'] += 1

            # 严重级别统计
            stats['by_severity'][alert.severity.value] += 1

            # 组件统计
            if alert.component not in stats['by_component']:
                stats['by_component'][alert.component] = 0
            stats['by_component'][alert.component] += 1

        return stats


# 全局告警管理器实例
alert_manager = AlertManager()


async def initialize_alert_system(config: Dict[str, Any]):
    """初始化告警系统"""
    try:
        # 初始化通知渠道
        if 'email' in config.get('notification_channels', {}):
            email_config = config['notification_channels']['email']
            alert_manager.add_notification_channel(
                EmailNotificationChannel('email', email_config)
            )

        if 'webhook' in config.get('notification_channels', {}):
            webhook_config = config['notification_channels']['webhook']
            alert_manager.add_notification_channel(
                WebhookNotificationChannel('webhook', webhook_config)
            )

        if 'slack' in config.get('notification_channels', {}):
            slack_config = config['notification_channels']['slack']
            alert_manager.add_notification_channel(
                SlackNotificationChannel('slack', slack_config)
            )

        # 初始化告警规则
        if 'alert_rules' in config:
            for rule_config in config['alert_rules']:
                rule = AlertRule(
                    id=rule_config['id'],
                    name=rule_config['name'],
                    description=rule_config['description'],
                    severity=AlertSeverity(rule_config['severity']),
                    condition=rule_config['condition'],
                    threshold=rule_config['threshold'],
                    evaluation_interval=rule_config.get('evaluation_interval', 60),
                    consecutive_failures=rule_config.get('consecutive_failures', 1),
                    notification_channels=rule_config.get('notification_channels', []),
                    cooldown_period=rule_config.get('cooldown_period', 300)
                )
                alert_manager.add_alert_rule(rule)

        # 启动监控
        await alert_manager.start_monitoring(
            interval=config.get('evaluation_interval', 60)
        )

        logger.info("alert_system_initialized",
                   notification_channels=len(alert_manager.notification_channels),
                   alert_rules=len(alert_manager.rule_engine.rules))

    except Exception as e:
        logger.error("alert_system_initialization_error", error=str(e))
        raise