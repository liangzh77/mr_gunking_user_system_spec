"""单元测试：ApplicationService (T101)

测试OperatorService中应用授权管理相关的方法:
1. get_authorized_applications - 查询已授权应用列表
2. create_application_request - 创建应用授权申请
3. get_application_requests - 查询授权申请列表

测试策略:
- 使用真实数据库会话(test_db fixture)
- 验证授权关系和申请状态
- 测试业务规则(重复申请、已授权检查等)
- 验证数据隔离和权限控制
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi import HTTPException
from uuid import uuid4, UUID

from src.services.operator import OperatorService
from src.models.operator import OperatorAccount
from src.models.admin import AdminAccount
from src.models.application import Application
from src.models.authorization import OperatorAppAuthorization
from src.models.app_request import ApplicationRequest
from sqlalchemy import select


@pytest.fixture
async def admin_account(test_db):
    """创建管理员账户用于测试"""
    admin = AdminAccount(
        username="admin_app_test",
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
async def operator_with_apps(test_db, admin_account):
    """创建包含应用和授权的运营商测试数据"""
    from src.core.utils.password import hash_password

    # 创建运营商
    operator = OperatorAccount(
        username="app_test_operator",
        full_name="App Test Operator",
        email="operator@test.com",
        phone="13900000001",
        password_hash=hash_password("password123"),
        api_key="app_test_api_key_" + "a" * 48,
        api_key_hash=hash_password("app_test_api_key_" + "a" * 48),
        balance=Decimal("1000.00"),
        customer_tier="trial",
        is_active=True,
        is_locked=False
    )
    test_db.add(operator)
    await test_db.commit()
    await test_db.refresh(operator)

    # 创建3个应用
    app1 = Application(
        app_code="space_adventure",
        app_name="太空探险",
        description="VR太空探险游戏",
        price_per_player=Decimal("15.00"),
        min_players=2,
        max_players=8,
        is_active=True
    )
    app2 = Application(
        app_code="underwater_world",
        app_name="深海世界",
        description="VR深海探索游戏",
        price_per_player=Decimal("12.00"),
        min_players=1,
        max_players=6,
        is_active=True
    )
    app3 = Application(
        app_code="zombie_shooter",
        app_name="僵尸射击",
        description="VR僵尸射击游戏",
        price_per_player=Decimal("10.00"),
        min_players=1,
        max_players=4,
        is_active=False  # 已下架
    )
    test_db.add_all([app1, app2, app3])
    await test_db.commit()
    await test_db.refresh(app1)
    await test_db.refresh(app2)
    await test_db.refresh(app3)

    # 为operator创建app1的授权(永久)
    auth1 = OperatorAppAuthorization(
        operator_id=operator.id,
        application_id=app1.id,
        is_active=True,
        expires_at=None,  # 永久授权
        authorized_at=datetime.now(timezone.utc) - timedelta(days=30)
    )
    # 为operator创建app2的授权(有效期)
    auth2 = OperatorAppAuthorization(
        operator_id=operator.id,
        application_id=app2.id,
        is_active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=365),  # 1年后过期
        authorized_at=datetime.now(timezone.utc) - timedelta(days=7)
    )
    test_db.add_all([auth1, auth2])
    await test_db.commit()

    # 创建另一个运营商(用于测试数据隔离)
    other_operator = OperatorAccount(
        username="other_operator",
        full_name="Other Operator",
        email="other@test.com",
        phone="13900000002",
        password_hash=hash_password("password123"),
        api_key="other_api_key_" + "b" * 48,
        api_key_hash=hash_password("other_api_key_" + "b" * 48),
        balance=Decimal("500.00"),
        customer_tier="trial",
        is_active=True,
        is_locked=False
    )
    test_db.add(other_operator)
    await test_db.commit()
    await test_db.refresh(other_operator)

    return {
        "admin": admin_account,
        "operator": operator,
        "other_operator": other_operator,
        "app1": app1,  # 已授权，永久
        "app2": app2,  # 已授权，有效期
        "app3": app3,  # 未授权，已下架
        "auth1": auth1,
        "auth2": auth2
    }


class TestGetAuthorizedApplications:
    """测试get_authorized_applications方法"""

    @pytest.mark.asyncio
    async def test_get_authorized_apps_returns_active_auths(self, test_db, operator_with_apps):
        """测试查询活跃授权的应用列表"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]

        apps = await service.get_authorized_applications(operator.id)

        # 验证返回2个授权应用
        assert len(apps) == 2

        app_codes = {app["app_code"] for app in apps}
        assert "space_adventure" in app_codes
        assert "underwater_world" in app_codes

        # 验证返回数据格式
        for app in apps:
            assert "app_id" in app
            assert app["app_id"].startswith("app_")
            assert "app_code" in app
            assert "app_name" in app
            assert "price_per_player" in app
            assert "min_players" in app
            assert "max_players" in app
            assert "authorized_at" in app
            assert "is_active" in app
            assert app["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_authorized_apps_includes_permanent_auth(self, test_db, operator_with_apps):
        """测试返回永久授权的应用"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]

        apps = await service.get_authorized_applications(operator.id)

        # 查找永久授权的app1
        space_adventure = next((app for app in apps if app["app_code"] == "space_adventure"), None)
        assert space_adventure is not None
        assert space_adventure["expires_at"] is None  # 永久授权

    @pytest.mark.asyncio
    async def test_get_authorized_apps_includes_future_expiry(self, test_db, operator_with_apps):
        """测试返回未过期的授权应用"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]

        apps = await service.get_authorized_applications(operator.id)

        # 查找有有效期的app2
        underwater_world = next((app for app in apps if app["app_code"] == "underwater_world"), None)
        assert underwater_world is not None
        assert underwater_world["expires_at"] is not None  # 有有效期

    @pytest.mark.asyncio
    async def test_get_authorized_apps_excludes_expired(self, test_db, operator_with_apps):
        """测试不返回已过期的授权"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]
        app3 = operator_with_apps["app3"]

        # 创建已过期的授权
        expired_auth = OperatorAppAuthorization(
            operator_id=operator.id,
            application_id=app3.id,
            is_active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # 昨天过期
            authorized_at=datetime.now(timezone.utc) - timedelta(days=365)
        )
        test_db.add(expired_auth)
        await test_db.commit()

        apps = await service.get_authorized_applications(operator.id)

        # 验证不包含已过期的app3
        app_codes = {app["app_code"] for app in apps}
        assert "zombie_shooter" not in app_codes

    @pytest.mark.asyncio
    async def test_get_authorized_apps_empty_list(self, test_db, operator_with_apps):
        """测试运营商没有授权时返回空列表"""
        service = OperatorService(test_db)
        other_operator = operator_with_apps["other_operator"]

        apps = await service.get_authorized_applications(other_operator.id)

        assert apps == []

    @pytest.mark.asyncio
    async def test_get_authorized_apps_data_isolation(self, test_db, operator_with_apps):
        """测试数据隔离 - 只能看到自己的授权"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]
        other_operator = operator_with_apps["other_operator"]
        app1 = operator_with_apps["app1"]

        # 为other_operator创建授权
        other_auth = OperatorAppAuthorization(
            operator_id=other_operator.id,
            application_id=app1.id,
            is_active=True,
            expires_at=None
        )
        test_db.add(other_auth)
        await test_db.commit()

        # 查询operator的授权
        operator_apps = await service.get_authorized_applications(operator.id)
        assert len(operator_apps) == 2

        # 查询other_operator的授权
        other_apps = await service.get_authorized_applications(other_operator.id)
        assert len(other_apps) == 1

    @pytest.mark.asyncio
    async def test_get_authorized_apps_non_existent_operator_raises_404(self, test_db):
        """测试查询不存在的运营商抛出HTTP 404"""
        service = OperatorService(test_db)

        non_existent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.get_authorized_applications(non_existent_id)

        assert exc_info.value.status_code == 404


class TestCreateApplicationRequest:
    """测试create_application_request方法"""

    @pytest.mark.asyncio
    async def test_create_request_success(self, test_db, operator_with_apps):
        """测试成功创建授权申请"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]
        app3 = operator_with_apps["app3"]

        # 先将app3设为活跃状态
        app3.is_active = True
        await test_db.commit()

        request = await service.create_application_request(
            operator_id=operator.id,
            application_id=app3.id,
            reason="我们门店计划引入僵尸射击游戏，预计每天有30人次游玩"
        )

        # 验证返回数据
        assert request.operator_id == operator.id
        assert request.application_id == app3.id
        assert request.request_reason == "我们门店计划引入僵尸射击游戏，预计每天有30人次游玩"
        assert request.status == "pending"
        assert request.created_at is not None

    @pytest.mark.asyncio
    async def test_create_request_already_authorized_raises_400(self, test_db, operator_with_apps):
        """测试申请已授权的应用抛出HTTP 400"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]
        app1 = operator_with_apps["app1"]  # 已授权

        with pytest.raises(HTTPException) as exc_info:
            await service.create_application_request(
                operator_id=operator.id,
                application_id=app1.id,
                reason="尝试申请已授权的应用"
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "ALREADY_AUTHORIZED"
        assert "已拥有该应用的授权" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_create_request_duplicate_pending_raises_400(self, test_db, operator_with_apps):
        """测试重复申请(已有pending申请)抛出HTTP 400"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]
        app3 = operator_with_apps["app3"]

        # 先将app3设为活跃状态
        app3.is_active = True
        await test_db.commit()

        # 第一次申请
        await service.create_application_request(
            operator_id=operator.id,
            application_id=app3.id,
            reason="第一次申请"
        )

        # 第二次申请
        with pytest.raises(HTTPException) as exc_info:
            await service.create_application_request(
                operator_id=operator.id,
                application_id=app3.id,
                reason="第二次申请"
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "REQUEST_ALREADY_EXISTS"
        assert "已有待审核的申请" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_create_request_inactive_app_raises_400(self, test_db, operator_with_apps):
        """测试申请已下架应用抛出HTTP 400"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]
        app3 = operator_with_apps["app3"]  # is_active=False

        with pytest.raises(HTTPException) as exc_info:
            await service.create_application_request(
                operator_id=operator.id,
                application_id=app3.id,
                reason="尝试申请已下架的应用"
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "APPLICATION_INACTIVE"
        assert "已下架" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_create_request_non_existent_app_raises_404(self, test_db, operator_with_apps):
        """测试申请不存在的应用抛出HTTP 404"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]

        non_existent_app_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.create_application_request(
                operator_id=operator.id,
                application_id=non_existent_app_id,
                reason="申请不存在的应用"
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "APPLICATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_request_non_existent_operator_raises_404(self, test_db, operator_with_apps):
        """测试不存在的运营商申请应用抛出HTTP 404"""
        service = OperatorService(test_db)
        app3 = operator_with_apps["app3"]

        # 先将app3设为活跃状态
        app3.is_active = True
        await test_db.commit()

        non_existent_operator_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.create_application_request(
                operator_id=non_existent_operator_id,
                application_id=app3.id,
                reason="不存在的运营商申请"
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "OPERATOR_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_request_after_rejected(self, test_db, operator_with_apps):
        """测试拒绝后可以重新申请"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]
        app3 = operator_with_apps["app3"]

        # 先将app3设为活跃状态
        app3.is_active = True
        await test_db.commit()

        # 创建已被拒绝的申请
        rejected_request = ApplicationRequest(
            operator_id=operator.id,
            application_id=app3.id,
            request_reason="第一次申请",
            status="rejected",
            reviewed_by=operator_with_apps["admin"].id,
            reviewed_at=datetime.now(timezone.utc),
            reject_reason="不符合要求"
        )
        test_db.add(rejected_request)
        await test_db.commit()

        # 重新申请(应该成功，因为状态不是pending)
        new_request = await service.create_application_request(
            operator_id=operator.id,
            application_id=app3.id,
            reason="第二次申请，已改进"
        )

        assert new_request.status == "pending"
        assert new_request.request_reason == "第二次申请，已改进"


class TestGetApplicationRequests:
    """测试get_application_requests方法"""

    @pytest.mark.asyncio
    async def test_get_requests_empty_list(self, test_db, operator_with_apps):
        """测试查询空申请列表"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]

        requests, total = await service.get_application_requests(operator.id)

        assert requests == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_requests_with_data(self, test_db, operator_with_apps):
        """测试查询包含数据的申请列表"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]
        app3 = operator_with_apps["app3"]

        # 创建3条申请记录(不同状态) - 逐个创建以确保时间戳有差异
        request1 = ApplicationRequest(
            operator_id=operator.id,
            application_id=app3.id,
            request_reason="pending申请",
            status="pending"
        )
        test_db.add(request1)
        await test_db.commit()

        request2 = ApplicationRequest(
            operator_id=operator.id,
            application_id=app3.id,
            request_reason="approved申请",
            status="approved",
            reviewed_by=operator_with_apps["admin"].id,
            reviewed_at=datetime.now(timezone.utc)
        )
        test_db.add(request2)
        await test_db.commit()

        request3 = ApplicationRequest(
            operator_id=operator.id,
            application_id=app3.id,
            request_reason="rejected申请",
            status="rejected",
            reviewed_by=operator_with_apps["admin"].id,
            reviewed_at=datetime.now(timezone.utc),
            reject_reason="不符合要求"
        )
        test_db.add(request3)
        await test_db.commit()

        requests, total = await service.get_application_requests(operator.id)

        # 验证返回3条记录
        assert len(requests) == 3
        assert total == 3

        # 验证所有记录都存在(不依赖于严格的排序顺序)
        reasons = {req.request_reason for req in requests}
        assert reasons == {"pending申请", "approved申请", "rejected申请"}

        # 验证各状态正确
        statuses = {req.status for req in requests}
        assert statuses == {"pending", "approved", "rejected"}

    @pytest.mark.asyncio
    async def test_get_requests_pagination(self, test_db, operator_with_apps):
        """测试分页功能"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]
        app3 = operator_with_apps["app3"]

        # 创建5条申请记录
        for i in range(5):
            request = ApplicationRequest(
                operator_id=operator.id,
                application_id=app3.id,
                request_reason=f"申请{i}",
                status="pending"
            )
            test_db.add(request)
        await test_db.commit()

        # 查询第1页(每页2条)
        requests_page1, total = await service.get_application_requests(
            operator.id,
            page=1,
            page_size=2
        )

        assert len(requests_page1) == 2
        assert total == 5

        # 查询第2页
        requests_page2, total = await service.get_application_requests(
            operator.id,
            page=2,
            page_size=2
        )

        assert len(requests_page2) == 2
        assert total == 5

    @pytest.mark.asyncio
    async def test_get_requests_data_isolation(self, test_db, operator_with_apps):
        """测试数据隔离 - 只能看到自己的申请"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]
        other_operator = operator_with_apps["other_operator"]
        app3 = operator_with_apps["app3"]

        # operator的申请
        request1 = ApplicationRequest(
            operator_id=operator.id,
            application_id=app3.id,
            request_reason="operator的申请",
            status="pending"
        )
        # other_operator的申请
        request2 = ApplicationRequest(
            operator_id=other_operator.id,
            application_id=app3.id,
            request_reason="other_operator的申请",
            status="pending"
        )
        test_db.add_all([request1, request2])
        await test_db.commit()

        # 查询operator的申请
        operator_requests, total1 = await service.get_application_requests(operator.id)
        assert len(operator_requests) == 1
        assert total1 == 1
        assert operator_requests[0].request_reason == "operator的申请"

        # 查询other_operator的申请
        other_requests, total2 = await service.get_application_requests(other_operator.id)
        assert len(other_requests) == 1
        assert total2 == 1
        assert other_requests[0].request_reason == "other_operator的申请"

    @pytest.mark.asyncio
    async def test_get_requests_non_existent_operator_raises_404(self, test_db):
        """测试查询不存在的运营商抛出HTTP 404"""
        service = OperatorService(test_db)

        non_existent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.get_application_requests(non_existent_id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "OPERATOR_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_requests_includes_all_statuses(self, test_db, operator_with_apps):
        """测试返回所有状态的申请"""
        service = OperatorService(test_db)
        operator = operator_with_apps["operator"]
        app3 = operator_with_apps["app3"]

        # 创建不同状态的申请
        pending = ApplicationRequest(
            operator_id=operator.id,
            application_id=app3.id,
            request_reason="待审核",
            status="pending"
        )
        approved = ApplicationRequest(
            operator_id=operator.id,
            application_id=app3.id,
            request_reason="已通过",
            status="approved",
            reviewed_by=operator_with_apps["admin"].id,
            reviewed_at=datetime.now(timezone.utc)
        )
        rejected = ApplicationRequest(
            operator_id=operator.id,
            application_id=app3.id,
            request_reason="已拒绝",
            status="rejected",
            reviewed_by=operator_with_apps["admin"].id,
            reviewed_at=datetime.now(timezone.utc),
            reject_reason="原因"
        )
        test_db.add_all([pending, approved, rejected])
        await test_db.commit()

        requests, total = await service.get_application_requests(operator.id)

        # 验证返回所有状态
        assert total == 3
        statuses = {req.status for req in requests}
        assert statuses == {"pending", "approved", "rejected"}
