"""
契约测试: 财务退款审核API (T157)

测试目标:
- 验证财务退款审核API端点契约
- 确保请求/响应格式符合contract定义
- 覆盖退款列表、详情查询、批准、拒绝场景

契约要求:
- GET /finance/refunds: 查询待审核退款列表
- GET /finance/refunds/{refund_id}: 查询退款详情
- POST /finance/refunds/{refund_id}/approve: 批准退款
- POST /finance/refunds/{refund_id}/reject: 拒绝退款
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from decimal import Decimal

from src.main import app
from src.models.finance import FinanceAccount
from src.models.operator import OperatorAccount
from src.models.refund import RefundRecord
from src.core.utils.password import hash_password
from datetime import datetime


# ========== Fixtures ==========

@pytest.fixture
async def create_finance_account(test_db):
    """创建财务测试账户"""
    finance = FinanceAccount(
        id=uuid4(),
        username="finance_zhang",
        password_hash=hash_password("FinancePass123"),
        full_name="张财务",
        email="finance.zhang@test.com",
        phone="13900139000",
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
        username="test_operator",
        password_hash=hash_password("Pass123"),
        full_name="测试运营商公司",
        phone="13800138001",
        email="test@example.com",
        api_key="test_api_key_12345678901234567890",
        api_key_hash=hash_password("test_api_key_12345678901234567890"),
        balance=Decimal("100.00"),
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
        requested_amount=Decimal("100.00"),
        refund_reason="业务调整,不再继续使用",
        status="pending"
    )
    test_db.add(refund)
    await test_db.commit()
    await test_db.refresh(refund)
    return refund


@pytest.fixture
async def create_approved_refund(test_db, create_test_operator, create_finance_account):
    """创建已批准的退款申请"""
    operator = create_test_operator
    finance = create_finance_account

    refund = RefundRecord(
        id=uuid4(),
        operator_id=operator.id,
        requested_amount=Decimal("50.00"),
        actual_amount=Decimal("50.00"),
        refund_reason="部分退款",
        status="approved",
        reviewed_by=finance.id,
        reviewed_at=datetime.now()
    )
    test_db.add(refund)
    await test_db.commit()
    await test_db.refresh(refund)
    return refund


# ========== 辅助函数 ==========

async def finance_login(client: AsyncClient) -> str:
    """财务人员登录,返回JWT Token"""
    response = await client.post(
        "/v1/auth/finance/login",
        json={
            "username": "finance_zhang",
            "password": "FinancePass123"
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return ""


# ========== GET /finance/refunds 测试 ==========

@pytest.mark.asyncio
async def test_get_refunds_list_default(test_db, create_finance_account, create_pending_refund):
    """测试获取退款列表(默认状态=pending)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/refunds",
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
async def test_get_refunds_list_with_status_filter(test_db, create_finance_account, create_approved_refund):
    """测试按状态筛选退款列表"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/refunds?status=approved",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data

    # 验证返回的记录都是approved状态
    for item in data["items"]:
        assert item["status"] == "approved"


@pytest.mark.asyncio
async def test_get_refunds_list_with_pagination(test_db, create_finance_account, create_pending_refund):
    """测试分页参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/refunds?page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["items"]) <= 10


@pytest.mark.asyncio
async def test_get_refunds_list_all_status(test_db, create_finance_account, create_pending_refund):
    """测试查询所有状态的退款"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/refunds?status=all",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_refunds_list_without_token(test_db):
    """测试未提供Token获取退款列表"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/finance/refunds")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_refunds_list_invalid_status(test_db, create_finance_account):
    """测试无效的status参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/refunds?status=invalid_status",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code in [400, 422]


# ========== GET /finance/refunds/{refund_id} 测试 ==========

@pytest.mark.asyncio
async def test_get_refund_details_success(test_db, create_finance_account, create_pending_refund):
    """测试获取退款详情"""
    refund = create_pending_refund

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            f"/v1/finance/refunds/{refund.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证详情结构
    assert "refund_id" in data
    assert "operator_id" in data
    assert "operator_name" in data
    assert "requested_amount" in data
    assert "current_balance" in data
    assert "status" in data
    assert "reason" in data
    assert "created_at" in data

    # 验证包含运营商财务信息
    assert "operator_finance" in data
    operator_finance = data["operator_finance"]
    assert "operator_id" in operator_finance
    assert "current_balance" in operator_finance
    assert "total_recharged" in operator_finance
    assert "total_consumed" in operator_finance


@pytest.mark.asyncio
async def test_get_refund_details_nonexistent(test_db, create_finance_account):
    """测试获取不存在的退款详情"""
    fake_id = uuid4()

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            f"/v1/finance/refunds/{fake_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_refund_details_invalid_id(test_db, create_finance_account):
    """测试无效的refund_id"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.get(
            "/v1/finance/refunds/invalid_id",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_get_refund_details_without_token(test_db, create_pending_refund):
    """测试未提供Token获取退款详情"""
    refund = create_pending_refund

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/v1/finance/refunds/{refund.id}")

    assert response.status_code == 401


# ========== POST /finance/refunds/{refund_id}/approve 测试 ==========

@pytest.mark.asyncio
async def test_approve_refund_success(test_db, create_finance_account, create_pending_refund):
    """测试批准退款"""
    refund = create_pending_refund

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/refunds/{refund.id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "note": "退款已处理"
            }
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert "refund_id" in data
    assert "requested_amount" in data
    assert "actual_refund_amount" in data
    assert "balance_after" in data


@pytest.mark.asyncio
async def test_approve_refund_without_note(test_db, create_finance_account, create_pending_refund):
    """测试批准退款(无备注)"""
    refund = create_pending_refund

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/refunds/{refund.id}/approve",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_approve_refund_already_approved(test_db, create_finance_account, create_approved_refund):
    """测试重复批准退款"""
    refund = create_approved_refund

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/refunds/{refund.id}/approve",
            headers={"Authorization": f"Bearer {token}"}
        )

    # 应该返回错误,已处理的申请不能重复操作
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_approve_refund_nonexistent(test_db, create_finance_account):
    """测试批准不存在的退款"""
    fake_id = uuid4()

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/refunds/{fake_id}/approve",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_approve_refund_without_token(test_db, create_pending_refund):
    """测试未提供Token批准退款"""
    refund = create_pending_refund

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(f"/v1/finance/refunds/{refund.id}/approve")

    assert response.status_code == 401


# ========== POST /finance/refunds/{refund_id}/reject 测试 ==========

@pytest.mark.asyncio
async def test_reject_refund_success(test_db, create_finance_account, create_pending_refund):
    """测试拒绝退款"""
    refund = create_pending_refund

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/refunds/{refund.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "退款原因不符合公司政策,建议继续使用或联系客服"
            }
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_reject_refund_missing_reason(test_db, create_finance_account, create_pending_refund):
    """测试拒绝退款缺少原因"""
    refund = create_pending_refund

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/refunds/{refund.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={}
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_reject_refund_short_reason(test_db, create_finance_account, create_pending_refund):
    """测试拒绝退款原因太短"""
    refund = create_pending_refund

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/refunds/{refund.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "太短"  # 少于10个字符
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_reject_refund_already_rejected(test_db, create_finance_account, create_test_operator):
    """测试重复拒绝退款"""
    operator = create_test_operator

    # 创建已拒绝的退款
    refund = RefundRecord(
        id=uuid4(),
        operator_id=operator.id,
        requested_amount=Decimal("100.00"),
        refund_reason="测试",
        status="rejected",
        reject_reason="已拒绝",
        reviewed_by=uuid4(),
        reviewed_at=datetime.now()
    )
    test_db.add(refund)
    await test_db.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/refunds/{refund.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "重复拒绝原因"
            }
        )

    # 应该返回错误,已处理的申请不能重复操作
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reject_refund_nonexistent(test_db, create_finance_account):
    """测试拒绝不存在的退款"""
    fake_id = uuid4()

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/refunds/{fake_id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "拒绝原因"
            }
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reject_refund_without_token(test_db, create_pending_refund):
    """测试未提供Token拒绝退款"""
    refund = create_pending_refund

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            f"/v1/finance/refunds/{refund.id}/reject",
            json={
                "reason": "拒绝原因"
            }
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_reject_refund_long_reason(test_db, create_finance_account, create_pending_refund):
    """测试拒绝退款原因太长"""
    refund = create_pending_refund

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await finance_login(client)

        response = await client.post(
            f"/v1/finance/refunds/{refund.id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "x" * 300  # 超过200字符
            }
        )

    assert response.status_code in [400, 422]
