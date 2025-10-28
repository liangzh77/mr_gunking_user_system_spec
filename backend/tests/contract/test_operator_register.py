"""
契约测试：运营商注册接口 (T050)

测试目标：
- 验证 POST /v1/auth/operators/register 接口契约
- 确保请求/响应格式符合 auth.yaml 定义
- 覆盖成功场景、参数验证、重复注册等边界情况

契约要求：
- 请求字段：username, password, name, phone, email（全部必填）
- username格式：3-20字符，仅包含字母数字下划线
- password格式：8-32字符，需包含大小写字母和数字
- phone格式：11位中国手机号
- email格式：标准邮箱格式
- 响应201：返回operator_id, username, api_key(64位), category, balance, created_at
- 响应400：用户名已存在、密码强度不足等参数错误
"""
import pytest
from httpx import AsyncClient

from src.main import app


# ========== 成功场景 ==========

@pytest.mark.asyncio
async def test_register_operator_success(test_db):
    """测试成功注册运营商账户"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "operator_beijing_01",
                "password": "StrongPass123",
                "name": "北京星空娱乐有限公司",
                "phone": "13800138000",
                "email": "operator@example.com"
            }
        )

    assert response.status_code == 201
    data = response.json()

    # 验证响应结构
    assert "success" in data
    assert data["success"] is True
    assert "message" in data
    assert "注册成功" in data["message"]
    assert "data" in data

    # 验证返回数据字段
    result = data["data"]
    assert "operator_id" in result
    assert "username" in result
    assert result["username"] == "operator_beijing_01"
    assert "api_key" in result
    assert len(result["api_key"]) == 64  # API Key必须是64位
    assert "category" in result
    assert result["category"] == "trial"  # 新注册默认试用客户
    assert "balance" in result
    assert result["balance"] == "0.00"  # 初始余额为0
    assert "created_at" in result
    # 验证ISO 8601时间格式
    import datetime
    datetime.datetime.fromisoformat(result["created_at"].replace("Z", "+00:00"))


@pytest.mark.asyncio
async def test_register_with_minimal_valid_username(test_db):
    """测试最小长度用户名（3字符）"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "abc",  # 最小3字符
                "password": "ValidPass123",
                "name": "测试公司",
                "phone": "13900139000",
                "email": "test@example.com"
            }
        )

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["username"] == "abc"


@pytest.mark.asyncio
async def test_register_with_maximal_valid_username(test_db):
    """测试最大长度用户名（20字符）"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "a" * 20,  # 最大20字符
                "password": "ValidPass123",
                "name": "测试公司",
                "phone": "13900139001",
                "email": "test2@example.com"
            }
        )

    assert response.status_code == 201
    data = response.json()
    assert len(data["data"]["username"]) == 20


# ========== 参数验证 - 用户名 ==========

@pytest.mark.asyncio
async def test_register_with_too_short_username(test_db):
    """测试用户名过短（<3字符）"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "ab",  # 少于3字符
                "password": "ValidPass123",
                "name": "测试公司",
                "phone": "13900139002",
                "email": "test3@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert "error_code" in data
    assert data["error_code"] == "INVALID_PARAMS"
    assert "用户名" in data["message"] or "username" in data["message"].lower()


@pytest.mark.asyncio
async def test_register_with_too_long_username(test_db):
    """测试用户名过长（>20字符）"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "a" * 21,  # 超过20字符
                "password": "ValidPass123",
                "name": "测试公司",
                "phone": "13900139003",
                "email": "test4@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_register_with_invalid_username_characters(test_db):
    """测试用户名包含非法字符（仅允许字母数字下划线）"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "user-name-123",  # 包含连字符（非法）
                "password": "ValidPass123",
                "name": "测试公司",
                "phone": "13900139004",
                "email": "test5@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_register_with_duplicate_username(test_db):
    """测试用户名重复（已存在）"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 第一次注册
        await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "duplicate_user",
                "password": "ValidPass123",
                "name": "测试公司1",
                "phone": "13900139005",
                "email": "unique1@example.com"
            }
        )

        # 第二次使用相同用户名注册
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "duplicate_user",  # 重复用户名
                "password": "ValidPass456",
                "name": "测试公司2",
                "phone": "13900139006",
                "email": "unique2@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "USERNAME_EXISTS"
    assert "用户名" in data["message"]
    assert "已被注册" in data["message"] or "已存在" in data["message"]


# ========== 参数验证 - 密码 ==========

@pytest.mark.asyncio
async def test_register_with_weak_password_no_uppercase(test_db):
    """测试密码强度不足：缺少大写字母"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "test_weak_pass1",
                "password": "weakpass123",  # 无大写字母
                "name": "测试公司",
                "phone": "13900139007",
                "email": "test6@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"
    assert "密码" in data["message"]


@pytest.mark.asyncio
async def test_register_with_weak_password_no_lowercase(test_db):
    """测试密码强度不足：缺少小写字母"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "test_weak_pass2",
                "password": "WEAKPASS123",  # 无小写字母
                "name": "测试公司",
                "phone": "13900139008",
                "email": "test7@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"
    assert "密码" in data["message"]


@pytest.mark.asyncio
async def test_register_with_weak_password_no_digit(test_db):
    """测试密码强度不足：缺少数字"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "test_weak_pass3",
                "password": "WeakPassword",  # 无数字
                "name": "测试公司",
                "phone": "13900139009",
                "email": "test8@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"
    assert "密码" in data["message"]


@pytest.mark.asyncio
async def test_register_with_too_short_password(test_db):
    """测试密码过短（<8字符）"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "test_short_pass",
                "password": "Pass1",  # 少于8字符
                "name": "测试公司",
                "phone": "13900139010",
                "email": "test9@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_register_with_too_long_password(test_db):
    """测试密码过长（>32字符）"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "test_long_pass",
                "password": "A" + "a" * 30 + "1",  # 超过32字符
                "name": "测试公司",
                "phone": "13900139011",
                "email": "test10@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


# ========== 参数验证 - 手机号 ==========

@pytest.mark.asyncio
async def test_register_with_invalid_phone_format(test_db):
    """测试手机号格式错误"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "test_invalid_phone",
                "password": "ValidPass123",
                "name": "测试公司",
                "phone": "12345678901",  # 非中国手机号格式（1开头但第二位不合法）
                "email": "test11@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"
    assert "手机" in data["message"] or "phone" in data["message"].lower()


@pytest.mark.asyncio
async def test_register_with_too_short_phone(test_db):
    """测试手机号长度不足"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "test_short_phone",
                "password": "ValidPass123",
                "name": "测试公司",
                "phone": "138001380",  # 少于11位
                "email": "test12@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


# ========== 参数验证 - 邮箱 ==========

@pytest.mark.asyncio
async def test_register_with_invalid_email_format(test_db):
    """测试邮箱格式错误"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "test_invalid_email",
                "password": "ValidPass123",
                "name": "测试公司",
                "phone": "13900139012",
                "email": "invalid-email-format"  # 缺少@和域名
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"
    assert "邮箱" in data["message"] or "email" in data["message"].lower()


# ========== 参数验证 - 必填字段 ==========

@pytest.mark.asyncio
async def test_register_missing_username(test_db):
    """测试缺少用户名"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                # "username": 缺失
                "password": "ValidPass123",
                "name": "测试公司",
                "phone": "13900139013",
                "email": "test13@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_register_missing_password(test_db):
    """测试缺少密码"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "test_missing_pass",
                # "password": 缺失
                "name": "测试公司",
                "phone": "13900139014",
                "email": "test14@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_register_missing_name(test_db):
    """测试缺少姓名/公司名"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "test_missing_name",
                "password": "ValidPass123",
                # "name": 缺失
                "phone": "13900139015",
                "email": "test15@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_register_missing_phone(test_db):
    """测试缺少手机号"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "test_missing_phone",
                "password": "ValidPass123",
                "name": "测试公司",
                # "phone": 缺失
                "email": "test16@example.com"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_register_missing_email(test_db):
    """测试缺少邮箱"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "test_missing_email",
                "password": "ValidPass123",
                "name": "测试公司",
                "phone": "13900139016",
                # "email": 缺失
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


# ========== 边界条件 ==========

@pytest.mark.asyncio
async def test_register_with_empty_body(test_db):
    """测试空请求体"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={}
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_register_with_null_values(test_db):
    """测试字段值为null"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": None,
                "password": None,
                "name": None,
                "phone": None,
                "email": None
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


# ========== API Key唯一性验证 ==========

@pytest.mark.asyncio
async def test_generated_api_keys_are_unique(test_db):
    """测试多次注册生成的API Key唯一"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 注册第一个运营商
        response1 = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "operator_unique_1",
                "password": "ValidPass123",
                "name": "公司1",
                "phone": "13900139017",
                "email": "unique1@test.com"
            }
        )

        # 注册第二个运营商
        response2 = await client.post(
            "/v1/auth/operators/register",
            json={
                "username": "operator_unique_2",
                "password": "ValidPass456",
                "name": "公司2",
                "phone": "13900139018",
                "email": "unique2@test.com"
            }
        )

    assert response1.status_code == 201
    assert response2.status_code == 201

    api_key1 = response1.json()["data"]["api_key"]
    api_key2 = response2.json()["data"]["api_key"]

    # 验证API Key不相同
    assert api_key1 != api_key2
    # 验证都是64位
    assert len(api_key1) == 64
    assert len(api_key2) == 64
