"""单元测试：RefundService (T082)

测试RefundService的核心退款方法:
1. create_refund_request - 创建退款申请
2. calculate_refundable_balance - 计算可退余额
3. approve_refund - 审核通过退款
4. reject_refund - 拒绝退款

测试策略:
- 使用真实数据库会话(test_db fixture)
- 测试余额验证
- 测试事务完整性(退款记录+余额扣减+交易记录)
- 验证状态转换和业务规则
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import HTTPException
from uuid import uuid4

from src.services.refund import RefundService
from src.models.operator import OperatorAccount
from src.models.admin import AdminAccount
from src.models.refund import RefundRecord
from src.models.transaction import TransactionRecord
from sqlalchemy import select


@pytest.fixture
async def refund_test_data(test_db):
    """准备RefundService测试数据"""
    # 创建管理员
    admin = AdminAccount(
        username="admin_refund_test",
        password_hash="hashed_pw",
        full_name="Test Admin",
        email="admin@test.com",
        phone="13800138000",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    await test_db.flush()

    # 创建有余额的运营商
    operator_with_balance = OperatorAccount(
        username="op_refund_with_balance",
        full_name="Operator With Balance",
        email="with_balance@test.com",
        phone="13900000001",
        password_hash="hashed_password",
        api_key="refund_api_key_1_" + "a" * 46,
        api_key_hash="hashed_secret",
        balance=Decimal("500.00"),
        customer_tier="trial",
        is_active=True,
        is_locked=False,
    )
    test_db.add(operator_with_balance)
    await test_db.flush()

    # 创建余额为0的运营商
    operator_zero_balance = OperatorAccount(
        username="op_refund_zero_balance",
        full_name="Operator Zero Balance",
        email="zero_balance@test.com",
        phone="13900000002",
        password_hash="hashed_password",
        api_key="refund_api_key_2_" + "b" * 46,
        api_key_hash="hashed_secret",
        balance=Decimal("0.00"),
        customer_tier="trial",
        is_active=True,
        is_locked=False,
    )
    test_db.add(operator_zero_balance)
    await test_db.commit()
    await test_db.refresh(operator_with_balance)
    await test_db.refresh(operator_zero_balance)

    return {
        "admin": admin,
        "operator_with_balance": operator_with_balance,
        "operator_zero_balance": operator_zero_balance
    }


class TestCreateRefundRequest:
    """测试create_refund_request方法"""

    @pytest.mark.asyncio
    async def test_create_request_success(self, test_db, refund_test_data):
        """测试成功创建退款申请"""
        service = RefundService(test_db)
        operator = refund_test_data["operator_with_balance"]

        refund = await service.create_refund_request(
            operator_id=operator.id,
            reason="测试退款原因"
        )

        # 验证退款记录
        assert refund.operator_id == operator.id
        assert refund.requested_amount == Decimal("500.00")  # 等于当前余额
        assert refund.status == "pending"
        assert refund.refund_reason == "测试退款原因"
        assert refund.created_at is not None

    @pytest.mark.asyncio
    async def test_create_request_zero_balance_raises_400(self, test_db, refund_test_data):
        """测试余额为0时无法申请退款"""
        service = RefundService(test_db)
        operator = refund_test_data["operator_zero_balance"]

        with pytest.raises(HTTPException) as exc_info:
            await service.create_refund_request(
                operator_id=operator.id,
                reason="尝试退款"
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "INVALID_PARAMS"
        assert "余额为0" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_create_request_non_existent_operator_raises_404(self, test_db):
        """测试不存在的运营商申请退款抛出HTTP 404"""
        service = RefundService(test_db)

        non_existent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.create_refund_request(
                operator_id=non_existent_id,
                reason="退款"
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "OPERATOR_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_request_captures_balance_snapshot(self, test_db, refund_test_data):
        """测试退款申请记录余额快照"""
        service = RefundService(test_db)
        operator = refund_test_data["operator_with_balance"]

        # 创建退款申请
        refund = await service.create_refund_request(
            operator_id=operator.id,
            reason="余额快照测试"
        )

        original_amount = refund.requested_amount

        # 修改运营商余额(模拟后续消费)
        operator.balance = Decimal("300.00")
        await test_db.commit()

        # 验证退款申请的金额未变化(快照)
        await test_db.refresh(refund)
        assert refund.requested_amount == original_amount  # 仍为500.00


class TestCalculateRefundableBalance:
    """测试calculate_refundable_balance方法"""

    @pytest.mark.asyncio
    async def test_calculate_with_balance(self, test_db, refund_test_data):
        """测试计算有余额的可退金额"""
        service = RefundService(test_db)
        operator = refund_test_data["operator_with_balance"]

        refundable = await service.calculate_refundable_balance(operator.id)

        assert refundable == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_calculate_zero_balance(self, test_db, refund_test_data):
        """测试计算零余额的可退金额"""
        service = RefundService(test_db)
        operator = refund_test_data["operator_zero_balance"]

        refundable = await service.calculate_refundable_balance(operator.id)

        assert refundable == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_calculate_non_existent_operator_raises_404(self, test_db):
        """测试不存在的运营商计算可退余额抛出HTTP 404"""
        service = RefundService(test_db)

        non_existent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.calculate_refundable_balance(non_existent_id)

        assert exc_info.value.status_code == 404


class TestApproveRefund:
    """测试approve_refund方法"""

    @pytest.mark.asyncio
    async def test_approve_refund_success(self, test_db, refund_test_data):
        """测试成功审核通过退款"""
        service = RefundService(test_db)
        operator = refund_test_data["operator_with_balance"]
        admin = refund_test_data["admin"]

        # 先创建退款申请
        refund = await service.create_refund_request(
            operator_id=operator.id,
            reason="测试审核通过"
        )

        initial_balance = operator.balance

        # 审核通过
        approved_refund = await service.approve_refund(
            refund_id=refund.id,
            approved_by=admin.id
        )

        # 验证退款记录
        assert approved_refund.status == "approved"
        assert approved_refund.actual_refund_amount == Decimal("500.00")
        assert approved_refund.reviewed_by == admin.id
        assert approved_refund.reviewed_at is not None

        # 验证余额扣减
        await test_db.refresh(operator)
        assert operator.balance == Decimal("0.00")

        # 验证交易记录创建
        stmt = select(TransactionRecord).where(
            TransactionRecord.operator_id == operator.id,
            TransactionRecord.transaction_type == "refund"
        )
        result = await test_db.execute(stmt)
        transaction = result.scalar_one()

        assert transaction.amount == Decimal("-500.00")  # 负数表示扣减
        assert transaction.balance_before == initial_balance
        assert transaction.balance_after == Decimal("0.00")
        assert transaction.related_refund_id == refund.id
        assert transaction.payment_status == "success"

    @pytest.mark.asyncio
    async def test_approve_refund_with_custom_amount(self, test_db, refund_test_data):
        """测试指定实际退款金额(部分退款)"""
        service = RefundService(test_db)
        operator = refund_test_data["operator_with_balance"]
        admin = refund_test_data["admin"]

        # 申请退500元
        refund = await service.create_refund_request(
            operator_id=operator.id,
            reason="部分退款测试"
        )

        # 实际只退300元
        approved_refund = await service.approve_refund(
            refund_id=refund.id,
            approved_by=admin.id,
            actual_refund_amount=Decimal("300.00")
        )

        assert approved_refund.actual_refund_amount == Decimal("300.00")

        # 验证余额只扣减300元
        await test_db.refresh(operator)
        assert operator.balance == Decimal("200.00")  # 500 - 300

    @pytest.mark.asyncio
    async def test_approve_refund_invalid_status_raises_400(self, test_db, refund_test_data):
        """测试非pending状态无法审核"""
        service = RefundService(test_db)
        operator = refund_test_data["operator_with_balance"]
        admin = refund_test_data["admin"]

        # 创建并审核通过一次
        refund = await service.create_refund_request(
            operator_id=operator.id,
            reason="重复审核测试"
        )

        await service.approve_refund(
            refund_id=refund.id,
            approved_by=admin.id
        )

        # 尝试再次审核
        with pytest.raises(HTTPException) as exc_info:
            await service.approve_refund(
                refund_id=refund.id,
                approved_by=admin.id
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "INVALID_REFUND_STATUS"

    @pytest.mark.asyncio
    async def test_approve_refund_insufficient_balance_raises_400(self, test_db, refund_test_data):
        """测试余额不足时无法审核通过"""
        service = RefundService(test_db)
        operator = refund_test_data["operator_with_balance"]
        admin = refund_test_data["admin"]

        # 创建退款申请(此时余额500)
        refund = await service.create_refund_request(
            operator_id=operator.id,
            reason="余额不足测试"
        )

        # 模拟余额减少
        operator.balance = Decimal("100.00")
        await test_db.commit()

        # 尝试审核通过(需要500但只有100)
        with pytest.raises(HTTPException) as exc_info:
            await service.approve_refund(
                refund_id=refund.id,
                approved_by=admin.id
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "INSUFFICIENT_BALANCE"

    @pytest.mark.asyncio
    async def test_approve_refund_non_existent_raises_404(self, test_db, refund_test_data):
        """测试不存在的退款申请抛出HTTP 404"""
        service = RefundService(test_db)
        admin = refund_test_data["admin"]

        non_existent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.approve_refund(
                refund_id=non_existent_id,
                approved_by=admin.id
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "REFUND_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_approve_refund_transaction_atomicity(self, test_db, refund_test_data):
        """测试退款事务原子性"""
        service = RefundService(test_db)
        operator = refund_test_data["operator_with_balance"]
        admin = refund_test_data["admin"]

        refund = await service.create_refund_request(
            operator_id=operator.id,
            reason="事务原子性测试"
        )

        initial_balance = operator.balance

        await service.approve_refund(
            refund_id=refund.id,
            approved_by=admin.id
        )

        # 验证三处都已更新
        await test_db.refresh(refund)
        await test_db.refresh(operator)

        # 1. 退款记录
        assert refund.status == "approved"

        # 2. 运营商余额
        assert operator.balance == Decimal("0.00")

        # 3. 交易记录
        stmt = select(TransactionRecord).where(
            TransactionRecord.related_refund_id == refund.id
        )
        result = await test_db.execute(stmt)
        transaction = result.scalar_one()

        assert transaction.transaction_type == "refund"
        assert transaction.amount == Decimal("-500.00")
        assert transaction.balance_before == initial_balance
        assert transaction.balance_after == Decimal("0.00")


class TestRejectRefund:
    """测试reject_refund方法"""

    @pytest.mark.asyncio
    async def test_reject_refund_success(self, test_db, refund_test_data):
        """测试成功拒绝退款申请"""
        service = RefundService(test_db)
        operator = refund_test_data["operator_with_balance"]
        admin = refund_test_data["admin"]

        # 创建退款申请
        refund = await service.create_refund_request(
            operator_id=operator.id,
            reason="测试拒绝"
        )

        initial_balance = operator.balance

        # 拒绝退款
        rejected_refund = await service.reject_refund(
            refund_id=refund.id,
            reviewed_by=admin.id,
            reject_reason="余额过高,不予退款"
        )

        # 验证退款记录
        assert rejected_refund.status == "rejected"
        assert rejected_refund.reject_reason == "余额过高,不予退款"
        assert rejected_refund.reviewed_by == admin.id
        assert rejected_refund.reviewed_at is not None
        assert rejected_refund.actual_refund_amount is None

        # 验证余额未变化
        await test_db.refresh(operator)
        assert operator.balance == initial_balance

        # 验证未创建交易记录
        stmt = select(TransactionRecord).where(
            TransactionRecord.related_refund_id == refund.id
        )
        result = await test_db.execute(stmt)
        transaction = result.scalar_one_or_none()
        assert transaction is None

    @pytest.mark.asyncio
    async def test_reject_refund_invalid_status_raises_400(self, test_db, refund_test_data):
        """测试非pending状态无法拒绝"""
        service = RefundService(test_db)
        operator = refund_test_data["operator_with_balance"]
        admin = refund_test_data["admin"]

        # 创建并拒绝一次
        refund = await service.create_refund_request(
            operator_id=operator.id,
            reason="重复拒绝测试"
        )

        await service.reject_refund(
            refund_id=refund.id,
            reviewed_by=admin.id,
            reject_reason="第一次拒绝"
        )

        # 尝试再次拒绝
        with pytest.raises(HTTPException) as exc_info:
            await service.reject_refund(
                refund_id=refund.id,
                reviewed_by=admin.id,
                reject_reason="第二次拒绝"
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "INVALID_REFUND_STATUS"

    @pytest.mark.asyncio
    async def test_reject_refund_non_existent_raises_404(self, test_db):
        """测试不存在的退款申请抛出HTTP 404"""
        service = RefundService(test_db)

        non_existent_id = uuid4()
        admin_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.reject_refund(
                refund_id=non_existent_id,
                reviewed_by=admin_id,
                reject_reason="拒绝"
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "REFUND_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_reject_after_approve_fails(self, test_db, refund_test_data):
        """测试已审核通过的退款无法再拒绝"""
        service = RefundService(test_db)
        operator = refund_test_data["operator_with_balance"]
        admin = refund_test_data["admin"]

        # 创建并审核通过
        refund = await service.create_refund_request(
            operator_id=operator.id,
            reason="先通过后拒绝测试"
        )

        await service.approve_refund(
            refund_id=refund.id,
            approved_by=admin.id
        )

        # 尝试拒绝已通过的申请
        with pytest.raises(HTTPException) as exc_info:
            await service.reject_refund(
                refund_id=refund.id,
                reviewed_by=admin.id,
                reject_reason="尝试拒绝"
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "INVALID_REFUND_STATUS"
