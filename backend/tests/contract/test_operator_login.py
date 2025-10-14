"""
契约测试：运营商登录接口 (T051)

测试目标：
- 验证 POST /v1/auth/operators/login 接口契约
- 确保请求/响应格式符合 auth.yaml 定义
- 覆盖成功登录、认证失败、账户注销等场景

契约要求：
- 请求字段：username, password（全部必填）
- 响应200：返回 access_token, token_type, expires_in, operator{operator_id, username, name, category}
- 响应401：用户名或密码错误
- 响应403：账户已注销
"""
import pytest
from httpx import AsyncClient

from src.main import app


# ========== 成功场景 ==========

@pytest.mark.asyncio
async def test_operator_login_success(test_db):
    """测试运营商成功登录"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 先注册一个账户
        register_response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "test_login_user",
                "password": "ValidPass123",
                "name": "测试登录公司",
                "phone": "13900139000",
                "email": "testlogin@example.com"
            }
        )
        assert register_response.status_code == 201

        # 使用注册的账户登录
        login_response = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "test_login_user",
                "password": "ValidPass123"
            }
        )

    assert login_response.status_code == 200
    data = login_response.json()

    # 验证响应结构
    assert "success" in data
    assert data["success"] is True
    assert "data" in data

    # 验证Token数据
    token_data = data["data"]
    assert "access_token" in token_data
    assert "token_type" in token_data
    assert token_data["token_type"] == "Bearer"
    assert "expires_in" in token_data
    assert isinstance(token_data["expires_in"], int)
    assert token_data["expires_in"] == 2592000  # 30天

    # 验证运营商信息
    assert "operator" in token_data
    operator = token_data["operator"]
    assert "operator_id" in operator
    assert "username" in operator
    assert operator["username"] == "test_login_user"
    assert "name" in operator
    assert operator["name"] == "测试登录公司"
    assert "category" in operator
    assert operator["category"] in ["trial", "normal", "vip"]

    # 验证JWT Token格式（应该是三部分由.分隔）
    token = token_data["access_token"]
    assert token.count(".") == 2  # JWT格式: header.payload.signature


@pytest.mark.asyncio
async def test_login_returns_valid_jwt_token(test_db):
    """测试登录返回有效的JWT Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 注册
        await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "jwt_test_user",
                "password": "ValidPass123",
                "name": "JWT测试公司",
                "phone": "13900139001",
                "email": "jwt@example.com"
            }
        )

        # 登录
        response = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "jwt_test_user",
                "password": "ValidPass123"
            }
        )

    assert response.status_code == 200
    token = response.json()["data"]["access_token"]

    # JWT Token应该以eyJ开头（Base64编码的JSON）
    assert token.startswith("eyJ")


# ========== 认证失败场景 ==========

@pytest.mark.asyncio
async def test_login_with_wrong_password(test_db):
    """测试密码错误"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 注册
        await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "wrong_pass_user",
                "password": "CorrectPass123",
                "name": "测试公司",
                "phone": "13900139002",
                "email": "wrongpass@example.com"
            }
        )

        # 使用错误密码登录
        response = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "wrong_pass_user",
                "password": "WrongPass456"  # 错误密码
            }
        )

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data
    assert data["error_code"] == "UNAUTHORIZED"
    assert "message" in data
    assert "用户名或密码错误" in data["message"]


@pytest.mark.asyncio
async def test_login_with_nonexistent_username(test_db):
    """测试用户名不存在"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "nonexistent_user_12345",
                "password": "SomePass123"
            }
        )

    assert response.status_code == 401
    data = response.json()
    assert data["error_code"] == "UNAUTHORIZED"
    assert "用户名或密码错误" in data["message"]


@pytest.mark.asyncio
async def test_login_with_empty_username(test_db):
    """测试用户名为空"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "",
                "password": "ValidPass123"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_login_with_empty_password(test_db):
    """测试密码为空"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "some_user",
                "password": ""
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


# ========== 必填字段验证 ==========

@pytest.mark.asyncio
async def test_login_missing_username(test_db):
    """测试缺少用户名"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/login",
            json={
                # "username": 缺失
                "password": "ValidPass123"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_login_missing_password(test_db):
    """测试缺少密码"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "some_user"
                # "password": 缺失
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_login_with_empty_body(test_db):
    """测试空请求体"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/login",
            json={}
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


# ========== 账户状态验证 ==========

@pytest.mark.asyncio
async def test_login_with_deactivated_account(test_db):
    """测试已注销账户无法登录"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 注册账户
        register_response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "deactivated_user",
                "password": "ValidPass123",
                "name": "即将注销的公司",
                "phone": "13900139003",
                "email": "deactivated@example.com"
            }
        )
        assert register_response.status_code == 201

        # 登录获取Token
        login_response = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "deactivated_user",
                "password": "ValidPass123"
            }
        )
        token = login_response.json()["data"]["access_token"]

        # 注销账户（需要认证）
        await client.delete(
            "/v1/operators/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        # 尝试用已注销账户登录
        response = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "deactivated_user",
                "password": "ValidPass123"
            }
        )

    assert response.status_code == 403
    data = response.json()
    assert "error_code" in data
    assert data["error_code"] == "ACCOUNT_DEACTIVATED"
    assert "已注销" in data["message"]


# ========== 安全测试 ==========

@pytest.mark.asyncio
async def test_login_case_sensitive_username(test_db):
    """测试用户名区分大小写"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 注册小写用户名
        await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "testuser",
                "password": "ValidPass123",
                "name": "测试公司",
                "phone": "13900139004",
                "email": "casetest@example.com"
            }
        )

        # 使用大写用户名登录
        response = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "TESTUSER",  # 大写
                "password": "ValidPass123"
            }
        )

    # 应该返回401（用户名区分大小写）
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_sql_injection_attempt(test_db):
    """测试SQL注入防护"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "admin' OR '1'='1",
                "password": "anything"
            }
        )

    # 应该返回401而不是500
    assert response.status_code == 401
    data = response.json()
    assert data["error_code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_multiple_successful_logins_generate_different_tokens(test_db):
    """测试多次登录生成不同Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 注册
        await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "multi_login_user",
                "password": "ValidPass123",
                "name": "多次登录测试",
                "phone": "13900139005",
                "email": "multilogin@example.com"
            }
        )

        # 第一次登录
        response1 = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "multi_login_user",
                "password": "ValidPass123"
            }
        )

        # 第二次登录
        response2 = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "multi_login_user",
                "password": "ValidPass123"
            }
        )

    assert response1.status_code == 200
    assert response2.status_code == 200

    token1 = response1.json()["data"]["access_token"]
    token2 = response2.json()["data"]["access_token"]

    # 两次登录应该生成不同的Token（包含不同的时间戳）
    assert token1 != token2


# ========== 响应格式验证 ==========

@pytest.mark.asyncio
async def test_login_response_contains_all_required_fields(test_db):
    """测试登录响应包含所有必需字段"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 注册
        await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "complete_fields_user",
                "password": "ValidPass123",
                "name": "完整字段测试",
                "phone": "13900139006",
                "email": "complete@example.com"
            }
        )

        # 登录
        response = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "complete_fields_user",
                "password": "ValidPass123"
            }
        )

    assert response.status_code == 200
    data = response.json()

    # 验证所有必需字段存在
    required_fields = ["success", "data"]
    for field in required_fields:
        assert field in data, f"缺少必需字段: {field}"

    token_data = data["data"]
    required_token_fields = ["access_token", "token_type", "expires_in", "operator"]
    for field in required_token_fields:
        assert field in token_data, f"缺少必需Token字段: {field}"

    operator = token_data["operator"]
    required_operator_fields = ["operator_id", "username", "name", "category"]
    for field in required_operator_fields:
        assert field in operator, f"缺少必需运营商字段: {field}"


@pytest.mark.asyncio
async def test_login_operator_category_is_valid_enum(test_db):
    """测试登录返回的客户分类是有效枚举值"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 注册
        await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "enum_test_user",
                "password": "ValidPass123",
                "name": "枚举测试",
                "phone": "13900139007",
                "email": "enum@example.com"
            }
        )

        # 登录
        response = await client.post(
            "/v1/auth/operators/login",
            json={
                "username": "enum_test_user",
                "password": "ValidPass123"
            }
        )

    assert response.status_code == 200
    category = response.json()["data"]["operator"]["category"]

    # 验证category是有效枚举值
    valid_categories = ["trial", "normal", "vip"]
    assert category in valid_categories, f"无效的客户分类: {category}"
