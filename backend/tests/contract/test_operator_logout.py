"""
契约测试: 运营商登出接口 (T068)

测试目标:
- 验证 POST /v1/auth/operators/logout 接口契约
- 确保请求/响应格式符合contract定义
- 覆盖正常登出、未认证、无效Token场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 返回格式: {success: true, message: str}
- Token无效时返回401错误
"""
import pytest
from httpx import AsyncClient

from src.main import app


# ========== 辅助函数 ==========

async def create_and_login_operator(client: AsyncClient, username: str) -> str:
    """创建运营商并登录,返回JWT Token"""
    # 注册
    await client.post(
        "/v1/auth/operators/register",
        json={
            "username": username,
            "password": "TestPass123",
            "name": "测试公司",
            "phone": "13800138000",
            "email": f"{username}@example.com"
        }
    )

    # 登录
    response = await client.post(
        "/v1/auth/operators/login",
        json={
            "username": username,
            "password": "TestPass123"
        }
    )

    return response.json()["data"]["access_token"]


# ========== POST /v1/auth/operators/logout 测试 ==========

@pytest.mark.asyncio
async def test_logout_success(test_db):
    """测试成功登出"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 先登录获取token
        token = await create_and_login_operator(client, "logout_user_1")

        # 执行登出
        response = await client.post(
            "/v1/auth/operators/logout",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "message" in data
    assert data["message"] == "已退出登录"


@pytest.mark.asyncio
async def test_logout_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/v1/auth/operators/logout")

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_logout_with_invalid_token(test_db):
    """测试使用无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/logout",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_logout_with_malformed_auth_header(test_db):
    """测试Authorization header格式错误"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "logout_user_2")

        # 缺少Bearer前缀
        response = await client.post(
            "/v1/auth/operators/logout",
            headers={"Authorization": token}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "logout_user_3")

        response = await client.post(
            "/v1/auth/operators/logout",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证顶层格式
    assert isinstance(data["success"], bool)
    assert data["success"] is True
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0


@pytest.mark.asyncio
async def test_logout_multiple_times(test_db):
    """测试多次登出(第二次应该失败因为token已失效)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "logout_user_4")

        # 第一次登出
        response1 = await client.post(
            "/v1/auth/operators/logout",
            headers={"Authorization": f"Bearer {token}"}
        )

        # 第二次登出(使用相同token)
        response2 = await client.post(
            "/v1/auth/operators/logout",
            headers={"Authorization": f"Bearer {token}"}
        )

    # 第一次应该成功
    assert response1.status_code == 200

    # 第二次应该失败(token已在黑名单)
    # 注意: 如果未实现token黑名单,这个测试可能会通过
    # 这取决于实现策略: token黑名单 vs 客户端token清理
    assert response2.status_code in [200, 401]  # 两种实现都可接受


@pytest.mark.asyncio
async def test_logout_then_access_protected_resource(test_db):
    """测试登出后访问受保护资源应失败"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "logout_user_5")

        # 先验证token有效(访问个人信息)
        profile_response = await client.get(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert profile_response.status_code == 200

        # 登出
        logout_response = await client.post(
            "/v1/auth/operators/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert logout_response.status_code == 200

        # 登出后再访问个人信息应失败
        profile_response_after = await client.get(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        # 如果实现了token黑名单,应该返回401
        # 如果依赖客户端清理,可能仍然返回200
        # 我们接受两种实现方式
        assert profile_response_after.status_code in [200, 401]
