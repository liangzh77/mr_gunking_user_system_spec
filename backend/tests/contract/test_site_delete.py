"""
契约测试:删除运营点接口 (T096)

测试目标:
- 验证 DELETE /v1/operators/me/sites/{site_id} 接口契约
- 确保请求/响应格式符合契约定义
- 覆盖成功场景、认证场景、软删除验证

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 路径参数: site_id (运营点ID)
- 返回200状态码和成功消息
- 逻辑删除(deleted_at设置时间戳)
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


async def create_site(client: AsyncClient, token: str, name: str, address: str, description: str = None) -> dict:
    """创建运营点并返回响应数据"""
    response = await client.post(
        "/v1/operators/me/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "address": address,
            "description": description
        }
    )
    return response.json()["data"]


# ========== DELETE /v1/operators/me/sites/{site_id} 测试 ==========

@pytest.mark.asyncio
async def test_delete_site_success(test_db):
    """测试成功删除运营点"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "delete_user_1")

        # 创建运营点
        site = await create_site(client, token, "测试门店", "北京市朝阳区建国路88号")
        site_id = site["site_id"]

        # 删除运营点
        response = await client.delete(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "message" in data


@pytest.mark.asyncio
async def test_delete_site_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete("/v1/operators/me/sites/site_test_123")

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_delete_site_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete(
            "/v1/operators/me/sites/site_test_123",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_site_not_found(test_db):
    """测试删除不存在的运营点"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "delete_user_2")

        response = await client.delete(
            "/v1/operators/me/sites/site_00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_site_isolation(test_db):
    """测试运营商数据隔离(不能删除其他运营商的运营点)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建两个运营商
        token1 = await create_and_login_operator(client, "delete_user_3")
        token2 = await create_and_login_operator(client, "delete_user_4")

        # 运营商1创建运营点
        site = await create_site(client, token1, "运营商1的门店", "北京市朝阳区某地址1号")
        site_id = site["site_id"]

        # 运营商2尝试删除运营商1的运营点(应该失败)
        response = await client.delete(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )

    # 应该返回404(因为运营商2看不到运营商1的运营点)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_site_soft_delete(test_db):
    """测试软删除(删除后仍然存在,但is_deleted=true)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "delete_user_5")

        # 创建运营点
        site = await create_site(client, token, "测试门店", "北京市朝阳区建国路88号")
        site_id = site["site_id"]

        # 删除运营点
        await client.delete(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # 查询运营点列表(不包含已删除)
        response1 = await client.get(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"}
        )

        # 查询运营点列表(包含已删除)
        response2 = await client.get(
            "/v1/operators/me/sites?include_deleted=true",
            headers={"Authorization": f"Bearer {token}"}
        )

    # 默认查询不应该包含已删除的运营点
    assert response1.status_code == 200
    assert len(response1.json()["data"]["sites"]) == 0

    # 包含已删除的查询应该看到运营点
    assert response2.status_code == 200
    sites = response2.json()["data"]["sites"]
    assert len(sites) == 1
    assert sites[0]["is_deleted"] is True


@pytest.mark.asyncio
async def test_delete_already_deleted_site(test_db):
    """测试删除已经被删除的运营点"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "delete_user_6")

        # 创建运营点
        site = await create_site(client, token, "测试门店", "北京市朝阳区建国路88号")
        site_id = site["site_id"]

        # 第一次删除
        response1 = await client.delete(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # 第二次删除(应该失败,因为已经被删除)
        response2 = await client.delete(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response1.status_code == 200
    assert response2.status_code == 404  # 已删除的运营点再次删除应该返回404
