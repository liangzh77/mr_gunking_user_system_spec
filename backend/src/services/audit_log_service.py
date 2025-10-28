"""审计日志服务

此服务负责记录财务人员的所有关键操作
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID as PyUUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.finance import FinanceOperationLog


class AuditLogService:
    """审计日志服务类"""

    def __init__(self, db: AsyncSession):
        """初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def log_operation(
        self,
        finance_id: PyUUID,
        operation_type: str,
        target_resource_type: Optional[str] = None,
        target_resource_id: Optional[PyUUID] = None,
        operation_details: Optional[Dict[str, Any]] = None,
        ip_address: str = "0.0.0.0",
        user_agent: Optional[str] = None,
    ) -> FinanceOperationLog:
        """记录财务操作日志

        Args:
            finance_id: 财务人员ID
            operation_type: 操作类型
            target_resource_type: 目标资源类型 (refund/invoice/report等)
            target_resource_id: 目标资源ID
            operation_details: 操作详情(JSON)
            ip_address: 操作IP地址
            user_agent: 用户代理字符串

        Returns:
            FinanceOperationLog: 创建的日志记录
        """
        log = FinanceOperationLog(
            finance_account_id=finance_id,
            operation_type=operation_type,
            target_resource_type=target_resource_type,
            target_resource_id=target_resource_id,
            operation_details=operation_details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.now(timezone.utc),
        )

        self.db.add(log)
        await self.db.flush()  # 刷新以获取ID，但不提交事务

        return log

    async def log_refund_approve(
        self,
        finance_id: PyUUID,
        refund_id: PyUUID,
        operator_id: PyUUID,
        operator_name: str,
        refund_amount: str,
        note: Optional[str] = None,
        ip_address: str = "0.0.0.0",
        user_agent: Optional[str] = None,
    ) -> FinanceOperationLog:
        """记录退款批准操作

        Args:
            finance_id: 财务人员ID
            refund_id: 退款ID
            operator_id: 运营商ID
            operator_name: 运营商名称
            refund_amount: 退款金额
            note: 审核备注
            ip_address: 操作IP
            user_agent: 用户代理

        Returns:
            FinanceOperationLog: 日志记录
        """
        return await self.log_operation(
            finance_id=finance_id,
            operation_type="refund_approve",
            target_resource_type="refund",
            target_resource_id=refund_id,
            operation_details={
                "operator_id": str(operator_id),
                "operator_name": operator_name,
                "refund_amount": refund_amount,
                "note": note,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_refund_reject(
        self,
        finance_id: PyUUID,
        refund_id: PyUUID,
        operator_id: PyUUID,
        operator_name: str,
        refund_amount: str,
        reject_reason: str,
        ip_address: str = "0.0.0.0",
        user_agent: Optional[str] = None,
    ) -> FinanceOperationLog:
        """记录退款拒绝操作

        Args:
            finance_id: 财务人员ID
            refund_id: 退款ID
            operator_id: 运营商ID
            operator_name: 运营商名称
            refund_amount: 退款金额
            reject_reason: 拒绝原因
            ip_address: 操作IP
            user_agent: 用户代理

        Returns:
            FinanceOperationLog: 日志记录
        """
        return await self.log_operation(
            finance_id=finance_id,
            operation_type="refund_reject",
            target_resource_type="refund",
            target_resource_id=refund_id,
            operation_details={
                "operator_id": str(operator_id),
                "operator_name": operator_name,
                "refund_amount": refund_amount,
                "reject_reason": reject_reason,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_invoice_approve(
        self,
        finance_id: PyUUID,
        invoice_id: PyUUID,
        operator_id: PyUUID,
        operator_name: str,
        invoice_amount: str,
        invoice_number: str,
        note: Optional[str] = None,
        ip_address: str = "0.0.0.0",
        user_agent: Optional[str] = None,
    ) -> FinanceOperationLog:
        """记录发票批准操作

        Args:
            finance_id: 财务人员ID
            invoice_id: 发票ID
            operator_id: 运营商ID
            operator_name: 运营商名称
            invoice_amount: 发票金额
            invoice_number: 发票号
            note: 审核备注
            ip_address: 操作IP
            user_agent: 用户代理

        Returns:
            FinanceOperationLog: 日志记录
        """
        return await self.log_operation(
            finance_id=finance_id,
            operation_type="invoice_approve",
            target_resource_type="invoice",
            target_resource_id=invoice_id,
            operation_details={
                "operator_id": str(operator_id),
                "operator_name": operator_name,
                "invoice_amount": invoice_amount,
                "invoice_number": invoice_number,
                "note": note,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_invoice_reject(
        self,
        finance_id: PyUUID,
        invoice_id: PyUUID,
        operator_id: PyUUID,
        operator_name: str,
        invoice_amount: str,
        reject_reason: str,
        ip_address: str = "0.0.0.0",
        user_agent: Optional[str] = None,
    ) -> FinanceOperationLog:
        """记录发票拒绝操作

        Args:
            finance_id: 财务人员ID
            invoice_id: 发票ID
            operator_id: 运营商ID
            operator_name: 运营商名称
            invoice_amount: 发票金额
            reject_reason: 拒绝原因
            ip_address: 操作IP
            user_agent: 用户代理

        Returns:
            FinanceOperationLog: 日志记录
        """
        return await self.log_operation(
            finance_id=finance_id,
            operation_type="invoice_reject",
            target_resource_type="invoice",
            target_resource_id=invoice_id,
            operation_details={
                "operator_id": str(operator_id),
                "operator_name": operator_name,
                "invoice_amount": invoice_amount,
                "reject_reason": reject_reason,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
