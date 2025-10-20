"""
契约测试: 财务发票审核API (T171)

测试目标:
- 验证财务发票审核API端点契约
- 确保请求/响应格式符合contract定义
- 覆盖发票列表、批准、拒绝场景

契约要求:
- GET /finance/invoices: 查询待审核发票列表
- POST /finance/invoices/{invoice_id}/approve: 批准发票
- POST /finance/invoices/{invoice_id}/reject: 拒绝发票
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from decimal import Decimal

from src.main import app
from src.models.finance import FinanceAccount
from src.models.operator import OperatorAccount
from src.models.invoice import InvoiceRecord
from src.core.utils.password import hash_password
from datetime import datetime


# ========== Fixtures ==========

@pytest.fixture
async def create_finance_account(test_db):
    """创建财务测试账户"""
    finance = FinanceAccount(
        id=uuid4(),
        username="finance_wang",
        password_hash=hash_password("FinancePass123"),
        full_name="王财务",
        email="finance.wang@test.com",
        phone="13900139002",
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
        username="test_operator_invoice",
        password_hash=hash_password("Pass123"),
        full_name="发票测试运营商",
        phone="13800138003",
        email="invoice@example.com",
        api_key="invoice_api_key_123456789012",
        api_key_hash=hash_password("invoice_api_key_123456789012"),
        balance=Decimal("0.00"),
        customer_tier="standard"
    )
    test_db.add(operator)
    await test_db.commit()
    await test_db.refresh(operator)
    return operator


@pytest.fixture
async def create_pending_invoice(test_db, create_test_operator):
    """创建待审核发票申请"""
    operator = create_test_operator

    invoice = InvoiceRecord(
        id=uuid4(),
        operator_id=operator.id,
        invoice_amount=Decimal("1000.00"),
        invoice_title="测试发票公司",
        tax_id="91110000MA00TEST01",
        status="pending"
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)
    return invoice


@pytest.fixture
async def create_approved_invoice(test_db, create_test_operator, create_finance_account):
    """创建已批准的发票申请"""
    operator = create_test_operator
    finance = create_finance_account

    invoice = InvoiceRecord(
        id=uuid4(),
        operator_id=operator.id,
        invoice_amount=Decimal("500.00"),
        invoice_title="已批准测试公司",
        tax_id="91110000MA00TEST02",
        status="approved",
        reviewed_by=finance.id,
        reviewed_at=datetime.now(),
        issued_at=datetime.now(),
        invoice_number="INV-20251020-12345"
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
            "username": "finance_wang",
            "password": "FinancePass123"
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return ""


# ========== GET /finance/invoices 测试 ==========

@pytest.mark.asyncio
async def test_get_invoices_list_default(test_db, create_finance_account, create_pending_invoice):
    """测试获取发票列表(默认状态=pending)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/invoices",
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


@pytest.mark.asyncio
async def test_get_invoices_list_with_status_filter(test_db, create_finance_account, create_approved_invoice):
    """测试按状态筛选发票列表"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/invoices?status=approved",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data

    # 验证返回的记录都是approved状态
    for item in data["items"]:
        assert item["status"] == "approved"


@pytest.mark.asyncio
async def test_get_invoices_list_with_pagination(test_db, create_finance_account, create_pending_invoice):
    """测试分页参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/invoices?page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["items"]) <= 10


@pytest.mark.asyncio
async def test_get_invoices_list_all_status(test_db, create_finance_account, create_pending_invoice):
    """测试查询所有状态的发票"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/invoices?status=all",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_invoices_list_without_token(test_db):
    """测试未提供Token获取发票列表"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/finance/invoices")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_invoices_list_invalid_status(test_db, create_finance_account):
    """测试无效的status参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/invoices?status=invalid_status",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code in [400, 422]


# ========== POST /finance/invoices/{invoice_id}/approve 测试 ==========

@pytest.mark.asyncio
async def test_approve_invoice_success(test_db, create_finance_account, create_pending_invoice):
    """测试批准发票"""
    invoice = create_pending_invoice

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{invoice.id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "note": "发票信息核实无误"
            }
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert "invoice_id" in data
    assert "pdf_url" in data


@pytest.mark.asyncio
async def test_approve_invoice_without_note(test_db, create_finance_account, create_pending_invoice):
    """测试批准发票(无备注)"""
    invoice = create_pending_invoice

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{invoice.id}/approve",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_approve_invoice_already_approved(test_db, create_finance_account, create_approved_invoice):
    """测试重复批准发票"""
    invoice = create_approved_invoice

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{invoice.id}/approve",
            headers={"Authorization": f"Bearer {token}"}
        )

    # 应该返回错误,已处理的申请不能重复操作
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_approve_invoice_nonexistent(test_db, create_finance_account):
    """测试批准不存在的发票"""
    fake_id = uuid4()

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{fake_id}/approve",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_approve_invoice_without_token(test_db, create_pending_invoice):
    """测试未提供Token批准发票"""
    invoice = create_pending_invoice

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(f"/v1/finance/invoices/{invoice.id}/approve")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_approve_invoice_invalid_id_format(test_db, create_finance_account):
    """测试无效的invoice_id格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            "/v1/finance/invoices/invalid_id/approve",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code in [400, 422]


# ========== POST /finance/invoices/{invoice_id}/reject 测试 ==========

@pytest.mark.asyncio
async def test_reject_invoice_success(test_db, create_finance_account, create_pending_invoice):
    """测试拒绝发票"""
    invoice = create_pending_invoice

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{invoice.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "税号格式不正确,请核对后重新提交"
            }
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_reject_invoice_missing_reason(test_db, create_finance_account, create_pending_invoice):
    """测试拒绝发票缺少原因"""
    invoice = create_pending_invoice

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{invoice.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={}
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_reject_invoice_short_reason(test_db, create_finance_account, create_pending_invoice):
    """测试拒绝发票原因太短"""
    invoice = create_pending_invoice

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{invoice.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "太短"  # 少于10个字符
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_reject_invoice_long_reason(test_db, create_finance_account, create_pending_invoice):
    """测试拒绝发票原因太长"""
    invoice = create_pending_invoice

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{invoice.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "x" * 300  # 超过200字符
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_reject_invoice_already_rejected(test_db, create_finance_account, create_test_operator):
    """测试重复拒绝发票"""
    operator = create_test_operator

    # 创建已拒绝的发票
    invoice = InvoiceRecord(
        id=uuid4(),
        operator_id=operator.id,
        invoice_amount=Decimal("1000.00"),
        invoice_title="已拒绝测试公司",
        tax_id="91110000MA00TEST03",
        status="rejected",
        reject_reason="已拒绝",
        reviewed_by=uuid4(),
        reviewed_at=datetime.now()
    )
    test_db.add(invoice)
    await test_db.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{invoice.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "重复拒绝原因"
            }
        )

    # 应该返回错误,已处理的申请不能重复操作
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reject_invoice_nonexistent(test_db, create_finance_account):
    """测试拒绝不存在的发票"""
    fake_id = uuid4()

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{fake_id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "拒绝原因"
            }
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reject_invoice_without_token(test_db, create_pending_invoice):
    """测试未提供Token拒绝发票"""
    invoice = create_pending_invoice

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            f"/v1/finance/invoices/{invoice.id}/reject",
            json={
                "reason": "拒绝原因"
            }
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_reject_invoice_invalid_id_format(test_db, create_finance_account):
    """测试无效的invoice_id格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            "/v1/finance/invoices/invalid_id/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "拒绝原因超过十个字符"
            }
        )

    assert response.status_code in [400, 422]


# ========== 响应格式验证测试 ==========

@pytest.mark.asyncio
async def test_invoice_list_response_format(test_db, create_finance_account, create_pending_invoice):
    """测试发票列表响应格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/invoices",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证分页字段
    assert "page" in data
    assert "page_size" in data
    assert "total" in data
    assert "items" in data

    # 验证发票项字段
    if len(data["items"]) > 0:
        item = data["items"][0]
        assert "invoice_id" in item
        assert "operator_id" in item
        assert "operator_name" in item
        assert "amount" in item
        assert "invoice_title" in item
        assert "tax_id" in item
        assert "status" in item
        assert "created_at" in item


@pytest.mark.asyncio
async def test_approve_invoice_response_format(test_db, create_finance_account, create_pending_invoice):
    """测试批准发票响应格式"""
    invoice = create_pending_invoice

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{invoice.id}/approve",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    assert "invoice_id" in data
    assert "pdf_url" in data
    assert isinstance(data["invoice_id"], str)
    assert isinstance(data["pdf_url"], str)
