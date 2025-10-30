"""
契约测试: 管理员查看运营商API Key (T-NEW)

测试目标:
- 验证管理员查看运营商API Key的API端点契约
- 确保请求/响应格式符合contract定义
- 覆盖成功获取、运营商不存在、权限控制等场景

契约要求:
- GET /v1/admins/operators/{operator_id}/api-key: 查看运营商API Key
- 需要管理员认证和operator:view权限
- 返回运营商的API Key信息
"""
import pytest
import secrets
import string
from httpx import AsyncClient
from uuid import uuid4

from src.main import app
from src.models.admin import AdminAccount
from src.models.operator import OperatorAccount
from src.core.utils.password import hash_password


def generate_api_key() -> str:
    """Generate a secure random API key."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(64))


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
async def create_test_operator(test_db):
    """创建测试运营商"""
    api_key = generate_api_key()
    operator = OperatorAccount(
        id=uuid4(),
        username="test_operator",
        password_hash=hash_password("Operator@123"),
        full_name="测试运营商",
        email="operator@test.com",
        phone="13900139000",
        api_key=api_key,
        api_key_hash=hash_password(api_key),
        customer_tier="standard",
        is_active=True
    )
    test_db.add(operator)
    await test_db.commit()
    await test_db.refresh(operator)
    return operator


@pytest.fixture
async def superadmin_token(create_superadmin):
    """获取superadmin的JWT Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/admins/auth/login",
            json={
                "username": "superadmin",
                "password": "Admin@123"
            }
        )
        return response.json()["access_token"]


# ========== GET /v1/admins/operators/{operator_id}/api-key 测试 ==========

@pytest.mark.asyncio
async def test_get_operator_api_key_success(test_db, create_test_operator, superadmin_token):
    """测试成功获取运营商API Key"""
    operator = create_test_operator

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/v1/admins/operators/{operator.id}/api-key",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert "operator_id" in data
    assert "username" in data
    assert "api_key" in data
    assert "created_at" in data

    # 验证返回的数据
    assert data["operator_id"] == str(operator.id)
    assert data["username"] == operator.username
    assert data["api_key"] == operator.api_key
    assert len(data["api_key"]) == 64  # API Key长度应为64位

    # 验证敏感信息不会返回
    assert "password_hash" not in data
    assert "api_key_hash" not in data
    assert "balance" not in data


@pytest.mark.asyncio
async def test_get_operator_api_key_not_found(test_db, superadmin_token):
    """测试获取不存在的运营商API Key"""
    non_existent_id = uuid4()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/v1/admins/operators/{non_existent_id}/api-key",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_operator_api_key_invalid_uuid(test_db, superadmin_token):
    """测试无效的运营商ID格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/admins/operators/invalid-uuid/api-key",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_operator_api_key_without_auth(test_db, create_test_operator):
    """测试未提供管理员Token"""
    operator = create_test_operator

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/v1/admins/operators/{operator.id}/api-key"
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_operator_api_key_invalid_token(test_db, create_test_operator):
    """测试无效管理员Token"""
    operator = create_test_operator

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/v1/admins/operators/{operator.id}/api-key",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_operator_api_key_for_deleted_operator(test_db, superadmin_token):
    """测试获取已删除运营商的API Key"""
    from datetime import datetime

    # 创建已删除的运营商
    api_key = generate_api_key()
    deleted_operator = OperatorAccount(
        id=uuid4(),
        username="deleted_operator",
        password_hash=hash_password("Operator@123"),
        full_name="已删除运营商",
        email="deleted@test.com",
        phone="13900139001",
        api_key=api_key,
        api_key_hash=hash_password(api_key),
        customer_tier="standard",
        is_active=True,
        deleted_at=datetime.utcnow()  # 标记为已删除
    )
    test_db.add(deleted_operator)
    await test_db.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/v1/admins/operators/{deleted_operator.id}/api-key",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )

    # 已删除的运营商应该返回404
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_operator_api_key_for_locked_operator(
    test_db,
    create_test_operator,
    superadmin_token
):
    """测试获取已锁定运营商的API Key（应该成功）"""
    from datetime import datetime

    operator = create_test_operator

    # 锁定运营商
    operator.is_locked = True
    operator.locked_reason = "异常IP检测锁定"
    operator.locked_at = datetime.utcnow()
    await test_db.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/v1/admins/operators/{operator.id}/api-key",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )

    # 即使运营商被锁定，管理员也应该能查看API Key
    assert response.status_code == 200
    data = response.json()
    assert data["api_key"] == operator.api_key


@pytest.mark.asyncio
async def test_get_operator_api_key_multiple_operators(test_db, superadmin_token):
    """测试查看多个不同运营商的API Key"""
    # 创建多个运营商
    operators = []
    for i in range(3):
        api_key = generate_api_key()
        operator = OperatorAccount(
            id=uuid4(),
            username=f"operator_{i}",
            password_hash=hash_password("Operator@123"),
            full_name=f"运营商{i}",
            email=f"operator{i}@test.com",
            phone=f"1390013900{i}",
            api_key=api_key,
            api_key_hash=hash_password(api_key),
            customer_tier="standard",
            is_active=True
        )
        test_db.add(operator)
        operators.append(operator)

    await test_db.commit()

    # 验证每个运营商的API Key都是唯一的
    api_keys = set()

    async with AsyncClient(app=app, base_url="http://test") as client:
        for operator in operators:
            response = await client.get(
                f"/v1/admins/operators/{operator.id}/api-key",
                headers={"Authorization": f"Bearer {superadmin_token}"}
            )

            assert response.status_code == 200
            data = response.json()
            api_keys.add(data["api_key"])

    # 确保所有API Key都是唯一的
    assert len(api_keys) == 3
