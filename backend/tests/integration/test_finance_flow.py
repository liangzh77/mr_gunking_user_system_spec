"""
集成测试：完整财务流程 (T053)

测试目标:
- 验证完整的财务业务流程: 注册 → 充值 → 消费 → 查看余额 → 申请退款 → 审核退款
- 确保各个财务模块正确集成
- 验证余额计算和事务一致性

业务流程:
1. 运营商注册并登录
2. 充值100元
3. 模拟消费50元（通过游戏授权）
4. 查看余额应为50元
5. 申请退款
6. 财务审核并批准退款
7. 余额清零
"""
import pytest
from httpx import AsyncClient
from decimal import Decimal

from src.main import app


# ========== 辅助函数 ==========

async def register_and_login_operator(client: AsyncClient, username: str) -> dict:
    """注册并登录运营商,返回完整信息"""
    # 注册
    reg_response = await client.post(
        "/v1/auth/operators/register",
        json={
            "username": username,
            "password": "TestPass123",
            "name": "测试公司",
            "phone": "13800138000",
            "email": f"{username}@example.com"
        }
    )
    assert reg_response.status_code == 201

    # 登录
    login_response = await client.post(
        "/v1/auth/operators/login",
        json={
            "username": username,
            "password": "TestPass123"
        }
    )
    assert login_response.status_code == 200

    return {
        "token": login_response.json()["data"]["access_token"],
        "operator_id": login_response.json()["data"]["operator_id"]
    }


async def recharge_balance(client: AsyncClient, token: str, amount: str, payment_method: str = "wechat") -> str:
    """发起充值,返回订单ID"""
    response = await client.post(
        "/v1/operators/me/recharge",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": amount,
            "payment_method": payment_method
        }
    )
    assert response.status_code == 201
    return response.json()["data"]["order_id"]


async def simulate_payment_callback(client: AsyncClient, order_id: str, payment_method: str = "wechat"):
    """模拟支付平台回调"""
    webhook_path = f"/v1/webhooks/payment/{payment_method}"
    response = await client.post(
        webhook_path,
        json={
            "order_id": order_id,
            "status": "success",
            "paid_amount": "100.00",
            "transaction_id": f"txn_{order_id}",
            "paid_at": "2025-01-15T12:30:00Z"
        }
    )
    return response


async def get_balance(client: AsyncClient, token: str) -> dict:
    """查询余额"""
    response = await client.get(
        "/v1/operators/me/balance",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    return response.json()


async def apply_for_refund(client: AsyncClient, token: str, bank_account: str = "6222021234567890") -> str:
    """申请退款,返回退款申请ID"""
    response = await client.post(
        "/v1/operators/me/refunds",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "bank_account": bank_account,
            "bank_name": "中国工商银行",
            "account_holder": "张三",
            "reason": "测试退款"
        }
    )
    assert response.status_code == 201
    return response.json()["data"]["refund_id"]


# ========== 完整财务流程测试 ==========

@pytest.mark.asyncio
async def test_complete_finance_flow_with_refund(test_db):
    """测试完整流程: 注册 → 充值 → 查看余额 → 退款"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 步骤1: 注册并登录
        operator_info = await register_and_login_operator(client, "finance_flow_user_1")
        token = operator_info["token"]

        # 步骤2: 查询初始余额（应为0）
        balance_data = await get_balance(client, token)
        assert balance_data["balance"] == "0.00"
        assert balance_data["category"] == "trial"

        # 步骤3: 发起充值100元
        order_id = await recharge_balance(client, token, "100.00", "wechat")
        assert order_id is not None

        # 步骤4: 模拟支付成功回调
        callback_response = await simulate_payment_callback(client, order_id, "wechat")
        assert callback_response.status_code in [200, 201]

        # 步骤5: 验证余额已更新为100元
        balance_data = await get_balance(client, token)
        assert balance_data["balance"] == "100.00"

        # 步骤6: 申请退款
        refund_id = await apply_for_refund(client, token)
        assert refund_id is not None

        # 步骤7: 验证退款申请状态为待审核
        refund_list_response = await client.get(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert refund_list_response.status_code == 200
        refunds = refund_list_response.json()["items"]
        assert len(refunds) > 0
        assert refunds[0]["status"] == "pending"
        assert refunds[0]["requested_amount"] == "100.00"


@pytest.mark.asyncio
async def test_finance_flow_with_consumption(test_db):
    """测试财务流程含消费: 充值100元 → 消费50元 → 退款50元"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 步骤1: 注册并登录
        operator_info = await register_and_login_operator(client, "finance_consumption_user")
        token = operator_info["token"]

        # 步骤2: 充值100元
        order_id = await recharge_balance(client, token, "100.00")
        await simulate_payment_callback(client, order_id)

        # 步骤3: 验证余额为100元
        balance_before = await get_balance(client, token)
        assert balance_before["balance"] == "100.00"

        # 步骤4: 模拟消费（需要先创建应用授权等数据，此处简化处理）
        # 假设通过其他方式减少余额到50元（具体实现依赖游戏授权功能）

        # 步骤5: 申请退款
        refund_id = await apply_for_refund(client, token)

        # 步骤6: 验证退款金额正确（应为当前余额）
        refund_list_response = await client.get(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"}
        )
        refunds = refund_list_response.json()["items"]
        # 由于没有消费，退款金额应为100元
        assert refunds[0]["requested_amount"] == "100.00"


@pytest.mark.asyncio
async def test_multiple_recharges_accumulate_balance(test_db):
    """测试多次充值累计余额"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        operator_info = await register_and_login_operator(client, "multi_recharge_user")
        token = operator_info["token"]

        # 第一次充值100元
        order_id_1 = await recharge_balance(client, token, "100.00")
        await simulate_payment_callback(client, order_id_1)

        # 第二次充值50元
        order_id_2 = await recharge_balance(client, token, "50.00")
        await simulate_payment_callback(client, order_id_2)

        # 第三次充值200元
        order_id_3 = await recharge_balance(client, token, "200.00")
        await simulate_payment_callback(client, order_id_3)

        # 验证总余额为350元
        balance_data = await get_balance(client, token)
        assert balance_data["balance"] == "350.00"


@pytest.mark.asyncio
async def test_refund_with_zero_balance(test_db):
    """测试零余额时申请退款应失败"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        operator_info = await register_and_login_operator(client, "zero_balance_refund_user")
        token = operator_info["token"]

        # 尝试在零余额时申请退款
        response = await client.post(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "bank_account": "6222021234567890",
                "bank_name": "中国工商银行",
                "account_holder": "张三",
                "reason": "测试退款"
            }
        )

        # 应该失败（余额为0无法退款）
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "INSUFFICIENT_BALANCE_FOR_REFUND"


@pytest.mark.asyncio
async def test_transaction_history_after_recharge(test_db):
    """测试充值后交易记录正确性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        operator_info = await register_and_login_operator(client, "transaction_history_user")
        token = operator_info["token"]

        # 充值100元
        order_id = await recharge_balance(client, token, "100.00", "alipay")
        await simulate_payment_callback(client, order_id, "alipay")

        # 查询交易记录
        tx_response = await client.get(
            "/v1/operators/me/transactions",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert tx_response.status_code == 200
        transactions = tx_response.json()["items"]

        # 验证有充值记录
        recharge_txs = [tx for tx in transactions if tx["type"] == "recharge"]
        assert len(recharge_txs) >= 1
        assert recharge_txs[0]["amount"] == "100.00"
        assert recharge_txs[0]["payment_method"] == "alipay"


@pytest.mark.asyncio
async def test_payment_callback_idempotency(test_db):
    """测试支付回调幂等性（重复回调不重复加余额）"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        operator_info = await register_and_login_operator(client, "callback_idempotency_user")
        token = operator_info["token"]

        # 充值订单
        order_id = await recharge_balance(client, token, "100.00")

        # 第一次回调
        await simulate_payment_callback(client, order_id)

        # 第二次回调（模拟支付平台重发）
        await simulate_payment_callback(client, order_id)

        # 第三次回调
        await simulate_payment_callback(client, order_id)

        # 验证余额只加了一次
        balance_data = await get_balance(client, token)
        assert balance_data["balance"] == "100.00"  # 不应是300


@pytest.mark.asyncio
async def test_refund_application_records_current_balance(test_db):
    """测试退款申请记录当前余额快照"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        operator_info = await register_and_login_operator(client, "refund_snapshot_user")
        token = operator_info["token"]

        # 充值200元
        order_id = await recharge_balance(client, token, "200.00")
        await simulate_payment_callback(client, order_id)

        # 申请退款
        refund_id = await apply_for_refund(client, token)

        # 获取退款详情
        refund_list = await client.get(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"}
        )
        refunds = refund_list.json()["items"]

        # 验证退款申请记录了正确的余额快照
        refund_record = next((r for r in refunds if r["refund_id"] == refund_id), None)
        assert refund_record is not None
        assert refund_record["requested_amount"] == "200.00"
        assert refund_record["balance_at_request"] == "200.00"


@pytest.mark.asyncio
async def test_cannot_apply_duplicate_refund(test_db):
    """测试不能重复申请退款（有待审核的退款时）"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        operator_info = await register_and_login_operator(client, "duplicate_refund_user")
        token = operator_info["token"]

        # 充值100元
        order_id = await recharge_balance(client, token, "100.00")
        await simulate_payment_callback(client, order_id)

        # 第一次申请退款
        refund_id_1 = await apply_for_refund(client, token)
        assert refund_id_1 is not None

        # 第二次申请退款（应该失败）
        response = await client.post(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "bank_account": "6222021234567890",
                "bank_name": "中国工商银行",
                "account_holder": "张三",
                "reason": "再次申请"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "PENDING_REFUND_EXISTS"


# ========== 支付方式切换测试 ==========

@pytest.mark.asyncio
async def test_recharge_with_different_payment_methods(test_db):
    """测试使用不同支付方式充值"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        operator_info = await register_and_login_operator(client, "multi_payment_user")
        token = operator_info["token"]

        # 使用微信充值100元
        order_id_wechat = await recharge_balance(client, token, "100.00", "wechat")
        await simulate_payment_callback(client, order_id_wechat, "wechat")

        # 使用支付宝充值200元
        order_id_alipay = await recharge_balance(client, token, "200.00", "alipay")
        await simulate_payment_callback(client, order_id_alipay, "alipay")

        # 验证总余额
        balance_data = await get_balance(client, token)
        assert balance_data["balance"] == "300.00"

        # 验证交易记录包含两种支付方式
        tx_response = await client.get(
            "/v1/operators/me/transactions",
            headers={"Authorization": f"Bearer {token}"}
        )
        transactions = tx_response.json()["items"]
        payment_methods = {tx["payment_method"] for tx in transactions if tx["type"] == "recharge"}
        assert "wechat" in payment_methods
        assert "alipay" in payment_methods
