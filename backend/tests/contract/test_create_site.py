"""
契约测试：创建运营点接口 (T083)

测试目标:
- 验证 POST /v1/operators/me/sites 接口契约
- 确保请求/响应格式符合契约定义
- 覆盖成功场景、验证场景、认证场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 请求体必需字段: name, address
- 请求体可选字段: description
- 返回201状态码和运营点对象
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


# ========== POST /v1/operators/me/sites 测试 ==========

@pytest.mark.asyncio
async def test_create_site_success(test_db):
    """测试成功创建运营点"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_owner_1")

        response = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "北京朝阳门店",
                "address": "北京市朝阳区建国路88号",
                "description": "朝阳区旗舰店，面积300平米"
            }
        )

    assert response.status_code == 201
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "message" in data
    assert "data" in data

    # 验证运营点数据
    site = data["data"]
    assert "site_id" in site
    assert site["name"] == "北京朝阳门店"
    assert site["address"] == "北京市朝阳区建国路88号"
    assert site["description"] == "朝阳区旗舰店，面积300平米"
    assert site["is_deleted"] is False
    assert "created_at" in site
    assert "updated_at" in site


@pytest.mark.asyncio
async def test_create_site_without_description(test_db):
    """测试创建运营点(不提供可选描述)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_owner_2")

        response = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "上海静安店",
                "address": "上海市静安区南京西路123号"
            }
        )

    assert response.status_code == 201
    data = response.json()

    site = data["data"]
    assert site["name"] == "上海静安店"
    assert site["address"] == "上海市静安区南京西路123号"
    # description可能为None或不存在


@pytest.mark.asyncio
async def test_create_site_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/operators/me/sites",
            json={
                "name": "测试门店",
                "address": "测试地址123号"
            }
        )

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_create_site_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": "Bearer invalid_token_12345"},
            json={
                "name": "测试门店",
                "address": "测试地址123号"
            }
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_site_missing_name(test_db):
    """测试缺少必需字段name"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_owner_3")

        response = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "address": "北京市朝阳区建国路88号"
            }
        )

    # FastAPI validation会返回422或400(取决于异常处理器)
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_site_missing_address(test_db):
    """测试缺少必需字段address"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_owner_4")

        response = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "北京朝阳门店"
            }
        )

    # FastAPI validation会返回422或400(取决于异常处理器)
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_site_name_too_short(test_db):
    """测试name字段太短(minLength: 2)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_owner_5")

        response = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "A",  # 只有1个字符
                "address": "北京市朝阳区建国路88号"
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_site_name_too_long(test_db):
    """测试name字段太长(maxLength: 50)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_owner_6")

        response = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "A" * 51,  # 51个字符
                "address": "北京市朝阳区建国路88号"
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_site_address_too_short(test_db):
    """测试address字段太短(minLength: 5)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_owner_7")

        response = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "测试门店",
                "address": "123"  # 只有3个字符
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_site_address_too_long(test_db):
    """测试address字段太长(maxLength: 200)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_owner_8")

        response = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "测试门店",
                "address": "A" * 201  # 201个字符
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_site_description_too_long(test_db):
    """测试description字段太长(maxLength: 500)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_owner_9")

        response = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "测试门店",
                "address": "北京市朝阳区建国路88号",
                "description": "A" * 501  # 501个字符
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_multiple_sites(test_db):
    """测试同一运营商创建多个运营点"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_owner_10")

        # 创建第一个运营点
        response1 = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "北京门店",
                "address": "北京市朝阳区建国路88号"
            }
        )

        # 创建第二个运营点
        response2 = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "上海门店",
                "address": "上海市静安区南京西路123号"
            }
        )

    assert response1.status_code == 201
    assert response2.status_code == 201

    site1 = response1.json()["data"]
    site2 = response2.json()["data"]

    # 验证两个运营点的ID不同
    assert site1["site_id"] != site2["site_id"]
    assert site1["name"] == "北京门店"
    assert site2["name"] == "上海门店"


@pytest.mark.asyncio
async def test_create_site_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_owner_11")

        response = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "测试门店",
                "address": "测试地址123号"
            }
        )

    assert response.status_code == 201
    data = response.json()

    # 验证顶层字段
    assert isinstance(data["success"], bool), "success应该是布尔类型"
    assert data["success"] is True
    assert isinstance(data.get("message", ""), str), "message应该是字符串类型"

    # 验证运营点对象必需字段
    site = data["data"]
    required_fields = ["site_id", "name", "address", "is_deleted", "created_at"]
    for field in required_fields:
        assert field in site, f"缺少必需字段: {field}"

    # 验证数据类型
    assert isinstance(site["site_id"], str), "site_id应该是字符串"
    assert isinstance(site["name"], str), "name应该是字符串"
    assert isinstance(site["address"], str), "address应该是字符串"
    assert isinstance(site["is_deleted"], bool), "is_deleted应该是布尔类型"
    assert isinstance(site["created_at"], str), "created_at应该是字符串(ISO format)"
