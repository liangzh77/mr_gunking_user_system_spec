"""
财务报表服务 (T166)

提供报表生成、查询、导出等功能
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID
import uuid

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.finance import FinanceReport
from ..models.transaction import TransactionRecord
from ..models.operator import OperatorAccount
from ..core import BadRequestException, NotFoundException


class FinanceReportService:
    """财务报表服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_report(
        self,
        finance_id: UUID,
        report_type: str,
        start_date: datetime,
        end_date: datetime,
        export_format: str = "pdf",
    ) -> FinanceReport:
        """
        生成财务报表

        Args:
            finance_id: 财务人员ID
            report_type: 报表类型(daily/weekly/monthly/custom)
            start_date: 开始日期
            end_date: 结束日期
            export_format: 导出格式(pdf/excel/csv)

        Returns:
            FinanceReport: 生成的报表记录

        Raises:
            BadRequestException: 参数错误
        """
        # 验证日期范围
        if start_date > end_date:
            raise BadRequestException("开始日期不能晚于结束日期")

        # 生成报表ID
        report_id = f"rpt_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"

        # 格式化周期描述
        period = f"{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"

        # 创建报表记录
        report = FinanceReport(
            report_id=report_id,
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            period=period,
            export_format=export_format,
            generated_by=finance_id,
            status="generating",
        )

        self.db.add(report)
        await self.db.flush()  # 获取报表ID

        try:
            # 查询交易数据统计
            stats = await self._calculate_statistics(start_date, end_date)

            # 更新报表数据
            report.total_recharge = stats["total_recharge"]
            report.total_consumption = stats["total_consumption"]
            report.total_refund = stats["total_refund"]
            report.net_income = stats["net_income"]
            report.total_transactions = stats["total_transactions"]
            report.total_operators = stats["total_operators"]
            report.active_operators = stats["active_operators"]

            # 查询每日明细数据
            daily_data = await self._get_daily_breakdown(start_date, end_date)
            report.daily_breakdown = daily_data

            # 查询Top客户数据
            top_customers = await self._get_top_customers(start_date, end_date, limit=10)
            report.top_customers = top_customers

            # 标记为完成
            report.status = "completed"

            await self.db.commit()
            await self.db.refresh(report)

            return report

        except Exception as e:
            # 标记为失败
            report.status = "failed"
            report.error_message = str(e)
            await self.db.commit()
            raise

    async def _calculate_statistics(
        self, start_date: datetime, end_date: datetime
    ) -> dict:
        """
        计算指定日期范围内的统计数据

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            dict: 统计数据
        """
        # 查询交易统计
        query = select(
            func.coalesce(
                func.sum(
                    case(
                        (TransactionRecord.transaction_type == "recharge", TransactionRecord.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("total_recharge"),
            func.coalesce(
                func.sum(
                    case(
                        (TransactionRecord.transaction_type == "consumption", TransactionRecord.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("total_consumption"),
            func.coalesce(
                func.sum(
                    case(
                        (TransactionRecord.transaction_type == "refund", TransactionRecord.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("total_refund"),
            func.count(TransactionRecord.id).label("total_transactions"),
            func.count(func.distinct(TransactionRecord.operator_id)).label("active_operators"),
        ).where(
            and_(
                TransactionRecord.created_at >= start_date,
                TransactionRecord.created_at <= end_date,
            )
        )

        result = await self.db.execute(query)
        row = result.first()

        total_recharge = Decimal(str(row.total_recharge))
        total_consumption = Decimal(str(row.total_consumption))
        total_refund = Decimal(str(row.total_refund))
        net_income = total_recharge - total_refund

        # 查询总运营商数量（活跃且未删除）
        operators_query = select(func.count(OperatorAccount.id)).where(
            and_(
                OperatorAccount.deleted_at.is_(None),
                OperatorAccount.is_active == True,
            )
        )
        operators_result = await self.db.execute(operators_query)
        total_operators = operators_result.scalar() or 0

        return {
            "total_recharge": total_recharge,
            "total_consumption": total_consumption,
            "total_refund": total_refund,
            "net_income": net_income,
            "total_transactions": row.total_transactions,
            "total_operators": total_operators,
            "active_operators": row.active_operators,
        }

    async def _get_daily_breakdown(
        self, start_date: datetime, end_date: datetime
    ) -> list:
        """
        获取每日数据明细

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            list: 每日数据列表
        """
        daily_data = []
        current_date = start_date.date()
        end_date_only = end_date.date()

        while current_date <= end_date_only:
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())

            # 查询当日统计
            query = select(
                func.coalesce(
                    func.sum(
                        case(
                            (TransactionRecord.transaction_type == "recharge", TransactionRecord.amount),
                            else_=0,
                        )
                    ),
                    0,
                ).label("recharge"),
                func.coalesce(
                    func.sum(
                        case(
                            (TransactionRecord.transaction_type == "consumption", TransactionRecord.amount),
                            else_=0,
                        )
                    ),
                    0,
                ).label("consumption"),
                func.coalesce(
                    func.sum(
                        case(
                            (TransactionRecord.transaction_type == "refund", TransactionRecord.amount),
                            else_=0,
                        )
                    ),
                    0,
                ).label("refund"),
            ).where(
                and_(
                    TransactionRecord.created_at >= day_start,
                    TransactionRecord.created_at <= day_end,
                )
            )

            result = await self.db.execute(query)
            row = result.first()

            recharge = float(row.recharge)
            consumption = float(row.consumption)
            refund = float(row.refund)
            net_income = recharge - refund

            daily_data.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "recharge": f"{recharge:.2f}",
                "consumption": f"{consumption:.2f}",
                "refund": f"{refund:.2f}",
                "net_income": f"{net_income:.2f}",
            })

            current_date += timedelta(days=1)

        return daily_data

    async def _get_top_customers(
        self, start_date: datetime, end_date: datetime, limit: int = 10
    ) -> list:
        """
        获取Top消费客户

        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量

        Returns:
            list: Top客户列表
        """
        query = (
            select(
                TransactionRecord.operator_id,
                func.sum(TransactionRecord.amount).label("total_consumption"),
                func.count(TransactionRecord.id).label("transaction_count"),
            )
            .where(
                and_(
                    TransactionRecord.transaction_type == "consumption",
                    TransactionRecord.created_at >= start_date,
                    TransactionRecord.created_at <= end_date,
                )
            )
            .group_by(TransactionRecord.operator_id)
            .order_by(func.sum(TransactionRecord.amount).desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        rows = result.all()

        top_customers = []
        for idx, row in enumerate(rows, 1):
            # 查询运营商信息
            operator_query = select(OperatorAccount).where(
                OperatorAccount.id == row.operator_id
            )
            operator_result = await self.db.execute(operator_query)
            operator = operator_result.scalar_one_or_none()

            if operator:
                top_customers.append({
                    "rank": idx,
                    "operator_id": str(row.operator_id),
                    "operator_name": operator.full_name,
                    "username": operator.username,
                    "total_consumption": f"{row.total_consumption:.2f}",
                    "transaction_count": row.transaction_count,
                })

        return top_customers

    async def get_report_by_id(self, report_id: str) -> FinanceReport:
        """
        根据报表ID查询报表

        Args:
            report_id: 报表ID

        Returns:
            FinanceReport: 报表记录

        Raises:
            NotFoundException: 报表不存在
        """
        query = select(FinanceReport).where(FinanceReport.report_id == report_id)
        result = await self.db.execute(query)
        report = result.scalar_one_or_none()

        if not report:
            raise NotFoundException(f"报表 {report_id} 不存在")

        return report

    async def get_reports_list(
        self, page: int = 1, page_size: int = 20, search: Optional[str] = None
    ) -> tuple[list[FinanceReport], int]:
        """
        获取报表列表（分页）

        Args:
            page: 页码
            page_size: 每页条数
            search: 搜索报表ID

        Returns:
            tuple: (报表列表, 总数)
        """
        # Build base query
        query = select(FinanceReport)
        count_query = select(func.count(FinanceReport.id))

        # Add search filter
        if search:
            from sqlalchemy import cast, String
            search_pattern = f"%{search}%"
            query = query.where(cast(FinanceReport.report_id, String).ilike(search_pattern))
            count_query = count_query.where(cast(FinanceReport.report_id, String).ilike(search_pattern))

        # 查询总数
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # 查询报表列表
        query = (
            query
            .order_by(FinanceReport.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        reports = result.scalars().all()

        return list(reports), total
