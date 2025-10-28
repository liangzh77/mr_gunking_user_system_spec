"""
契约测试: 审计日志功能 (T167 + Audit Logging)

测试目标:
- 验证退款和发票操作时审计日志被正确记录
- 确保审计日志包含完整的操作详情
- 测试审计日志查询API

契约要求:
- 批准/拒绝退款时,应该创建对应的审计日志
- 批准/拒绝发票时,应该创建对应的审计日志
- GET /finance/audit-logs 返回审计日志列表
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import select

from src.main import app
from src.models.finance import FinanceAccount, FinanceOperationLog
from src.models.operator import OperatorAccount
from src.models.refund import RefundRecord
from src.models.invoice import InvoiceRecord
from src.core.utils.password import hash_password


# ========== Fixtures ==========

@pytest.fixture
async def create_finance_account(test_db):
    """创建财务测试账户"""
    finance = FinanceAccount(
        id=uuid4(),
        username="finance_li",
        password_hash=hash_password("FinancePass123"),
        full_name="李财务",
        email="finance.li@test.com",
        phone="13900139001",
        role="specialist"
    )
    test_db.add(finance)
    await test_db.commit()
    await test_db.refresh(finance)
    return finance


@pytest.fixture
async def create_test_operator(test_db):
    """创建测试运营商"""
    operator = OperatorAccount(
        id=uuid4(),
        username="test_operator_audit",
        password_hash=hash_password("Pass123"),
        full_name="审计测试运营商",
        phone="13800138002",
        email="audit@example.com",
        api_key="audit_api_key_1234567890123456",
        api_key_hash=hash_password("audit_api_key_1234567890123456"),
        balance=Decimal("200.00"),
        customer_tier="standard"
    )
    test_db.add(operator)
    await test_db.commit()
    await test_db.refresh(operator)
    return operator


@pytest.fixture
async def create_pending_refund(test_db, create_test_operator):
    """创建待审核退款申请"""
    operator = create_test_operator

    refund = RefundRecord(
        id=uuid4(),
        operator_id=operator.id,
        requested_amount=Decimal("200.00"),
        refund_reason="测试审计日志功能",
        status="pending"
    )
    test_db.add(refund)
    await test_db.commit()
    await test_db.refresh(refund)
    return refund


@pytest.fixture
async def create_pending_invoice(test_db, create_test_operator):
    """创建待审核发票申请"""
    operator = create_test_operator

    invoice = InvoiceRecord(
        id=uuid4(),
        operator_id=operator.id,
        invoice_amount=Decimal("1000.00"),
        invoice_title="审计测试公司",
        tax_id="91110000MA001234XX",
        status="pending"
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)
    return invoice


# ========== 辅助函数 ==========

async def finance_login(client: AsyncClient) -> str:
    """财务人员登录,返回JWT Token"""
    response = await client.post(
        "/v1/auth/finance/login",
        json={
            "username": "finance_li",
            "password": "FinancePass123"
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return ""


# ========== 退款审计日志测试 ==========

@pytest.mark.asyncio
async def test_refund_approve_creates_audit_log(test_db, create_finance_account, create_pending_refund):
    """测试退款批准时创建审计日志"""
    refund = create_pending_refund
    finance = create_finance_account

    # 执行退款批准
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/refunds/{refund.id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={"note": "测试审计日志"}
        )

    assert response.status_code == 200

    # 验证审计日志是否被创建
    result = await test_db.execute(
        select(FinanceOperationLog)
        .where(FinanceOperationLog.finance_account_id == finance.id)
        .where(FinanceOperationLog.operation_type == "refund_approve")
        .where(FinanceOperationLog.target_resource_id == refund.id)
    )
    audit_log = result.scalar_one_or_none()

    assert audit_log is not None
    assert audit_log.operation_type == "refund_approve"
    assert audit_log.target_resource_type == "refund"
    assert audit_log.target_resource_id == refund.id
    assert audit_log.finance_account_id == finance.id

    # 验证operation_details内容
    details = audit_log.operation_details
    assert "operator_id" in details
    assert "operator_name" in details
    assert "refund_amount" in details
    assert "note" in details
    assert details["note"] == "测试审计日志"


@pytest.mark.asyncio
async def test_refund_reject_creates_audit_log(test_db, create_finance_account, create_pending_refund):
    """测试退款拒绝时创建审计日志"""
    refund = create_pending_refund
    finance = create_finance_account

    # 执行退款拒绝
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/refunds/{refund.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "退款原因不符合要求,请重新提交申请"}
        )

    assert response.status_code == 200

    # 验证审计日志是否被创建
    result = await test_db.execute(
        select(FinanceOperationLog)
        .where(FinanceOperationLog.finance_account_id == finance.id)
        .where(FinanceOperationLog.operation_type == "refund_reject")
        .where(FinanceOperationLog.target_resource_id == refund.id)
    )
    audit_log = result.scalar_one_or_none()

    assert audit_log is not None
    assert audit_log.operation_type == "refund_reject"
    assert audit_log.target_resource_type == "refund"
    assert audit_log.target_resource_id == refund.id

    # 验证operation_details内容
    details = audit_log.operation_details
    assert "operator_id" in details
    assert "operator_name" in details
    assert "refund_amount" in details
    assert "reject_reason" in details
    assert details["reject_reason"] == "退款原因不符合要求,请重新提交申请"


# ========== 发票审计日志测试 ==========

@pytest.mark.asyncio
async def test_invoice_approve_creates_audit_log(test_db, create_finance_account, create_pending_invoice):
    """测试发票批准时创建审计日志"""
    invoice = create_pending_invoice
    finance = create_finance_account

    # 执行发票批准
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{invoice.id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={"note": "发票审核通过"}
        )

    assert response.status_code == 200

    # 验证审计日志是否被创建
    result = await test_db.execute(
        select(FinanceOperationLog)
        .where(FinanceOperationLog.finance_account_id == finance.id)
        .where(FinanceOperationLog.operation_type == "invoice_approve")
        .where(FinanceOperationLog.target_resource_id == invoice.id)
    )
    audit_log = result.scalar_one_or_none()

    assert audit_log is not None
    assert audit_log.operation_type == "invoice_approve"
    assert audit_log.target_resource_type == "invoice"
    assert audit_log.target_resource_id == invoice.id

    # 验证operation_details内容
    details = audit_log.operation_details
    assert "operator_id" in details
    assert "operator_name" in details
    assert "invoice_amount" in details
    assert "invoice_number" in details
    assert "note" in details
    assert details["note"] == "发票审核通过"


@pytest.mark.asyncio
async def test_invoice_reject_creates_audit_log(test_db, create_finance_account, create_pending_invoice):
    """测试发票拒绝时创建审计日志"""
    invoice = create_pending_invoice
    finance = create_finance_account

    # 执行发票拒绝
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{invoice.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "税号格式不正确,请核对后重新提交"}
        )

    assert response.status_code == 200

    # 验证审计日志是否被创建
    result = await test_db.execute(
        select(FinanceOperationLog)
        .where(FinanceOperationLog.finance_account_id == finance.id)
        .where(FinanceOperationLog.operation_type == "invoice_reject")
        .where(FinanceOperationLog.target_resource_id == invoice.id)
    )
    audit_log = result.scalar_one_or_none()

    assert audit_log is not None
    assert audit_log.operation_type == "invoice_reject"
    assert audit_log.target_resource_type == "invoice"
    assert audit_log.target_resource_id == invoice.id

    # 验证operation_details内容
    details = audit_log.operation_details
    assert "operator_id" in details
    assert "operator_name" in details
    assert "invoice_amount" in details
    assert "reject_reason" in details
    assert details["reject_reason"] == "税号格式不正确,请核对后重新提交"


# ========== 审计日志查询API测试 ==========

@pytest.mark.asyncio
async def test_get_audit_logs_list(test_db, create_finance_account, create_pending_refund):
    """测试获取审计日志列表"""
    refund = create_pending_refund
    finance = create_finance_account

    # 先执行一个操作以创建审计日志
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        # 批准退款
        await client.post(
            f"/v1/finance/refunds/{refund.id}/approve",
            headers={"Authorization": f"Bearer {token}"}
        )

        # 查询审计日志列表
        response = await client.get(
            "/v1/finance/audit-logs",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证分页响应结构
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["items"], list)

    # 验证审计日志项结构
    if len(data["items"]) > 0:
        item = data["items"][0]
        assert "log_id" in item
        assert "finance_id" in item
        assert "finance_name" in item
        assert "operation_type" in item
        assert "operation_details" in item
        assert "created_at" in item


@pytest.mark.asyncio
async def test_get_audit_logs_with_operation_type_filter(test_db, create_finance_account, create_pending_refund):
    """测试按操作类型筛选审计日志"""
    refund = create_pending_refund
    finance = create_finance_account

    # 先执行退款批准操作
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        await client.post(
            f"/v1/finance/refunds/{refund.id}/approve",
            headers={"Authorization": f"Bearer {token}"}
        )

        # 查询特定类型的审计日志
        response = await client.get(
            "/v1/finance/audit-logs?operation_type=refund_approve",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证返回的日志都是指定类型
    for item in data["items"]:
        assert item["operation_type"] == "refund_approve"


@pytest.mark.asyncio
async def test_get_audit_logs_without_token(test_db):
    """测试未提供Token获取审计日志"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/finance/audit-logs")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_audit_log_records_finance_account_info(test_db, create_finance_account, create_pending_refund):
    """测试审计日志记录财务人员信息"""
    refund = create_pending_refund
    finance = create_finance_account

    # 执行退款批准
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        await client.post(
            f"/v1/finance/refunds/{refund.id}/approve",
            headers={"Authorization": f"Bearer {token}"}
        )

    # 查询审计日志并验证财务人员信息
    result = await test_db.execute(
        select(FinanceOperationLog)
        .where(FinanceOperationLog.finance_account_id == finance.id)
    )
    audit_log = result.scalar_one_or_none()

    assert audit_log is not None
    assert audit_log.finance_account_id == finance.id

    # 查询API验证返回的财务人员姓名
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/audit-logs",
            headers={"Authorization": f"Bearer {token}"}
        )

    data = response.json()
    if len(data["items"]) > 0:
        item = data["items"][0]
        assert item["finance_name"] == finance.full_name
