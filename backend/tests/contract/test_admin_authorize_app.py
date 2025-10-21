"""
契约测试: 管理员授权管理API (T122)

测试目标:
- 验证授权管理相关API端点契约
- 确保请求/响应格式符合contract定义
- 覆盖应用管理、授权管理、申请审核场景

契约要求:
- POST /admin/admins/applications: 创建应用
- PUT /admin/admins/applications/{app_id}/price: 更新应用价格
- PUT /admin/admins/applications/{app_id}/player-range: 更新玩家范围
- POST /admin/admins/operators/{operator_id}/applications: 授权应用
- DELETE /admin/admins/operators/{operator_id}/applications/{app_id}: 撤销授权
- GET /admin/admins/applications/requests: 获取授权申请列表
- POST /admin/admins/applications/requests/{request_id}/review: 审核申请
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from decimal import Decimal

from src.main import app
from src.models.admin import AdminAccount
from src.models.operator import OperatorAccount
from src.models.application import Application
from src.models.app_request import ApplicationRequest
from src.core.utils.password import hash_password


# ========== Fixtures ==========

@pytest.fixture
async def create_superadmin(test_db):
    """创建superadmin测试账户"""
    admin = AdminAccount(
        id=uuid4(),
        username="superadmin",
        password_hash=hash_password("Admin@123"),
        full_name="Super Administrator",
        email="superadmin@test.com",
        phone="13800138000",
        role="super_admin",
        permissions=[]
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


@pytest.fixture
async def create_operator(test_db):
    """创建测试运营商账户"""
    # 生成api_key和api_key_hash
    import hashlib
    api_key_raw = "test_api_key_" + str(uuid4())[:8]
    api_key_value = hashlib.sha256(api_key_raw.encode()).hexdigest()[:64]
    api_key_hash_value = hash_password(api_key_value)  # 使用bcrypt hash

    operator = OperatorAccount(
        id=uuid4(),
        username="test_operator",
        password_hash=hash_password("Operator@123"),
        full_name="Test Operator Company",
        email="operator@test.com",
        phone="13900139000",
        api_key=api_key_value,
        api_key_hash=api_key_hash_value,
        customer_tier="standard",
        balance=Decimal("1000.00")
    )
    test_db.add(operator)
    await test_db.commit()
    await test_db.refresh(operator)
    return operator


@pytest.fixture
async def create_application(test_db, create_superadmin):
    """创建测试应用"""
    app_obj = Application(
        id=uuid4(),
        app_code="test_app_001",
        app_name="Test Application",
        description="Test application description",
        price_per_player=Decimal("10.00"),
        min_players=2,
        max_players=8,
        is_active=True,
        created_by=create_superadmin.id
    )
    test_db.add(app_obj)
    await test_db.commit()
    await test_db.refresh(app_obj)
    return app_obj


@pytest.fixture
async def create_app_request(test_db, create_operator, create_application):
    """创建应用授权申请"""
    request = ApplicationRequest(
        id=uuid4(),
        operator_id=create_operator.id,
        application_id=create_application.id,
        request_reason="我们门店新增了VR设备，希望提供该游戏体验",
        status="pending"
    )
    test_db.add(request)
    await test_db.commit()
    await test_db.refresh(request)
    return request


# ========== 辅助函数 ==========

async def admin_login(client: AsyncClient, username: str = "superadmin", password: str = "Admin@123") -> str:
    """管理员登录,返回JWT Token"""
    response = await client.post(
        "/v1/admin/login",
        json={
            "username": username,
            "password": password
        }
    )

    if response.status_code == 200:
        return response.json()["access_token"]
    return ""


# ========== POST /admin/admins/applications 测试 (T141) ==========

@pytest.mark.asyncio
async def test_create_application_success(test_db, create_superadmin):
    """测试成功创建应用"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.post(
            "/v1/admins/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_code": "space_adventure_v1",
                "app_name": "太空探险",
                "description": "VR太空探险游戏",
                "price_per_player": 12.50,
                "min_players": 2,
                "max_players": 8
            }
        )

    assert response.status_code == 201
    data = response.json()

    # 验证响应结构 - dict格式,直接字段
    assert "id" in data
    assert data["app_code"] == "space_adventure_v1"
    assert data["app_name"] == "太空探险"
    assert "price_per_player" in data
    assert data["min_players"] == 2
    assert data["max_players"] == 8


@pytest.mark.asyncio
async def test_create_application_duplicate_code(test_db, create_superadmin, create_application):
    """测试创建重复app_code的应用"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.post(
            "/v1/admins/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_code": "test_app_001",  # 与fixture中的重复
                "app_name": "Duplicate App",
                "price_per_player": 10.00,
                "min_players": 2,
                "max_players": 8
            }
        )

    assert response.status_code in [400, 409]  # Bad Request or Conflict


@pytest.mark.asyncio
async def test_create_application_invalid_price(test_db, create_superadmin):
    """测试创建负价格应用"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.post(
            "/v1/admins/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_code": "negative_price_app",
                "app_name": "Negative Price App",
                "price_per_player": -10.00,
                "min_players": 2,
                "max_players": 8
            }
        )

    assert response.status_code in [400, 422]  # Validation error


@pytest.mark.asyncio
async def test_create_application_invalid_player_range(test_db, create_superadmin):
    """测试创建不合法玩家范围的应用(min > max)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.post(
            "/v1/admins/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_code": "invalid_range_app",
                "app_name": "Invalid Range App",
                "price_per_player": 10.00,
                "min_players": 10,
                "max_players": 2  # max < min
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_application_without_token(test_db):
    """测试未提供Token创建应用"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/admins/applications",
            json={
                "app_code": "unauthorized_app",
                "app_name": "Unauthorized App",
                "price_per_player": 10.00,
                "min_players": 2,
                "max_players": 8
            }
        )

    assert response.status_code == 401


# ========== PUT /admin/admins/applications/{app_id}/price 测试 (T143) ==========

@pytest.mark.asyncio
async def test_update_application_price_success(test_db, create_superadmin, create_application):
    """测试成功更新应用价格"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.put(
            f"/v1/admins/applications/{create_application.id}/price",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "new_price": 15.00
            }
        )

    assert response.status_code == 200
    data = response.json()

    # 验证价格已更新
    assert "price_per_player" in data
    assert float(data["price_per_player"]) == 15.00


@pytest.mark.asyncio
async def test_update_application_price_negative(test_db, create_superadmin, create_application):
    """测试更新为负价格"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.put(
            f"/v1/admins/applications/{create_application.id}/price",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "new_price": -5.00
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_update_application_price_not_found(test_db, create_superadmin):
    """测试更新不存在的应用价格"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        fake_id = str(uuid4())
        response = await client.put(
            f"/v1/admins/applications/{fake_id}/price",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "new_price": 15.00
            }
        )

    assert response.status_code == 404


# ========== PUT /admin/admins/applications/{app_id}/player-range 测试 (T144) ==========

@pytest.mark.asyncio
async def test_update_player_range_success(test_db, create_superadmin, create_application):
    """测试成功更新玩家范围"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.put(
            f"/v1/admins/applications/{create_application.id}/player-range",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "min_players": 4,
                "max_players": 10
            }
        )

    assert response.status_code == 200
    data = response.json()

    # 验证范围已更新
    assert data["min_players"] == 4
    assert data["max_players"] == 10


@pytest.mark.asyncio
async def test_update_player_range_invalid(test_db, create_superadmin, create_application):
    """测试更新不合法的玩家范围(min > max)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.put(
            f"/v1/admins/applications/{create_application.id}/player-range",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "min_players": 10,
                "max_players": 2  # max < min
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_update_player_range_not_found(test_db, create_superadmin):
    """测试更新不存在的应用玩家范围"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        fake_id = str(uuid4())
        response = await client.put(
            f"/v1/admins/applications/{fake_id}/player-range",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "min_players": 2,
                "max_players": 8
            }
        )

    assert response.status_code == 404


# ========== POST /admin/admins/operators/{operator_id}/applications 测试 (T145) ==========

@pytest.mark.asyncio
async def test_authorize_application_success(test_db, create_superadmin, create_operator, create_application):
    """测试成功授权应用"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.post(
            f"/v1/admins/operators/{create_operator.id}/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "application_id": str(create_application.id)
            }
        )

    assert response.status_code == 201
    data = response.json()

    # 验证授权记录
    assert "operator_id" in data
    assert "application_id" in data
    assert "authorized_at" in data


@pytest.mark.asyncio
async def test_authorize_application_with_expiry(test_db, create_superadmin, create_operator, create_application):
    """测试授权应用并设置到期时间"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.post(
            f"/v1/admins/operators/{create_operator.id}/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "application_id": str(create_application.id),
                "expires_at": "2025-12-31T23:59:59"
            }
        )

    assert response.status_code == 201
    data = response.json()

    assert "expires_at" in data
    assert data["expires_at"] is not None


@pytest.mark.asyncio
async def test_authorize_application_not_found_operator(test_db, create_superadmin, create_application):
    """测试授权不存在的运营商"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        fake_operator_id = str(uuid4())
        response = await client.post(
            f"/v1/admins/operators/{fake_operator_id}/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "application_id": str(create_application.id)
            }
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_authorize_application_not_found_app(test_db, create_superadmin, create_operator):
    """测试授权不存在的应用"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        fake_app_id = str(uuid4())
        response = await client.post(
            f"/v1/admins/operators/{create_operator.id}/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "application_id": fake_app_id
            }
        )

    assert response.status_code == 404


# ========== DELETE /admin/admins/operators/{operator_id}/applications/{app_id} 测试 (T146) ==========

@pytest.mark.asyncio
async def test_revoke_authorization_success(test_db, create_superadmin, create_operator, create_application):
    """测试成功撤销授权"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        # 先授权
        await client.post(
            f"/v1/admins/operators/{create_operator.id}/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "application_id": str(create_application.id)
            }
        )

        # 然后撤销
        response = await client.delete(
            f"/v1/admins/operators/{create_operator.id}/applications/{create_application.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "operator_id" in data or "message" in data  # 可能返回撤销的记录或消息


@pytest.mark.asyncio
async def test_revoke_authorization_not_authorized(test_db, create_superadmin, create_operator, create_application):
    """测试撤销未授权的应用"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        # 直接撤销(未先授权)
        response = await client.delete(
            f"/v1/admins/operators/{create_operator.id}/applications/{create_application.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code in [400, 404]  # 可能返回未找到或业务错误


@pytest.mark.asyncio
async def test_revoke_authorization_invalid_operator(test_db, create_superadmin, create_application):
    """测试撤销不存在运营商的授权"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        fake_operator_id = str(uuid4())
        response = await client.delete(
            f"/v1/admins/operators/{fake_operator_id}/applications/{create_application.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code in [400, 404]


# ========== GET /admin/admins/applications/requests 测试 (T147) ==========

@pytest.mark.asyncio
async def test_get_application_requests_success(test_db, create_superadmin, create_app_request):
    """测试获取授权申请列表"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.get(
            "/v1/admins/applications/requests",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构 - ApplicationRequestListResponse
    assert "page" in data
    assert "page_size" in data
    assert "total" in data
    assert "items" in data
    assert len(data["items"]) >= 1

    # 验证item结构
    item = data["items"][0]
    assert "request_id" in item
    assert "app_id" in item
    assert "app_name" in item
    assert "reason" in item
    assert "status" in item


@pytest.mark.asyncio
async def test_get_application_requests_with_status_filter(test_db, create_superadmin, create_app_request):
    """测试按状态筛选授权申请"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.get(
            "/v1/admins/applications/requests?status=pending",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证所有返回的item状态都是pending
    for item in data["items"]:
        assert item["status"] == "pending"


@pytest.mark.asyncio
async def test_get_application_requests_pagination(test_db, create_superadmin, create_app_request):
    """测试授权申请列表分页"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.get(
            "/v1/admins/applications/requests?page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_get_application_requests_without_token(test_db):
    """测试未提供Token获取授权申请列表"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/admins/applications/requests")

    assert response.status_code == 401


# ========== POST /admin/admins/applications/requests/{request_id}/review 测试 (T148) ==========

@pytest.mark.asyncio
async def test_review_application_request_approve(test_db, create_superadmin, create_app_request):
    """测试审批通过授权申请"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.post(
            f"/v1/admins/applications/requests/{create_app_request.id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action": "approve"
            }
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构 - ApplicationRequestItem
    assert data["status"] == "approved"
    assert "reviewed_by" in data
    assert "reviewed_at" in data


@pytest.mark.asyncio
async def test_review_application_request_reject(test_db, create_superadmin, create_app_request):
    """测试拒绝授权申请"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.post(
            f"/v1/admins/applications/requests/{create_app_request.id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action": "reject",
                "reject_reason": "该应用暂未对您的客户分类开放授权"
            }
        )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "rejected"
    assert data["reject_reason"] == "该应用暂未对您的客户分类开放授权"
    assert "reviewed_by" in data


@pytest.mark.asyncio
async def test_review_application_request_reject_without_reason(test_db, create_superadmin, create_app_request):
    """测试拒绝时未提供拒绝理由"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.post(
            f"/v1/admins/applications/requests/{create_app_request.id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action": "reject"
                # 缺少reject_reason
            }
        )

    assert response.status_code in [400, 422]  # 应该要求提供reject_reason


@pytest.mark.asyncio
async def test_review_application_request_invalid_action(test_db, create_superadmin, create_app_request):
    """测试无效的审核动作"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.post(
            f"/v1/admins/applications/requests/{create_app_request.id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action": "invalid_action"
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_review_application_request_not_found(test_db, create_superadmin):
    """测试审核不存在的申请"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        fake_request_id = str(uuid4())
        response = await client.post(
            f"/v1/admins/applications/requests/{fake_request_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action": "approve"
            }
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_review_application_request_without_token(test_db, create_app_request):
    """测试未提供Token审核申请"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            f"/v1/admins/applications/requests/{create_app_request.id}/review",
            json={
                "action": "approve"
            }
        )

    assert response.status_code == 401
