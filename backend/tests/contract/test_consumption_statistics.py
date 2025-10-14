"""
契约测试: 按时间统计消费接口 (T114)

测试目标:
- 验证 GET /v1/operators/me/statistics/consumption 接口契约
- 确保请求/响应格式符合contract定义
- 覆盖空数据、时间筛选、维度切换、响应格式场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 支持时间筛选: start_time, end_time (可选)
- 支持维度切换: dimension (day/week/month, 默认day)
- 返回格式: {success: true, data: {dimension: str, chart_data: [...], summary: {...}}}
- chart_data: 时间序列数据 (date, total_sessions, total_players, total_cost)
- summary: 汇总数据 (total_sessions, total_players, total_cost, avg_players_per_session)
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone

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


# ========== GET /v1/operators/me/statistics/consumption 测试 ==========

@pytest.mark.asyncio
async def test_get_consumption_statistics_empty_data(test_db):
    """测试获取空统计数据(无使用记录)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "consumption_user_1")

        response = await client.get(
            "/v1/operators/me/statistics/consumption",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "data" in data
    assert "dimension" in data["data"]
    assert "chart_data" in data["data"]
    assert "summary" in data["data"]

    # 空数据验证
    assert data["data"]["dimension"] == "day"
    assert isinstance(data["data"]["chart_data"], list)
    assert len(data["data"]["chart_data"]) == 0

    # summary应该有结构但值为0
    summary = data["data"]["summary"]
    assert summary["total_sessions"] == 0
    assert summary["total_players"] == 0
    assert summary["total_cost"] == "0.00"
    assert summary["avg_players_per_session"] == 0.0


@pytest.mark.asyncio
async def test_get_consumption_statistics_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/operators/me/statistics/consumption")

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_get_consumption_statistics_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/operators/me/statistics/consumption",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_consumption_statistics_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "consumption_user_2")

        response = await client.get(
            "/v1/operators/me/statistics/consumption",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证顶层格式
    assert isinstance(data["success"], bool), "success应该是布尔类型"
    assert data["success"] is True
    assert isinstance(data["data"], dict), "data应该是字典类型"

    # 验证data内部结构
    assert isinstance(data["data"]["dimension"], str), "dimension应该是字符串类型"
    assert isinstance(data["data"]["chart_data"], list), "chart_data应该是列表类型"
    assert isinstance(data["data"]["summary"], dict), "summary应该是字典类型"


@pytest.mark.asyncio
async def test_get_consumption_statistics_time_filter(test_db):
    """测试时间筛选参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "consumption_user_3")

        # 测试start_time和end_time参数
        response = await client.get(
            "/v1/operators/me/statistics/consumption?start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_consumption_statistics_dimension_day(test_db):
    """测试dimension=day参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "consumption_user_4")

        response = await client.get(
            "/v1/operators/me/statistics/consumption?dimension=day",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["dimension"] == "day"


@pytest.mark.asyncio
async def test_get_consumption_statistics_dimension_week(test_db):
    """测试dimension=week参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "consumption_user_5")

        response = await client.get(
            "/v1/operators/me/statistics/consumption?dimension=week",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["dimension"] == "week"


@pytest.mark.asyncio
async def test_get_consumption_statistics_dimension_month(test_db):
    """测试dimension=month参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "consumption_user_6")

        response = await client.get(
            "/v1/operators/me/statistics/consumption?dimension=month",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["dimension"] == "month"


@pytest.mark.asyncio
async def test_get_consumption_statistics_invalid_dimension(test_db):
    """测试无效dimension参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "consumption_user_7")

        response = await client.get(
            "/v1/operators/me/statistics/consumption?dimension=year",
            headers={"Authorization": f"Bearer {token}"}
        )

    # 应该返回400错误
    assert response.status_code == 400
    data = response.json()
    assert "error_code" in data
    assert data["error_code"] == "INVALID_DIMENSION"


@pytest.mark.asyncio
async def test_get_consumption_statistics_isolation(test_db):
    """测试运营商数据隔离(不能看到其他运营商的统计数据)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建两个运营商
        token1 = await create_and_login_operator(client, "consumption_user_8")
        token2 = await create_and_login_operator(client, "consumption_user_9")

        # 运营商1查询统计(应该只看到自己的数据,但无使用记录时为空)
        response1 = await client.get(
            "/v1/operators/me/statistics/consumption",
            headers={"Authorization": f"Bearer {token1}"}
        )

        # 运营商2查询统计(应该只看到自己的数据,但无使用记录时为空)
        response2 = await client.get(
            "/v1/operators/me/statistics/consumption",
            headers={"Authorization": f"Bearer {token2}"}
        )

    assert response1.status_code == 200
    assert response2.status_code == 200

    # 两个运营商的统计应该互不可见(当前都为空,因为没有使用记录)
    assert len(response1.json()["data"]["chart_data"]) == 0
    assert len(response2.json()["data"]["chart_data"]) == 0


@pytest.mark.asyncio
async def test_get_consumption_statistics_chart_data_field_format(test_db):
    """测试chart_data数组中每个对象的字段格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "consumption_user_10")

        response = await client.get(
            "/v1/operators/me/statistics/consumption",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 当前应该是空列表(因为没有使用记录)
    chart_data = data["data"]["chart_data"]
    assert isinstance(chart_data, list)

    # 如果有数据,应该包含以下字段(这里只验证结构,暂无实际数据)
    # 每个data_point应该有: date, total_sessions, total_players, total_cost
    for point in chart_data:
        assert "date" in point
        assert "total_sessions" in point
        assert "total_players" in point
        assert "total_cost" in point

        # 验证字段类型
        assert isinstance(point["date"], str)
        assert isinstance(point["total_sessions"], int)
        assert isinstance(point["total_players"], int)
        assert isinstance(point["total_cost"], str)


@pytest.mark.asyncio
async def test_get_consumption_statistics_summary_format(test_db):
    """测试summary对象的字段格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "consumption_user_11")

        response = await client.get(
            "/v1/operators/me/statistics/consumption",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证summary结构
    summary = data["data"]["summary"]
    assert "total_sessions" in summary
    assert "total_players" in summary
    assert "total_cost" in summary
    assert "avg_players_per_session" in summary

    # 验证字段类型
    assert isinstance(summary["total_sessions"], int)
    assert isinstance(summary["total_players"], int)
    assert isinstance(summary["total_cost"], str)
    assert isinstance(summary["avg_players_per_session"], (int, float))


@pytest.mark.asyncio
async def test_get_consumption_statistics_with_only_start_time(test_db):
    """测试只提供start_time参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "consumption_user_12")

        response = await client.get(
            "/v1/operators/me/statistics/consumption?start_time=2025-01-01T00:00:00Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_consumption_statistics_with_only_end_time(test_db):
    """测试只提供end_time参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "consumption_user_13")

        response = await client.get(
            "/v1/operators/me/statistics/consumption?end_time=2025-01-31T23:59:59Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_consumption_statistics_no_query_params(test_db):
    """测试不提供任何查询参数(应该返回所有时间的统计,默认按天)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "consumption_user_14")

        response = await client.get(
            "/v1/operators/me/statistics/consumption",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["dimension"] == "day"  # 默认维度


@pytest.mark.asyncio
async def test_get_consumption_statistics_avg_calculation(test_db):
    """测试平均每场玩家数的计算(验证契约中的avg_players_per_session字段)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "consumption_user_15")

        response = await client.get(
            "/v1/operators/me/statistics/consumption",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证summary包含 avg_players_per_session 字段
    summary = data["data"]["summary"]
    assert "avg_players_per_session" in summary
    assert isinstance(summary["avg_players_per_session"], (int, float))

    # 如果有数据,验证计算逻辑: avg = total_players / total_sessions
    if summary["total_sessions"] > 0:
        expected_avg = summary["total_players"] / summary["total_sessions"]
        # 允许1位小数的舍入误差
        assert abs(summary["avg_players_per_session"] - expected_avg) < 0.2
