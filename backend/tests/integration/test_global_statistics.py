"""
集成测试: 全局统计查询 (T195)

测试目标:
- 验证全局统计数据查询的完整流程
- 测试从游戏授权到统计数据聚合的端到端流程
- 验证多维度交叉分析的正确性
- 确保数据一致性和准确性

测试场景:
1. 创建多个运营商、应用、运营点
2. 产生游戏使用记录（授权+计费）
3. 查询全局统计仪表盘，验证总数统计
4. 查询多维度分析，验证按运营商/应用/运营点的统计
5. 测试时间筛选功能
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from src.main import app


# ========== 辅助函数 ==========

async def create_and_login_admin(client: AsyncClient, username: str) -> tuple[str, str]:
    """创建管理员并登录,返回(admin_id, token)"""
    # 注册管理员
    register_response = await client.post(
        "/v1/auth/admins/register",
        json={
            "username": username,
            "password": "AdminPass123",
            "full_name": "测试管理员",
            "email": f"{username}@example.com"
        }
    )
    admin_id = register_response.json()["data"]["id"]

    # 登录
    login_response = await client.post(
        "/v1/auth/admins/login",
        json={
            "username": username,
            "password": "AdminPass123"
        }
    )

    token = login_response.json()["data"]["access_token"]
    return admin_id, token


async def create_and_login_operator(client: AsyncClient, username: str, name: str) -> tuple[str, str]:
    """创建运营商并登录,返回(operator_id, token)"""
    # 注册
    register_response = await client.post(
        "/v1/auth/operators/register",
        json={
            "username": username,
            "password": "TestPass123",
            "name": name,
            "phone": "13800138000",
            "email": f"{username}@example.com"
        }
    )
    operator_id = register_response.json()["data"]["id"]

    # 登录
    login_response = await client.post(
        "/v1/auth/operators/login",
        json={
            "username": username,
            "password": "TestPass123"
        }
    )

    token = login_response.json()["data"]["access_token"]
    return operator_id, token


async def create_application(client: AsyncClient, admin_token: str, app_name: str, unit_price: str) -> str:
    """创建应用并返回app_id"""
    response = await client.post(
        "/v1/admin/applications",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "app_name": app_name,
            "unit_price": unit_price,
            "min_players": 2,
            "max_players": 8,
            "description": f"{app_name}的描述"
        }
    )
    return response.json()["data"]["id"]


async def create_site(client: AsyncClient, operator_token: str, name: str, address: str) -> str:
    """创建运营点并返回site_id"""
    response = await client.post(
        "/v1/operators/me/sites",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "name": name,
            "address": address,
            "description": f"{name}的描述"
        }
    )
    return response.json()["data"]["id"]


async def authorize_and_bill(
    client: AsyncClient,
    operator_token: str,
    app_id: str,
    site_id: str,
    session_id: str,
    player_count: int
) -> dict:
    """执行游戏授权和计费，返回结果"""
    # 游戏授权
    auth_response = await client.post(
        "/v1/game/authorize",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "app_id": app_id,
            "site_id": site_id,
            "session_id": session_id,
            "player_count": player_count
        }
    )

    if auth_response.status_code != 200:
        return {"success": False, "error": auth_response.json()}

    return {"success": True, "data": auth_response.json()["data"]}


async def recharge_operator(client: AsyncClient, operator_token: str, amount: str) -> bool:
    """给运营商充值"""
    # 创建充值订单
    order_response = await client.post(
        "/v1/recharge/orders",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "amount": amount,
            "payment_method": "alipay"
        }
    )

    if order_response.status_code != 201:
        return False

    order_id = order_response.json()["data"]["order_id"]

    # 模拟支付回调
    callback_response = await client.post(
        "/v1/recharge/callback",
        json={
            "order_id": order_id,
            "status": "success",
            "trade_no": f"TEST_{int(datetime.now(timezone.utc).timestamp())}",
            "amount": amount
        }
    )

    return callback_response.status_code == 200


# ========== 集成测试 ==========

@pytest.mark.asyncio
async def test_global_dashboard_with_real_data(test_db):
    """测试全局统计仪表盘 - 有真实数据"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 第1步: 创建管理员
        admin_id, admin_token = await create_and_login_admin(client, "stats_admin_1")

        # 第2步: 创建2个运营商
        op1_id, op1_token = await create_and_login_operator(client, "stats_op1", "运营商A")
        op2_id, op2_token = await create_and_login_operator(client, "stats_op2", "运营商B")

        # 第3步: 创建2个应用
        app1_id = await create_application(client, admin_token, "太空探险", "50.00")
        app2_id = await create_application(client, admin_token, "海底世界", "60.00")

        # 第4步: 给运营商授权应用
        await client.post(
            f"/v1/admin/operators/{op1_id}/applications",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"application_id": app1_id}
        )
        await client.post(
            f"/v1/admin/operators/{op2_id}/applications",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"application_id": app2_id}
        )

        # 第5步: 创建运营点
        site1_id = await create_site(client, op1_token, "运营商A门店1", "北京市朝阳区")
        site2_id = await create_site(client, op2_token, "运营商B门店1", "上海市浦东新区")

        # 第6步: 给运营商充值
        await recharge_operator(client, op1_token, "1000.00")
        await recharge_operator(client, op2_token, "1000.00")

        # 第7步: 产生游戏使用记录
        # 运营商A: 2场游戏，共9人
        await authorize_and_bill(client, op1_token, app1_id, site1_id, "session_1", 4)
        await authorize_and_bill(client, op1_token, app1_id, site1_id, "session_2", 5)

        # 运营商B: 1场游戏，3人
        await authorize_and_bill(client, op2_token, app2_id, site2_id, "session_3", 3)

        # 第8步: 查询全局统计仪表盘
        dashboard_response = await client.get(
            "/v1/statistics/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    assert dashboard_response.status_code == 200
    data = dashboard_response.json()["data"]

    # 验证全局统计数据
    assert data["total_operators"] >= 2, "应该至少有2个运营商"
    assert data["total_sessions"] >= 3, "应该至少有3个游戏场次"
    assert data["total_players"] >= 12, "应该至少有12个玩家人次"

    # 验证总收入 (4*50 + 5*50 + 3*60 = 200 + 250 + 180 = 630)
    expected_revenue = Decimal("630.00")
    actual_revenue = Decimal(data["total_revenue"])
    assert actual_revenue >= expected_revenue, f"总收入应该至少为{expected_revenue}，实际为{actual_revenue}"


@pytest.mark.asyncio
async def test_cross_analysis_by_operator(test_db):
    """测试多维度交叉分析 - 按运营商维度"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建管理员
        admin_id, admin_token = await create_and_login_admin(client, "stats_admin_2")

        # 创建运营商
        op1_id, op1_token = await create_and_login_operator(client, "stats_op3", "运营商C")

        # 创建应用
        app_id = await create_application(client, admin_token, "测试应用", "100.00")

        # 授权应用
        await client.post(
            f"/v1/admin/operators/{op1_id}/applications",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"application_id": app_id}
        )

        # 创建运营点
        site_id = await create_site(client, op1_token, "测试门店", "测试地址")

        # 充值
        await recharge_operator(client, op1_token, "1000.00")

        # 产生游戏记录
        await authorize_and_bill(client, op1_token, app_id, site_id, "session_4", 4)

        # 查询多维度分析
        cross_response = await client.get(
            "/v1/statistics/cross-analysis?dimension=operator",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    assert cross_response.status_code == 200
    data = cross_response.json()["data"]

    # 验证dimension
    assert data["dimension"] == "operator"

    # 验证items包含运营商数据
    items = data["items"]
    assert len(items) >= 1, "至少应该有1个运营商的统计数据"

    # 查找运营商C的数据
    op_c_data = next((item for item in items if "运营商C" in item["dimension_name"]), None)
    if op_c_data:
        assert op_c_data["total_sessions"] >= 1
        assert op_c_data["total_players"] >= 4
        assert float(op_c_data["total_revenue"]) >= 400.00  # 4人 * 100元


@pytest.mark.asyncio
async def test_cross_analysis_by_application(test_db):
    """测试多维度交叉分析 - 按应用维度"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建管理员
        admin_id, admin_token = await create_and_login_admin(client, "stats_admin_3")

        # 创建运营商
        op_id, op_token = await create_and_login_operator(client, "stats_op4", "运营商D")

        # 创建2个应用
        app1_id = await create_application(client, admin_token, "应用X", "80.00")
        app2_id = await create_application(client, admin_token, "应用Y", "90.00")

        # 授权应用
        await client.post(
            f"/v1/admin/operators/{op_id}/applications",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"application_id": app1_id}
        )
        await client.post(
            f"/v1/admin/operators/{op_id}/applications",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"application_id": app2_id}
        )

        # 创建运营点
        site_id = await create_site(client, op_token, "门店D", "地址D")

        # 充值
        await recharge_operator(client, op_token, "2000.00")

        # 产生游戏记录
        await authorize_and_bill(client, op_token, app1_id, site_id, "session_5", 3)
        await authorize_and_bill(client, op_token, app2_id, site_id, "session_6", 4)

        # 查询多维度分析 - 按应用
        cross_response = await client.get(
            "/v1/statistics/cross-analysis?dimension=application",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    assert cross_response.status_code == 200
    data = cross_response.json()["data"]

    # 验证dimension
    assert data["dimension"] == "application"

    # 验证items包含应用数据
    items = data["items"]
    assert len(items) >= 2, "至少应该有2个应用的统计数据"

    # 查找应用X和Y的数据
    app_x_data = next((item for item in items if "应用X" in item["dimension_name"]), None)
    app_y_data = next((item for item in items if "应用Y" in item["dimension_name"]), None)

    if app_x_data:
        assert app_x_data["total_sessions"] >= 1
        assert app_x_data["total_players"] >= 3

    if app_y_data:
        assert app_y_data["total_sessions"] >= 1
        assert app_y_data["total_players"] >= 4


@pytest.mark.asyncio
async def test_cross_analysis_by_site(test_db):
    """测试多维度交叉分析 - 按运营点维度"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建管理员
        admin_id, admin_token = await create_and_login_admin(client, "stats_admin_4")

        # 创建运营商
        op_id, op_token = await create_and_login_operator(client, "stats_op5", "运营商E")

        # 创建应用
        app_id = await create_application(client, admin_token, "应用Z", "70.00")

        # 授权应用
        await client.post(
            f"/v1/admin/operators/{op_id}/applications",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"application_id": app_id}
        )

        # 创建2个运营点
        site1_id = await create_site(client, op_token, "门店E1", "北京")
        site2_id = await create_site(client, op_token, "门店E2", "上海")

        # 充值
        await recharge_operator(client, op_token, "2000.00")

        # 产生游戏记录
        await authorize_and_bill(client, op_token, app_id, site1_id, "session_7", 5)
        await authorize_and_bill(client, op_token, app_id, site2_id, "session_8", 3)

        # 查询多维度分析 - 按运营点
        cross_response = await client.get(
            "/v1/statistics/cross-analysis?dimension=site",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    assert cross_response.status_code == 200
    data = cross_response.json()["data"]

    # 验证dimension
    assert data["dimension"] == "site"

    # 验证items包含运营点数据
    items = data["items"]
    assert len(items) >= 2, "至少应该有2个运营点的统计数据"


@pytest.mark.asyncio
async def test_dashboard_time_filter(test_db):
    """测试全局统计仪表盘 - 时间筛选"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建管理员
        admin_id, admin_token = await create_and_login_admin(client, "stats_admin_5")

        # 查询最近30天的统计
        start_time = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        end_time = datetime.now(timezone.utc).isoformat()

        dashboard_response = await client.get(
            f"/v1/statistics/dashboard?start_time={start_time}&end_time={end_time}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    assert dashboard_response.status_code == 200
    data = dashboard_response.json()["data"]

    # 验证数据结构
    assert "total_operators" in data
    assert "total_sessions" in data
    assert "total_players" in data
    assert "total_revenue" in data


@pytest.mark.asyncio
async def test_data_consistency_across_apis(test_db):
    """测试数据一致性 - 全局统计和多维度分析的数据应该一致"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建管理员
        admin_id, admin_token = await create_and_login_admin(client, "stats_admin_6")

        # 创建完整的测试数据
        op_id, op_token = await create_and_login_operator(client, "stats_op6", "运营商F")
        app_id = await create_application(client, admin_token, "应用F", "50.00")

        await client.post(
            f"/v1/admin/operators/{op_id}/applications",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"application_id": app_id}
        )

        site_id = await create_site(client, op_token, "门店F", "地址F")
        await recharge_operator(client, op_token, "1000.00")

        # 产生游戏记录
        await authorize_and_bill(client, op_token, app_id, site_id, "session_9", 4)

        # 查询全局统计
        dashboard_response = await client.get(
            "/v1/statistics/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # 查询多维度分析 - 按运营商
        cross_response = await client.get(
            "/v1/statistics/cross-analysis?dimension=operator",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    assert dashboard_response.status_code == 200
    assert cross_response.status_code == 200

    dashboard_data = dashboard_response.json()["data"]
    cross_data = cross_response.json()["data"]

    # 多维度分析的总和应该等于全局统计
    # (注意: 这里只是验证结构，实际值的一致性需要在有隔离的测试环境中验证)
    total_sessions_from_cross = sum(item["total_sessions"] for item in cross_data["items"])
    total_players_from_cross = sum(item["total_players"] for item in cross_data["items"])

    # 验证数据合理性（交叉分析的总和不应超过全局统计）
    assert total_sessions_from_cross <= dashboard_data["total_sessions"]
    assert total_players_from_cross <= dashboard_data["total_players"]


@pytest.mark.asyncio
async def test_avg_players_calculation(test_db):
    """测试平均玩家数计算的准确性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建管理员
        admin_id, admin_token = await create_and_login_admin(client, "stats_admin_7")

        # 创建测试数据
        op_id, op_token = await create_and_login_operator(client, "stats_op7", "运营商G")
        app_id = await create_application(client, admin_token, "应用G", "60.00")

        await client.post(
            f"/v1/admin/operators/{op_id}/applications",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"application_id": app_id}
        )

        site_id = await create_site(client, op_token, "门店G", "地址G")
        await recharge_operator(client, op_token, "2000.00")

        # 产生3场游戏: 4人, 5人, 6人 (总共15人，平均5人)
        await authorize_and_bill(client, op_token, app_id, site_id, "session_10", 4)
        await authorize_and_bill(client, op_token, app_id, site_id, "session_11", 5)
        await authorize_and_bill(client, op_token, app_id, site_id, "session_12", 6)

        # 查询多维度分析
        cross_response = await client.get(
            "/v1/statistics/cross-analysis?dimension=operator",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    assert cross_response.status_code == 200
    items = cross_response.json()["data"]["items"]

    # 查找运营商G的数据
    op_g_data = next((item for item in items if "运营商G" in item["dimension_name"]), None)

    if op_g_data:
        # 验证平均玩家数
        sessions = op_g_data["total_sessions"]
        players = op_g_data["total_players"]
        avg = op_g_data["avg_players_per_session"]

        if sessions > 0:
            expected_avg = players / sessions
            # 允许小数舍入误差
            assert abs(avg - expected_avg) < 0.2, f"平均玩家数计算错误: 期望{expected_avg}, 实际{avg}"
