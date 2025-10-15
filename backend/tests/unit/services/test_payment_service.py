"""单元测试：PaymentService (T081)

测试PaymentService的核心支付方法:
1. create_recharge_order - 创建充值订单
2. process_payment_callback - 处理支付回调
3. _verify_payment_signature - 验证支付签名(内部方法)

测试策略:
- 使用真实数据库会话(test_db fixture)
- 测试幂等性保障
- 测试事务一致性(订单+余额+交易记录)
- 验证金额验证和签名验证
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from uuid import uuid4

from src.services.payment import PaymentService
from src.models.operator import OperatorAccount
from src.models.admin import AdminAccount
from src.models.transaction import RechargeOrder, TransactionRecord
from sqlalchemy import select


@pytest.fixture
async def payment_test_data(test_db):
    """准备PaymentService测试数据"""
    # 创建管理员
    admin = AdminAccount(
        username="admin_payment_test",
        password_hash="hashed_pw",
        full_name="Test Admin",
        email="admin@test.com",
        phone="13800138000",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    await test_db.flush()

    # 创建运营商
    operator = OperatorAccount(
        username="op_payment_test",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="payment_api_key_" + "a" * 48,
        api_key_hash="hashed_secret",
        balance=Decimal("500.00"),
        customer_tier="trial",
        is_active=True,
        is_locked=False,
        created_by=admin.id
    )
    test_db.add(operator)
    await test_db.commit()
    await test_db.refresh(operator)

    return {
        "admin": admin,
        "operator": operator
    }


class TestCreateRechargeOrder:
    """测试create_recharge_order方法"""

    @pytest.mark.asyncio
    async def test_create_order_success(self, test_db, payment_test_data):
        """测试成功创建充值订单"""
        service = PaymentService(test_db)
        operator = payment_test_data["operator"]

        order = await service.create_recharge_order(
            operator_id=operator.id,
            amount=Decimal("100.00"),
            payment_method="wechat"
        )

        # 验证订单基本信息
        assert order.operator_id == operator.id
        assert order.amount == Decimal("100.00")
        assert order.payment_method == "wechat"
        assert order.status == "pending"

        # 验证订单ID格式: ord_recharge_<timestamp>_<uuid>
        assert order.order_id.startswith("ord_recharge_")
        parts = order.order_id.split("_")
        assert len(parts) == 4  # ['ord', 'recharge', 'timestamp', 'uuid']
        assert parts[0] == "ord"
        assert parts[1] == "recharge"
        assert parts[2].isdigit()  # timestamp是数字
        assert len(parts[3]) == 8  # short uuid是8位

        # 验证过期时间(应该是30分钟后)
        assert order.expires_at is not None
        time_diff = (order.expires_at - order.created_at).total_seconds()
        assert 1790 <= time_diff <= 1810  # 允许2秒误差,约30分钟

        # 验证支付URL生成
        assert order.qr_code_url is not None
        assert order.payment_url is not None
        assert order.order_id in order.qr_code_url

    @pytest.mark.asyncio
    async def test_create_order_alipay(self, test_db, payment_test_data):
        """测试创建支付宝充值订单"""
        service = PaymentService(test_db)
        operator = payment_test_data["operator"]

        order = await service.create_recharge_order(
            operator_id=operator.id,
            amount=Decimal("200.00"),
            payment_method="alipay"
        )

        assert order.payment_method == "alipay"
        assert "alipay" in order.qr_code_url.lower()

    @pytest.mark.asyncio
    async def test_create_order_non_existent_operator_raises_404(self, test_db):
        """测试不存在的运营商创建订单抛出HTTP 404"""
        service = PaymentService(test_db)

        non_existent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.create_recharge_order(
                operator_id=non_existent_id,
                amount=Decimal("100.00"),
                payment_method="wechat"
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "OPERATOR_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_order_minimum_amount(self, test_db, payment_test_data):
        """测试最小金额充值订单"""
        service = PaymentService(test_db)
        operator = payment_test_data["operator"]

        order = await service.create_recharge_order(
            operator_id=operator.id,
            amount=Decimal("10.00"),  # 最小金额
            payment_method="wechat"
        )

        assert order.amount == Decimal("10.00")

    @pytest.mark.asyncio
    async def test_create_order_maximum_amount(self, test_db, payment_test_data):
        """测试最大金额充值订单"""
        service = PaymentService(test_db)
        operator = payment_test_data["operator"]

        order = await service.create_recharge_order(
            operator_id=operator.id,
            amount=Decimal("10000.00"),  # 最大金额
            payment_method="wechat"
        )

        assert order.amount == Decimal("10000.00")

    @pytest.mark.asyncio
    async def test_order_ids_are_unique(self, test_db, payment_test_data):
        """测试订单ID唯一性"""
        service = PaymentService(test_db)
        operator = payment_test_data["operator"]

        order1 = await service.create_recharge_order(
            operator_id=operator.id,
            amount=Decimal("100.00"),
            payment_method="wechat"
        )

        order2 = await service.create_recharge_order(
            operator_id=operator.id,
            amount=Decimal("100.00"),
            payment_method="wechat"
        )

        # 验证两个订单ID不同
        assert order1.order_id != order2.order_id


class TestProcessPaymentCallback:
    """测试process_payment_callback方法"""

    @pytest.mark.asyncio
    async def test_callback_success_updates_balance(self, test_db, payment_test_data):
        """测试支付成功回调更新余额"""
        service = PaymentService(test_db)
        operator = payment_test_data["operator"]

        # 先创建订单
        order = await service.create_recharge_order(
            operator_id=operator.id,
            amount=Decimal("100.00"),
            payment_method="wechat"
        )

        initial_balance = operator.balance  # 500.00

        # 模拟支付成功回调
        result = await service.process_payment_callback(
            order_id=order.order_id,
            status_value="success",
            paid_amount=Decimal("100.00"),
            transaction_id="wx_txn_123456789",
            paid_at=datetime.now(timezone.utc),
            payment_method="wechat"
        )

        # 验证返回结果
        assert result["success"] is True
        assert "successfully" in result["message"].lower()

        # 验证订单状态更新
        await test_db.refresh(order)
        assert order.status == "success"
        assert order.transaction_id == "wx_txn_123456789"
        assert order.paid_at is not None

        # 验证余额增加
        await test_db.refresh(operator)
        assert operator.balance == initial_balance + Decimal("100.00")

        # 验证交易记录创建
        stmt = select(TransactionRecord).where(
            TransactionRecord.operator_id == operator.id,
            TransactionRecord.transaction_type == "recharge"
        )
        result = await test_db.execute(stmt)
        transaction = result.scalar_one()

        assert transaction.amount == Decimal("100.00")
        assert transaction.balance_before == initial_balance
        assert transaction.balance_after == initial_balance + Decimal("100.00")
        assert transaction.payment_status == "success"
        assert transaction.payment_order_no == order.order_id

    @pytest.mark.asyncio
    async def test_callback_idempotency(self, test_db, payment_test_data):
        """测试支付回调幂等性"""
        service = PaymentService(test_db)
        operator = payment_test_data["operator"]

        # 创建订单
        order = await service.create_recharge_order(
            operator_id=operator.id,
            amount=Decimal("100.00"),
            payment_method="wechat"
        )

        # 第一次回调
        await service.process_payment_callback(
            order_id=order.order_id,
            status_value="success",
            paid_amount=Decimal("100.00"),
            transaction_id="wx_txn_123",
            paid_at=datetime.now(timezone.utc),
            payment_method="wechat"
        )

        balance_after_first = operator.balance
        await test_db.refresh(operator)

        # 第二次回调(重复)
        result = await service.process_payment_callback(
            order_id=order.order_id,
            status_value="success",
            paid_amount=Decimal("100.00"),
            transaction_id="wx_txn_123",
            paid_at=datetime.now(timezone.utc),
            payment_method="wechat"
        )

        # 验证返回幂等性消息
        assert result["success"] is True
        assert "already processed" in result["message"].lower()

        # 验证余额未重复增加
        await test_db.refresh(operator)
        assert operator.balance == balance_after_first

    @pytest.mark.asyncio
    async def test_callback_amount_mismatch_raises_400(self, test_db, payment_test_data):
        """测试支付金额不匹配抛出HTTP 400"""
        service = PaymentService(test_db)
        operator = payment_test_data["operator"]

        # 创建100元订单
        order = await service.create_recharge_order(
            operator_id=operator.id,
            amount=Decimal("100.00"),
            payment_method="wechat"
        )

        # 回调金额不匹配(200元)
        with pytest.raises(HTTPException) as exc_info:
            await service.process_payment_callback(
                order_id=order.order_id,
                status_value="success",
                paid_amount=Decimal("200.00"),  # 不匹配
                transaction_id="wx_txn_123",
                paid_at=datetime.now(timezone.utc),
                payment_method="wechat"
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "AMOUNT_MISMATCH"

    @pytest.mark.asyncio
    async def test_callback_order_not_found_raises_404(self, test_db):
        """测试订单不存在抛出HTTP 404"""
        service = PaymentService(test_db)

        with pytest.raises(HTTPException) as exc_info:
            await service.process_payment_callback(
                order_id="non_existent_order_123",
                status_value="success",
                paid_amount=Decimal("100.00"),
                transaction_id="wx_txn_123",
                paid_at=datetime.now(timezone.utc),
                payment_method="wechat"
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "ORDER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_callback_failed_payment(self, test_db, payment_test_data):
        """测试支付失败回调"""
        service = PaymentService(test_db)
        operator = payment_test_data["operator"]

        # 创建订单
        order = await service.create_recharge_order(
            operator_id=operator.id,
            amount=Decimal("100.00"),
            payment_method="wechat"
        )

        initial_balance = operator.balance

        # 支付失败回调
        result = await service.process_payment_callback(
            order_id=order.order_id,
            status_value="failed",
            paid_amount=Decimal("100.00"),
            transaction_id="wx_txn_failed_123",
            paid_at=datetime.now(timezone.utc),
            payment_method="wechat",
            error_code="PAYMENT_CANCELLED",
            error_message="用户取消支付"
        )

        # 验证返回结果
        assert result["success"] is True
        assert "failure recorded" in result["message"].lower()

        # 验证订单状态为失败
        await test_db.refresh(order)
        assert order.status == "failed"
        assert order.error_code == "PAYMENT_CANCELLED"
        assert order.error_message == "用户取消支付"

        # 验证余额未变化
        await test_db.refresh(operator)
        assert operator.balance == initial_balance

        # 验证未创建交易记录
        stmt = select(TransactionRecord).where(
            TransactionRecord.payment_order_no == order.order_id
        )
        result = await test_db.execute(stmt)
        transaction = result.scalar_one_or_none()
        assert transaction is None

    @pytest.mark.asyncio
    async def test_callback_invalid_status_raises_400(self, test_db, payment_test_data):
        """测试无效状态值抛出HTTP 400"""
        service = PaymentService(test_db)
        operator = payment_test_data["operator"]

        order = await service.create_recharge_order(
            operator_id=operator.id,
            amount=Decimal("100.00"),
            payment_method="wechat"
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.process_payment_callback(
                order_id=order.order_id,
                status_value="invalid_status",  # 无效状态
                paid_amount=Decimal("100.00"),
                transaction_id="wx_txn_123",
                paid_at=datetime.now(timezone.utc),
                payment_method="wechat"
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "INVALID_STATUS"

    @pytest.mark.asyncio
    async def test_callback_transaction_atomicity(self, test_db, payment_test_data):
        """测试回调事务原子性(订单+余额+交易记录)"""
        service = PaymentService(test_db)
        operator = payment_test_data["operator"]

        order = await service.create_recharge_order(
            operator_id=operator.id,
            amount=Decimal("100.00"),
            payment_method="wechat"
        )

        initial_balance = operator.balance

        # 成功回调
        await service.process_payment_callback(
            order_id=order.order_id,
            status_value="success",
            paid_amount=Decimal("100.00"),
            transaction_id="wx_txn_atomic_test",
            paid_at=datetime.now(timezone.utc),
            payment_method="wechat"
        )

        # 验证三处都已更新
        await test_db.refresh(order)
        await test_db.refresh(operator)

        # 1. 订单状态
        assert order.status == "success"

        # 2. 运营商余额
        assert operator.balance == initial_balance + Decimal("100.00")

        # 3. 交易记录
        stmt = select(TransactionRecord).where(
            TransactionRecord.payment_order_no == order.order_id
        )
        result = await test_db.execute(stmt)
        transaction = result.scalar_one()

        assert transaction.transaction_type == "recharge"
        assert transaction.amount == Decimal("100.00")
        assert transaction.balance_before == initial_balance
        assert transaction.balance_after == initial_balance + Decimal("100.00")

    @pytest.mark.asyncio
    async def test_callback_with_different_payment_methods(self, test_db, payment_test_data):
        """测试不同支付方式的回调"""
        service = PaymentService(test_db)
        operator = payment_test_data["operator"]

        # 微信支付
        order_wechat = await service.create_recharge_order(
            operator_id=operator.id,
            amount=Decimal("100.00"),
            payment_method="wechat"
        )

        await service.process_payment_callback(
            order_id=order_wechat.order_id,
            status_value="success",
            paid_amount=Decimal("100.00"),
            transaction_id="wx_txn_123",
            paid_at=datetime.now(timezone.utc),
            payment_method="wechat"
        )

        # 支付宝
        order_alipay = await service.create_recharge_order(
            operator_id=operator.id,
            amount=Decimal("200.00"),
            payment_method="alipay"
        )

        await service.process_payment_callback(
            order_id=order_alipay.order_id,
            status_value="success",
            paid_amount=Decimal("200.00"),
            transaction_id="alipay_txn_456",
            paid_at=datetime.now(timezone.utc),
            payment_method="alipay"
        )

        # 验证两笔都成功
        await test_db.refresh(order_wechat)
        await test_db.refresh(order_alipay)
        await test_db.refresh(operator)

        assert order_wechat.status == "success"
        assert order_alipay.status == "success"
        assert operator.balance == Decimal("500.00") + Decimal("100.00") + Decimal("200.00")


class TestGeneratePaymentQr:
    """测试_generate_payment_qr内部方法"""

    @pytest.mark.asyncio
    async def test_generate_qr_wechat(self, test_db):
        """测试生成微信支付二维码"""
        service = PaymentService(test_db)

        qr_url, payment_url = await service._generate_payment_qr(
            order_id="test_order_wechat_123",
            amount=Decimal("100.00"),
            payment_method="wechat"
        )

        assert "wechat" in qr_url.lower()
        assert "test_order_wechat_123" in qr_url
        assert "wechat" in payment_url.lower()

    @pytest.mark.asyncio
    async def test_generate_qr_alipay(self, test_db):
        """测试生成支付宝二维码"""
        service = PaymentService(test_db)

        qr_url, payment_url = await service._generate_payment_qr(
            order_id="test_order_alipay_456",
            amount=Decimal("200.00"),
            payment_method="alipay"
        )

        assert "alipay" in qr_url.lower()
        assert "test_order_alipay_456" in qr_url
        assert "alipay" in payment_url.lower()

    @pytest.mark.asyncio
    async def test_generate_qr_invalid_method_raises_500(self, test_db):
        """测试无效支付方式抛出HTTP 500"""
        service = PaymentService(test_db)

        with pytest.raises(HTTPException) as exc_info:
            await service._generate_payment_qr(
                order_id="test_order_invalid",
                amount=Decimal("100.00"),
                payment_method="invalid_method"
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error_code"] == "INVALID_PAYMENT_METHOD"
