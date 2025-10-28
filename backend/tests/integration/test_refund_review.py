"""
集成测试：退款审核流程 (T158)

测试目标:
- 验证完整的财务退款审核流程
- 确保财务人员可以查看详情、审核通过、记录日志
- 验证退款审核后余额正确变化

业务流程:
1. 创建财务人员账号
2. 创建运营商账号并充值
3. 运营商申请退款
4. 财务人员登录
5. 财务人员查看退款申请列表
6. 财务人员查看退款详情
7. 财务人员审核通过退款（带备注）
8. 验证退款状态变更为approved
9. 验证审核信息记录正确
10. 验证余额归零
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


# ========== Fixtures ==========

@pytest.fixture
async def create_finance_account(test_db):
    """创建财务测试账户"""
    finance = FinanceAccount(
        id=uuid4(),
        username="finance_reviewer",
        password_hash=hash_password("FinancePass123"),
        full_name="张财务",
        email="finance@test.com",
        phone="13900139000",
        role="specialist"
    )
    test_db.add(finance)
    await test_db.commit()
    await test_db.refresh(finance)
    return finance


@pytest.fixture
async def create_test_operator_with_balance(test_db):
    """创建有余额的测试运营商"""
    operator = OperatorAccount(
        id=uuid4(),
        username="test_refund_op",
        password_hash=hash_password("TestPass123"),
        full_name="测试退款公司",
        phone="13800138001",
        email="refund@example.com",
        api_key="test_api_key_refund_12345678901",
        api_key_hash=hash_password("test_api_key_refund_12345678901"),
        balance=Decimal("200.00"),  # 初始余额200元
        total_recharged=Decimal("200.00"),
        customer_tier="standard"
    )
    test_db.add(operator)
    await test_db.commit()
    await test_db.refresh(operator)
    return operator


# ========== 辅助函数 ==========

async def finance_login(client: AsyncClient, username: str = "finance_reviewer", password: str = "FinancePass123") -> str:
    """财务人员登录，返回JWT Token"""
    response = await client.post(
        "/v1/auth/finance/login",
        json={
            "username": username,
            "password": password
        }
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


async def operator_login(client: AsyncClient, username: str, password: str) -> str:
    """运营商登录，返回JWT Token"""
    response = await client.post(
        "/v1/auth/operators/login",
        json={
            "username": username,
            "password": password
        }
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


async def apply_for_refund(client: AsyncClient, token: str, reason: str = "业务调整，不再继续使用") -> str:
    """申请退款，返回退款ID"""
    response = await client.post(
        "/v1/operators/me/refunds",
        headers={"Authorization": f"Bearer {token}"},
        json={"refund_reason": reason}
    )
    assert response.status_code == 201
    return response.json()["data"]["refund_id"]


async def get_balance(client: AsyncClient, token: str) -> dict:
    """查询余额"""
    response = await client.get(
        "/v1/operators/me/balance",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    return response.json()["data"]


# ========== 测试用例 ==========

@pytest.mark.asyncio
async def test_complete_refund_review_flow(
    async_client: AsyncClient,
    create_finance_account,
    create_test_operator_with_balance,
    test_db
):
    """测试完整的退款审核流程：查看详情 → 审核通过 → 记录日志"""

    # 1. 运营商登录并申请退款
    operator_token = await operator_login(async_client, "test_refund_op", "TestPass123")

    # 检查初始余额
    balance_before = await get_balance(async_client, operator_token)
    assert balance_before["balance"] == "200.00"

    # 申请退款
    refund_id = await apply_for_refund(async_client, operator_token, "测试完整流程退款")

    # 2. 财务人员登录
    finance_token = await finance_login(async_client)

    # 3. 查看退款申请列表
    list_response = await async_client.get(
        "/v1/finance/refunds",
        headers={"Authorization": f"Bearer {finance_token}"},
        params={"status": "pending"}
    )
    assert list_response.status_code == 200
    refunds_data = list_response.json()["data"]
    assert refunds_data["total"] >= 1
    assert any(r["refund_id"] == refund_id for r in refunds_data["refunds"])

    # 4. 查看退款详情
    detail_response = await async_client.get(
        f"/v1/finance/refunds/{refund_id}",
        headers={"Authorization": f"Bearer {finance_token}"}
    )
    assert detail_response.status_code == 200
    refund_detail = detail_response.json()["data"]
    assert refund_detail["refund_id"] == refund_id
    assert refund_detail["status"] == "pending"
    assert refund_detail["requested_amount"] == "200.00"
    assert refund_detail["operator_name"] == "测试退款公司"

    # 5. 审核通过退款
    approve_response = await async_client.post(
        f"/v1/finance/refunds/{refund_id}/approve",
        headers={"Authorization": f"Bearer {finance_token}"},
        json={"admin_note": "审核通过，符合退款条件"}
    )
    assert approve_response.status_code == 200
    approved_refund = approve_response.json()["data"]

    # 6. 验证退款状态变更
    assert approved_refund["status"] == "approved"
    assert approved_refund["actual_amount"] == "200.00"
    assert approved_refund["admin_note"] == "审核通过，符合退款条件"
    assert approved_refund["reviewed_by"] is not None
    assert approved_refund["reviewed_at"] is not None

    # 7. 验证运营商余额归零
    balance_after = await get_balance(async_client, operator_token)
    assert balance_after["balance"] == "0.00"

    # 8. 验证退款记录在数据库中正确保存
    await test_db.refresh(create_test_operator_with_balance)
    assert create_test_operator_with_balance.balance == Decimal("0.00")


@pytest.mark.asyncio
async def test_refund_review_reject_flow(
    async_client: AsyncClient,
    create_finance_account,
    create_test_operator_with_balance
):
    """测试退款拒绝流程"""

    # 1. 运营商登录并申请退款
    operator_token = await operator_login(async_client, "test_refund_op", "TestPass123")
    refund_id = await apply_for_refund(async_client, operator_token, "测试拒绝流程")

    # 检查初始余额
    balance_before = await get_balance(async_client, operator_token)
    initial_balance = balance_before["balance"]

    # 2. 财务人员登录
    finance_token = await finance_login(async_client)

    # 3. 拒绝退款
    reject_response = await async_client.post(
        f"/v1/finance/refunds/{refund_id}/reject",
        headers={"Authorization": f"Bearer {finance_token}"},
        json={"reject_reason": "申请材料不完整，请补充相关证明"}
    )
    assert reject_response.status_code == 200
    rejected_refund = reject_response.json()["data"]

    # 4. 验证退款状态
    assert rejected_refund["status"] == "rejected"
    assert rejected_refund["admin_note"] == "申请材料不完整，请补充相关证明"
    assert rejected_refund["reviewed_by"] is not None

    # 5. 验证余额未变化
    balance_after = await get_balance(async_client, operator_token)
    assert balance_after["balance"] == initial_balance


@pytest.mark.asyncio
async def test_refund_review_without_finance_token(
    async_client: AsyncClient,
    create_test_operator_with_balance
):
    """测试未登录时无法审核退款"""

    # 1. 运营商申请退款
    operator_token = await operator_login(async_client, "test_refund_op", "TestPass123")
    refund_id = await apply_for_refund(async_client, operator_token)

    # 2. 尝试未登录审核
    response = await async_client.post(
        f"/v1/finance/refunds/{refund_id}/approve",
        json={"admin_note": "测试"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refund_review_operator_cannot_approve(
    async_client: AsyncClient,
    create_test_operator_with_balance
):
    """测试运营商token无法审核退款"""

    # 1. 运营商申请退款
    operator_token = await operator_login(async_client, "test_refund_op", "TestPass123")
    refund_id = await apply_for_refund(async_client, operator_token)

    # 2. 尝试用运营商token审核
    response = await async_client.post(
        f"/v1/finance/refunds/{refund_id}/approve",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"admin_note": "测试"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_refund_review_nonexistent_refund(
    async_client: AsyncClient,
    create_finance_account
):
    """测试审核不存在的退款申请"""

    finance_token = await finance_login(async_client)

    fake_refund_id = str(uuid4())
    response = await async_client.post(
        f"/v1/finance/refunds/{fake_refund_id}/approve",
        headers={"Authorization": f"Bearer {finance_token}"},
        json={"admin_note": "测试"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_refund_review_list_pagination(
    async_client: AsyncClient,
    create_finance_account,
    create_test_operator_with_balance
):
    """测试退款列表分页功能"""

    # 1. 创建多个退款申请
    operator_token = await operator_login(async_client, "test_refund_op", "TestPass123")
    refund_ids = []
    for i in range(3):
        refund_id = await apply_for_refund(async_client, operator_token, f"测试退款{i+1}")
        refund_ids.append(refund_id)

    # 2. 财务人员登录
    finance_token = await finance_login(async_client)

    # 3. 测试分页
    response = await async_client.get(
        "/v1/finance/refunds",
        headers={"Authorization": f"Bearer {finance_token}"},
        params={"page": 1, "page_size": 2}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["refunds"]) <= 2
    assert data["page"] == 1
    assert data["page_size"] == 2


@pytest.mark.asyncio
async def test_refund_review_status_filter(
    async_client: AsyncClient,
    create_finance_account,
    create_test_operator_with_balance
):
    """测试按状态筛选退款申请"""

    # 1. 创建并批准一个退款
    operator_token = await operator_login(async_client, "test_refund_op", "TestPass123")
    refund_id = await apply_for_refund(async_client, operator_token, "测试状态筛选")

    finance_token = await finance_login(async_client)

    # 批准退款
    await async_client.post(
        f"/v1/finance/refunds/{refund_id}/approve",
        headers={"Authorization": f"Bearer {finance_token}"},
        json={"admin_note": "测试"}
    )

    # 2. 筛选已批准的退款
    response = await async_client.get(
        "/v1/finance/refunds",
        headers={"Authorization": f"Bearer {finance_token}"},
        params={"status": "approved"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert all(r["status"] == "approved" for r in data["refunds"])


@pytest.mark.asyncio
async def test_refund_review_double_approval_fails(
    async_client: AsyncClient,
    create_finance_account,
    create_test_operator_with_balance
):
    """测试重复审核同一退款申请会失败"""

    # 1. 申请退款
    operator_token = await operator_login(async_client, "test_refund_op", "TestPass123")
    refund_id = await apply_for_refund(async_client, operator_token)

    # 2. 第一次审核通过
    finance_token = await finance_login(async_client)
    first_response = await async_client.post(
        f"/v1/finance/refunds/{refund_id}/approve",
        headers={"Authorization": f"Bearer {finance_token}"},
        json={"admin_note": "第一次审核"}
    )
    assert first_response.status_code == 200

    # 3. 尝试第二次审核
    second_response = await async_client.post(
        f"/v1/finance/refunds/{refund_id}/approve",
        headers={"Authorization": f"Bearer {finance_token}"},
        json={"admin_note": "第二次审核"}
    )
    assert second_response.status_code == 400  # 已审核的退款不能重复审核
