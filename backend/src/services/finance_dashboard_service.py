"""Finance dashboard service (T169).

This service handles dashboard data aggregation and statistics for finance staff.
"""

from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import Optional, List
from uuid import UUID as PyUUID

from sqlalchemy import select, and_, func, case, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import NotFoundException, BadRequestException
from ..models.operator import OperatorAccount
from ..models.transaction import TransactionRecord
from ..models.usage_record import UsageRecord
from ..schemas.finance import (
    DashboardOverview,
    DashboardTrends,
    DailyTrendItem,
    TrendsSummary,
    TopCustomersResponse,
    TopCustomer,
    CustomerFinanceDetails
)


class FinanceDashboardService:
    """Finance dashboard data aggregation service."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_dashboard_overview(self) -> DashboardOverview:
        """Get today's income overview.

        Returns:
            DashboardOverview: Today's financial summary
        """
        # Get today's date range (UTC)
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        # Calculate today's recharge
        recharge_result = await self.db.execute(
            select(func.sum(TransactionRecord.amount)).where(
                and_(
                    TransactionRecord.transaction_type == "recharge",
                    TransactionRecord.created_at >= today_start,
                    TransactionRecord.created_at < today_end
                )
            )
        )
        today_recharge = recharge_result.scalar() or Decimal("0.00")

        # Calculate today's consumption (use abs to get positive value)
        consumption_result = await self.db.execute(
            select(func.sum(func.abs(TransactionRecord.amount))).where(
                and_(
                    TransactionRecord.transaction_type == "consumption",
                    TransactionRecord.created_at >= today_start,
                    TransactionRecord.created_at < today_end
                )
            )
        )
        today_consumption = consumption_result.scalar() or Decimal("0.00")

        # Calculate today's refund
        refund_result = await self.db.execute(
            select(func.sum(TransactionRecord.amount)).where(
                and_(
                    TransactionRecord.transaction_type == "refund",
                    TransactionRecord.created_at >= today_start,
                    TransactionRecord.created_at < today_end
                )
            )
        )
        today_refund = refund_result.scalar() or Decimal("0.00")

        # Calculate net income (recharge - refund)
        today_net_income = today_recharge - today_refund

        # Get total operators count (active, not deleted)
        total_operators_result = await self.db.execute(
            select(func.count()).select_from(OperatorAccount).where(
                and_(
                    OperatorAccount.deleted_at.is_(None),
                    OperatorAccount.is_active == True
                )
            )
        )
        total_operators = total_operators_result.scalar()

        # Get active operators today (operators with transactions today)
        active_operators_result = await self.db.execute(
            select(func.count(func.distinct(TransactionRecord.operator_id))).where(
                and_(
                    TransactionRecord.created_at >= today_start,
                    TransactionRecord.created_at < today_end
                )
            )
        )
        active_operators_today = active_operators_result.scalar() or 0

        return DashboardOverview(
            today_recharge=str(today_recharge),
            today_consumption=str(today_consumption),
            today_refund=str(today_refund),
            today_net_income=str(today_net_income),
            total_operators=total_operators,
            active_operators_today=active_operators_today
        )

    async def get_dashboard_trends(
        self,
        month: Optional[str] = None
    ) -> DashboardTrends:
        """Get monthly income trends.

        Args:
            month: Month in YYYY-MM format (default: current month)

        Returns:
            DashboardTrends: Monthly trends data with daily breakdown

        Raises:
            BadRequestException: If month format is invalid
        """
        # Parse month or use current month
        if month:
            try:
                year, month_num = month.split('-')
                target_date = date(int(year), int(month_num), 1)
            except (ValueError, IndexError):
                raise BadRequestException("Invalid month format. Use YYYY-MM format")
        else:
            now = datetime.now(timezone.utc)
            target_date = date(now.year, now.month, 1)
            month = target_date.strftime("%Y-%m")

        # Calculate month range
        month_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        # Get next month's first day
        if target_date.month == 12:
            next_month = date(target_date.year + 1, 1, 1)
        else:
            next_month = date(target_date.year, target_date.month + 1, 1)
        month_end = datetime.combine(next_month, datetime.min.time()).replace(tzinfo=timezone.utc)

        # Get daily aggregated data
        # Group by date and transaction type
        from sqlalchemy import Date, cast

        daily_query = (
            select(
                cast(TransactionRecord.created_at, Date).label('tx_date'),
                TransactionRecord.transaction_type,
                func.sum(TransactionRecord.amount).label('total_amount')
            )
            .where(
                and_(
                    TransactionRecord.created_at >= month_start,
                    TransactionRecord.created_at < month_end
                )
            )
            .group_by('tx_date', TransactionRecord.transaction_type)
        )

        daily_result = await self.db.execute(daily_query)
        daily_data = daily_result.all()

        # Build daily trend items
        daily_map = {}
        for row in daily_data:
            tx_date = row.tx_date
            tx_type = row.transaction_type
            amount = row.total_amount or Decimal("0.00")

            if tx_date not in daily_map:
                daily_map[tx_date] = {
                    "recharge": Decimal("0.00"),
                    "consumption": Decimal("0.00"),
                    "refund": Decimal("0.00")
                }

            daily_map[tx_date][tx_type] = amount

        # Generate chart data for all days in month
        chart_data = []
        current_date = target_date
        while current_date < next_month:
            day_data = daily_map.get(current_date, {
                "recharge": Decimal("0.00"),
                "consumption": Decimal("0.00"),
                "refund": Decimal("0.00")
            })

            recharge = day_data.get("recharge", Decimal("0.00"))
            consumption = day_data.get("consumption", Decimal("0.00"))
            refund = day_data.get("refund", Decimal("0.00"))
            net_income = recharge - refund

            chart_data.append(DailyTrendItem(
                date=current_date,  # 使用alias字段名
                recharge=str(recharge),
                consumption=str(consumption),
                refund=str(refund),
                net_income=str(net_income)
            ))

            current_date += timedelta(days=1)

        # Calculate monthly summary
        total_recharge = sum(Decimal(item.recharge) for item in chart_data)
        total_consumption = sum(Decimal(item.consumption) for item in chart_data)
        total_refund = sum(Decimal(item.refund) for item in chart_data)
        total_net_income = total_recharge - total_refund

        summary = TrendsSummary(
            total_recharge=str(total_recharge),
            total_consumption=str(total_consumption),
            total_refund=str(total_refund),
            total_net_income=str(total_net_income)
        )

        return DashboardTrends(
            month=month,
            chart_data=chart_data,
            summary=summary
        )

    async def get_top_customers(
        self,
        limit: int = 10,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> TopCustomersResponse:
        """Get top customers by consumption.

        Args:
            limit: Number of top customers to return (1-100)
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            TopCustomersResponse: Top customers list with statistics

        Raises:
            BadRequestException: If limit is invalid
        """
        # Validate limit
        if limit < 1 or limit > 100:
            raise BadRequestException("Limit must be between 1 and 100")

        # Build query for total consumption by operator (use abs to get positive values)
        consumption_query = (
            select(
                TransactionRecord.operator_id,
                func.sum(func.abs(TransactionRecord.amount)).label('total_consumption'),
                func.count(func.distinct(TransactionRecord.related_usage_id)).label('total_sessions')
            )
            .where(TransactionRecord.transaction_type == "consumption")
        )

        # Add time filters
        if start_time:
            consumption_query = consumption_query.where(TransactionRecord.created_at >= start_time)
        if end_time:
            consumption_query = consumption_query.where(TransactionRecord.created_at <= end_time)

        consumption_query = (
            consumption_query
            .group_by(TransactionRecord.operator_id)
            .order_by(desc('total_consumption'))
            .limit(limit)
        )

        consumption_result = await self.db.execute(consumption_query)
        consumption_data = consumption_result.all()

        # Calculate total consumption across all customers (use abs to get positive value)
        total_consumption_query = select(func.sum(func.abs(TransactionRecord.amount))).where(
            TransactionRecord.transaction_type == "consumption"
        )
        if start_time:
            total_consumption_query = total_consumption_query.where(TransactionRecord.created_at >= start_time)
        if end_time:
            total_consumption_query = total_consumption_query.where(TransactionRecord.created_at <= end_time)

        total_result = await self.db.execute(total_consumption_query)
        total_consumption = total_result.scalar() or Decimal("0.00")

        # Batch load operator details to avoid N+1 queries
        operator_ids = [row.operator_id for row in consumption_data]
        operators_result = await self.db.execute(
            select(OperatorAccount).where(OperatorAccount.id.in_(operator_ids))
        )
        operators_map = {op.id: op for op in operators_result.scalars().all()}

        # Build customer list with operator details
        customers = []
        for rank, row in enumerate(consumption_data, start=1):
            operator_id = row.operator_id
            customer_consumption = row.total_consumption or Decimal("0.00")
            total_sessions = row.total_sessions or 0

            # Get operator from batch-loaded map
            operator = operators_map.get(operator_id)

            if operator:
                consumption_percentage = float((customer_consumption / total_consumption * 100)) if total_consumption > 0 else 0.0

                customers.append(TopCustomer(
                    rank=rank,
                    operator_id=str(operator.id),
                    operator_name=operator.full_name,
                    category=operator.customer_tier,
                    total_consumption=str(customer_consumption),
                    consumption_percentage=round(consumption_percentage, 2),
                    total_sessions=total_sessions
                ))

        return TopCustomersResponse(
            customers=customers,
            total_consumption=str(total_consumption)
        )

    async def get_customer_finance_details(
        self,
        operator_id: str
    ) -> CustomerFinanceDetails:
        """Get detailed finance information for a specific customer.

        Args:
            operator_id: Operator ID

        Returns:
            CustomerFinanceDetails: Detailed finance information

        Raises:
            NotFoundException: If operator not found
            BadRequestException: If operator ID format invalid
        """
        # Convert to UUID
        try:
            operator_uuid = PyUUID(operator_id)
        except ValueError:
            raise BadRequestException("Invalid operator ID format")

        # Find operator
        result = await self.db.execute(
            select(OperatorAccount).where(OperatorAccount.id == operator_uuid)
        )
        operator = result.scalar_one_or_none()

        if not operator:
            raise NotFoundException("Operator not found")

        # Calculate total recharged
        recharge_result = await self.db.execute(
            select(func.sum(TransactionRecord.amount)).where(
                and_(
                    TransactionRecord.operator_id == operator_uuid,
                    TransactionRecord.transaction_type == "recharge"
                )
            )
        )
        total_recharged = recharge_result.scalar() or Decimal("0.00")

        # Calculate total consumed
        consumption_result = await self.db.execute(
            select(func.sum(TransactionRecord.amount)).where(
                and_(
                    TransactionRecord.operator_id == operator_uuid,
                    TransactionRecord.transaction_type == "consumption"
                )
            )
        )
        total_consumed = consumption_result.scalar() or Decimal("0.00")

        # Calculate total refunded
        refund_result = await self.db.execute(
            select(func.sum(TransactionRecord.amount)).where(
                and_(
                    TransactionRecord.operator_id == operator_uuid,
                    TransactionRecord.transaction_type == "refund"
                )
            )
        )
        total_refunded = refund_result.scalar() or Decimal("0.00")

        # Get total sessions count
        # TODO: Implement when usage records model is available
        total_sessions = 0

        # Get first transaction time
        first_tx_result = await self.db.execute(
            select(TransactionRecord.created_at)
            .where(TransactionRecord.operator_id == operator_uuid)
            .order_by(TransactionRecord.created_at.asc())
            .limit(1)
        )
        first_transaction_at = first_tx_result.scalar()

        # Get last transaction time
        last_tx_result = await self.db.execute(
            select(TransactionRecord.created_at)
            .where(TransactionRecord.operator_id == operator_uuid)
            .order_by(TransactionRecord.created_at.desc())
            .limit(1)
        )
        last_transaction_at = last_tx_result.scalar()

        return CustomerFinanceDetails(
            operator_id=str(operator.id),
            operator_name=operator.full_name,
            category=operator.customer_tier,
            current_balance=str(operator.balance),
            total_recharged=str(total_recharged),
            total_consumed=str(total_consumed),
            total_refunded=str(total_refunded),
            total_sessions=total_sessions,
            first_transaction_at=first_transaction_at or datetime.now(timezone.utc),
            last_transaction_at=last_transaction_at
        )
