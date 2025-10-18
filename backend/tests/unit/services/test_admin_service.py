"""单元测试：AdminService (T152-T154)

测试AdminService的所有管理功能:
1. 运营商管理 (T152)
2. 应用管理 (T153)
3. 授权管理 (T154)

测试策略:
- 使用真实数据库会话(test_db fixture)
- 验证业务逻辑和数据操作
- 测试边界条件和错误处理
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4
from fastapi import HTTPException

from src.services.admin_service import AdminService
from src.models.admin import AdminAccount
from src.models.operator import OperatorAccount
from src.models.application import Application
from src.models.app_request import ApplicationRequest
from src.models.authorization import OperatorAppAuthorization
from src.core import BadRequestException, NotFoundException
from src.core.utils.password import hash_password


@pytest.fixture
async def admin_account(test_db):
    """创建管理员账户"""
    admin = AdminAccount(
        username="test_admin",
        password_hash=hash_password("Admin@123"),
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
async def test_operators(test_db):
    """创建测试运营商"""
    operators = []
    for i in range(3):
        op = OperatorAccount(
            username=f"operator_{i}",
            full_name=f"Operator {i}",
            email=f"op{i}@test.com",
            phone=f"1390000000{i}",
            password_hash=hash_password("password123"),
            api_key=f"api_key_{i}" + "x" * 48,
            api_key_hash=hash_password(f"api_key_{i}" + "x" * 48),
            balance=Decimal(f"{i * 1000}.00"),
            customer_tier="standard" if i % 2 == 0 else "vip",
            is_active=i != 2,  # operator_2 is inactive
            is_locked=False
        )
        test_db.add(op)
        operators.append(op)

    await test_db.commit()
    for op in operators:
        await test_db.refresh(op)
    return operators


@pytest.fixture
async def test_applications(test_db, admin_account):
    """创建测试应用"""
    apps = []
    for i in range(2):
        app = Application(
            app_code=f"test_app_{i}",
            app_name=f"Test App {i}",
            description=f"Description {i}",
            price_per_player=Decimal(f"{10 + i}.00"),
            min_players=2,
            max_players=8,
            is_active=True,
        )
        test_db.add(app)
        apps.append(app)

    await test_db.commit()
    for app in apps:
        await test_db.refresh(app)
    return apps


# ==================== 运营商管理测试 (T152) ====================

class TestGetOperators:
    """测试get_operators方法"""

    @pytest.mark.asyncio
    async def test_get_operators_all(self, test_db, test_operators):
        """测试获取所有运营商"""
        service = AdminService(test_db)

        result = await service.get_operators()

        assert result["total"] == 3
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert len(result["items"]) == 3

    @pytest.mark.asyncio
    async def test_get_operators_with_search(self, test_db, test_operators):
        """测试搜索运营商"""
        service = AdminService(test_db)

        result = await service.get_operators(search="operator_0")

        assert result["total"] == 1
        assert result["items"][0]["username"] == "operator_0"

    @pytest.mark.asyncio
    async def test_get_operators_filter_active(self, test_db, test_operators):
        """测试过滤活跃运营商"""
        service = AdminService(test_db)

        result = await service.get_operators(status="active")

        assert result["total"] == 2  # operator_0 and operator_1 are active

    @pytest.mark.asyncio
    async def test_get_operators_filter_inactive(self, test_db, test_operators):
        """测试过滤非活跃运营商"""
        service = AdminService(test_db)

        result = await service.get_operators(status="inactive")

        assert result["total"] == 1  # operator_2 is inactive

    @pytest.mark.asyncio
    async def test_get_operators_pagination(self, test_db, test_operators):
        """测试分页"""
        service = AdminService(test_db)

        result = await service.get_operators(page=1, page_size=2)

        assert result["page"] == 1
        assert result["page_size"] == 2
        assert len(result["items"]) == 2


# ==================== 应用管理测试 (T153) ====================

class TestGetApplications:
    """测试get_applications方法"""

    @pytest.mark.asyncio
    async def test_get_applications_all(self, test_db, test_applications):
        """测试获取所有应用"""
        service = AdminService(test_db)

        result = await service.get_applications()

        assert result["total"] == 2
        assert len(result["items"]) == 2

    @pytest.mark.asyncio
    async def test_get_applications_with_search(self, test_db, test_applications):
        """测试搜索应用"""
        service = AdminService(test_db)

        result = await service.get_applications(search="test_app_0")

        assert result["total"] == 1
        assert result["items"][0]["app_code"] == "test_app_0"


class TestCreateApplication:
    """测试create_application方法"""

    @pytest.mark.asyncio
    async def test_create_application_success(self, test_db, admin_account):
        """测试成功创建应用"""
        service = AdminService(test_db)

        result = await service.create_application(
            admin_id=admin_account.id,
            app_code="new_app",
            app_name="New App",
            description="New app description",
            price_per_player=15.0,
            min_players=1,
            max_players=10
        )

        assert result["app_code"] == "new_app"
        assert result["app_name"] == "New App"
        assert result["price_per_player"] == 15.0
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_application_duplicate_code(self, test_db, test_applications, admin_account):
        """测试创建重复app_code应用"""
        service = AdminService(test_db)

        with pytest.raises(BadRequestException) as exc:
            await service.create_application(
                admin_id=admin_account.id,
                app_code="test_app_0",  # Already exists
                app_name="Duplicate App",
                description=None,
                price_per_player=20.0,
                min_players=1,
                max_players=5
            )

        assert "already exists" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_application_invalid_player_range(self, test_db, admin_account):
        """测试无效玩家范围"""
        service = AdminService(test_db)

        # max < min
        with pytest.raises(BadRequestException) as exc:
            await service.create_application(
                admin_id=admin_account.id,
                app_code="invalid_app",
                app_name="Invalid App",
                description=None,
                price_per_player=10.0,
                min_players=5,
                max_players=2
            )

        assert "must be >=" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_application_negative_price(self, test_db, admin_account):
        """测试负价格"""
        service = AdminService(test_db)

        with pytest.raises(BadRequestException) as exc:
            await service.create_application(
                admin_id=admin_account.id,
                app_code="negative_price_app",
                app_name="Negative Price App",
                description=None,
                price_per_player=-10.0,
                min_players=1,
                max_players=5
            )

        assert "must be positive" in str(exc.value)


class TestUpdateApplicationPrice:
    """测试update_application_price方法"""

    @pytest.mark.asyncio
    async def test_update_price_success(self, test_db, test_applications):
        """测试成功更新价格"""
        service = AdminService(test_db)
        app = test_applications[0]

        result = await service.update_application_price(
            app_id=str(app.id),
            new_price=25.0
        )

        assert result["price_per_player"] == 25.0

    @pytest.mark.asyncio
    async def test_update_price_not_found(self, test_db):
        """测试更新不存在的应用"""
        service = AdminService(test_db)

        with pytest.raises(NotFoundException):
            await service.update_application_price(
                app_id=str(uuid4()),
                new_price=20.0
            )

    @pytest.mark.asyncio
    async def test_update_price_negative(self, test_db, test_applications):
        """测试设置负价格"""
        service = AdminService(test_db)
        app = test_applications[0]

        with pytest.raises(BadRequestException):
            await service.update_application_price(
                app_id=str(app.id),
                new_price=-5.0
            )


class TestUpdatePlayerRange:
    """测试update_player_range方法"""

    @pytest.mark.asyncio
    async def test_update_player_range_success(self, test_db, test_applications):
        """测试成功更新玩家范围"""
        service = AdminService(test_db)
        app = test_applications[0]

        result = await service.update_player_range(
            app_id=str(app.id),
            min_players=1,
            max_players=12
        )

        assert result["min_players"] == 1
        assert result["max_players"] == 12

    @pytest.mark.asyncio
    async def test_update_player_range_invalid(self, test_db, test_applications):
        """测试无效玩家范围"""
        service = AdminService(test_db)
        app = test_applications[0]

        with pytest.raises(BadRequestException):
            await service.update_player_range(
                app_id=str(app.id),
                min_players=10,
                max_players=5
            )


# ==================== 授权管理测试 (T154) ====================

class TestGetApplicationRequests:
    """测试get_application_requests方法"""

    @pytest.mark.asyncio
    async def test_get_requests_empty(self, test_db):
        """测试空列表"""
        service = AdminService(test_db)

        result = await service.get_application_requests()

        assert result.total == 0
        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_get_requests_with_data(self, test_db, test_operators, test_applications):
        """测试获取申请列表"""
        # Create some requests
        for i in range(2):
            req = ApplicationRequest(
                operator_id=test_operators[i].id,
                application_id=test_applications[0].id,
                request_reason=f"Request {i}",
                status="pending"
            )
            test_db.add(req)
        await test_db.commit()

        service = AdminService(test_db)
        result = await service.get_application_requests()

        assert result.total == 2
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_get_requests_filter_by_status(self, test_db, test_operators, test_applications, admin_account):
        """测试按状态过滤"""
        # Create requests with different statuses
        req1 = ApplicationRequest(
            operator_id=test_operators[0].id,
            application_id=test_applications[0].id,
            request_reason="Pending request",
            status="pending"
        )
        req2 = ApplicationRequest(
            operator_id=test_operators[1].id,
            application_id=test_applications[1].id,
            request_reason="Approved request",
            status="approved",
            reviewed_by=admin_account.id,
            reviewed_at=datetime.now(timezone.utc)
        )
        test_db.add_all([req1, req2])
        await test_db.commit()

        service = AdminService(test_db)

        # Test pending filter
        result = await service.get_application_requests(status="pending")
        assert result.total == 1
        assert result.items[0].status == "pending"

        # Test approved filter
        result = await service.get_application_requests(status="approved")
        assert result.total == 1
        assert result.items[0].status == "approved"


class TestReviewApplicationRequest:
    """测试review_application_request方法"""

    @pytest.mark.asyncio
    async def test_approve_request_success(self, test_db, test_operators, test_applications, admin_account):
        """测试成功批准申请"""
        # Create pending request
        req = ApplicationRequest(
            operator_id=test_operators[0].id,
            application_id=test_applications[0].id,
            request_reason="Test request",
            status="pending"
        )
        test_db.add(req)
        await test_db.commit()
        await test_db.refresh(req)

        service = AdminService(test_db)
        result = await service.review_application_request(
            request_id=str(req.id),
            admin_id=admin_account.id,
            action="approve"
        )

        assert result.status == "approved"
        assert result.reviewed_by == str(admin_account.id)

    @pytest.mark.asyncio
    async def test_reject_request_with_reason(self, test_db, test_operators, test_applications, admin_account):
        """测试拒绝申请并提供理由"""
        req = ApplicationRequest(
            operator_id=test_operators[0].id,
            application_id=test_applications[0].id,
            request_reason="Test request",
            status="pending"
        )
        test_db.add(req)
        await test_db.commit()
        await test_db.refresh(req)

        service = AdminService(test_db)
        result = await service.review_application_request(
            request_id=str(req.id),
            admin_id=admin_account.id,
            action="reject",
            reject_reason="Not qualified"
        )

        assert result.status == "rejected"
        assert result.reject_reason == "Not qualified"

    @pytest.mark.asyncio
    async def test_reject_without_reason_fails(self, test_db, test_operators, test_applications, admin_account):
        """测试拒绝申请但未提供理由"""
        req = ApplicationRequest(
            operator_id=test_operators[0].id,
            application_id=test_applications[0].id,
            request_reason="Test request",
            status="pending"
        )
        test_db.add(req)
        await test_db.commit()
        await test_db.refresh(req)

        service = AdminService(test_db)

        with pytest.raises(BadRequestException) as exc:
            await service.review_application_request(
                request_id=str(req.id),
                admin_id=admin_account.id,
                action="reject"
            )

        assert "required" in str(exc.value)

    @pytest.mark.asyncio
    async def test_review_already_reviewed_request(self, test_db, test_operators, test_applications, admin_account):
        """测试审批已审批的申请"""
        req = ApplicationRequest(
            operator_id=test_operators[0].id,
            application_id=test_applications[0].id,
            request_reason="Test request",
            status="approved",
            reviewed_by=admin_account.id,
            reviewed_at=datetime.now(timezone.utc)
        )
        test_db.add(req)
        await test_db.commit()
        await test_db.refresh(req)

        service = AdminService(test_db)

        with pytest.raises(BadRequestException) as exc:
            await service.review_application_request(
                request_id=str(req.id),
                admin_id=admin_account.id,
                action="approve"
            )

        assert "already" in str(exc.value)

    @pytest.mark.asyncio
    async def test_review_request_not_found(self, test_db, admin_account):
        """测试审批不存在的申请"""
        service = AdminService(test_db)

        with pytest.raises(NotFoundException):
            await service.review_application_request(
                request_id=str(uuid4()),
                admin_id=admin_account.id,
                action="approve"
            )


class TestAuthorizeApplication:
    """测试authorize_application方法"""

    @pytest.mark.asyncio
    async def test_authorize_success(self, test_db, test_operators, test_applications, admin_account):
        """测试成功授权"""
        service = AdminService(test_db)

        result = await service.authorize_application(
            operator_id=str(test_operators[0].id),
            application_id=str(test_applications[0].id),
            admin_id=admin_account.id
        )

        assert result["operator_id"] == str(test_operators[0].id)
        assert result["application_id"] == str(test_applications[0].id)
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_authorize_with_expiry(self, test_db, test_operators, test_applications, admin_account):
        """测试带过期时间的授权"""
        service = AdminService(test_db)
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        result = await service.authorize_application(
            operator_id=str(test_operators[0].id),
            application_id=str(test_applications[0].id),
            admin_id=admin_account.id,
            expires_at=expires_at
        )

        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_authorize_operator_not_found(self, test_db, test_applications, admin_account):
        """测试授权不存在的运营商"""
        service = AdminService(test_db)

        with pytest.raises(NotFoundException) as exc:
            await service.authorize_application(
                operator_id=str(uuid4()),
                application_id=str(test_applications[0].id),
                admin_id=admin_account.id
            )

        assert "Operator not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_authorize_application_not_found(self, test_db, test_operators, admin_account):
        """测试授权不存在的应用"""
        service = AdminService(test_db)

        with pytest.raises(NotFoundException) as exc:
            await service.authorize_application(
                operator_id=str(test_operators[0].id),
                application_id=str(uuid4()),
                admin_id=admin_account.id
            )

        assert "Application not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_authorize_duplicate(self, test_db, test_operators, test_applications, admin_account):
        """测试重复授权"""
        service = AdminService(test_db)

        # First authorization
        await service.authorize_application(
            operator_id=str(test_operators[0].id),
            application_id=str(test_applications[0].id),
            admin_id=admin_account.id
        )

        # Second authorization (should fail)
        with pytest.raises(BadRequestException) as exc:
            await service.authorize_application(
                operator_id=str(test_operators[0].id),
                application_id=str(test_applications[0].id),
                admin_id=admin_account.id
            )

        assert "already exists" in str(exc.value)


class TestRevokeAuthorization:
    """测试revoke_authorization方法"""

    @pytest.mark.asyncio
    async def test_revoke_success(self, test_db, test_operators, test_applications, admin_account):
        """测试成功撤销授权"""
        # Create authorization first
        auth = OperatorAppAuthorization(
            operator_id=test_operators[0].id,
            application_id=test_applications[0].id,
            authorized_by=admin_account.id,
            is_active=True,
            authorized_at=datetime.now(timezone.utc)
        )
        test_db.add(auth)
        await test_db.commit()

        service = AdminService(test_db)
        result = await service.revoke_authorization(
            operator_id=str(test_operators[0].id),
            application_id=str(test_applications[0].id)
        )

        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_revoke_not_found(self, test_db, test_operators, test_applications):
        """测试撤销不存在的授权"""
        service = AdminService(test_db)

        with pytest.raises(NotFoundException):
            await service.revoke_authorization(
                operator_id=str(test_operators[0].id),
                application_id=str(test_applications[0].id)
            )
