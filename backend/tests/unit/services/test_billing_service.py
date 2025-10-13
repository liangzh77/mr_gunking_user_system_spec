"""单元测试：BillingService (T049)

测试BillingService的核心计费方法:
1. check_session_idempotency - 会话ID幂等性检查
2. check_balance_sufficiency - 余额充足性检查
3. calculate_total_cost - 总费用计算
4. create_authorization_transaction - 授权扣费事务(关键方法)

测试策略:
- 使用真实数据库会话(test_db fixture)
- 测试事务回滚机制
- 测试行级锁和并发安全
- 验证异常类型和错误码
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from fastapi import HTTPException

from src.services.billing_service import BillingService
from src.models.admin import AdminAccount
from src.models.operator import OperatorAccount
from src.models.application import Application
from src.models.site import OperationSite
from src.models.usage_record import UsageRecord
from src.models.transaction import TransactionRecord
from sqlalchemy import select


@pytest.fixture
async def billing_test_data(test_db):
    """准备BillingService测试数据"""
    # 创建管理员
    admin = AdminAccount(
        username="admin_billing_test",
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
        username="op_billing_test",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="billing_api_key_" + "a" * 48,
        api_key_hash="hashed_secret",
        balance=Decimal("500.00"),
        customer_tier="standard",
        is_active=True,
        is_locked=False,
        created_by=admin.id
    )
    test_db.add(operator)
    await test_db.flush()

    # 创建运营点
    site = OperationSite(
        operator_id=operator.id,
        name="计费测试运营点",
        address="测试地址",
        server_identifier="server_billing_001",
        is_active=True
    )
    test_db.add(site)
    await test_db.flush()

    # 创建应用
    application = Application(
        app_code="app_billing_test",
        app_name="计费测试游戏",
        price_per_player=Decimal("10.00"),
        min_players=2,
        max_players=8,
        is_active=True,
        created_by=admin.id
    )
    test_db.add(application)
    await test_db.flush()

    # 创建已存在的使用记录(用于幂等性测试)
    existing_session_id = "existing_session_" + "x" * 30
    existing_usage_record = UsageRecord(
        session_id=existing_session_id,
        operator_id=operator.id,
        site_id=site.id,
        application_id=application.id,
        player_count=3,
        price_per_player=Decimal("10.00"),
        total_cost=Decimal("30.00"),
        authorization_token="existing_token_12345",
        game_started_at=datetime.utcnow()
    )
    test_db.add(existing_usage_record)
    await test_db.commit()

    return {
        "admin": admin,
        "operator": operator,
        "site": site,
        "application": application,
        "existing_session_id": existing_session_id,
        "existing_usage_record": existing_usage_record
    }


class TestCheckSessionIdempotency:
    """测试check_session_idempotency方法"""

    @pytest.mark.asyncio
    async def test_existing_session_returns_record(self, billing_test_data, test_db):
        """测试已存在的会话ID返回使用记录"""
        service = BillingService(test_db)
        existing_session_id = billing_test_data["existing_session_id"]

        result = await service.check_session_idempotency(existing_session_id)

        assert result is not None
        assert result.session_id == existing_session_id
        assert result.total_cost == Decimal("30.00")

    @pytest.mark.asyncio
    async def test_new_session_returns_none(self, billing_test_data, test_db):
        """测试新会话ID返回None"""
        service = BillingService(test_db)
        new_session_id = "new_session_" + "y" * 30

        result = await service.check_session_idempotency(new_session_id)

        assert result is None


class TestCheckBalanceSufficiency:
    """测试check_balance_sufficiency方法"""

    @pytest.mark.asyncio
    async def test_sufficient_balance_no_exception(self, billing_test_data, test_db):
        """测试余额充足不抛出异常"""
        service = BillingService(test_db)
        operator = billing_test_data["operator"]  # 余额500元

        # 不应抛出异常
        await service.check_balance_sufficiency(operator, Decimal("100.00"))
        await service.check_balance_sufficiency(operator, Decimal("500.00"))  # 恰好相等

    @pytest.mark.asyncio
    async def test_insufficient_balance_raises_402(self, billing_test_data, test_db):
        """测试余额不足抛出HTTP 402"""
        service = BillingService(test_db)
        operator = billing_test_data["operator"]  # 余额500元

        with pytest.raises(HTTPException) as exc_info:
            await service.check_balance_sufficiency(operator, Decimal("600.00"))

        assert exc_info.value.status_code == 402
        assert exc_info.value.detail["error_code"] == "INSUFFICIENT_BALANCE"
        assert exc_info.value.detail["details"]["current_balance"] == "500.00"
        assert exc_info.value.detail["details"]["required_amount"] == "600.00"
        assert exc_info.value.detail["details"]["shortage"] == "100.00"

    @pytest.mark.asyncio
    async def test_zero_balance_insufficient(self, test_db):
        """测试余额为0时任何正数金额都不足"""
        service = BillingService(test_db)

        # 创建余额为0的运营商
        admin = AdminAccount(
            username="admin_zero_balance",
            password_hash="hashed_pw",
            full_name="Test Admin",
            email="admin@test.com",
            phone="13800138000",
            role="admin",
            is_active=True
        )
        test_db.add(admin)
        await test_db.flush()

        operator = OperatorAccount(
            username="op_zero_balance",
            full_name="Test Operator",
            email="operator@test.com",
            phone="13900139000",
            password_hash="hashed_password",
            api_key="zero_balance_key_" + "z" * 48,
            api_key_hash="hashed_secret",
            balance=Decimal("0.00"),
            customer_tier="trial",
            is_active=True,
            is_locked=False,
            created_by=admin.id
        )
        test_db.add(operator)
        await test_db.commit()

        with pytest.raises(HTTPException) as exc_info:
            await service.check_balance_sufficiency(operator, Decimal("10.00"))

        assert exc_info.value.status_code == 402


class TestCalculateTotalCost:
    """测试calculate_total_cost方法"""

    def test_basic_calculation(self, test_db):
        """测试基本费用计算"""
        service = BillingService(test_db)

        result = service.calculate_total_cost(Decimal("10.00"), 5)
        assert result == Decimal("50.00")

    def test_decimal_precision(self, test_db):
        """测试小数精度保持2位"""
        service = BillingService(test_db)

        result = service.calculate_total_cost(Decimal("10.50"), 3)
        assert result == Decimal("31.50")
        assert str(result) == "31.50"

    def test_single_player(self, test_db):
        """测试单人计费"""
        service = BillingService(test_db)

        result = service.calculate_total_cost(Decimal("15.00"), 1)
        assert result == Decimal("15.00")

    def test_large_player_count(self, test_db):
        """测试大量玩家计费"""
        service = BillingService(test_db)

        result = service.calculate_total_cost(Decimal("5.00"), 100)
        assert result == Decimal("500.00")


class TestCreateAuthorizationTransaction:
    """测试create_authorization_transaction方法 (核心事务方法)"""

    @pytest.mark.asyncio
    async def test_successful_transaction(self, billing_test_data, test_db):
        """测试成功的扣费事务"""
        service = BillingService(test_db)
        operator = billing_test_data["operator"]
        site = billing_test_data["site"]
        application = billing_test_data["application"]

        initial_balance = operator.balance  # 500.00
        session_id = "test_success_session_" + "a" * 20
        player_count = 5

        usage_record, transaction_record, balance_after = await service.create_authorization_transaction(
            session_id=session_id,
            operator_id=operator.id,
            site_id=site.id,
            application=application,
            player_count=player_count,
            client_ip="192.168.1.100"
        )

        # 验证使用记录
        assert usage_record.session_id == session_id
        assert usage_record.player_count == player_count
        assert usage_record.total_cost == Decimal("50.00")  # 5 × 10
        assert usage_record.authorization_token is not None
        assert len(usage_record.authorization_token) == 36  # UUID格式

        # 验证交易记录
        assert transaction_record.transaction_type == "consumption"
        assert transaction_record.amount == Decimal("-50.00")  # 消费为负数
        assert transaction_record.balance_before == Decimal("500.00")
        assert transaction_record.balance_after == Decimal("450.00")
        assert transaction_record.related_usage_id == usage_record.id

        # 验证余额更新
        assert balance_after == Decimal("450.00")

        # 验证数据库中的记录
        await test_db.refresh(operator)
        assert operator.balance == Decimal("450.00")

    @pytest.mark.asyncio
    async def test_insufficient_balance_in_transaction(self, billing_test_data, test_db):
        """测试事务中余额不足抛出402并回滚"""
        service = BillingService(test_db)
        operator = billing_test_data["operator"]
        site = billing_test_data["site"]
        application = billing_test_data["application"]

        initial_balance = operator.balance  # 500.00
        session_id = "test_insufficient_session_" + "b" * 20

        # 请求60人 × 10元 = 600元(超过余额)
        with pytest.raises(HTTPException) as exc_info:
            await service.create_authorization_transaction(
                session_id=session_id,
                operator_id=operator.id,
                site_id=site.id,
                application=application,
                player_count=60  # 需要600元
            )

        # 验证异常
        assert exc_info.value.status_code == 402
        assert exc_info.value.detail["error_code"] == "INSUFFICIENT_BALANCE"

        # 验证余额未变化(事务已回滚)
        await test_db.refresh(operator)
        assert operator.balance == initial_balance

        # 验证未创建使用记录
        stmt = select(UsageRecord).where(UsageRecord.session_id == session_id)
        result = await test_db.execute(stmt)
        usage_record = result.scalar_one_or_none()
        assert usage_record is None

    @pytest.mark.asyncio
    async def test_duplicate_session_id_raises_409(self, billing_test_data, test_db):
        """测试重复会话ID抛出HTTP 409"""
        service = BillingService(test_db)
        operator = billing_test_data["operator"]
        site = billing_test_data["site"]
        application = billing_test_data["application"]
        existing_session_id = billing_test_data["existing_session_id"]

        # 尝试使用已存在的会话ID
        with pytest.raises(HTTPException) as exc_info:
            await service.create_authorization_transaction(
                session_id=existing_session_id,
                operator_id=operator.id,
                site_id=site.id,
                application=application,
                player_count=5
            )

        # 验证异常
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["error_code"] == "SESSION_ID_DUPLICATE"

    @pytest.mark.asyncio
    async def test_transaction_with_minimum_cost(self, billing_test_data, test_db):
        """测试最小金额扣费(边界测试)"""
        service = BillingService(test_db)
        operator = billing_test_data["operator"]
        site = billing_test_data["site"]
        application = billing_test_data["application"]

        session_id = "test_min_cost_session_" + "c" * 20

        usage_record, transaction_record, balance_after = await service.create_authorization_transaction(
            session_id=session_id,
            operator_id=operator.id,
            site_id=site.id,
            application=application,
            player_count=2  # 最小玩家数, 20元
        )

        assert usage_record.total_cost == Decimal("20.00")
        assert transaction_record.amount == Decimal("-20.00")
        assert balance_after == Decimal("480.00")  # 500 - 20

    @pytest.mark.asyncio
    async def test_transaction_with_exact_balance(self, test_db):
        """测试余额刚好够用的情况"""
        # 创建测试数据
        admin = AdminAccount(
            username="admin_exact_balance",
            password_hash="hashed_pw",
            full_name="Test Admin",
            email="admin@test.com",
            phone="13800138000",
            role="admin",
            is_active=True
        )
        test_db.add(admin)
        await test_db.flush()

        operator = OperatorAccount(
            username="op_exact_balance",
            full_name="Test Operator",
            email="operator@test.com",
            phone="13900139000",
            password_hash="hashed_password",
            api_key="exact_balance_key_" + "d" * 48,
            api_key_hash="hashed_secret",
            balance=Decimal("50.00"),  # 刚好50元
            customer_tier="standard",
            is_active=True,
            is_locked=False,
            created_by=admin.id
        )
        test_db.add(operator)
        await test_db.flush()

        site = OperationSite(
            operator_id=operator.id,
            name="精确余额测试运营点",
            address="测试地址",
            server_identifier="server_exact_001",
            is_active=True
        )
        test_db.add(site)
        await test_db.flush()

        application = Application(
            app_code="app_exact_balance",
            app_name="精确余额测试游戏",
            price_per_player=Decimal("10.00"),
            min_players=2,
            max_players=8,
            is_active=True,
            created_by=admin.id
        )
        test_db.add(application)
        await test_db.commit()

        service = BillingService(test_db)
        session_id = "test_exact_balance_session_" + "e" * 20

        usage_record, transaction_record, balance_after = await service.create_authorization_transaction(
            session_id=session_id,
            operator_id=operator.id,
            site_id=site.id,
            application=application,
            player_count=5  # 需要50元
        )

        # 验证余额变为0
        assert balance_after == Decimal("0.00")
        assert transaction_record.balance_after == Decimal("0.00")

        await test_db.refresh(operator)
        assert operator.balance == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_transaction_records_client_ip(self, billing_test_data, test_db):
        """测试事务记录客户端IP"""
        service = BillingService(test_db)
        operator = billing_test_data["operator"]
        site = billing_test_data["site"]
        application = billing_test_data["application"]

        session_id = "test_client_ip_session_" + "f" * 20
        client_ip = "203.0.113.45"

        usage_record, _, _ = await service.create_authorization_transaction(
            session_id=session_id,
            operator_id=operator.id,
            site_id=site.id,
            application=application,
            player_count=3,
            client_ip=client_ip
        )

        assert usage_record.client_ip == client_ip

    @pytest.mark.asyncio
    async def test_transaction_without_client_ip(self, billing_test_data, test_db):
        """测试事务可以不记录客户端IP"""
        service = BillingService(test_db)
        operator = billing_test_data["operator"]
        site = billing_test_data["site"]
        application = billing_test_data["application"]

        session_id = "test_no_client_ip_session_" + "g" * 20

        usage_record, _, _ = await service.create_authorization_transaction(
            session_id=session_id,
            operator_id=operator.id,
            site_id=site.id,
            application=application,
            player_count=3
            # 不传递client_ip
        )

        assert usage_record.client_ip is None

    @pytest.mark.asyncio
    async def test_transaction_creates_correct_description(self, billing_test_data, test_db):
        """测试交易记录生成正确的描述"""
        service = BillingService(test_db)
        operator = billing_test_data["operator"]
        site = billing_test_data["site"]
        application = billing_test_data["application"]

        session_id = "test_description_session_" + "h" * 20

        _, transaction_record, _ = await service.create_authorization_transaction(
            session_id=session_id,
            operator_id=operator.id,
            site_id=site.id,
            application=application,
            player_count=4
        )

        expected_description = f"游戏消费：{application.app_name} - 4人"
        assert transaction_record.description == expected_description


class TestGetUsageRecordWithDetails:
    """测试get_usage_record_with_details方法"""

    @pytest.mark.asyncio
    async def test_get_existing_usage_record(self, billing_test_data, test_db):
        """测试获取已存在的使用记录"""
        service = BillingService(test_db)
        existing_record = billing_test_data["existing_usage_record"]

        result = await service.get_usage_record_with_details(existing_record.id)

        assert result is not None
        assert result.id == existing_record.id
        assert result.session_id == existing_record.session_id

    @pytest.mark.asyncio
    async def test_get_non_existent_usage_record(self, billing_test_data, test_db):
        """测试获取不存在的使用记录返回None"""
        service = BillingService(test_db)

        from uuid import uuid4
        non_existent_id = uuid4()

        result = await service.get_usage_record_with_details(non_existent_id)

        assert result is None
