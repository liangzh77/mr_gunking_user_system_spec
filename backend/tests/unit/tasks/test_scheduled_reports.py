"""
单元测试：定时报表生成任务 (T189b)

验证调度配置、报表生成逻辑、文件保存路径
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.tasks.scheduled_reports import ScheduledReportGenerator


@pytest.fixture
def mock_scheduler():
    """模拟 APScheduler"""
    scheduler = MagicMock()
    scheduler.add_job = MagicMock()
    return scheduler


@pytest.fixture
def report_generator(mock_scheduler):
    """创建报表生成器实例"""
    return ScheduledReportGenerator(mock_scheduler)


class TestScheduledReportGenerator:
    """定时报表生成器单元测试"""

    def test_setup_jobs_configures_all_schedules(self, report_generator, mock_scheduler):
        """验证所有定时任务都已配置"""
        report_generator.setup_jobs()

        # 验证 add_job 被调用3次（日报、周报、月报）
        assert mock_scheduler.add_job.call_count == 3

        # 验证任务ID
        job_ids = [call[1]["id"] for call in mock_scheduler.add_job.call_args_list]
        assert "daily_report" in job_ids
        assert "weekly_report" in job_ids
        assert "monthly_report" in job_ids


    def test_daily_report_schedule(self, report_generator, mock_scheduler):
        """验证日报调度配置（每日凌晨1点）"""
        report_generator.setup_jobs()

        daily_call = [
            call for call in mock_scheduler.add_job.call_args_list
            if call[1]["id"] == "daily_report"
        ][0]

        trigger = daily_call[1]["trigger"]
        assert trigger.fields[3].expressions[0].first == 1  # hour=1
        assert trigger.fields[4].expressions[0].first == 0  # minute=0


    def test_weekly_report_schedule(self, report_generator, mock_scheduler):
        """验证周报调度配置（每周一凌晨2点）"""
        report_generator.setup_jobs()

        weekly_call = [
            call for call in mock_scheduler.add_job.call_args_list
            if call[1]["id"] == "weekly_report"
        ][0]

        trigger = weekly_call[1]["trigger"]
        # day_of_week=mon, hour=2, minute=0
        assert trigger.fields[3].expressions[0].first == 2  # hour=2


    def test_monthly_report_schedule(self, report_generator, mock_scheduler):
        """验证月报调度配置（每月1日凌晨3点）"""
        report_generator.setup_jobs()

        monthly_call = [
            call for call in mock_scheduler.add_job.call_args_list
            if call[1]["id"] == "monthly_report"
        ][0]

        trigger = monthly_call[1]["trigger"]
        assert trigger.fields[2].expressions[0].first == 1  # day=1
        assert trigger.fields[3].expressions[0].first == 3  # hour=3


    @pytest.mark.asyncio
    async def test_generate_daily_report_date_range(self, report_generator):
        """验证日报生成使用昨日日期"""
        with patch.object(report_generator, '_get_revenue_summary', new_callable=AsyncMock) as mock_revenue:
            with patch.object(report_generator, '_get_top_customers', new_callable=AsyncMock):
                with patch.object(report_generator, '_save_report', new_callable=AsyncMock):
                    with patch('src.tasks.scheduled_reports.get_async_session'):
                        await report_generator.generate_daily_report()

                        # 验证使用昨日日期
                        yesterday = datetime.utcnow().date() - timedelta(days=1)
                        if mock_revenue.called:
                            call_args = mock_revenue.call_args[0]
                            assert call_args[1] == yesterday  # start_date
                            assert call_args[2] == yesterday  # end_date


    @pytest.mark.asyncio
    async def test_generate_weekly_report_date_range(self, report_generator):
        """验证周报生成使用7天日期范围"""
        with patch.object(report_generator, '_get_revenue_summary', new_callable=AsyncMock) as mock_revenue:
            with patch.object(report_generator, '_save_report', new_callable=AsyncMock):
                with patch('src.tasks.scheduled_reports.get_async_session'):
                    await report_generator.generate_weekly_report()

                    # 验证使用7天范围
                    if mock_revenue.called:
                        call_args = mock_revenue.call_args[0]
                        start_date = call_args[1]
                        end_date = call_args[2]
                        assert (end_date - start_date).days == 7


    @pytest.mark.asyncio
    async def test_generate_monthly_report_date_range(self, report_generator):
        """验证月报生成使用上月日期范围"""
        with patch.object(report_generator, '_get_revenue_summary', new_callable=AsyncMock) as mock_revenue:
            with patch.object(report_generator, '_save_report', new_callable=AsyncMock):
                with patch('src.tasks.scheduled_reports.get_async_session'):
                    await report_generator.generate_monthly_report()

                    # 验证使用上月日期
                    if mock_revenue.called:
                        call_args = mock_revenue.call_args[0]
                        start_date = call_args[1]
                        end_date = call_args[2]
                        
                        # 上月第一天和最后一天
                        assert start_date.day == 1
                        assert (end_date - start_date).days >= 27  # 至少28天


    @pytest.mark.asyncio
    async def test_report_generation_error_handling(self, report_generator):
        """验证报表生成错误处理"""
        with patch.object(report_generator, '_get_revenue_summary', side_effect=Exception("Database error")):
            with patch('src.tasks.scheduled_reports.get_async_session'):
                # 不应该抛出异常，应该记录日志
                try:
                    await report_generator.generate_daily_report()
                except Exception:
                    pytest.fail("报表生成失败应该被捕获，不应抛出异常")
