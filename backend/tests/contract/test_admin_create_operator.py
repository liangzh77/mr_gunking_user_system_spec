"""
契约测试: 管理员创建运营商API (T121)

测试目标:
- 验证管理员创建运营商账户的API端点契约
- 确保请求/响应格式符合contract定义
- 覆盖创建成功、验证失败、权限控制等场景

契约要求:
- POST /v1/admin/operators: 创建新运营商账户
- 需要管理员认证
- 返回创建的运营商信息(不包含密码)
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
        permissions=[]
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


@pytest.fixture
async def superadmin_token(create_superadmin):
    """获取superadmin的JWT Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/login",
            json={
                "username": "superadmin",
                "password": "Admin@123"
            }
        )
        return response.json()["access_token"]


# ========== 辅助函数 ==========

async def create_operator_payload(**overrides):
    """生成创建运营商的请求payload"""
    default_payload = {
        "username": "test_operator",
        "password": "Operator@123",
        "full_name": "测试运营商",
        "email": "operator@test.com",
        "phone": "13900139000",
        "customer_tier": "standard"
    }
    default_payload.update(overrides)
    return default_payload


# ========== POST /v1/admin/operators 测试 ==========

@pytest.mark.asyncio
async def test_create_operator_success(test_db, superadmin_token):
    """测试成功创建运营商"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = await create_operator_payload()

        response = await client.post(
            "/v1/admins/operators",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json=payload
        )

    assert response.status_code == 201
    data = response.json()

    # 验证响应结构
    assert "id" in data
    assert "username" in data
    assert "full_name" in data
    assert "email" in data
    assert "phone" in data
    assert "customer_tier" in data
    assert "balance" in data
    assert "api_key" in data
    assert "is_active" in data
    assert "created_at" in data

    # 验证返回的数据
    assert data["username"] == payload["username"]
    assert data["full_name"] == payload["full_name"]
    assert data["email"] == payload["email"]
    assert data["phone"] == payload["phone"]
    assert data["customer_tier"] == payload["customer_tier"]
    assert data["balance"] == 0.00
    assert data["is_active"] is True
    assert data["api_key"] is not None
    assert len(data["api_key"]) == 64  # API Key长度应为64位

    # 验证密码不会返回
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_create_operator_with_different_tiers(test_db, superadmin_token):
    """测试创建不同等级的运营商"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 测试创建VIP运营商
        vip_payload = await create_operator_payload(
            username="vip_operator",
            customer_tier="vip"
        )

        response = await client.post(
            "/v1/admins/operators",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json=vip_payload
        )

        assert response.status_code == 201
        data = response.json()
        assert data["customer_tier"] == "vip"

        # 测试创建试用运营商
        trial_payload = await create_operator_payload(
            username="trial_operator",
            customer_tier="trial"
        )

        response = await client.post(
            "/v1/admins/operators",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json=trial_payload
        )

        assert response.status_code == 201
        data = response.json()
        assert data["customer_tier"] == "trial"


@pytest.mark.asyncio
async def test_create_operator_invalid_tier(test_db, superadmin_token):
    """测试无效的客户等级"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = await create_operator_payload(customer_tier="invalid_tier")

        response = await client.post(
            "/v1/admins/operators",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json=payload
        )

    assert response.status_code in [400, 422]  # Validation error


@pytest.mark.asyncio
async def test_create_operator_duplicate_username(test_db, superadmin_token):
    """测试重复用户名"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = await create_operator_payload()

        # 第一次创建
        response1 = await client.post(
            "/v1/admins/operators",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json=payload
        )
        assert response1.status_code == 201

        # 第二次创建相同用户名
        response2 = await client.post(
            "/v1/admins/operators",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json=payload
        )

    assert response2.status_code in [400, 409]  # Conflict/Bad Request


@pytest.mark.asyncio
async def test_create_operator_duplicate_email(test_db, superadmin_token):
    """测试重复邮箱"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 第一次创建
        payload1 = await create_operator_payload(username="operator1")
        response1 = await client.post(
            "/v1/admins/operators",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json=payload1
        )
        assert response1.status_code == 201

        # 第二次创建相同邮箱
        payload2 = await create_operator_payload(
            username="operator2",
            email=payload1["email"]  # 使用相同邮箱
        )
        response2 = await client.post(
            "/v1/admins/operators",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json=payload2
        )

    assert response2.status_code in [400, 409]  # Conflict/Bad Request


@pytest.mark.asyncio
async def test_create_operator_missing_required_fields(test_db, superadmin_token):
    """测试缺少必填字段"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 缺少用户名
        response1 = await client.post(
            "/v1/admins/operators",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={
                "password": "Operator@123",
                "full_name": "测试运营商",
                "email": "operator@test.com",
                "phone": "13900139000"
            }
        )
        assert response1.status_code in [400, 422]

        # 缺少密码
        response2 = await client.post(
            "/v1/admins/operators",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={
                "username": "test_operator",
                "full_name": "测试运营商",
                "email": "operator@test.com",
                "phone": "13900139000"
            }
        )
        assert response2.status_code in [400, 422]

        # 缺少邮箱
        response3 = await client.post(
            "/v1/admins/operators",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={
                "username": "test_operator",
                "password": "Operator@123",
                "full_name": "测试运营商",
                "phone": "13900139000"
            }
        )
        assert response3.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_operator_weak_password(test_db, superadmin_token):
    """测试弱密码"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        weak_passwords = [
            "123",           # 太短
            "password",      # 太简单
            "12345678",      # 纯数字
            "abcdefgh",      # 纯字母
            "12345678a",     # 数字+字母但无大写字母和特殊字符
        ]

        for weak_password in weak_passwords:
            payload = await create_operator_payload(
                username=f"operator_{weak_passwords.index(weak_password)}",
                password=weak_password
            )

            response = await client.post(
                "/v1/admins/operators",
                headers={"Authorization": f"Bearer {superadmin_token}"},
                json=payload
            )

            assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_operator_invalid_email(test_db, superadmin_token):
    """测试无效邮箱格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        invalid_emails = [
            "invalid_email",           # 无@符号
            "@domain.com",            # 无用户名
            "user@",                  # 无域名
            "user..name@domain.com",  # 连续点号
            "user@domain",            # 无顶级域名
        ]

        for invalid_email in invalid_emails:
            payload = await create_operator_payload(
                username=f"operator_{invalid_emails.index(invalid_email)}",
                email=invalid_email
            )

            response = await client.post(
                "/v1/admins/operators",
                headers={"Authorization": f"Bearer {superadmin_token}"},
                json=payload
            )

            assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_operator_invalid_phone(test_db, superadmin_token):
    """测试无效手机号"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        invalid_phones = [
            "123",              # 太短
            "abcdefghijk",      # 非数字
            "1234567890123456", # 太长
        ]

        for invalid_phone in invalid_phones:
            payload = await create_operator_payload(
                username=f"operator_{invalid_phones.index(invalid_phone)}",
                phone=invalid_phone
            )

            response = await client.post(
                "/v1/admins/operators",
                headers={"Authorization": f"Bearer {superadmin_token}"},
                json=payload
            )

            assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_operator_without_auth(test_db):
    """测试未提供管理员Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = await create_operator_payload()

        response = await client.post(
            "/v1/admins/operators",
            json=payload
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_operator_invalid_token(test_db):
    """测试无效管理员Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = await create_operator_payload()

        response = await client.post(
            "/v1/admins/operators",
            headers={"Authorization": "Bearer invalid_token_12345"},
            json=payload
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_operator_with_insufficient_permissions(test_db):
    """测试权限不足的管理员创建运营商"""
    # 创建普通管理员账户
    admin = AdminAccount(
        id=uuid4(),
        username="regular_admin",
        password_hash=hash_password("Admin@123"),
        full_name="Regular Administrator",
        email="admin@test.com",
        phone="13800138001",
        role="admin",
        permissions=[]  # 无管理运营商权限
    )
    test_db.add(admin)
    await test_db.commit()

    # 登录获取token
    async with AsyncClient(app=app, base_url="http://test") as client:
        login_response = await client.post(
            "/v1/admin/login",
            json={
                "username": "regular_admin",
                "password": "Admin@123"
            }
        )
        token = login_response.json()["access_token"]

        # 尝试创建运营商
        payload = await create_operator_payload()
        response = await client.post(
            "/v1/admins/operators",
            headers={"Authorization": f"Bearer {token}"},
            json=payload
        )

    # 根据实现可能返回403(Forbidden)或401(Unauthorized)
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_create_operator_long_username(test_db, superadmin_token):
    """测试过长的用户名"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        long_username = "a" * 65  # 超过64字符限制

        payload = await create_operator_payload(username=long_username)

        response = await client.post(
            "/v1/admins/operators",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json=payload
        )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_operator_special_chars_in_username(test_db, superadmin_token):
    """测试用户名包含特殊字符"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        invalid_usernames = [
            "operator with spaces",
            "operator@domain.com",
            "operator#123",
            "operator/slash",
        ]

        for invalid_username in invalid_usernames:
            payload = await create_operator_payload(username=invalid_username)

            response = await client.post(
                "/v1/admins/operators",
                headers={"Authorization": f"Bearer {superadmin_token}"},
                json=payload
            )

            # 根据验证规则可能返回400或422
            assert response.status_code in [400, 422]