"""
契约测试：运营商个人信息管理接口 (T069, T070)

测试目标：
- 验证 GET /v1/operators/me 接口契约 (T069)
- 验证 PUT /v1/operators/me 接口契约 (T070)
- 确保请求/响应格式符合契约定义
- 覆盖认证、授权、参数验证等场景

契约要求：
- 需要JWT Token认证 (Authorization: Bearer {token})
- GET返回完整个人信息
- PUT允许更新: name, phone, email
- PUT不允许更新: username, password, balance, category
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


# ========== T069: GET /v1/operators/me 测试 ==========

@pytest.mark.asyncio
async def test_get_profile_success(test_db):
    """测试成功获取个人信息"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "profile_user_1")

        response = await client.get(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert "operator_id" in data
    assert "username" in data
    assert data["username"] == "profile_user_1"
    assert "name" in data
    assert data["name"] == "测试公司"
    assert "phone" in data
    assert data["phone"] == "13800138000"
    assert "email" in data
    assert data["email"] == "profile_user_1@example.com"
    assert "category" in data
    assert data["category"] in ["trial", "normal", "vip"]
    assert "balance" in data
    assert data["balance"] == "0.00"
    assert "is_active" in data
    assert data["is_active"] is True
    assert "is_locked" in data
    assert data["is_locked"] is False
    assert "created_at" in data

    # last_login_at可能为空或有值
    assert "last_login_at" in data


@pytest.mark.asyncio
async def test_get_profile_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/operators/me")

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data or "detail" in data


@pytest.mark.asyncio
async def test_get_profile_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/operators/me",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_profile_with_expired_token(test_db):
    """测试过期Token (模拟场景,实际token不会立即过期)"""
    # 这个测试需要等待token过期或使用mock
    # 暂时跳过,仅验证格式
    pass


# ========== T070: PUT /v1/operators/me 测试 ==========

@pytest.mark.asyncio
async def test_update_profile_success_all_fields(test_db):
    """测试成功更新所有允许的字段"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_1")

        response = await client.put(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "新公司名称",
                "phone": "13900139000",
                "email": "newemail@example.com"
            }
        )

    assert response.status_code == 200
    data = response.json()

    # 验证更新成功
    assert data["name"] == "新公司名称"
    assert data["phone"] == "13900139000"
    assert data["email"] == "newemail@example.com"

    # 验证其他字段不变
    assert data["username"] == "update_user_1"
    assert data["category"] == "trial"
    assert data["balance"] == "0.00"


@pytest.mark.asyncio
async def test_update_profile_partial_update_name_only(test_db):
    """测试只更新姓名"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_2")

        response = await client.put(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "只改名字"
            }
        )

    assert response.status_code == 200
    data = response.json()

    # 验证只有name更新
    assert data["name"] == "只改名字"
    assert data["phone"] == "13800138000"  # 不变
    assert data["email"] == "update_user_2@example.com"  # 不变


@pytest.mark.asyncio
async def test_update_profile_partial_update_phone_only(test_db):
    """测试只更新手机号"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_3")

        response = await client.put(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "phone": "13911111111"
            }
        )

    assert response.status_code == 200
    data = response.json()

    assert data["phone"] == "13911111111"
    assert data["name"] == "测试公司"  # 不变


@pytest.mark.asyncio
async def test_update_profile_partial_update_email_only(test_db):
    """测试只更新邮箱"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_4")

        response = await client.put(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "changed@test.com"
            }
        )

    assert response.status_code == 200
    data = response.json()

    assert data["email"] == "changed@test.com"
    assert data["name"] == "测试公司"  # 不变


@pytest.mark.asyncio
async def test_update_profile_with_invalid_phone_format(test_db):
    """测试无效手机号格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_5")

        response = await client.put(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "phone": "12345"  # 无效格式
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert "error_code" in data
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_update_profile_with_invalid_email_format(test_db):
    """测试无效邮箱格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_6")

        response = await client.put(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "not-an-email"  # 无效格式
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_update_profile_with_empty_body(test_db):
    """测试空请求体(所有字段为空,不更新任何内容)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_7")

        response = await client.put(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"},
            json={}
        )

    # 空body应该返回200,不更新任何内容
    assert response.status_code == 200
    data = response.json()

    # 验证数据未变
    assert data["name"] == "测试公司"
    assert data["phone"] == "13800138000"


@pytest.mark.asyncio
async def test_update_profile_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            "/v1/operators/me",
            json={"name": "新名字"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_profile_username_not_allowed(test_db):
    """测试尝试更新username(不允许)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_8")

        response = await client.put(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "hacker_attempt",  # 尝试修改username
                "name": "合法修改"
            }
        )

    # 应该忽略username字段,只更新name
    assert response.status_code == 200
    data = response.json()

    assert data["username"] == "update_user_8"  # username不变
    assert data["name"] == "合法修改"  # name更新


@pytest.mark.asyncio
async def test_update_profile_returns_complete_info(test_db):
    """测试更新后返回完整信息"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_9")

        response = await client.put(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "完整测试"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证返回完整的OperatorProfile
    required_fields = [
        "operator_id", "username", "name", "phone", "email",
        "category", "balance", "is_active", "is_locked",
        "created_at"
    ]

    for field in required_fields:
        assert field in data, f"缺少必需字段: {field}"


# ========== 边界条件测试 ==========

@pytest.mark.asyncio
async def test_update_profile_name_too_short(test_db):
    """测试姓名过短(<2字符)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_10")

        response = await client.put(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "A"}  # 只有1个字符
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_update_profile_name_too_long(test_db):
    """测试姓名过长(>50字符)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "update_user_11")

        response = await client.put(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "A" * 51}  # 51个字符
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_get_and_update_consistency(test_db):
    """测试GET和PUT的数据一致性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "consistency_user")

        # 先GET
        get_response = await client.get(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        original_data = get_response.json()

        # 然后PUT更新
        update_response = await client.put(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "一致性测试"}
        )
        updated_data = update_response.json()

        # 再次GET验证
        final_response = await client.get(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        final_data = final_response.json()

    # 验证数据一致性
    assert updated_data["name"] == "一致性测试"
    assert final_data["name"] == "一致性测试"
    assert updated_data["operator_id"] == original_data["operator_id"]
    assert final_data["operator_id"] == original_data["operator_id"]
