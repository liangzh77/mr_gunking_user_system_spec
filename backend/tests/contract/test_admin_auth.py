"""
契约测试: 管理员认证API (T120/T134)

测试目标:
- 验证管理员认证相关API端点契约
- 确保请求/响应格式符合contract定义
- 覆盖登录、登出、获取信息、刷新token、修改密码场景

契约要求:
- POST /admin/login: 管理员登录
- POST /admin/logout: 管理员登出
- GET /admin/me: 获取当前管理员信息
- POST /admin/refresh: 刷新access token
- POST /admin/change-password: 修改密码
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4

from src.main import app
from src.models.admin import AdminAccount
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
        permissions={}  # 必须是字典而不是列表
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


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
        return response.json()["access_token"]  # 直接访问access_token
    return ""


# ========== POST /admin/login 测试 ==========

@pytest.mark.asyncio
async def test_admin_login_success(test_db, create_superadmin):
    """测试管理员成功登录"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/login",
            json={
                "username": "superadmin",
                "password": "Admin@123"
            }
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构 - 直接字段,没有success/data包装
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert "user" in data

    # 验证用户信息
    user_info = data["user"]
    assert user_info["username"] == "superadmin"
    assert "id" in user_info
    assert "full_name" in user_info
    assert "email" in user_info
    assert "role" in user_info


@pytest.mark.asyncio
async def test_admin_login_invalid_password(test_db, create_superadmin):
    """测试错误密码登录"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/login",
            json={
                "username": "superadmin",
                "password": "WrongPassword123"
            }
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_login_nonexistent_user(test_db, create_superadmin):
    """测试不存在的用户登录"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/login",
            json={
                "username": "nonexistent_admin",
                "password": "SomePassword123"
            }
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_login_missing_username(test_db):
    """测试缺少用户名"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/login",
            json={
                "password": "Admin@123"
            }
        )

    assert response.status_code in [400, 422]  # Validation error


@pytest.mark.asyncio
async def test_admin_login_missing_password(test_db):
    """测试缺少密码"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/login",
            json={
                "username": "superadmin"
            }
        )

    assert response.status_code in [400, 422]  # Validation error


# ========== POST /admin/logout 测试 ==========

@pytest.mark.asyncio
async def test_admin_logout_success(test_db, create_superadmin):
    """测试管理员成功登出"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.post(
            "/v1/admin/logout",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data  # MessageResponse格式


@pytest.mark.asyncio
async def test_admin_logout_without_token(test_db):
    """测试未提供Token登出"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/v1/admin/logout")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_logout_invalid_token(test_db):
    """测试无效Token登出"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/logout",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


# ========== GET /admin/me 测试 ==========

@pytest.mark.asyncio
async def test_get_admin_me_success(test_db, create_superadmin):
    """测试获取当前管理员信息"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.get(
            "/v1/admin/me",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构 - AdminUserInfo格式,直接字段
    assert data["username"] == "superadmin"
    assert "id" in data
    assert "full_name" in data
    assert "email" in data
    assert "role" in data


@pytest.mark.asyncio
async def test_get_admin_me_without_token(test_db):
    """测试未提供Token获取信息"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/admin/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_admin_me_invalid_token(test_db):
    """测试无效Token获取信息"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/admin/me",
            headers={"Authorization": "Bearer invalid_token"}
        )

    assert response.status_code == 401


# ========== POST /admin/refresh 测试 ==========

@pytest.mark.asyncio
async def test_refresh_token_success(test_db, create_superadmin):
    """测试成功刷新Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        old_token = await admin_login(client)

        # 小延迟确保新token时间戳不同
        import asyncio
        await asyncio.sleep(1)

        response = await client.post(
            "/v1/admin/refresh",
            headers={"Authorization": f"Bearer {old_token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构 - AdminLoginResponse格式
    assert "access_token" in data
    assert "token_type" in data
    assert "expires_in" in data
    assert "user" in data
    # 验证token格式正确(JWT格式)
    assert len(data["access_token"]) > 100  # JWT token应该很长
    assert data["access_token"].count('.') == 2  # JWT有3部分用.分隔


@pytest.mark.asyncio
async def test_refresh_token_without_token(test_db):
    """测试未提供Token刷新"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/v1/admin/refresh")

    assert response.status_code in [401, 422]


@pytest.mark.asyncio
async def test_refresh_token_invalid_token(test_db):
    """测试无效Token刷新"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/refresh",
            headers={"Authorization": "Bearer invalid_token"}
        )

    assert response.status_code == 401


# ========== POST /admin/change-password 测试 ==========

@pytest.mark.asyncio
async def test_change_password_success(test_db, create_superadmin):
    """测试成功修改密码"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        # 修改密码
        response = await client.post(
            "/v1/admin/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "Admin@123",
                "new_password": "NewPassword@456"
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data  # MessageResponse格式

    # 验证新密码可以登录
    async with AsyncClient(app=app, base_url="http://test") as client:
        response2 = await client.post(
            "/v1/admin/login",
            json={
                "username": "superadmin",
                "password": "NewPassword@456"
            }
        )
        assert response2.status_code == 200

        # 恢复原密码以不影响其他测试
        new_token = response2.json()["access_token"]
        await client.post(
            "/v1/admin/change-password",
            headers={"Authorization": f"Bearer {new_token}"},
            json={
                "old_password": "NewPassword@456",
                "new_password": "Admin@123"
            }
        )


@pytest.mark.asyncio
async def test_change_password_wrong_old_password(test_db, create_superadmin):
    """测试旧密码错误"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.post(
            "/v1/admin/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "WrongOldPassword",
                "new_password": "NewPassword@456"
            }
        )

    assert response.status_code in [400, 401]


@pytest.mark.asyncio
async def test_change_password_missing_old_password(test_db, create_superadmin):
    """测试缺少旧密码"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.post(
            "/v1/admin/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "new_password": "NewPassword@456"
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_change_password_missing_new_password(test_db, create_superadmin):
    """测试缺少新密码"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await admin_login(client)

        response = await client.post(
            "/v1/admin/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "Admin@123"
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_change_password_without_token(test_db):
    """测试未提供Token修改密码"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/change-password",
            json={
                "old_password": "Admin@123",
                "new_password": "NewPassword@456"
            }
        )

    assert response.status_code == 401
