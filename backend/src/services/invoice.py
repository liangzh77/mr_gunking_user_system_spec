"""发票服务 (InvoiceService) - T065

此服务提供发票管理的核心业务逻辑:
1. 发票申请创建 - 运营商提交开票申请
2. 电子发票生成 - 财务审核通过后生成PDF
3. 发票审核 - 财务人员审核发票申请

业务规则:
- 开票金额不能超过已充值金额
- 税号格式验证(15-20位字母数字)
- 发票状态: pending(待审核) -> approved(已通过)/rejected(已拒绝)
- 审核通过后自动生成电子发票PDF
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID
import os

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.operator import OperatorAccount
from ..models.invoice import InvoiceRecord
from ..models.transaction import TransactionRecord


class InvoiceService:
    """发票服务类

    提供发票申请、审核、PDF生成功能
    """

    def __init__(self, db: AsyncSession):
        """初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def create_invoice_request(
        self,
        operator_id: UUID,
        amount: Decimal,
        invoice_title: str,
        tax_id: str,
        email: Optional[str] = None
    ) -> InvoiceRecord:
        """创建发票申请 (T076辅助)

        业务规则:
        - 开票金额不能超过已充值金额(total_recharged)
        - 税号格式已由schema验证(15-20位字母数字)
        - 发票状态初始为pending(待财务审核)
        - email可选,默认使用账户邮箱

        Args:
            operator_id: 运营商ID
            amount: 开票金额
            invoice_title: 发票抬头
            tax_id: 纳税人识别号
            email: 接收邮箱(可选)

        Returns:
            InvoiceRecord: 新创建的发票申请记录

        Raises:
            HTTPException 400: 开票金额超过已充值金额
            HTTPException 404: 运营商不存在
        """
        # 1. 验证运营商存在
        operator_stmt = select(OperatorAccount).where(
            OperatorAccount.id == operator_id,
            OperatorAccount.deleted_at.is_(None)
        )
        operator_result = await self.db.execute(operator_stmt)
        operator = operator_result.scalar_one_or_none()

        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "OPERATOR_NOT_FOUND",
                    "message": "运营商不存在"
                }
            )

        # 2. 计算已充值总额(sum所有recharge类型交易)
        recharge_sum_stmt = select(
            func.sum(TransactionRecord.amount)
        ).where(
            TransactionRecord.operator_id == operator_id,
            TransactionRecord.transaction_type == "recharge"
        )
        recharge_result = await self.db.execute(recharge_sum_stmt)
        total_recharged = recharge_result.scalar() or Decimal("0.00")

        # 3. 验证开票金额不超过已充值金额
        if amount > total_recharged:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_PARAMS",
                    "message": f"开票金额({amount}元)不能超过已充值金额({total_recharged}元)"
                }
            )

        # 4. 设置email(如果未提供则使用账户邮箱)
        final_email = email if email else operator.email

        # 5. 创建发票申请记录
        invoice = InvoiceRecord(
            operator_id=operator_id,
            amount=amount,
            invoice_title=invoice_title,
            tax_id=tax_id.upper(),  # 统一为大写
            email=final_email,
            status="pending"  # 初始状态为待审核
        )

        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)

        return invoice

    async def approve_invoice(
        self,
        invoice_id: UUID,
        approved_by: UUID
    ) -> InvoiceRecord:
        """审核通过发票申请并生成PDF

        业务流程:
        1. 查询发票申请并验证状态(必须是pending)
        2. 更新发票记录状态为approved
        3. 生成电子发票PDF
        4. 更新pdf_url字段

        Args:
            invoice_id: 发票申请ID
            approved_by: 审核人ID(财务人员)

        Returns:
            InvoiceRecord: 更新后的发票记录(包含pdf_url)

        Raises:
            HTTPException 400: 发票申请状态不正确
            HTTPException 404: 发票申请不存在
            HTTPException 500: PDF生成失败
        """
        # 1. 查询发票申请
        invoice_stmt = select(InvoiceRecord).where(
            InvoiceRecord.id == invoice_id
        )
        invoice_result = await self.db.execute(invoice_stmt)
        invoice = invoice_result.scalar_one_or_none()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "INVOICE_NOT_FOUND",
                    "message": "发票申请不存在"
                }
            )

        # 2. 验证发票状态必须是pending
        if invoice.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_INVOICE_STATUS",
                    "message": f"发票申请状态不正确,当前状态: {invoice.status}"
                }
            )

        # 3. 生成电子发票PDF
        try:
            pdf_url = await self._generate_invoice_pdf(invoice)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "PDF_GENERATION_FAILED",
                    "message": f"生成电子发票失败: {str(e)}"
                }
            )

        # 4. 更新发票记录
        invoice.status = "approved"
        invoice.pdf_url = pdf_url
        invoice.reviewed_by = approved_by
        invoice.reviewed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(invoice)

        return invoice

    async def reject_invoice(
        self,
        invoice_id: UUID,
        reviewed_by: UUID,
        reject_reason: str
    ) -> InvoiceRecord:
        """拒绝发票申请

        Args:
            invoice_id: 发票申请ID
            reviewed_by: 审核人ID(财务人员)
            reject_reason: 拒绝原因

        Returns:
            InvoiceRecord: 更新后的发票记录

        Raises:
            HTTPException 400: 发票申请状态不正确
            HTTPException 404: 发票申请不存在
        """
        # 1. 查询发票申请
        invoice_stmt = select(InvoiceRecord).where(
            InvoiceRecord.id == invoice_id
        )
        invoice_result = await self.db.execute(invoice_stmt)
        invoice = invoice_result.scalar_one_or_none()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "INVOICE_NOT_FOUND",
                    "message": "发票申请不存在"
                }
            )

        # 2. 验证发票状态必须是pending
        if invoice.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_INVOICE_STATUS",
                    "message": f"发票申请状态不正确,当前状态: {invoice.status}"
                }
            )

        # 3. 更新发票记录状态为rejected
        invoice.status = "rejected"
        invoice.reject_reason = reject_reason
        invoice.reviewed_by = reviewed_by
        invoice.reviewed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(invoice)

        return invoice

    async def _generate_invoice_pdf(
        self,
        invoice: InvoiceRecord
    ) -> str:
        """生成电子发票PDF

        使用ReportLab库生成标准格式的电子发票PDF。
        实际生产环境应调用第三方电子发票平台API。

        Args:
            invoice: 发票记录对象

        Returns:
            str: PDF文件的URL路径

        Raises:
            Exception: PDF生成失败
        """
        # TODO: 集成真实电子发票平台API或使用ReportLab生成PDF
        # from reportlab.lib.pagesizes import A4
        # from reportlab.pdfgen import canvas
        # from reportlab.lib.units import cm

        # 模拟生成PDF文件
        # 实际环境应:
        # 1. 使用ReportLab/PyPDF2生成标准格式发票
        # 2. 或调用第三方电子发票平台API(如百旺金赋、航天信息)
        # 3. 保存到文件系统或对象存储(OSS)

        # 模拟文件路径
        invoice_filename = f"invoice_{invoice.id}.pdf"
        pdf_path = f"/invoices/{invoice_filename}"

        # 模拟PDF文件URL
        # 实际环境应返回可访问的HTTP URL
        pdf_url = f"https://storage.example.com{pdf_path}"

        # 示例: 使用ReportLab生成PDF的伪代码
        """
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm

        # 创建PDF文件
        pdf_file_path = f"backend/invoices/{invoice_filename}"
        c = canvas.Canvas(pdf_file_path, pagesize=A4)

        # 添加发票标题
        c.setFont("Helvetica-Bold", 20)
        c.drawString(10*cm, 28*cm, "电子发票")

        # 添加发票信息
        c.setFont("Helvetica", 12)
        c.drawString(2*cm, 25*cm, f"发票抬头: {invoice.invoice_title}")
        c.drawString(2*cm, 24*cm, f"纳税人识别号: {invoice.tax_id}")
        c.drawString(2*cm, 23*cm, f"开票金额: {invoice.amount}元")
        c.drawString(2*cm, 22*cm, f"开票日期: {invoice.reviewed_at.strftime('%Y-%m-%d')}")

        # 保存PDF
        c.save()

        # 返回可访问的URL
        pdf_url = f"https://yourdomain.com/api/v1/invoices/{invoice.id}/download"
        """

        return pdf_url

    async def get_invoice_pdf_content(
        self,
        invoice_id: UUID
    ) -> tuple[bytes, str]:
        """获取发票PDF文件内容

        用于提供发票下载功能

        Args:
            invoice_id: 发票ID

        Returns:
            tuple[bytes, str]: (PDF文件内容, 文件名)

        Raises:
            HTTPException 404: 发票不存在或未生成PDF
            HTTPException 500: 读取文件失败
        """
        # 1. 查询发票记录
        invoice_stmt = select(InvoiceRecord).where(
            InvoiceRecord.id == invoice_id
        )
        invoice_result = await self.db.execute(invoice_stmt)
        invoice = invoice_result.scalar_one_or_none()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "INVOICE_NOT_FOUND",
                    "message": "发票不存在"
                }
            )

        # 2. 验证PDF已生成
        if not invoice.pdf_url or invoice.status != "approved":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "PDF_NOT_AVAILABLE",
                    "message": "发票PDF尚未生成或未审核通过"
                }
            )

        # 3. 读取PDF文件内容
        # TODO: 实际环境从文件系统或OSS读取
        # pdf_file_path = f"backend/invoices/invoice_{invoice.id}.pdf"
        # with open(pdf_file_path, 'rb') as f:
        #     pdf_content = f.read()

        # 模拟返回空PDF内容
        pdf_content = b"%PDF-1.4\n%Fake PDF content for testing"
        filename = f"invoice_{invoice.id}.pdf"

        return pdf_content, filename
