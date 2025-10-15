"""
契约测试: 申请应用授权接口 (T098)

测试目标:
- 验证 POST /v1/operators/me/applications/requests 接口契约
- 确保请求/响应格式符合contract定义
- 覆盖成功、重复申请、已授权、应用不存在等场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 请求体: {app_id: "app_xxx", reason: "申请理由"}
- 返回格式: {success: true, message: "...", data: {request_id: "..."}}
- 业务校验: 不能重复申请、不能申请已授权应用
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID

from src.main import app


# ========== 辅助函数 ==========

async def create_and_login_operator(client: AsyncClient, username: str) -> tuple[str, str]:
    """创建运营商并登录,返回(JWT Token, operator_id)"""
    # 注册
    response = await client.post(
        "/v1/auth/operators/register",
        json={
            "username": username,
            "password": "TestPass123",
            "name": "测试公司",
            "phone": "13800138000",
            "email": f"{username}@example.com"
        }
    )
    operator_id = response.json()["data"]["operator_id"]

    # 登录
    response = await client.post(
        "/v1/auth/operators/login",
        json={
            "username": username,
            "password": "TestPass123"
        }
    )

    return response.json()["data"]["access_token"], operator_id


async def create_application(db, app_code: str, app_name: str, is_active: bool = True) -> str:
    """创建应用,返回application_id"""
    from src.models.application import Application
    from decimal import Decimal

    app = Application(
        app_code=app_code,
        app_name=app_name,
        description=f"{app_name}的描述",
        price_per_player=Decimal("10.00"),
        min_players=2,
        max_players=8,
        is_active=is_active
    )

    db.add(app)
    await db.commit()
    await db.refresh(app)

    return str(app.id)


async def create_authorization(db, operator_id: str, application_id: str, expires_at=None):
    """创建授权关系"""
    from src.models.authorization import OperatorAppAuthorization
    from uuid import UUID

    # 解析operator_id
    if operator_id.startswith("op_"):
        op_uuid = UUID(operator_id[3:])
    else:
        op_uuid = UUID(operator_id)

    auth = OperatorAppAuthorization(
        operator_id=op_uuid,
        application_id=UUID(application_id),
        is_active=True,
        expires_at=expires_at
    )

    db.add(auth)
    await db.commit()


async def create_pending_request(db, operator_id: str, application_id: str, reason: str = "测试申请"):
    """创建待审核的申请"""
    from src.models.app_request import ApplicationRequest
    from uuid import UUID

    # 解析operator_id
    if operator_id.startswith("op_"):
        op_uuid = UUID(operator_id[3:])
    else:
        op_uuid = UUID(operator_id)

    request = ApplicationRequest(
        operator_id=op_uuid,
        application_id=UUID(application_id),
        reason=reason,
        status="pending"
    )

    db.add(request)
    await db.commit()
    await db.refresh(request)

    return str(request.id)


# ========== POST /v1/operators/me/applications/requests 测试 ==========

@pytest.mark.asyncio
async def test_create_application_request_success(test_db):
    """测试成功申请应用授权"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "req_user_1")

        # 创建应用
        app_id = await create_application(test_db, "new_game", "新游戏")

        # 申请授权
        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": f"app_{app_id}",
                "reason": "我们门店有很多VR设备,希望引入这款游戏"
            }
        )

    assert response.status_code == 201
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "message" in data
    assert len(data["message"]) > 0  # message不为空即可,不检查具体内容
    assert "data" in data
    assert "request_id" in data["data"]
    assert data["data"]["request_id"].startswith("req_")


@pytest.mark.asyncio
async def test_create_application_request_with_raw_uuid(test_db):
    """测试使用原始UUID申请(不带app_前缀)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "req_user_2")

        # 创建应用
        app_id = await create_application(test_db, "uuid_game", "UUID游戏")

        # 使用原始UUID申请
        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": app_id,  # 不带前缀
                "reason": "测试原始UUID格式"
            }
        )

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_create_application_request_duplicate(test_db):
    """测试重复申请(同一运营商对同一应用有pending申请)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "req_user_3")

        # 创建应用
        app_id = await create_application(test_db, "dup_game", "重复游戏")

        # 创建pending申请
        await create_pending_request(test_db, operator_id, app_id)

        # 再次申请
        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": f"app_{app_id}",
                "reason": "第二次申请"
            }
        )

    assert response.status_code == 400
    data = response.json()
    # HTTPException with dict detail直接返回dict(没有success字段)
    assert "message" in data
    assert len(data["message"]) > 0


@pytest.mark.asyncio
async def test_create_application_request_already_authorized(test_db):
    """测试申请已授权的应用"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "req_user_4")

        # 创建应用
        app_id = await create_application(test_db, "auth_game", "已授权游戏")

        # 创建授权关系
        await create_authorization(test_db, operator_id, app_id)

        # 申请授权
        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": f"app_{app_id}",
                "reason": "申请已授权的应用"
            }
        )

    assert response.status_code == 400
    data = response.json()
    # HTTPException with dict detail直接返回dict(没有success字段)
    assert "message" in data
    assert len(data["message"]) > 0


@pytest.mark.asyncio
async def test_create_application_request_application_not_found(test_db):
    """测试申请不存在的应用"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "req_user_5")

        # 使用不存在的app_id
        fake_uuid = str(uuid4())

        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": f"app_{fake_uuid}",
                "reason": "测试申请一个不存在的应用,理由需要至少10个字符"
            }
        )

    assert response.status_code == 404
    data = response.json()
    # HTTPException with dict detail直接返回dict(没有success字段)
    assert "message" in data
    assert len(data["message"]) > 0


@pytest.mark.asyncio
async def test_create_application_request_application_inactive(test_db):
    """测试申请已下架的应用"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "req_user_6")

        # 创建已下架的应用
        app_id = await create_application(test_db, "inactive_game", "下架游戏", is_active=False)

        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": f"app_{app_id}",
                "reason": "申请已下架的应用"
            }
        )

    assert response.status_code == 400
    data = response.json()
    # HTTPException with dict detail直接返回dict(没有success字段)
    assert "message" in data
    assert len(data["message"]) > 0


@pytest.mark.asyncio
async def test_create_application_request_invalid_app_id_format(test_db):
    """测试无效的app_id格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "req_user_7")

        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": "invalid_uuid_format",
                "reason": "测试无效UUID"
            }
        )

    # Pydantic validation错误返回400 (经过异常处理中间件)
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"
    assert "message" in data


@pytest.mark.asyncio
async def test_create_application_request_reason_too_short(test_db):
    """测试申请理由过短"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "req_user_8")

        # 创建应用
        app_id = await create_application(test_db, "short_reason_game", "短理由游戏")

        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": f"app_{app_id}",
                "reason": "短"  # 少于10字符
            }
        )

    # Pydantic validation错误返回400 (经过异常处理中间件)
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"
    assert "message" in data


@pytest.mark.asyncio
async def test_create_application_request_reason_too_long(test_db):
    """测试申请理由过长"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "req_user_9")

        # 创建应用
        app_id = await create_application(test_db, "long_reason_game", "长理由游戏")

        long_reason = "申" * 501  # 超过500字符

        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": f"app_{app_id}",
                "reason": long_reason
            }
        )

    # Pydantic validation错误返回400 (经过异常处理中间件)
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"
    assert "message" in data


@pytest.mark.asyncio
async def test_create_application_request_missing_fields(test_db):
    """测试缺少必填字段"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "req_user_10")

        # 缺少app_id
        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "测试缺少app_id"
            }
        )

    # Pydantic validation错误返回400 (经过异常处理中间件)
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"
    assert "message" in data


@pytest.mark.asyncio
async def test_create_application_request_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/operators/me/applications/requests",
            json={
                "app_id": "app_12345678-1234-1234-1234-123456789012",
                "reason": "测试未登录"
            }
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_application_request_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": "Bearer invalid_token_12345"},
            json={
                "app_id": "app_12345678-1234-1234-1234-123456789012",
                "reason": "测试无效token"
            }
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_application_request_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "req_user_11")

        # 创建应用
        app_id = await create_application(test_db, "format_test", "格式测试游戏")

        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": f"app_{app_id}",
                "reason": "测试响应格式的完整性和数据类型"
            }
        )

    assert response.status_code == 201
    data = response.json()

    # 验证顶层格式
    assert isinstance(data["success"], bool)
    assert data["success"] is True
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0
    assert isinstance(data["data"], dict)

    # 验证data内容
    assert "request_id" in data["data"]
    assert isinstance(data["data"]["request_id"], str)
    assert data["data"]["request_id"].startswith("req_")

    # 验证request_id是有效的UUID格式
    request_uuid = data["data"]["request_id"][4:]  # 去掉req_前缀
    try:
        UUID(request_uuid)
    except ValueError:
        pytest.fail("request_id格式无效,不是有效的UUID")


@pytest.mark.asyncio
async def test_create_application_request_database_consistency(test_db):
    """测试数据库一致性(申请后能查询到)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "req_user_12")

        # 创建应用
        app_id = await create_application(test_db, "consistency_game", "一致性游戏")

        # 申请授权
        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": f"app_{app_id}",
                "reason": "测试数据库一致性,验证申请后能立即查询到"
            }
        )

        assert response.status_code == 201
        request_id = response.json()["data"]["request_id"]

        # 查询申请列表,验证刚才的申请在列表中
        response = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    requests = data["data"]["items"]

    # 验证申请在列表中
    found = False
    for req in requests:
        if req["request_id"] == request_id:
            found = True
            assert req["status"] == "pending"
            assert req["reason"] == "测试数据库一致性,验证申请后能立即查询到"
            assert req["app_code"] == "consistency_game"
            break

    assert found, f"创建的申请{request_id}未在列表中找到"
