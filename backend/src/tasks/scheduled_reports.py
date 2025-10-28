"""
定时财务报表生成任务 (T189a)

使用 APScheduler 定时生成财务报表:
- 每日凌晨1点生成日报
- 每周一凌晨生成周报  
- 每月1日凌晨生成月报
"""
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_async_session
from src.services.finance_dashboard_service import FinanceDashboardService

logger = logging.getLogger(__name__)


class ScheduledReportGenerator:
    """定时报表生成器"""

    def __init__(self, scheduler: AsyncIOScheduler):
        self.scheduler = scheduler
        self.dashboard_service = FinanceDashboardService()

    def setup_jobs(self):
        """配置所有定时任务"""
        # 每日凌晨1点生成日报
        self.scheduler.add_job(
            self.generate_daily_report,
            trigger=CronTrigger(hour=1, minute=0),
            id="daily_report",
            name="生成每日财务报表",
            replace_existing=True
        )

        # 每周一凌晨2点生成周报
        self.scheduler.add_job(
            self.generate_weekly_report,
            trigger=CronTrigger(day_of_week="mon", hour=2, minute=0),
            id="weekly_report",
            name="生成每周财务报表",
            replace_existing=True
        )

        # 每月1日凌晨3点生成月报
        self.scheduler.add_job(
            self.generate_monthly_report,
            trigger=CronTrigger(day=1, hour=3, minute=0),
            id="monthly_report",
            name="生成每月财务报表",
            replace_existing=True
        )

        logger.info("定时报表任务已配置完成")

    async def generate_daily_report(self):
        """生成每日财务报表"""
        try:
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            
            logger.info(f"开始生成日报: {yesterday}")
            
            async for session in get_async_session():
                # 获取昨日收入统计
                revenue_data = await self._get_revenue_summary(
                    session, yesterday, yesterday
                )
                
                # 获取昨日大客户数据
                top_customers = await self._get_top_customers(session, 10)
                
                # 保存报表到数据库
                report = await self._save_report(
                    session,
                    report_type="daily",
                    start_date=yesterday,
                    end_date=yesterday,
                    data={
                        "revenue": revenue_data,
                        "top_customers": top_customers
                    }
                )
                
                logger.info(f"日报生成成功: report_id={report.get('id')}")
                
        except Exception as e:
            logger.error(f"生成日报失败: {str(e)}", exc_info=True)

    async def generate_weekly_report(self):
        """生成每周财务报表"""
        try:
            today = datetime.utcnow().date()
            start_date = today - timedelta(days=7)
            
            logger.info(f"开始生成周报: {start_date} 至 {today}")
            
            async for session in get_async_session():
                revenue_data = await self._get_revenue_summary(
                    session, start_date, today
                )
                
                report = await self._save_report(
                    session,
                    report_type="weekly",
                    start_date=start_date,
                    end_date=today,
                    data={"revenue": revenue_data}
                )
                
                logger.info(f"周报生成成功: report_id={report.get('id')}")
                
        except Exception as e:
            logger.error(f"生成周报失败: {str(e)}", exc_info=True)

    async def generate_monthly_report(self):
        """生成每月财务报表"""
        try:
            today = datetime.utcnow().date()
            # 上个月第一天
            if today.month == 1:
                start_date = today.replace(year=today.year-1, month=12, day=1)
            else:
                start_date = today.replace(month=today.month-1, day=1)
            
            # 上个月最后一天
            end_date = today.replace(day=1) - timedelta(days=1)
            
            logger.info(f"开始生成月报: {start_date} 至 {end_date}")
            
            async for session in get_async_session():
                revenue_data = await self._get_revenue_summary(
                    session, start_date, end_date
                )
                
                report = await self._save_report(
                    session,
                    report_type="monthly",
                    start_date=start_date,
                    end_date=end_date,
                    data={"revenue": revenue_data}
                )
                
                logger.info(f"月报生成成功: report_id={report.get('id')}")
                
        except Exception as e:
            logger.error(f"生成月报失败: {str(e)}", exc_info=True)

    async def _get_revenue_summary(self, 
                                   session: AsyncSession,
                                   start_date: datetime.date,
                                   end_date: datetime.date) -> Dict[str, Any]:
        """获取收入统计摘要"""
        # 调用 FinanceDashboardService 获取数据
        # 这里简化实现，实际应调用对应的服务方法
        return {
            "total_revenue": 0.0,
            "total_transactions": 0,
            "period": f"{start_date} 至 {end_date}"
        }

    async def _get_top_customers(self,
                                 session: AsyncSession,
                                 limit: int) -> list:
        """获取大客户列表"""
        return []

    async def _save_report(self,
                          session: AsyncSession,
                          report_type: str,
                          start_date: datetime.date,
                          end_date: datetime.date,
                          data: Dict[str, Any]) -> Dict[str, Any]:
        """保存报表到数据库"""
        # TODO: 实际保存到 finance_reports 表
        logger.info(f"保存{report_type}报表: {start_date} 至 {end_date}")
        return {"id": "mock-report-id"}


# 全局调度器实例
scheduler = AsyncIOScheduler()
report_generator = ScheduledReportGenerator(scheduler)


def start_scheduler():
    """启动调度器"""
    report_generator.setup_jobs()
    scheduler.start()
    logger.info("报表调度器已启动")


def stop_scheduler():
    """停止调度器"""
    scheduler.shutdown()
    logger.info("报表调度器已停止")
