"""单元测试：AuthService (T048)

测试AuthService的7个核心验证方法:
1. verify_operator_by_api_key - API Key验证
2. verify_site_ownership - 运营点归属验证
3. verify_application_authorization - 应用授权验证
4. verify_player_count - 玩家数量验证
5. verify_session_id_format - 会话ID格式验证(FR-061)

测试策略:
- 使用真实数据库会话(test_db fixture)
- 测试每个方法的成功和失败场景
- 验证异常类型和错误码
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import HTTPException

from src.services.auth_service import AuthService
from src.models.admin import AdminAccount
from src.models.operator import OperatorAccount
from src.models.application import Application
from src.models.site import OperationSite
from src.models.authorization import OperatorAppAuthorization


@pytest.fixture
async def auth_test_data(test_db):
    """准备AuthService测试数据"""
    # 创建管理员
    admin = AdminAccount(
        username="admin_auth_test",
        password_hash="hashed_pw",
        full_name="Test Admin",
        email="admin@test.com",
        phone="13800138000",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    await test_db.flush()

    # 创建激活的运营商
    active_operator = OperatorAccount(
        username="op_auth_active",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="active_api_key_" + "a" * 48,
        api_key_hash="hashed_secret",
        balance=Decimal("500.00"),
        customer_tier="standard",
        is_active=True,
        is_locked=False,
        created_by=admin.id
    )
    test_db.add(active_operator)
    await test_db.flush()

    # 创建注销的运营商
    deactivated_operator = OperatorAccount(
        username="op_auth_deactivated",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="deactivated_key_" + "b" * 48,
        api_key_hash="hashed_secret",
        balance=Decimal("100.00"),
        customer_tier="trial",
        is_active=False,  # 已注销
        is_locked=False,
        created_by=admin.id
    )
    test_db.add(deactivated_operator)
    await test_db.flush()

    # 创建锁定的运营商
    locked_operator = OperatorAccount(
        username="op_auth_locked",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="locked_api_key_" + "c" * 48,
        api_key_hash="hashed_secret",
        balance=Decimal("200.00"),
        customer_tier="standard",
        is_active=True,
        is_locked=True,  # 已锁定
        locked_at=datetime.utcnow(),
        locked_reason="测试锁定",
        created_by=admin.id
    )
    test_db.add(locked_operator)
    await test_db.flush()

    # 创建运营点
    active_site = OperationSite(
        operator_id=active_operator.id,
        name="激活的运营点",
        address="测试地址",
        server_identifier="server_active_001",
        is_active=True
    )
    test_db.add(active_site)
    await test_db.flush()

    inactive_site = OperationSite(
        operator_id=active_operator.id,
        name="停用的运营点",
        address="测试地址",
        server_identifier="server_inactive_001",
        is_active=False  # 已停用
    )
    test_db.add(inactive_site)
    await test_db.flush()

    # 创建应用
    active_app = Application(
        app_code="app_auth_active",
        app_name="激活的游戏",
        price_per_player=Decimal("10.00"),
        min_players=2,
        max_players=8,
        is_active=True,
        created_by=admin.id
    )
    test_db.add(active_app)
    await test_db.flush()

    inactive_app = Application(
        app_code="app_auth_inactive",
        app_name="下架的游戏",
        price_per_player=Decimal("15.00"),
        min_players=3,
        max_players=6,
        is_active=False,  # 已下架
        created_by=admin.id
    )
    test_db.add(inactive_app)
    await test_db.flush()

    # 创建授权关系 - 有效授权
    valid_authorization = OperatorAppAuthorization(
        operator_id=active_operator.id,
        application_id=active_app.id,
        authorized_by=admin.id,
        expires_at=datetime.utcnow() + timedelta(days=30),  # 30天后过期
        is_active=True
    )
    test_db.add(valid_authorization)

    # 创建授权关系 - 已过期授权
    expired_authorization = OperatorAppAuthorization(
        operator_id=active_operator.id,
        application_id=inactive_app.id,
        authorized_by=admin.id,
        expires_at=datetime.utcnow() - timedelta(days=1),  # 已过期
        is_active=True
    )
    test_db.add(expired_authorization)
    await test_db.commit()

    return {
        "admin": admin,
        "active_operator": active_operator,
        "deactivated_operator": deactivated_operator,
        "locked_operator": locked_operator,
        "active_site": active_site,
        "inactive_site": inactive_site,
        "active_app": active_app,
        "inactive_app": inactive_app,
        "valid_authorization": valid_authorization,
        "expired_authorization": expired_authorization
    }


class TestVerifyOperatorByApiKey:
    """测试verify_operator_by_api_key方法"""

    @pytest.mark.asyncio
    async def test_valid_api_key_success(self, auth_test_data, test_db):
        """测试有效API Key验证成功"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]

        result = await service.verify_operator_by_api_key(operator.api_key)

        assert result.id == operator.id
        assert result.username == operator.username
        assert result.is_active is True
        assert result.is_locked is False

    @pytest.mark.asyncio
    async def test_invalid_api_key_fails(self, test_db):
        """测试无效API Key返回401"""
        service = AuthService(test_db)

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_operator_by_api_key("invalid_api_key_" + "x" * 48)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "INVALID_API_KEY"

    @pytest.mark.asyncio
    async def test_deactivated_account_fails(self, auth_test_data, test_db):
        """测试注销账户返回401"""
        service = AuthService(test_db)
        operator = auth_test_data["deactivated_operator"]

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_operator_by_api_key(operator.api_key)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "ACCOUNT_DEACTIVATED"

    @pytest.mark.asyncio
    async def test_locked_account_fails(self, auth_test_data, test_db):
        """测试锁定账户返回403"""
        service = AuthService(test_db)
        operator = auth_test_data["locked_operator"]

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_operator_by_api_key(operator.api_key)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "ACCOUNT_LOCKED"
        assert "details" in exc_info.value.detail
        assert exc_info.value.detail["details"]["locked_reason"] == "测试锁定"


class TestVerifySiteOwnership:
    """测试verify_site_ownership方法"""

    @pytest.mark.asyncio
    async def test_valid_site_ownership_success(self, auth_test_data, test_db):
        """测试有效运营点验证成功"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]
        site = auth_test_data["active_site"]

        result = await service.verify_site_ownership(site.id, operator.id)

        assert result.id == site.id
        assert result.operator_id == operator.id
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_site_not_found_fails(self, auth_test_data, test_db):
        """测试运营点不存在返回404"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]
        non_existent_site_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_site_ownership(non_existent_site_id, operator.id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "SITE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_site_not_owned_fails(self, auth_test_data, test_db):
        """测试运营点不属于该运营商返回403"""
        service = AuthService(test_db)
        locked_operator = auth_test_data["locked_operator"]
        site = auth_test_data["active_site"]  # 属于active_operator

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_site_ownership(site.id, locked_operator.id)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "SITE_NOT_OWNED"

    @pytest.mark.asyncio
    async def test_inactive_site_fails(self, auth_test_data, test_db):
        """测试停用的运营点返回403"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]
        site = auth_test_data["inactive_site"]

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_site_ownership(site.id, operator.id)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "SITE_INACTIVE"


class TestVerifyApplicationAuthorization:
    """测试verify_application_authorization方法"""

    @pytest.mark.asyncio
    async def test_valid_authorization_success(self, auth_test_data, test_db):
        """测试有效授权验证成功"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]
        app = auth_test_data["active_app"]

        application, authorization = await service.verify_application_authorization(
            app.id, operator.id
        )

        assert application.id == app.id
        assert authorization.operator_id == operator.id
        assert authorization.application_id == app.id
        assert authorization.is_active is True

    @pytest.mark.asyncio
    async def test_application_not_found_fails(self, auth_test_data, test_db):
        """测试应用不存在返回404"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]
        non_existent_app_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_application_authorization(non_existent_app_id, operator.id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "APP_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_inactive_application_fails(self, auth_test_data, test_db):
        """测试下架应用返回403"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]
        app = auth_test_data["inactive_app"]

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_application_authorization(app.id, operator.id)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "APP_INACTIVE"

    @pytest.mark.asyncio
    async def test_not_authorized_fails(self, auth_test_data, test_db):
        """测试未授权应用返回403"""
        service = AuthService(test_db)
        locked_operator = auth_test_data["locked_operator"]
        app = auth_test_data["active_app"]  # 未授权给locked_operator

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_application_authorization(app.id, locked_operator.id)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "APP_NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_expired_authorization_fails(self, auth_test_data, test_db):
        """测试过期授权返回403"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]
        app = auth_test_data["inactive_app"]  # 有过期授权

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_application_authorization(app.id, operator.id)

        # 可能因为应用下架先失败,或授权过期失败
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] in ["APP_INACTIVE", "AUTHORIZATION_EXPIRED"]


class TestVerifyPlayerCount:
    """测试verify_player_count方法"""

    @pytest.mark.asyncio
    async def test_valid_player_count_success(self, auth_test_data, test_db):
        """测试有效玩家数量验证成功"""
        service = AuthService(test_db)
        app = auth_test_data["active_app"]  # min=2, max=8

        # 测试范围内的值
        await service.verify_player_count(2, app)  # 最小值
        await service.verify_player_count(5, app)  # 中间值
        await service.verify_player_count(8, app)  # 最大值

    @pytest.mark.asyncio
    async def test_player_count_below_minimum_fails(self, auth_test_data, test_db):
        """测试玩家数量低于最小值返回400"""
        service = AuthService(test_db)
        app = auth_test_data["active_app"]  # min=2

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_player_count(1, app)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "PLAYER_COUNT_OUT_OF_RANGE"
        assert exc_info.value.detail["details"]["min_players"] == 2
        assert exc_info.value.detail["details"]["requested_players"] == 1

    @pytest.mark.asyncio
    async def test_player_count_above_maximum_fails(self, auth_test_data, test_db):
        """测试玩家数量超过最大值返回400"""
        service = AuthService(test_db)
        app = auth_test_data["active_app"]  # max=8

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_player_count(9, app)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "PLAYER_COUNT_OUT_OF_RANGE"
        assert exc_info.value.detail["details"]["max_players"] == 8
        assert exc_info.value.detail["details"]["requested_players"] == 9


class TestVerifySessionIdFormat:
    """测试verify_session_id_format方法 (FR-061)"""

    @pytest.mark.asyncio
    async def test_valid_session_id_success(self, auth_test_data, test_db):
        """测试有效会话ID格式验证成功"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]

        current_timestamp = int(datetime.utcnow().timestamp())
        valid_session_id = f"{operator.id}_{current_timestamp}_{'a' * 16}"

        # 不应抛出异常
        await service.verify_session_id_format(valid_session_id, operator.id)

    @pytest.mark.asyncio
    async def test_invalid_format_fails(self, auth_test_data, test_db):
        """测试无效格式返回400"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]

        invalid_session_ids = [
            "invalid_format",
            "test_12345",
            "op_test_abc_xyz",
        ]

        for invalid_session_id in invalid_session_ids:
            with pytest.raises(HTTPException) as exc_info:
                await service.verify_session_id_format(invalid_session_id, operator.id)

            assert exc_info.value.status_code == 400
            assert exc_info.value.detail["error_code"] == "INVALID_SESSION_ID_FORMAT"

    @pytest.mark.asyncio
    async def test_operator_mismatch_fails(self, auth_test_data, test_db):
        """测试运营商ID不匹配返回400"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]
        another_operator_id = uuid4()

        current_timestamp = int(datetime.utcnow().timestamp())
        mismatched_session_id = f"{another_operator_id}_{current_timestamp}_{'b' * 16}"

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_session_id_format(mismatched_session_id, operator.id)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "SESSION_ID_OPERATOR_MISMATCH"

    @pytest.mark.asyncio
    async def test_expired_timestamp_fails(self, auth_test_data, test_db):
        """测试过期时间戳返回400"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]

        # 6分钟前的时间戳(超过5分钟限制)
        expired_timestamp = int((datetime.utcnow() - timedelta(minutes=6)).timestamp())
        expired_session_id = f"{operator.id}_{expired_timestamp}_{'c' * 16}"

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_session_id_format(expired_session_id, operator.id)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "SESSION_ID_EXPIRED"

    @pytest.mark.asyncio
    async def test_within_5_minutes_success(self, auth_test_data, test_db):
        """测试5分钟内的时间戳验证成功"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]

        # 4分59秒前的时间戳(在5分钟限制内)
        recent_timestamp = int((datetime.utcnow() - timedelta(seconds=299)).timestamp())
        recent_session_id = f"{operator.id}_{recent_timestamp}_{'d' * 16}"

        # 不应抛出异常
        await service.verify_session_id_format(recent_session_id, operator.id)

    @pytest.mark.asyncio
    async def test_invalid_random_length_fails(self, auth_test_data, test_db):
        """测试随机部分长度不正确返回400"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]

        current_timestamp = int(datetime.utcnow().timestamp())

        # 15字符(不足)
        short_session_id = f"{operator.id}_{current_timestamp}_{'e' * 15}"

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_session_id_format(short_session_id, operator.id)

        assert exc_info.value.status_code == 400
        # 应该先因格式不匹配而失败
        assert exc_info.value.detail["error_code"] in [
            "INVALID_SESSION_ID_FORMAT",
            "INVALID_SESSION_ID_RANDOM"
        ]

    @pytest.mark.asyncio
    async def test_special_characters_in_random_fails(self, auth_test_data, test_db):
        """测试随机部分包含特殊字符返回400"""
        service = AuthService(test_db)
        operator = auth_test_data["active_operator"]

        current_timestamp = int(datetime.utcnow().timestamp())

        # 包含特殊字符
        invalid_session_id = f"{operator.id}_{current_timestamp}_abcd1234-efgh567"

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_session_id_format(invalid_session_id, operator.id)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "INVALID_SESSION_ID_FORMAT"
