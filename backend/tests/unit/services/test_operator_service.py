"""单元测试：OperatorService (T080)

测试OperatorService的核心业务方法:
1. register - 运营商注册
2. login - 运营商登录
3. get_profile/update_profile - 个人信息管理
4. deactivate_account - 账户注销
5. regenerate_api_key - API Key重新生成
6. get_transactions/get_refunds/get_invoices - 查询方法
7. apply_refund/apply_invoice - 申请方法

测试策略:
- 使用真实数据库会话(test_db fixture)
- 验证密码哈希和API Key生成
- 测试JWT Token生成
- 验证业务规则和异常处理
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from uuid import uuid4

from src.services.operator import OperatorService
from src.models.operator import OperatorAccount
from src.models.admin import AdminAccount
from src.models.transaction import TransactionRecord
from src.models.refund import RefundRecord
from src.models.invoice import InvoiceRecord
from src.schemas.operator import OperatorRegisterRequest, OperatorUpdateRequest
from src.core.utils.password import verify_password
from sqlalchemy import select


@pytest.fixture
async def admin_account(test_db):
    """创建管理员账户用于测试"""
    admin = AdminAccount(
        username="admin_operator_test",
        password_hash="hashed_pw",
        full_name="Test Admin",
        email="admin@test.com",
        phone="13800138000",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


@pytest.fixture
async def operator_test_data(test_db, admin_account):
    """准备OperatorService测试数据"""
    # 创建已存在的运营商(用于登录测试)
    from src.core.utils.password import hash_password

    operator = OperatorAccount(
        username="existing_operator",
        full_name="Existing Operator",
        email="existing@test.com",
        phone="13900000001",
        password_hash=hash_password("password123"),
        api_key="existing_api_key_" + "a" * 48,
        api_key_hash=hash_password("existing_api_key_" + "a" * 48),
        balance=Decimal("500.00"),
        customer_tier="trial",  # 使用schema和数据库都支持的值
        is_active=True,
        is_locked=False,
        created_by=admin_account.id
    )
    test_db.add(operator)
    await test_db.commit()
    await test_db.refresh(operator)

    # 创建锁定的运营商(用于测试登录失败)
    locked_operator = OperatorAccount(
        username="locked_operator",
        full_name="Locked Operator",
        email="locked@test.com",
        phone="13900000002",
        password_hash=hash_password("password123"),
        api_key="locked_api_key_" + "b" * 48,
        api_key_hash=hash_password("locked_api_key_" + "b" * 48),
        balance=Decimal("0.00"),
        customer_tier="trial",
        is_active=True,
        is_locked=True,
        locked_reason="安全原因",
        created_by=admin_account.id
    )
    test_db.add(locked_operator)
    await test_db.commit()
    await test_db.refresh(locked_operator)

    # 创建已注销的运营商
    deactivated_operator = OperatorAccount(
        username="deactivated_operator",
        full_name="Deactivated Operator",
        email="deactivated@test.com",
        phone="13900000003",
        password_hash=hash_password("password123"),
        api_key="deactivated_key_" + "c" * 48,
        api_key_hash=hash_password("deactivated_key_" + "c" * 48),
        balance=Decimal("0.00"),
        customer_tier="trial",
        is_active=False,
        is_locked=False,
        deleted_at=datetime.now(timezone.utc),
        created_by=admin_account.id
    )
    test_db.add(deactivated_operator)
    await test_db.commit()
    await test_db.refresh(deactivated_operator)

    return {
        "admin": admin_account,
        "operator": operator,
        "locked_operator": locked_operator,
        "deactivated_operator": deactivated_operator
    }


class TestRegister:
    """测试register方法"""

    @pytest.mark.asyncio
    async def test_successful_registration(self, test_db, admin_account):
        """测试成功注册运营商"""
        service = OperatorService(test_db)

        request = OperatorRegisterRequest(
            username="new_operator_001",
            password="StrongPass123",  # 需要大小写字母+数字
            name="New Operator",
            phone="13900000100",
            email="new_operator@test.com"
        )

        result = await service.register(request)

        # 验证返回数据
        assert result.username == "new_operator_001"
        assert result.operator_id.startswith("op_")
        assert result.category == "trial"  # 新注册默认trial
        assert result.balance == "0.00"
        assert len(result.api_key) == 64  # 64位十六进制API Key
        assert result.created_at is not None

        # 验证数据库记录
        stmt = select(OperatorAccount).where(
            OperatorAccount.username == "new_operator_001"
        )
        db_result = await test_db.execute(stmt)
        operator = db_result.scalar_one()

        assert operator.full_name == "New Operator"
        assert operator.email == "new_operator@test.com"
        assert operator.phone == "13900000100"
        assert operator.is_active is True
        assert operator.is_locked is False
        assert verify_password("StrongPass123", operator.password_hash)
        # API Key明文存储用于认证
        assert operator.api_key == result.api_key
        # API Key Hash用于额外安全验证
        assert verify_password(result.api_key, operator.api_key_hash)

    @pytest.mark.asyncio
    async def test_duplicate_username_raises_400(self, test_db, operator_test_data):
        """测试用户名已存在抛出HTTP 400"""
        service = OperatorService(test_db)

        request = OperatorRegisterRequest(
            username="existing_operator",  # 已存在的用户名
            password="Password123",  # 需要大小写字母+数字
            name="Duplicate Operator",
            phone="13900000200",
            email="duplicate@test.com"
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.register(request)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "USERNAME_EXISTS"
        assert "用户名已被注册" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_password_is_hashed(self, test_db):
        """测试密码被正确哈希存储"""
        service = OperatorService(test_db)

        request = OperatorRegisterRequest(
            username="password_test_user",
            password="MySecret123",  # 需要大小写字母+数字
            name="Password Test User",
            phone="13900000300",
            email="password_test@test.com"
        )

        result = await service.register(request)

        # 查询数据库中的记录
        stmt = select(OperatorAccount).where(
            OperatorAccount.username == "password_test_user"
        )
        db_result = await test_db.execute(stmt)
        operator = db_result.scalar_one()

        # 验证密码未明文存储
        assert operator.password_hash != "MySecret123"
        # 验证密码哈希可以被验证
        assert verify_password("MySecret123", operator.password_hash)

    @pytest.mark.asyncio
    async def test_api_key_is_unique_random(self, test_db):
        """测试API Key是唯一的随机值"""
        service = OperatorService(test_db)

        request1 = OperatorRegisterRequest(
            username="api_test_user_1",
            password="Password1",  # 需要大小写字母+数字
            name="API Test User 1",
            phone="13900000400",
            email="api1@test.com"
        )

        request2 = OperatorRegisterRequest(
            username="api_test_user_2",
            password="Password2",  # 需要大小写字母+数字
            name="API Test User 2",
            phone="13900000401",
            email="api2@test.com"
        )

        result1 = await service.register(request1)
        result2 = await service.register(request2)

        # 验证两个API Key不相同
        assert result1.api_key != result2.api_key
        # 验证长度符合要求
        assert len(result1.api_key) == 64
        assert len(result2.api_key) == 64


class TestLogin:
    """测试login方法"""

    @pytest.mark.asyncio
    async def test_successful_login(self, test_db, operator_test_data):
        """测试成功登录"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        result = await service.login(
            username="existing_operator",
            password="password123",
            login_ip="192.168.1.100"
        )

        # 验证返回数据
        assert result.success is True
        assert result.data.access_token is not None
        assert result.data.token_type == "Bearer"
        assert result.data.expires_in == 2592000  # 30天 = 2592000秒
        assert result.data.operator.username == "existing_operator"
        assert result.data.operator.category == "trial"

        # 验证last_login_at和last_login_ip被更新
        await test_db.refresh(operator)
        assert operator.last_login_at is not None
        assert operator.last_login_ip == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_wrong_username_raises_401(self, test_db, operator_test_data):
        """测试错误的用户名抛出HTTP 401"""
        service = OperatorService(test_db)

        with pytest.raises(HTTPException) as exc_info:
            await service.login(
                username="non_existent_user",
                password="password123"
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "UNAUTHORIZED"
        assert "用户名或密码错误" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_wrong_password_raises_401(self, test_db, operator_test_data):
        """测试错误的密码抛出HTTP 401"""
        service = OperatorService(test_db)

        with pytest.raises(HTTPException) as exc_info:
            await service.login(
                username="existing_operator",
                password="wrong_password"
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "UNAUTHORIZED"

    @pytest.mark.asyncio
    async def test_locked_account_raises_403(self, test_db, operator_test_data):
        """测试锁定账户抛出HTTP 403"""
        service = OperatorService(test_db)

        with pytest.raises(HTTPException) as exc_info:
            await service.login(
                username="locked_operator",
                password="password123"
            )

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "ACCOUNT_LOCKED"
        assert "账户已被锁定" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_deactivated_account_raises_401(self, test_db, operator_test_data):
        """测试已注销账户抛出HTTP 401(因为查询时过滤了deleted_at不为None的记录)"""
        service = OperatorService(test_db)

        with pytest.raises(HTTPException) as exc_info:
            await service.login(
                username="deactivated_operator",
                password="password123"
            )

        # 由于查询时where条件包含deleted_at.is_(None),已注销账户会被过滤掉
        # 因此返回401 UNAUTHORIZED而不是403
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "UNAUTHORIZED"

    @pytest.mark.asyncio
    async def test_login_without_ip_address(self, test_db, operator_test_data):
        """测试不提供IP地址的登录"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        result = await service.login(
            username="existing_operator",
            password="password123"
            # 不提供login_ip
        )

        assert result.success is True

        # 验证last_login_at被更新,但last_login_ip未更新
        await test_db.refresh(operator)
        assert operator.last_login_at is not None


class TestGetProfile:
    """测试get_profile方法"""

    @pytest.mark.asyncio
    async def test_get_existing_operator_profile(self, test_db, operator_test_data):
        """测试获取已存在运营商的个人信息"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        result = await service.get_profile(operator.id)

        assert result.operator_id == operator.id
        assert result.username == "existing_operator"
        assert result.name == "Existing Operator"
        assert result.phone == "13900000001"
        assert result.email == "existing@test.com"
        assert result.category == "trial"
        assert result.balance == "500.00"
        assert result.is_active is True
        assert result.is_locked is False

    @pytest.mark.asyncio
    async def test_get_non_existent_operator_raises_404(self, test_db):
        """测试获取不存在的运营商抛出HTTP 404"""
        service = OperatorService(test_db)

        non_existent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.get_profile(non_existent_id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "OPERATOR_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_deleted_operator_raises_404(self, test_db, operator_test_data):
        """测试获取已删除运营商抛出HTTP 404(软删除)"""
        service = OperatorService(test_db)
        deactivated = operator_test_data["deactivated_operator"]

        with pytest.raises(HTTPException) as exc_info:
            await service.get_profile(deactivated.id)

        assert exc_info.value.status_code == 404


class TestUpdateProfile:
    """测试update_profile方法"""

    @pytest.mark.asyncio
    async def test_update_all_fields(self, test_db, operator_test_data):
        """测试更新所有允许更新的字段"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        request = OperatorUpdateRequest(
            name="Updated Name",
            phone="13900009999",
            email="updated@test.com"
        )

        result = await service.update_profile(operator.id, request)

        assert result.name == "Updated Name"
        assert result.phone == "13900009999"
        assert result.email == "updated@test.com"
        # 验证其他字段未变
        assert result.username == "existing_operator"
        assert result.balance == "500.00"

    @pytest.mark.asyncio
    async def test_update_partial_fields(self, test_db, operator_test_data):
        """测试部分字段更新"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        request = OperatorUpdateRequest(
            name="Partial Update"
            # 只更新name
        )

        result = await service.update_profile(operator.id, request)

        assert result.name == "Partial Update"
        # 验证未提供的字段保持不变
        assert result.phone == "13900000001"
        assert result.email == "existing@test.com"

    @pytest.mark.asyncio
    async def test_update_non_existent_operator_raises_404(self, test_db):
        """测试更新不存在的运营商抛出HTTP 404"""
        service = OperatorService(test_db)

        request = OperatorUpdateRequest(
            name="New Name"
        )

        non_existent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.update_profile(non_existent_id, request)

        assert exc_info.value.status_code == 404


class TestDeactivateAccount:
    """测试deactivate_account方法"""

    @pytest.mark.asyncio
    async def test_deactivate_account_with_zero_balance(self, test_db, operator_test_data):
        """测试注销余额为0的账户"""
        service = OperatorService(test_db)
        locked_operator = operator_test_data["locked_operator"]  # 余额为0

        await service.deactivate_account(locked_operator.id)

        # 验证账户状态
        await test_db.refresh(locked_operator)
        assert locked_operator.is_active is False
        assert locked_operator.deleted_at is not None

    @pytest.mark.asyncio
    async def test_deactivate_account_with_positive_balance_raises_400(self, test_db, operator_test_data):
        """测试注销余额不为0的账户抛出HTTP 400"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]  # 余额500元

        with pytest.raises(HTTPException) as exc_info:
            await service.deactivate_account(operator.id)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "BALANCE_NOT_ZERO"
        assert "500.00" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_deactivate_non_existent_account_raises_404(self, test_db):
        """测试注销不存在的账户抛出HTTP 404"""
        service = OperatorService(test_db)

        non_existent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.deactivate_account(non_existent_id)

        assert exc_info.value.status_code == 404


class TestRegenerateApiKey:
    """测试regenerate_api_key方法"""

    @pytest.mark.asyncio
    async def test_regenerate_api_key_success(self, test_db, operator_test_data):
        """测试成功重新生成API Key"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        old_api_key = operator.api_key

        new_api_key = await service.regenerate_api_key(operator.id)

        # 验证新API Key与旧的不同
        assert new_api_key != old_api_key
        assert len(new_api_key) == 64

        # 验证数据库中的API Key已更新
        await test_db.refresh(operator)
        assert operator.api_key == new_api_key
        assert verify_password(new_api_key, operator.api_key_hash)

    @pytest.mark.asyncio
    async def test_regenerate_api_key_non_existent_operator_raises_404(self, test_db):
        """测试为不存在的运营商重新生成API Key抛出HTTP 404"""
        service = OperatorService(test_db)

        non_existent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.regenerate_api_key(non_existent_id)

        assert exc_info.value.status_code == 404


class TestGetTransactions:
    """测试get_transactions方法"""

    @pytest.mark.asyncio
    async def test_get_transactions_empty_list(self, test_db, operator_test_data):
        """测试查询空交易记录列表"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        transactions, total = await service.get_transactions(operator.id)

        assert transactions == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_transactions_with_data(self, test_db, operator_test_data):
        """测试查询包含数据的交易记录"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        # 创建测试交易记录
        transaction1 = TransactionRecord(
            operator_id=operator.id,
            transaction_type="recharge",
            amount=Decimal("100.00"),
            balance_before=Decimal("500.00"),
            balance_after=Decimal("600.00"),
            payment_status="success",
            description="充值测试"
        )
        transaction2 = TransactionRecord(
            operator_id=operator.id,
            transaction_type="consumption",
            amount=Decimal("-50.00"),
            balance_before=Decimal("600.00"),
            balance_after=Decimal("550.00"),
            payment_status="success",
            description="消费测试"
        )
        test_db.add_all([transaction1, transaction2])
        await test_db.commit()

        transactions, total = await service.get_transactions(operator.id)

        assert len(transactions) == 2
        assert total == 2
        # 验证按时间降序排列(最新的在前)
        assert transactions[0].description == "消费测试"
        assert transactions[1].description == "充值测试"

    @pytest.mark.asyncio
    async def test_get_transactions_with_type_filter(self, test_db, operator_test_data):
        """测试按交易类型过滤"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        # 创建不同类型的交易
        transaction1 = TransactionRecord(
            operator_id=operator.id,
            transaction_type="recharge",
            amount=Decimal("100.00"),
            balance_before=Decimal("500.00"),
            balance_after=Decimal("600.00"),
            payment_status="success"
        )
        transaction2 = TransactionRecord(
            operator_id=operator.id,
            transaction_type="consumption",
            amount=Decimal("-50.00"),
            balance_before=Decimal("600.00"),
            balance_after=Decimal("550.00"),
            payment_status="success"
        )
        test_db.add_all([transaction1, transaction2])
        await test_db.commit()

        # 只查询充值类型
        transactions, total = await service.get_transactions(
            operator.id,
            transaction_type="recharge"
        )

        assert len(transactions) == 1
        assert total == 1
        assert transactions[0].transaction_type == "recharge"

    @pytest.mark.asyncio
    async def test_get_transactions_pagination(self, test_db, operator_test_data):
        """测试分页功能"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        # 创建5条交易记录
        for i in range(5):
            transaction = TransactionRecord(
                operator_id=operator.id,
                transaction_type="recharge",
                amount=Decimal("10.00"),
                balance_before=Decimal("0.00"),
                balance_after=Decimal("10.00"),
                payment_status="success",
                description=f"交易{i}"
            )
            test_db.add(transaction)
        await test_db.commit()

        # 查询第1页(每页2条)
        transactions_page1, total = await service.get_transactions(
            operator.id,
            page=1,
            page_size=2
        )

        assert len(transactions_page1) == 2
        assert total == 5

        # 查询第2页
        transactions_page2, total = await service.get_transactions(
            operator.id,
            page=2,
            page_size=2
        )

        assert len(transactions_page2) == 2
        assert total == 5

    @pytest.mark.asyncio
    async def test_get_transactions_non_existent_operator_raises_404(self, test_db):
        """测试查询不存在的运营商交易抛出HTTP 404"""
        service = OperatorService(test_db)

        non_existent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.get_transactions(non_existent_id)

        assert exc_info.value.status_code == 404


class TestApplyRefund:
    """测试apply_refund方法"""

    @pytest.mark.asyncio
    async def test_apply_refund_with_positive_balance(self, test_db, operator_test_data):
        """测试余额大于0时成功申请退款"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]  # 余额500元

        refund = await service.apply_refund(
            operator_id=operator.id,
            reason="测试退款申请"
        )

        assert refund.operator_id == operator.id
        assert refund.requested_amount == Decimal("500.00")
        assert refund.status == "pending"
        assert refund.reason == "测试退款申请"

    @pytest.mark.asyncio
    async def test_apply_refund_with_zero_balance_raises_400(self, test_db, operator_test_data):
        """测试余额为0时无法申请退款"""
        service = OperatorService(test_db)
        locked_operator = operator_test_data["locked_operator"]  # 余额为0

        with pytest.raises(HTTPException) as exc_info:
            await service.apply_refund(
                operator_id=locked_operator.id,
                reason="尝试退款"
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "INVALID_PARAMS"
        assert "余额为0" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_apply_refund_non_existent_operator_raises_404(self, test_db):
        """测试不存在的运营商申请退款抛出HTTP 404"""
        service = OperatorService(test_db)

        non_existent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.apply_refund(
                operator_id=non_existent_id,
                reason="退款"
            )

        assert exc_info.value.status_code == 404


class TestApplyInvoice:
    """测试apply_invoice方法"""

    @pytest.mark.asyncio
    async def test_apply_invoice_within_recharged_amount(self, test_db, operator_test_data):
        """测试开票金额不超过已充值金额时成功申请"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        # 先创建充值交易记录
        transaction = TransactionRecord(
            operator_id=operator.id,
            transaction_type="recharge",
            amount=Decimal("1000.00"),
            balance_before=Decimal("500.00"),
            balance_after=Decimal("1500.00"),
            payment_status="success",
            description="充值1000元"
        )
        test_db.add(transaction)
        await test_db.commit()

        # 申请开票500元(小于已充值1000元)
        invoice = await service.apply_invoice(
            operator_id=operator.id,
            amount="500.00",
            invoice_title="测试公司",
            tax_id="91110000123456789X"
        )

        assert invoice.operator_id == operator.id
        assert invoice.amount == Decimal("500.00")
        assert invoice.invoice_title == "测试公司"
        assert invoice.tax_id == "91110000123456789X"
        assert invoice.status == "pending"
        assert invoice.email == "existing@test.com"  # 使用账户邮箱

    @pytest.mark.asyncio
    async def test_apply_invoice_with_custom_email(self, test_db, operator_test_data):
        """测试使用自定义邮箱申请发票"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        # 创建充值记录
        transaction = TransactionRecord(
            operator_id=operator.id,
            transaction_type="recharge",
            amount=Decimal("500.00"),
            balance_before=Decimal("0.00"),
            balance_after=Decimal("500.00"),
            payment_status="success"
        )
        test_db.add(transaction)
        await test_db.commit()

        invoice = await service.apply_invoice(
            operator_id=operator.id,
            amount="300.00",
            invoice_title="测试公司",
            tax_id="91110000123456789X",
            email="custom_email@test.com"
        )

        assert invoice.email == "custom_email@test.com"

    @pytest.mark.asyncio
    async def test_apply_invoice_exceeds_recharged_amount_raises_400(self, test_db, operator_test_data):
        """测试开票金额超过已充值金额时抛出HTTP 400"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        # 创建充值记录200元
        transaction = TransactionRecord(
            operator_id=operator.id,
            transaction_type="recharge",
            amount=Decimal("200.00"),
            balance_before=Decimal("0.00"),
            balance_after=Decimal("200.00"),
            payment_status="success"
        )
        test_db.add(transaction)
        await test_db.commit()

        # 申请开票500元(超过已充值200元)
        with pytest.raises(HTTPException) as exc_info:
            await service.apply_invoice(
                operator_id=operator.id,
                amount="500.00",
                invoice_title="测试公司",
                tax_id="91110000123456789X"
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "INVALID_PARAMS"
        assert "不能超过已充值金额" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_apply_invoice_with_no_recharge_raises_400(self, test_db, operator_test_data):
        """测试未充值时申请开票抛出HTTP 400"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        # 没有创建任何充值记录
        with pytest.raises(HTTPException) as exc_info:
            await service.apply_invoice(
                operator_id=operator.id,
                amount="100.00",
                invoice_title="测试公司",
                tax_id="91110000123456789X"
            )

        assert exc_info.value.status_code == 400
        assert "不能超过已充值金额" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_apply_invoice_tax_id_uppercase(self, test_db, operator_test_data):
        """测试税号自动转换为大写"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        # 创建充值记录
        transaction = TransactionRecord(
            operator_id=operator.id,
            transaction_type="recharge",
            amount=Decimal("100.00"),
            balance_before=Decimal("0.00"),
            balance_after=Decimal("100.00"),
            payment_status="success"
        )
        test_db.add(transaction)
        await test_db.commit()

        invoice = await service.apply_invoice(
            operator_id=operator.id,
            amount="50.00",
            invoice_title="测试公司",
            tax_id="91110000123456789x"  # 小写x
        )

        # 验证税号被转换为大写
        assert invoice.tax_id == "91110000123456789X"


class TestGetRefunds:
    """测试get_refunds方法"""

    @pytest.mark.asyncio
    async def test_get_refunds_empty_list(self, test_db, operator_test_data):
        """测试查询空退款记录列表"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        refunds, total = await service.get_refunds(operator.id)

        assert refunds == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_refunds_with_data(self, test_db, operator_test_data):
        """测试查询包含数据的退款记录"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        # 创建退款记录
        refund1 = RefundRecord(
            operator_id=operator.id,
            requested_amount=Decimal("100.00"),
            status="pending",
            reason="原因1"
        )
        refund2 = RefundRecord(
            operator_id=operator.id,
            requested_amount=Decimal("200.00"),
            status="approved",
            actual_refund_amount=Decimal("200.00"),
            reason="原因2",
            reviewed_by=operator_test_data["admin"].id,  # approved状态需要审核人
            reviewed_at=datetime.now(timezone.utc)  # approved状态需要审核时间
        )
        test_db.add_all([refund1, refund2])
        await test_db.commit()

        refunds, total = await service.get_refunds(operator.id)

        assert len(refunds) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_get_refunds_pagination(self, test_db, operator_test_data):
        """测试退款记录分页"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        # 创建3条退款记录
        for i in range(3):
            refund = RefundRecord(
                operator_id=operator.id,
                requested_amount=Decimal("100.00"),
                status="pending",
                reason=f"退款{i}"
            )
            test_db.add(refund)
        await test_db.commit()

        # 查询第1页(每页2条)
        refunds_page1, total = await service.get_refunds(
            operator.id,
            page=1,
            page_size=2
        )

        assert len(refunds_page1) == 2
        assert total == 3


class TestGetInvoices:
    """测试get_invoices方法"""

    @pytest.mark.asyncio
    async def test_get_invoices_empty_list(self, test_db, operator_test_data):
        """测试查询空发票记录列表"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        invoices, total = await service.get_invoices(operator.id)

        assert invoices == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_invoices_with_data(self, test_db, operator_test_data):
        """测试查询包含数据的发票记录"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        # 创建发票记录
        invoice1 = InvoiceRecord(
            operator_id=operator.id,
            amount=Decimal("500.00"),
            invoice_title="公司A",
            tax_id="91110000111111111A",
            email="test@test.com",
            status="pending"
        )
        invoice2 = InvoiceRecord(
            operator_id=operator.id,
            amount=Decimal("1000.00"),
            invoice_title="公司B",
            tax_id="91110000222222222B",
            email="test@test.com",
            status="approved",
            pdf_url="https://example.com/invoice.pdf",
            reviewed_by=operator_test_data["admin"].id,  # approved状态需要审核人
            reviewed_at=datetime.now(timezone.utc)  # approved状态需要审核时间
        )
        test_db.add_all([invoice1, invoice2])
        await test_db.commit()

        invoices, total = await service.get_invoices(operator.id)

        assert len(invoices) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_get_invoices_pagination(self, test_db, operator_test_data):
        """测试发票记录分页"""
        service = OperatorService(test_db)
        operator = operator_test_data["operator"]

        # 创建3条发票记录
        for i in range(3):
            invoice = InvoiceRecord(
                operator_id=operator.id,
                amount=Decimal("100.00"),
                invoice_title=f"公司{i}",
                tax_id=f"9111000011111111{i}A",
                email="test@test.com",
                status="pending"
            )
            test_db.add(invoice)
        await test_db.commit()

        # 查询第1页(每页2条)
        invoices_page1, total = await service.get_invoices(
            operator.id,
            page=1,
            page_size=2
        )

        assert len(invoices_page1) == 2
        assert total == 3
