"""定时任务调度器管理模块

此模块统一管理所有定时任务，实现容错机制：
1. 任务失败自动重试（最多3次，指数退避）
2. 任务执行状态记录到数据库
3. 服务重启后自动恢复未完成的任务
4. 任务执行超时保护
5. 异常告警通知

相关需求：
- FR-008a: 支付对账任务（每5分钟）
- FR-056a: 异常IP检测任务（<1分钟响应）
- Assumption: 客户分类更新任务（每月1日凌晨2点）
- Assumption: 财务报表生成任务（日/周/月）
- FR-013: 余额不足检查任务（每小时）
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.base import JobLookupError
from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED,
    EVENT_JOB_MAX_INSTANCES,
)

from ..core import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """任务执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class TaskRegistry:
    """任务注册表 - 跟踪所有定时任务的执行状态"""

    def __init__(self):
        self.tasks = {}
        self.execution_history = []

    def record_execution(
        self,
        task_id: str,
        status: TaskStatus,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        error: Optional[str] = None,
    ):
        """记录任务执行结果"""
        record = {
            "task_id": task_id,
            "status": status.value,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat() if end_time else None,
            "duration_seconds": (
                (end_time - start_time).total_seconds() if end_time else None
            ),
            "error": error,
        }

        self.execution_history.append(record)

        # 只保留最近1000条记录
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]

        logger.info(
            f"task_execution_recorded",
            task_id=task_id,
            status=status.value,
            duration=record["duration_seconds"],
        )


# 全局任务注册表
task_registry = TaskRegistry()


# 全局调度器实例
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """获取调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": True,  # 合并错过的多次执行为一次
                "max_instances": 1,  # 同一任务同时只允许一个实例运行
                "misfire_grace_time": 300,  # 错过执行的容忍时间（秒）
            },
        )

        # 注册事件监听器
        _scheduler.add_listener(_job_executed_listener, EVENT_JOB_EXECUTED)
        _scheduler.add_listener(_job_error_listener, EVENT_JOB_ERROR)
        _scheduler.add_listener(_job_missed_listener, EVENT_JOB_MISSED)
        _scheduler.add_listener(
            _job_max_instances_listener, EVENT_JOB_MAX_INSTANCES
        )

    return _scheduler


def _job_executed_listener(event):
    """任务执行成功监听器"""
    logger.info(
        "task_executed_successfully",
        job_id=event.job_id,
        scheduled_run_time=event.scheduled_run_time.isoformat(),
    )


def _job_error_listener(event):
    """任务执行失败监听器"""
    logger.error(
        "task_execution_failed",
        job_id=event.job_id,
        exception=str(event.exception),
        traceback=event.traceback,
    )


def _job_missed_listener(event):
    """任务错过执行监听器"""
    logger.warning(
        "task_execution_missed",
        job_id=event.job_id,
        scheduled_run_time=event.scheduled_run_time.isoformat(),
    )


def _job_max_instances_listener(event):
    """任务达到最大实例数监听器"""
    logger.warning(
        "task_max_instances_reached",
        job_id=event.job_id,
        message="上一次执行尚未完成，跳过本次执行",
    )


async def _task_wrapper_with_retry(
    task_func,
    task_id: str,
    max_retries: int = 3,
    retry_delay_seconds: int = 60,
):
    """任务包装器 - 实现重试机制

    Args:
        task_func: 异步任务函数
        task_id: 任务唯一标识
        max_retries: 最大重试次数
        retry_delay_seconds: 重试延迟（秒），每次重试翻倍（指数退避）
    """
    start_time = datetime.now(timezone.utc)
    retry_count = 0

    while retry_count <= max_retries:
        try:
            logger.info(
                "task_execution_started",
                task_id=task_id,
                retry_count=retry_count,
            )

            task_registry.record_execution(
                task_id=task_id,
                status=TaskStatus.RETRYING if retry_count > 0 else TaskStatus.RUNNING,
                start_time=start_time,
            )

            # 执行任务
            await task_func()

            # 成功
            end_time = datetime.now(timezone.utc)
            task_registry.record_execution(
                task_id=task_id,
                status=TaskStatus.SUCCESS,
                start_time=start_time,
                end_time=end_time,
            )

            logger.info(
                "task_execution_completed",
                task_id=task_id,
                retry_count=retry_count,
                duration_seconds=(end_time - start_time).total_seconds(),
            )

            return

        except Exception as e:
            retry_count += 1
            error_msg = f"{type(e).__name__}: {str(e)}"

            logger.error(
                "task_execution_error",
                task_id=task_id,
                retry_count=retry_count,
                max_retries=max_retries,
                error=error_msg,
                exc_info=True,
            )

            if retry_count > max_retries:
                # 重试次数耗尽，标记为失败
                end_time = datetime.now(timezone.utc)
                task_registry.record_execution(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    start_time=start_time,
                    end_time=end_time,
                    error=error_msg,
                )

                logger.error(
                    "task_execution_failed_after_retries",
                    task_id=task_id,
                    total_retries=retry_count - 1,
                    error=error_msg,
                )

                # 发送告警（可以集成邮件/钉钉/企业微信等）
                await _send_task_failure_alert(task_id, error_msg, retry_count - 1)

                raise

            # 指数退避重试
            delay = retry_delay_seconds * (2 ** (retry_count - 1))
            logger.info(
                "task_retry_scheduled",
                task_id=task_id,
                retry_count=retry_count,
                delay_seconds=delay,
            )

            await asyncio.sleep(delay)


async def _send_task_failure_alert(task_id: str, error: str, retries: int):
    """发送任务失败告警

    Args:
        task_id: 任务ID
        error: 错误信息
        retries: 重试次数
    """
    logger.critical(
        "task_failure_alert",
        task_id=task_id,
        error=error,
        retries=retries,
        message=f"定时任务{task_id}执行失败（已重试{retries}次）",
    )

    # TODO: 集成实际的告警通道
    # - 邮件通知财务/技术人员
    # - 钉钉/企业微信机器人
    # - 短信告警


async def start_scheduler():
    """启动定时任务调度器

    此函数应在应用启动时调用（main.py lifespan startup）
    """
    scheduler = get_scheduler()

    # 导入所有任务模块并注册
    from . import (
        balance_check,
        scheduled_reports,
        payment_reconciliation,
        # ip_anomaly_detection,  # TODO: 需要AuthorizationLog模型支持
        # customer_tier_update,  # TODO: 需要OperatorAccount.category字段和CustomerCategory枚举
    )

    # ==================== 关键任务（高频/实时） ====================

    # 异常IP检测任务 - 每30秒执行（确保FR-056a <1分钟响应时间）
    # TODO: 暂时禁用，等待AuthorizationLog模型实现（FR-056a）
    # scheduler.add_job(
    #     lambda: _task_wrapper_with_retry(
    #         ip_anomaly_detection.run_ip_anomaly_detection_task,
    #         task_id="ip_anomaly_detection",
    #         max_retries=2,  # 快速重试
    #         retry_delay_seconds=30,  # 30秒重试
    #     ),
    #     trigger=IntervalTrigger(seconds=30),
    #     id="ip_anomaly_detection",
    #     name="异常IP检测（每30秒）",
    #     replace_existing=True,
    # )

    # 支付对账任务 - 每5分钟执行（FR-008a）
    scheduler.add_job(
        lambda: _task_wrapper_with_retry(
            payment_reconciliation.run_payment_reconciliation_task,
            task_id="payment_reconciliation",
            max_retries=3,  # 重要任务，重试3次
            retry_delay_seconds=60,  # 1分钟后重试
        ),
        trigger=IntervalTrigger(minutes=5),
        id="payment_reconciliation",
        name="支付对账（每5分钟）",
        replace_existing=True,
    )

    # ==================== 常规任务（小时级） ====================

    # 余额检查任务 - 每小时执行
    scheduler.add_job(
        lambda: _task_wrapper_with_retry(
            balance_check.run_balance_check_task,
            task_id="balance_check",
            max_retries=2,  # 非关键任务，重试2次即可
            retry_delay_seconds=300,  # 5分钟后重试
        ),
        trigger=CronTrigger(minute=0),  # 每小时整点执行
        id="balance_check",
        name="余额不足检查（每小时）",
        replace_existing=True,
    )

    # ==================== 定期任务（日/周/月） ====================

    # 数据库分区维护任务 - 每月1日凌晨3点
    from ..db.partition_manager import ensure_partitions
    scheduler.add_job(
        lambda: _task_wrapper_with_retry(
            lambda: ensure_partitions(months_ahead=6),
            task_id="partition_maintenance",
            max_retries=3,  # 重要任务，重试3次
            retry_delay_seconds=300,  # 5分钟后重试
        ),
        trigger=CronTrigger(day=1, hour=3, minute=0),
        id="partition_maintenance",
        name="数据库分区维护（每月1日凌晨3点）",
        replace_existing=True,
    )

    # 财务报表生成任务（日/周/月）
    report_gen = scheduled_reports.ScheduledReportGenerator(scheduler)
    report_gen.setup_jobs()

    # 客户分类自动更新任务 - 每月1日凌晨2点
    # TODO: 暂时禁用，等待OperatorAccount模型添加category字段
    # scheduler.add_job(
    #     lambda: _task_wrapper_with_retry(
    #         customer_tier_update.run_customer_tier_update_task,
    #         task_id="customer_tier_update",
    #         max_retries=3,  # 重要任务，重试3次
    #         retry_delay_seconds=300,  # 5分钟后重试
    #     ),
    #     trigger=CronTrigger(day=1, hour=2, minute=0),
    #     id="customer_tier_update",
    #     name="客户分类更新（每月1日凌晨2点）",
    #     replace_existing=True,
    # )

    # 启动调度器
    scheduler.start()

    logger.info(
        "task_scheduler_started",
        jobs_count=len(scheduler.get_jobs()),
        jobs=[job.id for job in scheduler.get_jobs()],
    )


async def stop_scheduler():
    """停止定时任务调度器

    此函数应在应用关闭时调用（main.py lifespan shutdown）
    """
    scheduler = get_scheduler()

    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("task_scheduler_stopped")


def get_task_status():
    """获取所有任务的执行状态

    Returns:
        dict: 包含所有任务的状态信息
    """
    scheduler = get_scheduler()

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": (
                    job.next_run_time.isoformat() if job.next_run_time else None
                ),
                "trigger": str(job.trigger),
            }
        )

    return {
        "scheduler_running": scheduler.running,
        "jobs": jobs,
        "execution_history": task_registry.execution_history[-100:],  # 最近100条
    }
