"""
契约测试: 查询授权申请列表接口 (T099)

测试目标:
- 验证 GET /v1/operators/me/applications/requests 接口契约
- 确保请求/响应格式符合contract定义
- 覆盖分页、空列表、多状态、排序等场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 查询参数: page(默认1), page_size(默认20, 最大100)
- 返回格式: {success: true, data: {page, page_size, total, items: [...]}}
- 按created_at降序返回(最新的在前)
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


async def create_application(db, app_code: str, app_name: str) -> str:
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
        is_active=True
    )

    db.add(app)
    await db.commit()
    await db.refresh(app)

    return str(app.id)


async def create_request(db, operator_id: str, application_id: str, reason: str, status: str = "pending") -> str:
    """创建申请记录,返回request_id"""
    from src.models.app_request import ApplicationRequest
    from uuid import UUID
    from datetime import datetime, timezone

    # 解析operator_id
    if operator_id.startswith("op_"):
        op_uuid = UUID(operator_id[3:])
    else:
        op_uuid = UUID(operator_id)

    # 如果是approved或rejected状态,需要提供reviewed_by和reviewed_at
    if status in ["approved", "rejected"]:
        fake_admin_uuid = UUID("12345678-1234-1234-1234-123456789012")
        reviewed_by = fake_admin_uuid
        reviewed_at = datetime.now(timezone.utc)
        reject_reason = "测试拒绝原因" if status == "rejected" else None
    else:
        reviewed_by = None
        reviewed_at = None
        reject_reason = None

    request = ApplicationRequest(
        operator_id=op_uuid,
        application_id=UUID(application_id),
        reason=reason,
        status=status,
        reviewed_by=reviewed_by,
        reviewed_at=reviewed_at,
        reject_reason=reject_reason
    )

    db.add(request)
    await db.commit()
    await db.refresh(request)

    return str(request.id)


# ========== GET /v1/operators/me/applications/requests 测试 ==========

@pytest.mark.asyncio
async def test_get_application_requests_success(test_db):
    """测试成功查询申请列表(有数据)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "list_user_1")

        # 创建3个应用
        app1_id = await create_application(test_db, "game1", "游戏1")
        app2_id = await create_application(test_db, "game2", "游戏2")
        app3_id = await create_application(test_db, "game3", "游戏3")

        # 创建3条申请记录(不同状态)
        await create_request(test_db, operator_id, app1_id, "申请游戏1", "pending")
        await create_request(test_db, operator_id, app2_id, "申请游戏2", "approved")
        await create_request(test_db, operator_id, app3_id, "申请游戏3", "rejected")

        # 查询申请列表
        response = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "data" in data
    assert "page" in data["data"]
    assert "page_size" in data["data"]
    assert "total" in data["data"]
    assert "items" in data["data"]

    # 验证返回了3条记录
    assert data["data"]["total"] == 3
    assert len(data["data"]["items"]) == 3

    # 验证item数据结构
    item = data["data"]["items"][0]
    assert "request_id" in item
    assert item["request_id"].startswith("req_")
    assert "app_id" in item
    assert item["app_id"].startswith("app_")
    assert "app_code" in item
    assert "app_name" in item
    assert "reason" in item
    assert "status" in item
    assert item["status"] in ["pending", "approved", "rejected"]
    assert "created_at" in item
    assert "reviewed_at" in item  # 可能为null
    assert "reject_reason" in item  # 可能为null


@pytest.mark.asyncio
async def test_get_application_requests_empty(test_db):
    """测试查询空列表(无申请记录)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "list_user_2")

        # 不创建任何申请
        response = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证返回空列表
    assert data["success"] is True
    assert data["data"]["total"] == 0
    assert data["data"]["items"] == []
    assert data["data"]["page"] == 1
    assert data["data"]["page_size"] == 20


@pytest.mark.asyncio
async def test_get_application_requests_pagination(test_db):
    """测试分页功能"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "list_user_3")

        # 创建5个应用和申请
        for i in range(5):
            app_id = await create_application(test_db, f"page_game_{i}", f"分页游戏{i}")
            await create_request(test_db, operator_id, app_id, f"申请{i}", "pending")

        # 第1页,每页2条
        response = await client.get(
            "/v1/operators/me/applications/requests?page=1&page_size=2",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证分页信息
    assert data["data"]["page"] == 1
    assert data["data"]["page_size"] == 2
    assert data["data"]["total"] == 5
    assert len(data["data"]["items"]) == 2


@pytest.mark.asyncio
async def test_get_application_requests_pagination_page2(test_db):
    """测试第2页数据"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "list_user_4")

        # 创建5个应用和申请
        for i in range(5):
            app_id = await create_application(test_db, f"page2_game_{i}", f"第二页游戏{i}")
            await create_request(test_db, operator_id, app_id, f"申请{i}", "pending")

        # 第2页,每页2条
        response = await client.get(
            "/v1/operators/me/applications/requests?page=2&page_size=2",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证分页信息
    assert data["data"]["page"] == 2
    assert data["data"]["page_size"] == 2
    assert data["data"]["total"] == 5
    assert len(data["data"]["items"]) == 2


@pytest.mark.asyncio
async def test_get_application_requests_pagination_last_page(test_db):
    """测试最后一页(不满一页)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "list_user_5")

        # 创建5个应用和申请
        for i in range(5):
            app_id = await create_application(test_db, f"last_game_{i}", f"最后一页游戏{i}")
            await create_request(test_db, operator_id, app_id, f"申请{i}", "pending")

        # 第3页,每页2条(只有1条数据)
        response = await client.get(
            "/v1/operators/me/applications/requests?page=3&page_size=2",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证最后一页
    assert data["data"]["page"] == 3
    assert data["data"]["page_size"] == 2
    assert data["data"]["total"] == 5
    assert len(data["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_get_application_requests_page_out_of_range(test_db):
    """测试页码超出范围"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "list_user_6")

        # 只创建1条申请
        app_id = await create_application(test_db, "single_game", "单个游戏")
        await create_request(test_db, operator_id, app_id, "申请", "pending")

        # 查询第10页(超出范围)
        response = await client.get(
            "/v1/operators/me/applications/requests?page=10&page_size=20",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证返回空列表,但total仍为1
    assert data["data"]["total"] == 1
    assert data["data"]["items"] == []


@pytest.mark.asyncio
async def test_get_application_requests_sorted_by_time(test_db):
    """测试按created_at降序返回(最新的在前)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "list_user_7")

        # 依次创建3个应用和申请
        app1_id = await create_application(test_db, "first_game", "第一个游戏")
        await create_request(test_db, operator_id, app1_id, "第一个申请", "pending")

        import asyncio
        await asyncio.sleep(0.1)

        app2_id = await create_application(test_db, "second_game", "第二个游戏")
        await create_request(test_db, operator_id, app2_id, "第二个申请", "pending")

        await asyncio.sleep(0.1)

        app3_id = await create_application(test_db, "third_game", "第三个游戏")
        await create_request(test_db, operator_id, app3_id, "第三个申请", "pending")

        # 查询列表
        response = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    items = response.json()["data"]["items"]

    # 验证按时间降序排列
    assert len(items) == 3
    assert items[0]["app_code"] == "third_game"  # 最新的在前
    assert items[1]["app_code"] == "second_game"
    assert items[2]["app_code"] == "first_game"  # 最早的在后


@pytest.mark.asyncio
async def test_get_application_requests_only_own_data(test_db):
    """测试只返回当前运营商的申请(数据隔离)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建2个运营商
        token1, op_id1 = await create_and_login_operator(client, "isolate_user_1")
        token2, op_id2 = await create_and_login_operator(client, "isolate_user_2")

        # 创建应用
        app1_id = await create_application(test_db, "isolate_game1", "隔离游戏1")
        app2_id = await create_application(test_db, "isolate_game2", "隔离游戏2")

        # 运营商1申请应用1
        await create_request(test_db, op_id1, app1_id, "运营商1的申请", "pending")

        # 运营商2申请应用2
        await create_request(test_db, op_id2, app2_id, "运营商2的申请", "pending")

        # 运营商1查询列表
        response = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token1}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证运营商1只能看到自己的申请
    assert data["data"]["total"] == 1
    items = data["data"]["items"]
    assert len(items) == 1
    assert items[0]["app_code"] == "isolate_game1"
    assert items[0]["reason"] == "运营商1的申请"


@pytest.mark.asyncio
async def test_get_application_requests_all_statuses(test_db):
    """测试返回所有状态的申请(pending/approved/rejected)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "list_user_9")

        # 创建3个应用和不同状态的申请
        app1_id = await create_application(test_db, "pending_app", "待审核应用")
        await create_request(test_db, operator_id, app1_id, "待审核", "pending")

        app2_id = await create_application(test_db, "approved_app", "已通过应用")
        await create_request(test_db, operator_id, app2_id, "已通过", "approved")

        app3_id = await create_application(test_db, "rejected_app", "已拒绝应用")
        await create_request(test_db, operator_id, app3_id, "已拒绝", "rejected")

        # 查询列表
        response = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证返回所有状态
    assert data["data"]["total"] == 3
    items = data["data"]["items"]

    statuses = [item["status"] for item in items]
    assert "pending" in statuses
    assert "approved" in statuses
    assert "rejected" in statuses


@pytest.mark.asyncio
async def test_get_application_requests_invalid_page(test_db):
    """测试无效的page参数(小于1)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "list_user_10")

        response = await client.get(
            "/v1/operators/me/applications/requests?page=0",
            headers={"Authorization": f"Bearer {token}"}
        )

    # Pydantic validation错误返回400 (经过异常处理中间件)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_application_requests_invalid_page_size(test_db):
    """测试无效的page_size参数(超过100)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "list_user_11")

        response = await client.get(
            "/v1/operators/me/applications/requests?page_size=101",
            headers={"Authorization": f"Bearer {token}"}
        )

    # Pydantic validation错误返回400 (经过异常处理中间件)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_application_requests_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/operators/me/applications/requests")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_application_requests_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_application_requests_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "list_user_12")

        # 创建应用和申请
        app_id = await create_application(test_db, "format_game", "格式测试")
        await create_request(test_db, operator_id, app_id, "格式测试申请", "pending")

        response = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证顶层格式
    assert isinstance(data["success"], bool)
    assert data["success"] is True
    assert isinstance(data["data"], dict)

    # 验证data结构
    assert isinstance(data["data"]["page"], int)
    assert isinstance(data["data"]["page_size"], int)
    assert isinstance(data["data"]["total"], int)
    assert isinstance(data["data"]["items"], list)

    # 验证item格式
    item = data["data"]["items"][0]
    assert isinstance(item["request_id"], str)
    assert isinstance(item["app_id"], str)
    assert isinstance(item["app_code"], str)
    assert isinstance(item["app_name"], str)
    assert isinstance(item["reason"], str)
    assert isinstance(item["status"], str)
    assert isinstance(item["created_at"], str)
    assert item["reviewed_at"] is None or isinstance(item["reviewed_at"], str)
    assert item["reject_reason"] is None or isinstance(item["reject_reason"], str)


@pytest.mark.asyncio
async def test_get_application_requests_default_pagination(test_db):
    """测试默认分页参数(page=1, page_size=20)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token, operator_id = await create_and_login_operator(client, "list_user_13")

        # 创建1个应用和申请
        app_id = await create_application(test_db, "default_game", "默认分页游戏")
        await create_request(test_db, operator_id, app_id, "默认分页申请", "pending")

        # 不传分页参数
        response = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证使用默认值
    assert data["data"]["page"] == 1
    assert data["data"]["page_size"] == 20
