"""
契约测试: 多维度交叉分析接口 (T194)

测试目标:
- 验证 GET /v1/statistics/cross-analysis 接口契约
- 确保请求/响应格式符合contract定义
- 覆盖多维度筛选、对比分析、空数据、权限验证场景

契约要求:
- 需要管理员JWT Token认证 (Authorization: Bearer {token})
- 支持维度筛选: dimension (operator/site/application)
- 支持时间筛选: start_time, end_time (可选)
- 支持维度值筛选: dimension_values (可选，多个值用逗号分隔)
- 返回格式: {success: true, data: {dimension: str, items: [...]}}
- items: 按维度分组的统计数据列表
- 每个item包含: dimension_id, dimension_name, total_sessions, total_players, total_revenue, avg_players_per_session
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


# ========== GET /v1/statistics/cross-analysis 测试 ==========

@pytest.mark.asyncio
async def test_get_cross_analysis_without_dimension(test_db):
    """测试未提供dimension参数(应该返回400错误)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_1")

        response = await client.get(
            "/v1/statistics/cross-analysis",
            headers={"Authorization": f"Bearer {token}"}
        )

    # dimension是必需参数
    assert response.status_code == 400
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_get_cross_analysis_by_operator(test_db):
    """测试按运营商维度分析"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_2")

        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=operator",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "data" in data
    assert "dimension" in data["data"]
    assert "items" in data["data"]

    # 验证dimension字段
    assert data["data"]["dimension"] == "operator"
    assert isinstance(data["data"]["items"], list)


@pytest.mark.asyncio
async def test_get_cross_analysis_by_site(test_db):
    """测试按运营点维度分析"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_3")

        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=site",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["dimension"] == "site"
    assert isinstance(data["data"]["items"], list)


@pytest.mark.asyncio
async def test_get_cross_analysis_by_application(test_db):
    """测试按应用维度分析"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_4")

        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=application",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["dimension"] == "application"
    assert isinstance(data["data"]["items"], list)


@pytest.mark.asyncio
async def test_get_cross_analysis_invalid_dimension(test_db):
    """测试无效的dimension参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_5")

        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=invalid_dimension",
            headers={"Authorization": f"Bearer {token}"}
        )

    # 应该返回400错误
    assert response.status_code == 400
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_get_cross_analysis_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/statistics/cross-analysis?dimension=operator")

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_get_cross_analysis_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=operator",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_cross_analysis_with_operator_token(test_db):
    """测试运营商Token访问(应该被拒绝,只允许管理员)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        operator_token = await create_and_login_operator(client, "cross_operator_1")

        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=operator",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

    # 应该返回403 Forbidden (没有权限) 或 401 Unauthorized
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_get_cross_analysis_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_6")

        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=operator",
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
    assert isinstance(data["data"]["items"], list), "items应该是列表类型"


@pytest.mark.asyncio
async def test_get_cross_analysis_items_format(test_db):
    """测试items数组中每个对象的字段格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_7")

        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=operator",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证items结构
    items = data["data"]["items"]
    assert isinstance(items, list)

    # 如果有数据,验证每个item的字段
    for item in items:
        assert "dimension_id" in item, "每个item应该有dimension_id"
        assert "dimension_name" in item, "每个item应该有dimension_name"
        assert "total_sessions" in item, "每个item应该有total_sessions"
        assert "total_players" in item, "每个item应该有total_players"
        assert "total_revenue" in item, "每个item应该有total_revenue"
        assert "avg_players_per_session" in item, "每个item应该有avg_players_per_session"

        # 验证字段类型
        assert isinstance(item["dimension_id"], str), "dimension_id应该是字符串类型"
        assert isinstance(item["dimension_name"], str), "dimension_name应该是字符串类型"
        assert isinstance(item["total_sessions"], int), "total_sessions应该是整数类型"
        assert isinstance(item["total_players"], int), "total_players应该是整数类型"
        assert isinstance(item["total_revenue"], str), "total_revenue应该是字符串类型"
        assert isinstance(item["avg_players_per_session"], (int, float)), "avg_players_per_session应该是数字类型"


@pytest.mark.asyncio
async def test_get_cross_analysis_time_filter(test_db):
    """测试时间筛选参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_8")

        # 测试start_time和end_time参数
        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=operator&start_time=2025-01-01T00:00:00Z&end_time=2025-01-31T23:59:59Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_cross_analysis_with_dimension_values_filter(test_db):
    """测试dimension_values筛选参数(只返回特定维度值的数据)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_9")

        # 假设有operator_id1和operator_id2
        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=operator&dimension_values=id1,id2",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # 如果返回了数据，应该只包含筛选的维度值
    items = data["data"]["items"]
    # 这里只验证格式，实际值依赖于数据库内容


@pytest.mark.asyncio
async def test_get_cross_analysis_empty_data(test_db):
    """测试无数据时的响应"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_10")

        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=operator",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 空数据时应该返回空列表
    assert data["success"] is True
    assert isinstance(data["data"]["items"], list)
    # items可能为空（无使用记录）或有运营商但数据为0


@pytest.mark.asyncio
async def test_get_cross_analysis_invalid_time_format(test_db):
    """测试无效的时间格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_11")

        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=operator&start_time=invalid-date",
            headers={"Authorization": f"Bearer {token}"}
        )

    # 应该返回400错误
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_cross_analysis_with_only_start_time(test_db):
    """测试只提供start_time参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_12")

        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=site&start_time=2025-01-01T00:00:00Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_cross_analysis_with_only_end_time(test_db):
    """测试只提供end_time参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_13")

        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=application&end_time=2025-01-31T23:59:59Z",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_cross_analysis_avg_calculation(test_db):
    """测试avg_players_per_session计算逻辑"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_14")

        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=operator",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    items = data["data"]["items"]
    for item in items:
        # 如果有数据,验证平均值计算
        if item["total_sessions"] > 0:
            expected_avg = item["total_players"] / item["total_sessions"]
            # 允许1位小数的舍入误差
            assert abs(item["avg_players_per_session"] - expected_avg) < 0.2


@pytest.mark.asyncio
async def test_get_cross_analysis_revenue_format(test_db):
    """测试total_revenue格式为两位小数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_admin(client, "cross_admin_15")

        response = await client.get(
            "/v1/statistics/cross-analysis?dimension=operator",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    items = data["data"]["items"]
    for item in items:
        # 验证total_revenue格式
        assert "." in item["total_revenue"], "total_revenue应该包含小数点"
        parts = item["total_revenue"].split(".")
        assert len(parts) == 2, "total_revenue应该有整数和小数部分"
        assert len(parts[1]) == 2, "total_revenue应该有两位小数"

        # 验证可以解析为数字
        try:
            revenue_value = float(item["total_revenue"])
            assert revenue_value >= 0, "total_revenue不能为负数"
        except ValueError:
            pytest.fail("total_revenue应该可以转换为浮点数")
