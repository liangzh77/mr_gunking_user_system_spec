"""
契约测试:更新运营点接口 (T095)

测试目标:
- 验证 PUT /v1/operators/me/sites/{site_id} 接口契约
- 确保请求/响应格式符合契约定义
- 覆盖成功场景、验证场景、认证场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 路径参数: site_id (运营点ID)
- 请求体可选字段: name, address, description
- 返回200状态码和更新后的运营点对象
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


# ========== PUT /v1/operators/me/sites/{site_id} 测试 ==========

@pytest.mark.asyncio
async def test_update_site_success(test_db):
    """测试成功更新运营点所有字段"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_1")

        # 创建运营点
        site = await create_site(client, token, "北京门店", "北京市朝阳区建国路88号", "旗舰店")
        site_id = site["site_id"]

        # 更新所有字段
        response = await client.put(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "北京朝阳旗舰店",
                "address": "北京市朝阳区建国路88号SOHO大厦",
                "description": "朝阳区旗舰店,面积300平米,设备已升级"
            }
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "message" in data
    assert "data" in data

    # 验证更新后的数据
    updated_site = data["data"]
    assert updated_site["site_id"] == site_id
    assert updated_site["name"] == "北京朝阳旗舰店"
    assert updated_site["address"] == "北京市朝阳区建国路88号SOHO大厦"
    assert updated_site["description"] == "朝阳区旗舰店,面积300平米,设备已升级"


@pytest.mark.asyncio
async def test_update_site_partial(test_db):
    """测试部分更新运营点(只更新name)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_2")

        # 创建运营点
        site = await create_site(client, token, "上海门店", "上海市静安区南京西路123号", "测试描述")
        site_id = site["site_id"]

        # 只更新name
        response = await client.put(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "上海静安旗舰店"
            }
        )

    assert response.status_code == 200
    data = response.json()

    updated_site = data["data"]
    assert updated_site["name"] == "上海静安旗舰店"
    # address和description应该保持不变
    assert updated_site["address"] == "上海市静安区南京西路123号"
    assert updated_site["description"] == "测试描述"


@pytest.mark.asyncio
async def test_update_site_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            "/v1/operators/me/sites/site_test_123",
            json={
                "name": "测试门店"
            }
        )

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_update_site_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            "/v1/operators/me/sites/site_test_123",
            headers={"Authorization": "Bearer invalid_token_12345"},
            json={
                "name": "测试门店"
            }
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_site_not_found(test_db):
    """测试更新不存在的运营点"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_3")

        response = await client.put(
            "/v1/operators/me/sites/site_00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "测试门店"
            }
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_site_name_too_short(test_db):
    """测试name字段太短(minLength: 2)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_4")

        # 创建运营点
        site = await create_site(client, token, "测试门店", "北京市朝阳区建国路88号")
        site_id = site["site_id"]

        response = await client.put(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "A"  # 只有1个字符
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_update_site_name_too_long(test_db):
    """测试name字段太长(maxLength: 50)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_5")

        # 创建运营点
        site = await create_site(client, token, "测试门店", "北京市朝阳区建国路88号")
        site_id = site["site_id"]

        response = await client.put(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "A" * 51  # 51个字符
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_update_site_address_too_short(test_db):
    """测试address字段太短(minLength: 5)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_6")

        # 创建运营点
        site = await create_site(client, token, "测试门店", "北京市朝阳区建国路88号")
        site_id = site["site_id"]

        response = await client.put(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "address": "123"  # 只有3个字符
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_update_site_address_too_long(test_db):
    """测试address字段太长(maxLength: 200)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_7")

        # 创建运营点
        site = await create_site(client, token, "测试门店", "北京市朝阳区建国路88号")
        site_id = site["site_id"]

        response = await client.put(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "address": "A" * 201  # 201个字符
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_update_site_description_too_long(test_db):
    """测试description字段太长(maxLength: 500)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_8")

        # 创建运营点
        site = await create_site(client, token, "测试门店", "北京市朝阳区建国路88号")
        site_id = site["site_id"]

        response = await client.put(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "description": "A" * 501  # 501个字符
            }
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_update_site_isolation(test_db):
    """测试运营商数据隔离(不能更新其他运营商的运营点)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建两个运营商
        token1 = await create_and_login_operator(client, "update_user_9")
        token2 = await create_and_login_operator(client, "update_user_10")

        # 运营商1创建运营点
        site = await create_site(client, token1, "运营商1的门店", "北京市朝阳区某地址1号")
        site_id = site["site_id"]

        # 运营商2尝试更新运营商1的运营点(应该失败)
        response = await client.put(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token2}"},
            json={
                "name": "恶意修改"
            }
        )

    # 应该返回404(因为运营商2看不到运营商1的运营点)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_site_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_11")

        # 创建运营点
        site = await create_site(client, token, "测试门店", "测试地址123号")
        site_id = site["site_id"]

        # 更新
        response = await client.put(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "更新后的门店",
                "address": "更新后的地址123号"
            }
        )

    assert response.status_code == 200
    data = response.json()

    # 验证顶层格式
    assert isinstance(data["success"], bool), "success应该是布尔类型"
    assert data["success"] is True
    assert isinstance(data.get("message", ""), str), "message应该是字符串类型"

    # 验证运营点对象必需字段
    site = data["data"]
    required_fields = ["site_id", "name", "address", "is_deleted", "created_at", "updated_at"]
    for field in required_fields:
        assert field in site, f"缺少必需字段: {field}"

    # 验证数据类型
    assert isinstance(site["site_id"], str), "site_id应该是字符串"
    assert isinstance(site["name"], str), "name应该是字符串"
    assert isinstance(site["address"], str), "address应该是字符串"
    assert isinstance(site["is_deleted"], bool), "is_deleted应该是布尔类型"
    assert isinstance(site["created_at"], str), "created_at应该是字符串(ISO format)"
    assert isinstance(site["updated_at"], str), "updated_at应该是字符串(ISO format)"
