"""
集成测试：支付回调失败场景与回滚 (T054)

测试目标:
- 验证支付回调失败时的事务回滚机制
- 确保充值订单状态正确更新
- 验证余额不会在回调失败时错误增加
- 测试支付平台异常情况的处理

失败场景:
1. 支付失败回调（用户未完成支付）
2. 回调签名验证失败
3. 订单金额不匹配
4. 订单ID不存在
5. 数据库事务失败回滚
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from decimal import Decimal

from src.main import app


# ========== 辅助函数 ==========

async def register_and_login_operator(client: AsyncClient, username: str) -> str:
    """注册并登录运营商,返回JWT Token"""
    await client.post(
        "/v1/auth/operators/register",
        json={
            "username": username,
            "password": "TestPass123",
            "name": "测试公司",
            "phone": "13800138000",
            "email": f"{username}@example.com"
        }
    )

    login_response = await client.post(
        "/v1/auth/operators/login",
        json={
            "username": username,
            "password": "TestPass123"
        }
    )

    return login_response.json()["data"]["access_token"]


async def create_recharge_order(client: AsyncClient, token: str, amount: str) -> str:
    """创建充值订单,返回订单ID"""
    response = await client.post(
        "/v1/operators/me/recharge",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": amount,
            "payment_method": "wechat"
        }
    )
    assert response.status_code == 201
    return response.json()["data"]["order_id"]


async def get_balance(client: AsyncClient, token: str) -> str:
    """查询当前余额"""
    response = await client.get(
        "/v1/operators/me/balance",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    return response.json()["balance"]


# ========== 支付失败回调测试 ==========

@pytest.mark.asyncio
async def test_payment_callback_with_failed_status(test_db):
    """测试支付失败回调（用户未完成支付）"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await register_and_login_operator(client, "payment_fail_user")

        # 创建充值订单
        order_id = await create_recharge_order(client, token, "100.00")

        # 发送支付失败回调
        callback_response = await client.post(
            "/v1/webhooks/payment/wechat",
            json={
                "order_id": order_id,
                "status": "failed",  # 支付失败
                "paid_amount": "0.00",
                "transaction_id": f"txn_{order_id}",
                "paid_at": "2025-01-15T12:30:00Z",
                "error_code": "USER_CANCEL",
                "error_message": "用户取消支付"
            }
        )

        # 回调应该返回200（已接收）
        assert callback_response.status_code == 200

        # 验证余额未增加
        balance = await get_balance(client, token)
        assert balance == "0.00"

        # 验证订单状态为失败
        tx_response = await client.get(
            "/v1/operators/me/transactions",
            headers={"Authorization": f"Bearer {token}"}
        )
        transactions = tx_response.json()["items"]
        # 应该没有成功的充值交易
        recharge_txs = [tx for tx in transactions if tx["type"] == "recharge" and tx["status"] == "completed"]
        assert len(recharge_txs) == 0


@pytest.mark.asyncio
async def test_payment_callback_with_invalid_signature(test_db):
    """测试回调签名验证失败"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await register_and_login_operator(client, "invalid_sig_user")

        order_id = await create_recharge_order(client, token, "100.00")

        # 发送签名错误的回调
        callback_response = await client.post(
            "/v1/webhooks/payment/wechat",
            headers={"X-Wechat-Signature": "invalid_signature_12345"},
            json={
                "order_id": order_id,
                "status": "success",
                "paid_amount": "100.00",
                "transaction_id": f"txn_{order_id}",
                "paid_at": "2025-01-15T12:30:00Z"
            }
        )

        # 应该返回400（签名验证失败）
        assert callback_response.status_code == 400

        # 验证余额未增加
        balance = await get_balance(client, token)
        assert balance == "0.00"


@pytest.mark.asyncio
async def test_payment_callback_amount_mismatch(test_db):
    """测试回调金额与订单金额不匹配"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await register_and_login_operator(client, "amount_mismatch_user")

        # 创建100元订单
        order_id = await create_recharge_order(client, token, "100.00")

        # 回调中支付金额为50元（不匹配）
        callback_response = await client.post(
            "/v1/webhooks/payment/wechat",
            json={
                "order_id": order_id,
                "status": "success",
                "paid_amount": "50.00",  # 金额不匹配
                "transaction_id": f"txn_{order_id}",
                "paid_at": "2025-01-15T12:30:00Z"
            }
        )

        # 应该返回400（金额不匹配）
        assert callback_response.status_code == 400
        data = callback_response.json()
        assert data["error_code"] == "AMOUNT_MISMATCH"

        # 验证余额未增加
        balance = await get_balance(client, token)
        assert balance == "0.00"


@pytest.mark.asyncio
async def test_payment_callback_order_not_found(test_db):
    """测试回调中的订单ID不存在"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 发送不存在的订单ID
        callback_response = await client.post(
            "/v1/webhooks/payment/wechat",
            json={
                "order_id": "ord_recharge_nonexistent_12345",
                "status": "success",
                "paid_amount": "100.00",
                "transaction_id": "txn_12345",
                "paid_at": "2025-01-15T12:30:00Z"
            }
        )

        # 应该返回404（订单不存在）
        assert callback_response.status_code == 404
        data = callback_response.json()
        assert data["error_code"] == "ORDER_NOT_FOUND"


@pytest.mark.asyncio
async def test_payment_callback_duplicate_callback(test_db):
    """测试重复回调（幂等性保障）"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await register_and_login_operator(client, "duplicate_callback_user")

        order_id = await create_recharge_order(client, token, "100.00")

        # 第一次回调（成功）
        callback1 = await client.post(
            "/v1/webhooks/payment/wechat",
            json={
                "order_id": order_id,
                "status": "success",
                "paid_amount": "100.00",
                "transaction_id": f"txn_{order_id}",
                "paid_at": "2025-01-15T12:30:00Z"
            }
        )
        assert callback1.status_code in [200, 201]

        # 第二次回调（相同内容）
        callback2 = await client.post(
            "/v1/webhooks/payment/wechat",
            json={
                "order_id": order_id,
                "status": "success",
                "paid_amount": "100.00",
                "transaction_id": f"txn_{order_id}",
                "paid_at": "2025-01-15T12:30:00Z"
            }
        )
        assert callback2.status_code == 200  # 幂等性：返回成功但不重复处理

        # 验证余额只加了一次
        balance = await get_balance(client, token)
        assert balance == "100.00"  # 不是200.00


@pytest.mark.asyncio
async def test_payment_callback_database_transaction_rollback(test_db):
    """测试数据库事务失败时的回滚"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await register_and_login_operator(client, "db_rollback_user")

        order_id = await create_recharge_order(client, token, "100.00")

        # Mock数据库提交失败
        with patch("src.db.session.AsyncSession.commit", side_effect=Exception("Database error")):
            try:
                callback_response = await client.post(
                    "/v1/webhooks/payment/wechat",
                    json={
                        "order_id": order_id,
                        "status": "success",
                        "paid_amount": "100.00",
                        "transaction_id": f"txn_{order_id}",
                        "paid_at": "2025-01-15T12:30:00Z"
                    }
                )
                # 应该返回500（服务器内部错误）
                assert callback_response.status_code == 500
            except Exception:
                pass  # Mock可能引发异常

        # 验证余额未增加（事务已回滚）
        balance = await get_balance(client, token)
        assert balance == "0.00"


@pytest.mark.asyncio
async def test_payment_callback_with_expired_order(test_db):
    """测试回调已过期订单"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await register_and_login_operator(client, "expired_order_user")

        order_id = await create_recharge_order(client, token, "100.00")

        # 模拟订单已过期（30分钟后）
        # 注意：实际实现中需要检查订单创建时间
        from datetime import datetime, timedelta
        expired_time = (datetime.utcnow() + timedelta(minutes=35)).isoformat() + "Z"

        callback_response = await client.post(
            "/v1/webhooks/payment/wechat",
            json={
                "order_id": order_id,
                "status": "success",
                "paid_amount": "100.00",
                "transaction_id": f"txn_{order_id}",
                "paid_at": expired_time  # 超过30分钟有效期
            }
        )

        # 应该拒绝过期订单
        assert callback_response.status_code == 400
        data = callback_response.json()
        assert data["error_code"] in ["ORDER_EXPIRED", "INVALID_PARAMS"]

        # 验证余额未增加
        balance = await get_balance(client, token)
        assert balance == "0.00"


@pytest.mark.asyncio
async def test_payment_callback_missing_required_fields(test_db):
    """测试回调缺少必需字段"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await register_and_login_operator(client, "missing_fields_user")

        order_id = await create_recharge_order(client, token, "100.00")

        # 回调缺少paid_amount字段
        callback_response = await client.post(
            "/v1/webhooks/payment/wechat",
            json={
                "order_id": order_id,
                "status": "success",
                # paid_amount缺失
                "transaction_id": f"txn_{order_id}",
                "paid_at": "2025-01-15T12:30:00Z"
            }
        )

        # 应该返回400
        assert callback_response.status_code == 400

        # 验证余额未增加
        balance = await get_balance(client, token)
        assert balance == "0.00"


@pytest.mark.asyncio
async def test_alipay_callback_failure(test_db):
    """测试支付宝回调失败场景"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await register_and_login_operator(client, "alipay_fail_user")

        # 创建支付宝订单
        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "200.00",
                "payment_method": "alipay"
            }
        )
        order_id = response.json()["data"]["order_id"]

        # 发送支付宝失败回调
        callback_response = await client.post(
            "/v1/webhooks/payment/alipay",
            json={
                "order_id": order_id,
                "status": "failed",
                "paid_amount": "0.00",
                "transaction_id": f"txn_ali_{order_id}",
                "paid_at": "2025-01-15T12:30:00Z",
                "error_code": "BALANCE_NOT_ENOUGH",
                "error_message": "支付宝余额不足"
            }
        )

        assert callback_response.status_code == 200

        # 验证余额未增加
        balance = await get_balance(client, token)
        assert balance == "0.00"


# ========== 并发回调测试 ==========

@pytest.mark.asyncio
async def test_concurrent_callbacks_for_same_order(test_db):
    """测试同一订单的并发回调（防止竞态条件）"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await register_and_login_operator(client, "concurrent_callback_user")

        order_id = await create_recharge_order(client, token, "100.00")

        # 并发发送多个回调
        import asyncio
        tasks = [
            client.post(
                "/v1/webhooks/payment/wechat",
                json={
                    "order_id": order_id,
                    "status": "success",
                    "paid_amount": "100.00",
                    "transaction_id": f"txn_{order_id}_{i}",
                    "paid_at": "2025-01-15T12:30:00Z"
                }
            )
            for i in range(5)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证至少一个成功
        success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code in [200, 201])
        assert success_count >= 1

        # 验证余额只加了一次（幂等性）
        balance = await get_balance(client, token)
        assert balance == "100.00"


@pytest.mark.asyncio
async def test_callback_with_invalid_json(test_db):
    """测试回调JSON格式错误"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        callback_response = await client.post(
            "/v1/webhooks/payment/wechat",
            content="invalid json content",
            headers={"Content-Type": "application/json"}
        )

        # 应该返回400（JSON解析错误）
        assert callback_response.status_code == 400


@pytest.mark.asyncio
async def test_successful_callback_updates_transaction_record(test_db):
    """测试成功回调正确更新交易记录"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await register_and_login_operator(client, "tx_update_user")

        order_id = await create_recharge_order(client, token, "150.00")

        # 成功回调
        transaction_id = f"wxpay_txn_{order_id}_abc123"
        await client.post(
            "/v1/webhooks/payment/wechat",
            json={
                "order_id": order_id,
                "status": "success",
                "paid_amount": "150.00",
                "transaction_id": transaction_id,
                "paid_at": "2025-01-15T14:20:30Z"
            }
        )

        # 查询交易记录
        tx_response = await client.get(
            "/v1/operators/me/transactions",
            headers={"Authorization": f"Bearer {token}"}
        )
        transactions = tx_response.json()["items"]

        # 验证交易记录包含正确的transaction_id
        recharge_tx = next((tx for tx in transactions if tx["type"] == "recharge"), None)
        assert recharge_tx is not None
        assert recharge_tx["amount"] == "150.00"
        assert recharge_tx["status"] == "completed"
        assert recharge_tx["transaction_id"] == transaction_id
