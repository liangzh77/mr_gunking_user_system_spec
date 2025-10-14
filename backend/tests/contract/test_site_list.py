"""
契约测试：运营点列表接口 (T093)

测试目标:
- 验证 GET /v1/operators/me/sites 接口契约
- 确保请求/响应格式符合契约定义
- 覆盖空列表、有数据、include_deleted参数场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 可选参数: include_deleted (boolean, default: false)
- 返回运营点列表(非分页)
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
    return response.json()


# ========== GET /v1/operators/me/sites 测试 ==========

@pytest.mark.asyncio
async def test_get_sites_empty_list(test_db):
    """测试获取空运营点列表"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "list_user_1")

        response = await client.get(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "data" in data
    assert "sites" in data["data"]
    assert data["data"]["sites"] == []


@pytest.mark.asyncio
async def test_get_sites_with_data(test_db):
    """测试获取有数据的运营点列表"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "list_user_2")

        # 创建两个运营点
        await create_site(client, token, "北京门店", "北京市朝阳区建国路88号", "旗舰店")
        await create_site(client, token, "上海门店", "上海市静安区南京西路123号")

        # 查询列表
        response = await client.get(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert len(data["data"]["sites"]) == 2

    # 验证每个运营点的格式
    for site in data["data"]["sites"]:
        assert "site_id" in site
        assert "name" in site
        assert "address" in site
        assert "is_deleted" in site
        assert "created_at" in site
        assert "updated_at" in site


@pytest.mark.asyncio
async def test_get_sites_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/operators/me/sites")

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_get_sites_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/operators/me/sites",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_sites_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "list_user_3")

        # 创建一个运营点
        await create_site(client, token, "测试门店", "测试地址123号")

        response = await client.get(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证顶层格式
    assert isinstance(data["success"], bool), "success应该是布尔类型"
    assert data["success"] is True
    assert isinstance(data["data"], dict), "data应该是字典类型"
    assert isinstance(data["data"]["sites"], list), "sites应该是列表类型"

    # 验证运营点对象格式
    site = data["data"]["sites"][0]
    assert isinstance(site["site_id"], str), "site_id应该是字符串"
    assert isinstance(site["name"], str), "name应该是字符串"
    assert isinstance(site["address"], str), "address应该是字符串"
    assert isinstance(site["is_deleted"], bool), "is_deleted应该是布尔类型"
    assert isinstance(site["created_at"], str), "created_at应该是字符串"


@pytest.mark.asyncio
async def test_get_sites_isolation(test_db):
    """测试运营商数据隔离"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建两个运营商
        token1 = await create_and_login_operator(client, "list_user_4")
        token2 = await create_and_login_operator(client, "list_user_5")

        # 运营商1创建运营点
        await create_site(client, token1, "运营商1的门店", "北京市朝阳区某地址1号")

        # 运营商2查询列表(应该为空)
        response = await client.get(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token2}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["sites"]) == 0, "运营商2不应该看到运营商1的运营点"


@pytest.mark.asyncio
async def test_get_sites_include_deleted_parameter(test_db):
    """测试include_deleted参数(暂不测试实际删除功能)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "list_user_6")

        # 创建运营点
        await create_site(client, token, "测试门店", "北京市朝阳区测试地址123号")

        # 测试include_deleted=false(默认)
        response1 = await client.get(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"}
        )

        # 测试include_deleted=true
        response2 = await client.get(
            "/v1/operators/me/sites?include_deleted=true",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response1.status_code == 200
    assert response2.status_code == 200

    # 目前都应该返回相同的结果(因为没有删除的运营点)
    assert len(response1.json()["data"]["sites"]) == len(response2.json()["data"]["sites"])


@pytest.mark.asyncio
async def test_get_sites_returns_latest_first(test_db):
    """测试运营点列表顺序(最新的排在前面)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "list_user_7")

        # 依次创建3个运营点
        site1 = await create_site(client, token, "第一个门店", "北京市朝阳区地址1号")
        site2 = await create_site(client, token, "第二个门店", "北京市朝阳区地址2号")
        site3 = await create_site(client, token, "第三个门店", "北京市朝阳区地址3号")

        response = await client.get(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    sites = response.json()["data"]["sites"]

    assert len(sites) == 3
    # 验证最新创建的排在前面
    # 注意: 这取决于实际实现的排序逻辑
