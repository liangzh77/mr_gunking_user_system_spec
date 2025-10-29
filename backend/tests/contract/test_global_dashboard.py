"""
契约测试: 全局统计仪表盘接口 (T193)

测试目标:
- 验证 GET /v1/statistics/dashboard 接口契约
- 确保请求/响应格式符合contract定义
- 覆盖空数据、有数据、时间筛选、权限验证场景

契约要求:
- 需要管理员JWT Token认证 (Authorization: Bearer {token})
- 支持时间筛选: start_time, end_time (可选)
- 返回格式: {success: true, data: {total_operators, total_sessions, total_players, total_revenue}}
- total_operators: 总运营商数量 (int)
- total_sessions: 总游戏场次 (int)
- total_players: 总玩家人次 (int)
- total_revenue: 总收入 (string, 格式化为两位小数)
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone

from src.main import app


# ========== 辅助函数 ==========

async def create_and_login_admin(client: AsyncClient, username: str) -> str:
    """创建管理员并登录,返回JWT Token"""
    # 注册管理员
    await client.post(
        "/v1/auth/admins/register",
        json={
            "username": username,
            "password": "AdminPass123",
            "full_name": "测试管理员",
            "email": f"{username}@example.com"
        }
    )

    # 登录
    response = await client.post(
        "/v1/auth/admins/login",
        json={
            "username": username,
            "password": "AdminPass123"
        }
    )

    return response.json()["data"]["access_token"]


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


# ========== GET /v1/statistics/dashboard 测试 ==========

@pytest.mark.asyncio
async def test_get_global_dashboard_empty_data(test_db):
    """测试获取空全局统计数据(无任何使用记录)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "dashboard_admin_1")

        response = await client.get(
            "/v1/statistics/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "data" in data

    # 验证字段存在
    dashboard = data["data"]
    assert "total_operators" in dashboard
    assert "total_sessions" in dashboard
    assert "total_players" in dashboard
    assert "total_revenue" in dashboard

    # 空数据验证
    assert dashboard["total_operators"] >= 0  # 可能有注册但未使用的运营商
    assert dashboard["total_sessions"] == 0
    assert dashboard["total_players"] == 0
    assert dashboard["total_revenue"] == "0.00"


@pytest.mark.asyncio
async def test_get_global_dashboard_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/statistics/dashboard")

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_get_global_dashboard_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/statistics/dashboard",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_global_dashboard_with_operator_token(test_db):
    """测试运营商Token访问(应该被拒绝,只允许管理员)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        operator_token = await create_and_login_operator(client, "dashboard_operator_1")

        response = await client.get(
            "/v1/statistics/dashboard",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

    # 应该返回403 Forbidden (没有权限) 或 401 Unauthorized
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_get_global_dashboard_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "dashboard_admin_2")

        response = await client.get(
            "/v1/statistics/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证顶层格式
    assert isinstance(data["success"], bool), "success应该是布尔类型"
    assert data["success"] is True
    assert isinstance(data["data"], dict), "data应该是字典类型"

    # 验证data内部结构
    dashboard = data["data"]
    assert isinstance(dashboard["total_operators"], int), "total_operators应该是整数类型"
    assert isinstance(dashboard["total_sessions"], int), "total_sessions应该是整数类型"
    assert isinstance(dashboard["total_players"], int), "total_players应该是整数类型"
    assert isinstance(dashboard["total_revenue"], str), "total_revenue应该是字符串类型(两位小数)"

    # 验证total_revenue格式为两位小数
    assert "." in dashboard["total_revenue"]
    parts = dashboard["total_revenue"].split(".")
    assert len(parts) == 2, "total_revenue应该包含小数点"
    assert len(parts[1]) == 2, "total_revenue应该有两位小数"


@pytest.mark.asyncio
async def test_get_global_dashboard_time_filter(test_db):
    """测试时间筛选参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "dashboard_admin_3")

        # 测试start_time和end_time参数
        response = await client.get(
            "/v1/statistics/dashboard?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_global_dashboard_with_only_start_time(test_db):
    """测试只提供start_time参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "dashboard_admin_4")

        response = await client.get(
            "/v1/statistics/dashboard?start_time=2025-01-01T00:00:00Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_global_dashboard_with_only_end_time(test_db):
    """测试只提供end_time参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "dashboard_admin_5")

        response = await client.get(
            "/v1/statistics/dashboard?end_time=2025-01-31T23:59:59Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_global_dashboard_no_query_params(test_db):
    """测试不提供任何查询参数(应该返回所有时间的统计)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "dashboard_admin_6")

        response = await client.get(
            "/v1/statistics/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "total_operators" in data["data"]
    assert "total_sessions" in data["data"]
    assert "total_players" in data["data"]
    assert "total_revenue" in data["data"]


@pytest.mark.asyncio
async def test_get_global_dashboard_field_types(test_db):
    """测试各字段的数据类型正确性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "dashboard_admin_7")

        response = await client.get(
            "/v1/statistics/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    dashboard = data["data"]

    # 验证非负数
    assert dashboard["total_operators"] >= 0, "total_operators不能为负数"
    assert dashboard["total_sessions"] >= 0, "total_sessions不能为负数"
    assert dashboard["total_players"] >= 0, "total_players不能为负数"

    # 验证total_revenue可以解析为数字
    try:
        revenue_value = float(dashboard["total_revenue"])
        assert revenue_value >= 0, "total_revenue不能为负数"
    except ValueError:
        pytest.fail("total_revenue应该可以转换为浮点数")


@pytest.mark.asyncio
async def test_get_global_dashboard_invalid_time_format(test_db):
    """测试无效的时间格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "dashboard_admin_8")

        response = await client.get(
            "/v1/statistics/dashboard?start_time=invalid-date",
            headers={"Authorization": f"Bearer {token}"}
        )

    # 应该返回400错误
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_global_dashboard_end_before_start(test_db):
    """测试end_time早于start_time的情况"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "dashboard_admin_9")

        response = await client.get(
            "/v1/statistics/dashboard?start_time=2025-01-31T00:00:00Z&end_time=2025-01-01T00:00:00Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    # 应该返回400错误或返回空数据
    assert response.status_code in [200, 400]
    if response.status_code == 200:
        data = response.json()
        # 如果接受这个请求，应该返回空数据
        assert data["data"]["total_sessions"] == 0


@pytest.mark.asyncio
async def test_get_global_dashboard_consistency(test_db):
    """测试数据一致性(多次调用返回相同结果)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "dashboard_admin_10")

        # 第一次调用
        response1 = await client.get(
            "/v1/statistics/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )

        # 第二次调用
        response2 = await client.get(
            "/v1/statistics/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()["data"]
    data2 = response2.json()["data"]

    # 在没有新数据的情况下，两次查询结果应该一致
    assert data1["total_operators"] == data2["total_operators"]
    assert data1["total_sessions"] == data2["total_sessions"]
    assert data1["total_players"] == data2["total_players"]
    assert data1["total_revenue"] == data2["total_revenue"]
