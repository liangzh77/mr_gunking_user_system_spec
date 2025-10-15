"""
契约测试: 查询已授权应用接口 (T097)

测试目标:
- 验证 GET /v1/operators/me/applications 接口契约
- 确保请求/响应格式符合contract定义
- 覆盖有授权、无授权、过期授权场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 无查询参数
- 返回格式: {success: true, data: {applications: [...]}
- 只返回活跃且未过期的授权
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.main import app


# ========== 辅助函数 ==========

async def create_and_login_operator(client: AsyncClient, username: str) -> tuple[str, str]:
    """创建运营商并登录,返回(JWT Token, operator_id)"""
    # 注册
    response = await client.post(
        "/v1/auth/operators/register",
        json={
            "username": username,
            "password": "TestPass123",
            "name": "测试公司",
            "phone": "13800138000",
            "email": f"{username}@example.com"
        }
    )
    operator_id = response.json()["data"]["operator_id"]

    # 登录
    response = await client.post(
        "/v1/auth/operators/login",
        json={
            "username": username,
            "password": "TestPass123"
        }
    )

    return response.json()["data"]["access_token"], operator_id


async def create_application(db, app_code: str, app_name: str) -> str:
    """创建应用,返回application_id"""
    from src.models.application import Application
    from decimal import Decimal

    application = Application(
        app_code=app_code,
        app_name=app_name,
        description=f"{app_name}的描述",
        price_per_player=Decimal("10.00"),
        min_players=2,
        max_players=8,
        is_active=True
    )

    db.add(application)
    await db.commit()
    await db.refresh(application)

    return str(application.id)


async def create_authorization(db, operator_id: str, application_id: str, expires_at=None):
    """创建授权关系"""
    from src.models.authorization import OperatorAppAuthorization
    from uuid import UUID

    # 解析operator_id
    if operator_id.startswith("op_"):
        op_uuid = UUID(operator_id[3:])
    else:
        op_uuid = UUID(operator_id)

    auth = OperatorAppAuthorization(
        operator_id=op_uuid,
        application_id=UUID(application_id),
        is_active=True,
        expires_at=expires_at
    )

    db.add(auth)
    await db.commit()


# ========== GET /v1/operators/me/applications 测试 ==========

@pytest.mark.asyncio
async def test_get_authorized_applications_success(test_db):
    """测试成功查询已授权应用列表"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "auth_app_user_1")

        # 创建2个应用
        app1_id = await create_application(test_db, "space_adventure", "太空探险")
        app2_id = await create_application(test_db, "star_war", "星际战争")

        # 创建授权关系
        await create_authorization(test_db, operator_id, app1_id)
        await create_authorization(test_db, operator_id, app2_id)

        # 查询已授权应用
        response = await client.get(
            "/v1/operators/me/applications",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "data" in data
    assert "applications" in data["data"]

    # 验证返回了2个应用
    applications = data["data"]["applications"]
    assert len(applications) == 2

    # 验证应用数据结构
    first_app = applications[0]
    assert "app_id" in first_app
    assert first_app["app_id"].startswith("app_")
    assert "app_code" in first_app
    assert "app_name" in first_app
    assert "description" in first_app
    assert "price_per_player" in first_app
    assert "min_players" in first_app
    assert "max_players" in first_app
    assert "authorized_at" in first_app
    assert "expires_at" in first_app
    assert "is_active" in first_app
    assert first_app["is_active"] is True


@pytest.mark.asyncio
async def test_get_authorized_applications_empty(test_db):
    """测试查询无授权的运营商"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "auth_app_user_2")

        # 不创建任何授权
        response = await client.get(
            "/v1/operators/me/applications",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证返回空列表
    assert data["success"] is True
    assert data["data"]["applications"] == []


@pytest.mark.asyncio
async def test_get_authorized_applications_future_expiry(test_db):
    """测试返回未来过期的授权(仍有效)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "auth_app_user_3")

        # 创建应用
        app_id = await create_application(test_db, "future_expire_game", "未来过期游戏")

        # 创建未来过期的授权(30天后过期)
        future_time = datetime.now(timezone.utc) + timedelta(days=30)
        await create_authorization(test_db, operator_id, app_id, expires_at=future_time)

        # 查询已授权应用
        response = await client.get(
            "/v1/operators/me/applications",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证返回未过期授权
    applications = data["data"]["applications"]
    assert len(applications) == 1
    assert applications[0]["app_code"] == "future_expire_game"
    # 验证expires_at不为None
    assert applications[0]["expires_at"] is not None


@pytest.mark.asyncio
async def test_get_authorized_applications_permanent(test_db):
    """测试返回永久授权(expires_at为null)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "auth_app_user_4")

        # 创建应用
        app_id = await create_application(test_db, "permanent_game", "永久游戏")

        # 创建永久授权(expires_at=None)
        await create_authorization(test_db, operator_id, app_id, expires_at=None)

        # 查询已授权应用
        response = await client.get(
            "/v1/operators/me/applications",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证返回永久授权
    applications = data["data"]["applications"]
    assert len(applications) == 1
    assert applications[0]["expires_at"] is None


@pytest.mark.asyncio
async def test_get_authorized_applications_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/operators/me/applications")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_authorized_applications_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/operators/me/applications",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_authorized_applications_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "auth_app_user_5")

        # 创建应用和授权
        app_id = await create_application(test_db, "format_test", "格式测试游戏")
        await create_authorization(test_db, operator_id, app_id)

        response = await client.get(
            "/v1/operators/me/applications",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证顶层格式
    assert isinstance(data["success"], bool)
    assert data["success"] is True
    assert isinstance(data["data"], dict)
    assert isinstance(data["data"]["applications"], list)

    # 验证应用对象格式
    first_app = data["data"]["applications"][0]
    assert isinstance(first_app["app_id"], str)
    assert isinstance(first_app["app_code"], str)
    assert isinstance(first_app["app_name"], str)
    assert isinstance(first_app["price_per_player"], str)
    assert isinstance(first_app["min_players"], int)
    assert isinstance(first_app["max_players"], int)
    assert isinstance(first_app["authorized_at"], str)
    assert isinstance(first_app["is_active"], bool)


@pytest.mark.asyncio
async def test_get_authorized_applications_multiple_apps(test_db):
    """测试返回多个授权应用"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "auth_app_user_6")

        # 创建3个应用并依次授权
        app1_id = await create_application(test_db, "game1", "游戏1")
        await create_authorization(test_db, operator_id, app1_id)

        app2_id = await create_application(test_db, "game2", "游戏2")
        await create_authorization(test_db, operator_id, app2_id)

        app3_id = await create_application(test_db, "game3", "游戏3")
        await create_authorization(test_db, operator_id, app3_id)

        # 查询已授权应用
        response = await client.get(
            "/v1/operators/me/applications",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    applications = response.json()["data"]["applications"]

    # 验证返回3个应用
    assert len(applications) == 3

    # 验证所有应用都在列表中(不关心顺序)
    app_codes = {item["app_code"] for item in applications}
    assert "game1" in app_codes
    assert "game2" in app_codes
    assert "game3" in app_codes

    # 验证所有应用都有authorized_at字段
    for item in applications:
        assert "authorized_at" in item
        assert item["authorized_at"] is not None
