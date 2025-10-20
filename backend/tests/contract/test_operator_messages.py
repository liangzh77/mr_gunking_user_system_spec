"""
契约测试: 运营商消息通知功能

测试目标:
- 验证退款/发票审核后自动创建消息通知
- 测试运营商消息查询API
- 测试消息标记为已读功能
- 测试消息删除功能

契约要求:
- 批准/拒绝退款时,应该创建对应的消息通知
- 批准/拒绝发票时,应该创建对应的消息通知
- GET /messages 返回消息列表
- GET /messages/unread-count 返回未读消息数量
- POST /messages/{id}/read 标记消息为已读
- POST /messages/read-all 标记所有消息为已读
- DELETE /messages/{id} 删除消息
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import select

from src.main import app
from src.models.finance import FinanceAccount
from src.models.operator import OperatorAccount
from src.models.refund import RefundRecord
from src.models.invoice import InvoiceRecord
from src.models.message import OperatorMessage
from src.core.utils.password import hash_password


# ========== Fixtures ==========

@pytest.fixture
async def create_finance_account(test_db):
    """创建财务测试账户"""
    finance = FinanceAccount(
        id=uuid4(),
        username="finance_msg_test",
        password_hash=hash_password("FinancePass123"),
        full_name="消息测试财务",
        email="finance.msg@test.com",
        phone="13900139003",
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
        username="test_operator_msg",
        password_hash=hash_password("Pass123"),
        full_name="消息测试运营商",
        phone="13800138003",
        email="msg@example.com",
        api_key="msg_api_key_12345678901234567890",
        api_key_hash=hash_password("msg_api_key_12345678901234567890"),
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
        refund_reason="测试消息通知功能",
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
        invoice_type="vat_normal",
        invoice_amount=Decimal("1000.00"),
        invoice_title="消息测试公司",
        tax_id="91110000MA001235XX",
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
            "username": "finance_msg_test",
            "password": "FinancePass123"
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return ""


async def operator_login(client: AsyncClient) -> str:
    """运营商登录,返回JWT Token"""
    response = await client.post(
        "/v1/auth/operators/login",
        json={
            "username": "test_operator_msg",
            "password": "Pass123"
        }
    )
    if response.status_code == 200:
        return response.json()["data"]["access_token"]
    return ""


# ========== 退款审核消息通知测试 ==========

@pytest.mark.asyncio
async def test_refund_approve_creates_message(test_db, create_finance_account, create_pending_refund):
    """测试退款批准时创建消息通知"""
    refund = create_pending_refund
    finance = create_finance_account
    operator_id = refund.operator_id

    # 执行退款批准
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/refunds/{refund.id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={"note": "退款审核通过"}
        )

    assert response.status_code == 200

    # 验证消息是否被创建
    result = await test_db.execute(
        select(OperatorMessage)
        .where(OperatorMessage.operator_id == operator_id)
        .where(OperatorMessage.message_type == "refund_approved")
        .where(OperatorMessage.related_id == refund.id)
    )
    message = result.scalar_one_or_none()

    assert message is not None
    assert message.message_type == "refund_approved"
    assert message.related_type == "refund"
    assert message.related_id == refund.id
    assert "退款申请已批准" in message.title
    assert "¥200.00" in message.content
    assert message.is_read is False


@pytest.mark.asyncio
async def test_refund_reject_creates_message(test_db, create_finance_account, create_pending_refund):
    """测试退款拒绝时创建消息通知"""
    refund = create_pending_refund
    finance = create_finance_account
    operator_id = refund.operator_id

    # 执行退款拒绝
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/refunds/{refund.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "退款原因不符合要求,请重新提交"}
        )

    assert response.status_code == 200

    # 验证消息是否被创建
    result = await test_db.execute(
        select(OperatorMessage)
        .where(OperatorMessage.operator_id == operator_id)
        .where(OperatorMessage.message_type == "refund_rejected")
    )
    message = result.scalar_one_or_none()

    assert message is not None
    assert message.message_type == "refund_rejected"
    assert message.related_type == "refund"
    assert "退款申请被拒绝" in message.title
    assert "退款原因不符合要求" in message.content


# ========== 发票审核消息通知测试 ==========

@pytest.mark.asyncio
async def test_invoice_approve_creates_message(test_db, create_finance_account, create_pending_invoice):
    """测试发票批准时创建消息通知"""
    invoice = create_pending_invoice
    finance = create_finance_account
    operator_id = invoice.operator_id

    # 执行发票批准
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{invoice.id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={"note": "发票审核通过"}
        )

    assert response.status_code == 200

    # 验证消息是否被创建
    result = await test_db.execute(
        select(OperatorMessage)
        .where(OperatorMessage.operator_id == operator_id)
        .where(OperatorMessage.message_type == "invoice_approved")
    )
    message = result.scalar_one_or_none()

    assert message is not None
    assert message.message_type == "invoice_approved"
    assert message.related_type == "invoice"
    assert "发票已开具" in message.title
    assert "¥1000.00" in message.content


@pytest.mark.asyncio
async def test_invoice_reject_creates_message(test_db, create_finance_account, create_pending_invoice):
    """测试发票拒绝时创建消息通知"""
    invoice = create_pending_invoice
    finance = create_finance_account
    operator_id = invoice.operator_id

    # 执行发票拒绝
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/invoices/{invoice.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "税号格式不正确,请核对后重新提交"}
        )

    assert response.status_code == 200

    # 验证消息是否被创建
    result = await test_db.execute(
        select(OperatorMessage)
        .where(OperatorMessage.operator_id == operator_id)
        .where(OperatorMessage.message_type == "invoice_rejected")
    )
    message = result.scalar_one_or_none()

    assert message is not None
    assert message.message_type == "invoice_rejected"
    assert "发票申请被拒绝" in message.title
    assert "税号格式不正确" in message.content


# ========== 运营商消息查询API测试 ==========

@pytest.mark.asyncio
async def test_get_messages_list(test_db, create_test_operator, create_finance_account, create_pending_refund):
    """测试获取消息列表"""
    operator = create_test_operator
    refund = create_pending_refund

    # 先创建一条消息
    async with AsyncClient(app=app, base_url="http://test") as client:
        finance_token = await finance_login(client)

        # 批准退款以创建消息
        await client.post(
            f"/v1/finance/refunds/{refund.id}/approve",
            headers={"Authorization": f"Bearer {finance_token}"},
            json={"note": "退款审核通过"}
        )

        # 运营商查询消息列表
        operator_token = await operator_login(client)
        response = await client.get(
            "/v1/messages",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证分页响应结构
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 1

    # 验证消息项结构
    if len(data["items"]) > 0:
        item = data["items"][0]
        assert "message_id" in item
        assert "message_type" in item
        assert "title" in item
        assert "content" in item
        assert "is_read" in item
        assert "created_at" in item


@pytest.mark.asyncio
async def test_get_unread_count(test_db, create_test_operator, create_finance_account, create_pending_refund):
    """测试获取未读消息数量"""
    refund = create_pending_refund

    # 先创建一条消息
    async with AsyncClient(app=app, base_url="http://test") as client:
        finance_token = await finance_login(client)

        # 批准退款以创建消息
        await client.post(
            f"/v1/finance/refunds/{refund.id}/approve",
            headers={"Authorization": f"Bearer {finance_token}"},
            json={"note": "退款审核通过"}
        )

        # 运营商查询未读消息数量
        operator_token = await operator_login(client)
        response = await client.get(
            "/v1/messages/unread-count",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

    assert response.status_code == 200
    data = response.json()

    assert "unread_count" in data
    assert data["unread_count"] >= 1


@pytest.mark.asyncio
async def test_mark_message_as_read(test_db, create_test_operator, create_finance_account, create_pending_refund):
    """测试标记消息为已读"""
    refund = create_pending_refund
    operator_id = refund.operator_id

    # 先创建一条消息
    async with AsyncClient(app=app, base_url="http://test") as client:
        finance_token = await finance_login(client)

        # 批准退款以创建消息
        await client.post(
            f"/v1/finance/refunds/{refund.id}/approve",
            headers={"Authorization": f"Bearer {finance_token}"},
            json={"note": "退款审核通过"}
        )

        # 查询消息ID
        result = await test_db.execute(
            select(OperatorMessage)
            .where(OperatorMessage.operator_id == operator_id)
        )
        message = result.scalar_one()

        # 运营商标记消息为已读
        operator_token = await operator_login(client)
        response = await client.post(
            f"/v1/messages/{message.id}/read",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

    assert response.status_code == 200
    data = response.json()

    assert "message_id" in data
    assert "read_at" in data

    # 验证数据库中消息已标记为已读
    await test_db.refresh(message)
    assert message.is_read is True
    assert message.read_at is not None


@pytest.mark.asyncio
async def test_mark_all_messages_as_read(test_db, create_test_operator, create_finance_account, create_pending_refund, create_pending_invoice):
    """测试标记所有消息为已读"""
    refund = create_pending_refund
    invoice = create_pending_invoice

    # 先创建多条消息
    async with AsyncClient(app=app, base_url="http://test") as client:
        finance_token = await finance_login(client)

        # 批准退款和发票以创建多条消息
        await client.post(
            f"/v1/finance/refunds/{refund.id}/approve",
            headers={"Authorization": f"Bearer {finance_token}"},
            json={"note": "退款审核通过"}
        )
        await client.post(
            f"/v1/finance/invoices/{invoice.id}/approve",
            headers={"Authorization": f"Bearer {finance_token}"},
            json={"note": "发票审核通过"}
        )

        # 运营商标记所有消息为已读
        operator_token = await operator_login(client)
        response = await client.post(
            "/v1/messages/read-all",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

    assert response.status_code == 200
    data = response.json()

    assert "marked_count" in data
    assert data["marked_count"] >= 2


@pytest.mark.asyncio
async def test_delete_message(test_db, create_test_operator, create_finance_account, create_pending_refund):
    """测试删除消息"""
    refund = create_pending_refund
    operator_id = refund.operator_id

    # 先创建一条消息
    async with AsyncClient(app=app, base_url="http://test") as client:
        finance_token = await finance_login(client)

        # 批准退款以创建消息
        await client.post(
            f"/v1/finance/refunds/{refund.id}/approve",
            headers={"Authorization": f"Bearer {finance_token}"},
            json={"note": "退款审核通过"}
        )

        # 查询消息ID
        result = await test_db.execute(
            select(OperatorMessage)
            .where(OperatorMessage.operator_id == operator_id)
        )
        message = result.scalar_one()
        message_id = message.id

        # 运营商删除消息
        operator_token = await operator_login(client)
        response = await client.delete(
            f"/v1/messages/{message_id}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

    assert response.status_code == 200

    # 验证消息已被删除
    result = await test_db.execute(
        select(OperatorMessage).where(OperatorMessage.id == message_id)
    )
    deleted_message = result.scalar_one_or_none()
    assert deleted_message is None


@pytest.mark.asyncio
async def test_get_messages_with_filters(test_db, create_test_operator, create_finance_account, create_pending_refund):
    """测试按条件筛选消息"""
    refund = create_pending_refund

    # 先创建一条消息
    async with AsyncClient(app=app, base_url="http://test") as client:
        finance_token = await finance_login(client)

        # 批准退款以创建消息
        await client.post(
            f"/v1/finance/refunds/{refund.id}/approve",
            headers={"Authorization": f"Bearer {finance_token}"},
            json={"note": "退款审核通过"}
        )

        # 运营商查询特定类型的消息
        operator_token = await operator_login(client)
        response = await client.get(
            "/v1/messages?message_type=refund_approved&is_read=false",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证筛选结果
    assert len(data["items"]) > 0
    for item in data["items"]:
        assert item["message_type"] == "refund_approved"
        assert item["is_read"] is False
