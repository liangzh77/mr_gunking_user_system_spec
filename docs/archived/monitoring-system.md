# MR游戏运营管理系统 - 监控系统文档

## 概述

本系统提供了全面的监控和告警能力，包含超过50个专业监控指标，覆盖业务、技术、安全和系统资源等多个维度。

## 监控架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   业务指标       │    │   技术指标       │    │   安全指标       │
│                 │    │                 │    │                 │
│ • 游戏会话       │    │ • API响应时间    │    │ • 认证失败       │
│ • 运营商活动     │    │ • 数据库性能     │    │ • 可疑活动       │
│ • 财务操作       │    │ • 缓存命中率     │    │ • API滥用        │
│ • 充值转化率     │    │ • 系统资源使用   │    │ • 数据访问       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Prometheus     │
                    │  指标收集器      │
                    └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   健康检查       │    │   告警系统       │    │   仪表板         │
│                 │    │                 │    │                 │
│ • 数据库连接     │    │ • 规则引擎       │    │ • 实时指标       │
│ • Redis状态      │    │ • 多渠道通知     │    │ • 健康状态       │
│ • 磁盘空间       │    │ • 告警聚合       │    │ • 趋势分析       │
│ • 内存使用       │    │ • 自动抑制       │    │ • 告警管理       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 核心监控指标

### 1. 业务指标 (Business Metrics)

| 指标名称 | 类型 | 描述 | 标签 |
|---------|------|------|------|
| `mr_game_sessions_active_total` | Gauge | 当前活跃游戏会话总数 | app_id, operator_id, site_id |
| `mr_game_sessions_total` | Counter | 游戏会话总数 | app_id, operator_id, site_id, status |
| `mr_game_session_duration_seconds` | Histogram | 游戏会话持续时间 | app_id, operator_id |
| `mr_game_session_cost_yuan` | Histogram | 游戏会话费用 | app_id, operator_id |
| `mr_operator_login_total` | Counter | 运营商登录总数 | status, auth_method |
| `mr_balance_operations_total` | Counter | 余额操作总数 | operator_id, operation_type, status |
| `mr_transaction_amount_yuan` | Histogram | 交易金额分布 | transaction_type, operator_id |
| `mr_recharge_orders_total` | Counter | 充值订单总数 | payment_method, status, amount_tier |
| `mr_recharge_conversion_rate` | Gauge | 充值转化率 | payment_method, time_period |

### 2. 技术性能指标 (Technical Performance Metrics)

| 指标名称 | 类型 | 描述 | 标签 |
|---------|------|------|------|
| `mr_api_latency_seconds` | Histogram | API响应时间 | endpoint, method, operator_tier |
| `mr_db_query_duration_seconds` | Histogram | 数据库查询时间 | operation_type, table_name |
| `mr_cache_operations_total` | Counter | 缓存操作总数 | operation, cache_type, result |
| `mr_redis_connections_active` | Gauge | Redis活跃连接数 | pool_name |
| `mr_redis_commands_total` | Counter | Redis命令执行总数 | command, status |
| `mr_db_connection_pool_active` | Gauge | 数据库连接池活跃连接数 | pool_type |
| `mr_db_connection_pool_idle` | Gauge | 数据库连接池空闲连接数 | pool_type |

### 3. 系统资源指标 (System Resource Metrics)

| 指标名称 | 类型 | 描述 | 标签 |
|---------|------|------|------|
| `mr_system_cpu_usage_percent` | Gauge | 系统CPU使用率 | core |
| `mr_system_memory_usage_bytes` | Gauge | 系统内存使用量 | type |
| `mr_system_disk_usage_bytes` | Gauge | 磁盘使用量 | mount_point, type |
| `mr_system_network_io_bytes` | Counter | 网络IO字节数 | direction, interface |
| `mr_process_cpu_usage_percent` | Gauge | 应用进程CPU使用率 | - |
| `mr_process_memory_usage_bytes` | Gauge | 应用进程内存使用量 | type |
| `mr_process_file_descriptors` | Gauge | 文件描述符数量 | - |

### 4. 安全指标 (Security Metrics)

| 指标名称 | 类型 | 描述 | 标签 |
|---------|------|------|------|
| `mr_auth_failures_total` | Counter | 认证失败总数 | auth_type, reason, ip_address |
| `mr_suspicious_activities_total` | Counter | 可疑活动总数 | activity_type, risk_level |
| `mr_api_abuse_attempts_total` | Counter | API滥用尝试总数 | abuse_type, ip_address |
| `mr_blocked_requests_total` | Counter | 被拦截的请求总数 | block_reason, ip_address |
| `mr_data_access_total` | Counter | 数据访问总数 | data_type, access_type, user_role |
| `mr_encryption_operations_total` | Counter | 加密操作总数 | operation, algorithm, status |

### 5. 服务质量指标 (Service Quality Metrics)

| 指标名称 | 类型 | 描述 | 标签 |
|---------|------|------|------|
| `mr_service_availability` | Gauge | 服务可用性 | service_name |
| `mr_error_rate` | Gauge | 错误率 | service_name, error_type |
| `mr_sla_compliance` | Gauge | SLA合规性 | sla_type, time_period |
| `mr_health_check_status` | Gauge | 健康检查状态 | check_type, component |
| `mr_health_check_duration_seconds` | Histogram | 健康检查耗时 | check_type, component |

## 健康检查系统

### 检查类型

1. **数据库健康检查**
   - 连接性测试
   - 查询性能测试
   - 连接池状态监控

2. **Redis健康检查**
   - 连接状态测试
   - 延迟测试
   - 内存使用监控

3. **磁盘空间检查**
   - 可用空间监控
   - 使用率阈值告警
   - I/O性能监控

4. **内存使用检查**
   - 物理内存使用率
   - 交换空间使用
   - 内存泄漏检测

5. **外部API检查**
   - 第三方服务可用性
   - 响应时间监控
   - 错误率统计

### 检查级别

- **Basic**: 基础检查（核心组件）
- **Standard**: 标准检查（主要组件）
- **Comprehensive**: 全面检查（所有组件）

## 告警系统

### 告警规则配置

```yaml
alert_rules:
  - id: high_cpu_usage
    name: CPU使用率过高
    description: 系统CPU使用率超过阈值
    severity: warning
    condition: system.cpu.usage > 80
    threshold: 80
    consecutive_failures: 2
    evaluation_interval: 60
    notification_channels: [email, slack]
    cooldown_period: 300

  - id: high_memory_usage
    name: 内存使用率过高
    description: 系统内存使用率超过阈值
    severity: critical
    condition: system.memory.usage > 90
    threshold: 90
    consecutive_failures: 1
    evaluation_interval: 60
    notification_channels: [email]
    cooldown_period: 180
```

### 通知渠道

1. **邮件通知**
   - SMTP配置支持
   - HTML/文本格式
   - 多收件人支持

2. **Webhook通知**
   - 自定义HTTP端点
   - JSON格式payload
   - 重试机制

3. **Slack通知**
   - 直接集成Slack API
   - 富文本消息格式
   - 颜色编码严重级别

### 告警状态

- **Active**: 活跃告警
- **Acknowledged**: 已确认告警
- **Resolved**: 已解决告警
- **Suppressed**: 已抑制告警

## API接口

### 健康检查API

```http
GET /api/v1/monitoring/health
```

**查询参数:**
- `level`: 检查级别 (basic/standard/comprehensive)

**响应示例:**
```json
{
  "success": true,
  "data": {
    "overall_status": "healthy",
    "timestamp": "2024-01-01T12:00:00Z",
    "total_checks": 5,
    "passed_checks": 5,
    "failed_checks": 0,
    "checks": [
      {
        "component": "database",
        "type": "database",
        "status": "healthy",
        "message": "Database connection successful",
        "duration_ms": 15.5,
        "timestamp": "2024-01-01T12:00:00Z"
      }
    ]
  }
}
```

### 监控仪表板API

```http
GET /api/v1/monitoring/dashboard
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "health": {
      "overall_status": "healthy",
      "passed_checks": 8,
      "failed_checks": 0
    },
    "metrics": {
      "collection_active": true,
      "total_metrics": 52
    },
    "business": {
      "active_sessions": 156,
      "total_players": 624,
      "revenue_today": 12580.50
    },
    "alerts": [
      {
        "id": "alert_001",
        "title": "CPU使用率过高",
        "severity": "warning",
        "status": "active"
      }
    ]
  }
}
```

### Prometheus指标

```http
GET /metrics
```

提供Prometheus格式的所有指标数据，可与Grafana等可视化工具集成。

## 配置管理

### 环境变量

```bash
# 监控系统配置
MONITORING_ENABLED=true
MONITORING_INTERVAL=60

# 健康检查配置
HEALTH_CHECK_DISK_WARNING=80
HEALTH_CHECK_DISK_CRITICAL=90
HEALTH_CHECK_MEMORY_WARNING=80
HEALTH_CHECK_MEMORY_CRITICAL=90

# 告警系统配置
ALERT_EMAIL_SMTP_HOST=smtp.example.com
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_USERNAME=alerts@example.com
ALERT_EMAIL_PASSWORD=your_password

# Slack配置
ALERT_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### 配置文件

```yaml
# monitoring_config.yaml
health_monitoring:
  database_url: ${DATABASE_URL}
  redis_url: ${REDIS_URL}
  monitoring_interval: 60
  disk_warning_threshold: 80.0
  disk_critical_threshold: 90.0
  memory_warning_threshold: 80.0
  memory_critical_threshold: 90.0

alert_system:
  evaluation_interval: 60
  notification_channels:
    email:
      enabled: true
      host: ${ALERT_EMAIL_SMTP_HOST}
      port: ${ALERT_EMAIL_SMTP_PORT}
      username: ${ALERT_EMAIL_USERNAME}
      password: ${ALERT_EMAIL_PASSWORD}
      from: "MR监控系统 <alerts@example.com>"
      to: ["admin@example.com"]

    slack:
      enabled: true
      webhook_url: ${ALERT_SLACK_WEBHOOK_URL}

    webhook:
      enabled: false
      url: "https://your-webhook-endpoint.com/alerts"
      headers:
        Authorization: "Bearer your-token"
```

## 最佳实践

### 1. 指标设计原则

- **有意义**: 指标应反映业务价值和用户体验
- **可操作**: 指标变化应能触发具体的行动
- **可理解**: 指标名称和标签应清晰明确
- **一致性好**: 指标定义应在整个系统中保持一致

### 2. 告警策略

- **分层告警**: 根据严重级别设置不同的通知策略
- **避免告警疲劳**: 合理设置冷却期和聚合规则
- **上下文信息**: 告警消息应包含足够的上下文信息
- **自动化响应**: 对常见问题设置自动化的处理流程

### 3. 监控覆盖

- **全栈监控**: 从基础设施到应用层的全面覆盖
- **业务监控**: 关注关键业务指标和用户体验
- **安全监控**: 监控安全事件和异常行为
- **成本监控**: 跟踪资源使用和成本情况

### 4. 数据保留

- **指标数据**: 根据重要程度设置不同的保留期
- **日志数据**: 重要日志长期保存，调试日志短期保存
- **告警历史**: 保留告警历史用于趋势分析
- **性能数据**: 保留性能基线用于容量规划

## 故障排查指南

### 1. 常见问题诊断

**高CPU使用率**
1. 检查`mr_system_cpu_usage_percent`指标
2. 查看进程级别的CPU使用情况
3. 分析慢查询和热点代码
4. 检查是否有异常的定时任务

**内存泄漏**
1. 监控`mr_process_memory_usage_bytes`趋势
2. 检查对象创建和释放情况
3. 分析内存使用模式
4. 重启应用作为临时解决方案

**数据库连接问题**
1. 检查`mr_db_connection_pool_active`指标
2. 分析慢查询日志
3. 检查连接池配置
4. 监控数据库锁等待情况

### 2. 监控工具使用

**Prometheus查询示例**
```promql
# CPU使用率超过80%的时间
rate(mr_system_cpu_usage_percent[5m]) > 80

# API响应时间P95
histogram_quantile(0.95, mr_api_latency_seconds_bucket)

# 错误率
rate(mr_api_errors_total[5m]) / rate(mr_http_requests_total[5m])
```

**Grafana仪表板配置**
- 系统资源仪表板
- 应用性能仪表板
- 业务指标仪表板
- 错误监控仪表板

## 扩展开发

### 1. 自定义指标

```python
from prometheus_client import Counter, Histogram

# 创建自定义指标
custom_business_metric = Counter(
    name="mr_custom_business_total",
    documentation="自定义业务指标",
    labelnames=["operation", "status"]
)

# 记录指标
custom_business_metric.labels(operation="login", status="success").inc()
```

### 2. 自定义健康检查

```python
from ..core.monitoring.health_monitor import HealthCheck, HealthCheckResult, HealthStatus

class CustomHealthCheck(HealthCheck):
    async def execute_check(self) -> HealthCheckResult:
        # 实现自定义检查逻辑
        return HealthCheckResult(
            component="custom_service",
            check_type="custom",
            status=HealthStatus.HEALTHY,
            message="Custom service is healthy",
            duration_ms=0,
            timestamp=datetime.now()
        )
```

### 3. 自定义通知渠道

```python
from ..core.monitoring.alert_system import NotificationChannel, Alert

class CustomNotificationChannel(NotificationChannel):
    async def send_notification(self, alert: Alert, message: str) -> bool:
        # 实现自定义通知逻辑
        return True
```

## 总结

MR游戏运营管理系统的监控系统提供了：

- **全面的指标覆盖**: 50+个专业监控指标
- **智能告警系统**: 多层级告警和多渠道通知
- **实时健康检查**: 全面的组件健康状态监控
- **可视化仪表板**: 实时监控数据和趋势分析
- **高可扩展性**: 支持自定义指标、检查和通知渠道

该监控系统确保了系统的高可用性、性能优化和快速故障响应能力，为业务稳定运行提供了强有力的保障。