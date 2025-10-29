"""单元测试：GlobalStatisticsService (T206)

测试GlobalStatisticsService的全局统计功能：
1. get_global_dashboard - 获取全局仪表盘数据
2. get_cross_analysis - 多维度交叉分析
3. get_player_distribution - 玩家数量分布统计

测试策略：
- 使用真实数据库会话(test_db fixture)
- 测试各种数据聚合场景
- 验证时间筛选功能
- 验证维度值筛选功能
"""

import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from src.services.global_statistics import GlobalStatisticsService
from src.models.operator import OperatorAccount
from src.models.site import OperationSite
from src.models.application import Application
from src.models.usage_record import UsageRecord
from src.models.admin import AdminAccount
from src.core.utils.password import hash_password


@pytest.fixture
async def global_stats_test_data(test_db):
    """准备全局统计测试数据"""
    # 创建管理员
    admin = AdminAccount(
        id=uuid4(),
        username=f"stats_admin_{uuid4().hex[:8]}",
        password_hash=hash_password("AdminPass123"),
        full_name="统计测试管理员",
        email=f"stats_admin_{uuid4().hex[:8]}@test.com",
        phone="13900139999",
        role="admin",
        is_active=True
    )
    test_db.add(admin)

    # 创建3个运营商
    operators = []
    for i in range(1, 4):
        operator = OperatorAccount(
            id=uuid4(),
            username=f"stats_op{i}_{uuid4().hex[:8]}",
            password_hash=hash_password("Pass123"),
            full_name=f"统计测试运营商{i}",
            phone=f"1380013800{i}",
            email=f"stats_op{i}_{uuid4().hex[:8]}@test.com",
            api_key=f"api_key_{uuid4().hex}",
            api_key_hash=hash_password(f"api_key_{uuid4().hex}"),
            balance=Decimal("1000.00"),
            customer_tier="standard",
            is_active=True
        )
        test_db.add(operator)
        operators.append(operator)

    await test_db.flush()

    # 为每个运营商创建运营点
    sites = []
    for i, operator in enumerate(operators, 1):
        site = OperationSite(
            id=uuid4(),
            operator_id=operator.id,
            name=f"测试门店{i}",
            address=f"测试地址{i}",
            server_endpoint=f"https://site{i}.test.com",
            created_by=admin.id
        )
        test_db.add(site)
        sites.append(site)

    # 创建2个应用
    apps = []
    for i in range(1, 3):
        app = Application(
            id=uuid4(),
            app_code=f"APP_{datetime.now().strftime('%Y%m%d')}_{uuid4().hex[:3].upper()}",
            app_name=f"测试应用{i}",
            price_per_player=Decimal(str(10.00 * i)),  # app1: 10元, app2: 20元
            min_players=2,
            max_players=8,
            is_active=True
        )
        test_db.add(app)
        apps.append(app)

    await test_db.commit()

    # 刷新所有对象以获取ID
    for op in operators:
        await test_db.refresh(op)
    for site in sites:
        await test_db.refresh(site)
    for app in apps:
        await test_db.refresh(app)
    await test_db.refresh(admin)

    # 创建使用记录（模拟不同时间、不同维度的数据）
    base_time = datetime.now(timezone.utc) - timedelta(days=7)

    usage_records = []

    # 运营商1，门店1，应用1：3条记录（2人、4人、6人）
    for day, players in enumerate([2, 4, 6]):
        record = UsageRecord(
            id=uuid4(),
            operator_id=operators[0].id,
            site_id=sites[0].id,
            application_id=apps[0].id,
            session_id=f"sess_{uuid4().hex[:8]}",
            player_count=players,
            price_per_player=apps[0].price_per_player,
            total_cost=Decimal(str(players * 10.00)),
            created_at=base_time + timedelta(days=day)
        )
        test_db.add(record)
        usage_records.append(record)

    # 运营商2，门店2，应用2：2条记录（3人、5人）
    for day, players in enumerate([3, 5], 3):
        record = UsageRecord(
            id=uuid4(),
            operator_id=operators[1].id,
            site_id=sites[1].id,
            application_id=apps[1].id,
            session_id=f"sess_{uuid4().hex[:8]}",
            player_count=players,
            price_per_player=apps[1].price_per_player,
            total_cost=Decimal(str(players * 20.00)),
            created_at=base_time + timedelta(days=day)
        )
        test_db.add(record)
        usage_records.append(record)

    # 运营商3，门店3，应用1：1条记录（4人）
    record = UsageRecord(
        id=uuid4(),
        operator_id=operators[2].id,
        site_id=sites[2].id,
        application_id=apps[0].id,
        session_id=f"sess_{uuid4().hex[:8]}",
        player_count=4,
        price_per_player=apps[0].price_per_player,
        total_cost=Decimal("40.00"),
        created_at=base_time + timedelta(days=5)
    )
    test_db.add(record)
    usage_records.append(record)

    await test_db.commit()

    for record in usage_records:
        await test_db.refresh(record)

    return {
        "operators": operators,
        "sites": sites,
        "apps": apps,
        "usage_records": usage_records,
        "base_time": base_time
    }


@pytest.mark.asyncio
async def test_get_global_dashboard_all_data(test_db, global_stats_test_data):
    """测试获取全局仪表盘数据（无时间筛选）"""
    service = GlobalStatisticsService(test_db)

    result = await service.get_global_dashboard()

    # 验证数据
    assert result["total_operators"] == 3  # 3个运营商
    assert result["total_sessions"] == 6  # 6条使用记录
    assert result["total_players"] == 24  # 2+4+6+3+5+4 = 24人次
    # 收入: 20+40+60+60+100+40 = 320元
    assert result["total_revenue"] == "320.00"


@pytest.mark.asyncio
async def test_get_global_dashboard_with_time_filter(test_db, global_stats_test_data):
    """测试全局仪表盘数据（带时间筛选）"""
    service = GlobalStatisticsService(test_db)
    base_time = global_stats_test_data["base_time"]

    # 筛选前3天的数据
    start_time = base_time
    end_time = base_time + timedelta(days=2, hours=23, minutes=59)

    result = await service.get_global_dashboard(
        start_time=start_time,
        end_time=end_time
    )

    # 验证数据（只包含前3条记录：day 0, 1, 2）
    assert result["total_operators"] == 3  # 运营商数不受时间筛选影响
    assert result["total_sessions"] == 3  # 前3条记录
    assert result["total_players"] == 12  # 2+4+6 = 12人次
    assert result["total_revenue"] == "120.00"  # 20+40+60 = 120元


@pytest.mark.asyncio
async def test_get_global_dashboard_empty_data(test_db):
    """测试全局仪表盘数据（空数据）"""
    service = GlobalStatisticsService(test_db)

    result = await service.get_global_dashboard()

    # 验证空数据
    assert result["total_operators"] == 0
    assert result["total_sessions"] == 0
    assert result["total_players"] == 0
    assert result["total_revenue"] == "0.00"


@pytest.mark.asyncio
async def test_get_cross_analysis_by_operator(test_db, global_stats_test_data):
    """测试按运营商维度的交叉分析"""
    service = GlobalStatisticsService(test_db)

    result = await service.get_cross_analysis(dimension="operator")

    # 验证维度
    assert result["dimension"] == "operator"

    # 验证数据（按收入降序）
    items = result["items"]
    assert len(items) == 3  # 3个运营商

    # 运营商2收入最高（160元）
    assert items[0]["dimension_name"] == "统计测试运营商2"
    assert items[0]["total_sessions"] == 2
    assert items[0]["total_players"] == 8  # 3+5
    assert items[0]["total_revenue"] == "160.00"
    assert items[0]["avg_players_per_session"] == 4.0

    # 运营商1收入第二（120元）
    assert items[1]["dimension_name"] == "统计测试运营商1"
    assert items[1]["total_sessions"] == 3
    assert items[1]["total_players"] == 12  # 2+4+6
    assert items[1]["total_revenue"] == "120.00"
    assert items[1]["avg_players_per_session"] == 4.0

    # 运营商3收入最低（40元）
    assert items[2]["dimension_name"] == "统计测试运营商3"
    assert items[2]["total_sessions"] == 1
    assert items[2]["total_players"] == 4
    assert items[2]["total_revenue"] == "40.00"
    assert items[2]["avg_players_per_session"] == 4.0


@pytest.mark.asyncio
async def test_get_cross_analysis_by_site(test_db, global_stats_test_data):
    """测试按运营点维度的交叉分析"""
    service = GlobalStatisticsService(test_db)

    result = await service.get_cross_analysis(dimension="site")

    # 验证维度
    assert result["dimension"] == "site"

    # 验证数据
    items = result["items"]
    assert len(items) == 3  # 3个运营点

    # 门店2收入最高（160元）
    assert items[0]["dimension_name"] == "测试门店2"
    assert items[0]["total_revenue"] == "160.00"


@pytest.mark.asyncio
async def test_get_cross_analysis_by_application(test_db, global_stats_test_data):
    """测试按应用维度的交叉分析"""
    service = GlobalStatisticsService(test_db)

    result = await service.get_cross_analysis(dimension="application")

    # 验证维度
    assert result["dimension"] == "application"

    # 验证数据
    items = result["items"]
    assert len(items) == 2  # 2个应用

    # 应用1收入最高（160元，4条记录）
    assert items[0]["dimension_name"] == "测试应用1"
    assert items[0]["total_sessions"] == 4  # 3+1
    assert items[0]["total_players"] == 16  # 2+4+6+4
    assert items[0]["total_revenue"] == "160.00"

    # 应用2收入第二（160元，2条记录）
    assert items[1]["dimension_name"] == "测试应用2"
    assert items[1]["total_sessions"] == 2
    assert items[1]["total_players"] == 8  # 3+5
    assert items[1]["total_revenue"] == "160.00"


@pytest.mark.asyncio
async def test_get_cross_analysis_with_time_filter(test_db, global_stats_test_data):
    """测试交叉分析（带时间筛选）"""
    service = GlobalStatisticsService(test_db)
    base_time = global_stats_test_data["base_time"]

    # 筛选前3天的数据
    start_time = base_time
    end_time = base_time + timedelta(days=2, hours=23, minutes=59)

    result = await service.get_cross_analysis(
        dimension="operator",
        start_time=start_time,
        end_time=end_time
    )

    # 验证数据（只有运营商1的前3条记录）
    items = result["items"]
    assert len(items) == 1  # 只有运营商1有数据
    assert items[0]["dimension_name"] == "统计测试运营商1"
    assert items[0]["total_sessions"] == 3
    assert items[0]["total_revenue"] == "120.00"


@pytest.mark.asyncio
async def test_get_cross_analysis_with_dimension_values_filter(test_db, global_stats_test_data):
    """测试交叉分析（带维度值筛选）"""
    service = GlobalStatisticsService(test_db)
    operators = global_stats_test_data["operators"]

    # 只查询运营商1和运营商2
    dimension_values = [operators[0].id, operators[1].id]

    result = await service.get_cross_analysis(
        dimension="operator",
        dimension_values=dimension_values
    )

    # 验证数据（只包含运营商1和运营商2）
    items = result["items"]
    assert len(items) == 2
    assert all(
        item["dimension_name"] in ["统计测试运营商1", "统计测试运营商2"]
        for item in items
    )


@pytest.mark.asyncio
async def test_get_cross_analysis_invalid_dimension(test_db, global_stats_test_data):
    """测试交叉分析（无效维度）"""
    service = GlobalStatisticsService(test_db)

    with pytest.raises(ValueError) as exc_info:
        await service.get_cross_analysis(dimension="invalid_dimension")

    assert "Invalid dimension" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_player_distribution(test_db, global_stats_test_data):
    """测试玩家数量分布统计"""
    service = GlobalStatisticsService(test_db)

    result = await service.get_player_distribution()

    # 验证总场次
    assert result["total_sessions"] == 6

    # 验证最常见玩家数量（4人，出现2次）
    assert result["most_common_player_count"] == 4

    # 验证分布数据
    distribution = result["distribution"]
    assert len(distribution) == 5  # 2人、3人、4人、5人、6人

    # 验证每个玩家数量的统计
    player_2 = next(d for d in distribution if d["player_count"] == 2)
    assert player_2["session_count"] == 1
    assert player_2["percentage"] == pytest.approx(16.67, abs=0.01)  # 1/6 * 100
    assert player_2["total_revenue"] == "20.00"

    player_4 = next(d for d in distribution if d["player_count"] == 4)
    assert player_4["session_count"] == 2
    assert player_4["percentage"] == pytest.approx(33.33, abs=0.01)  # 2/6 * 100
    assert player_4["total_revenue"] == "80.00"  # 40+40


@pytest.mark.asyncio
async def test_get_player_distribution_with_time_filter(test_db, global_stats_test_data):
    """测试玩家分布统计（带时间筛选）"""
    service = GlobalStatisticsService(test_db)
    base_time = global_stats_test_data["base_time"]

    # 筛选前3天的数据
    start_time = base_time
    end_time = base_time + timedelta(days=2, hours=23, minutes=59)

    result = await service.get_player_distribution(
        start_time=start_time,
        end_time=end_time
    )

    # 验证数据（只包含前3条记录：2人、4人、6人）
    assert result["total_sessions"] == 3
    assert result["most_common_player_count"] in [2, 4, 6]  # 都只出现1次

    distribution = result["distribution"]
    assert len(distribution) == 3


@pytest.mark.asyncio
async def test_get_player_distribution_empty_data(test_db):
    """测试玩家分布统计（空数据）"""
    service = GlobalStatisticsService(test_db)

    result = await service.get_player_distribution()

    # 验证空数据
    assert result["total_sessions"] == 0
    assert result["most_common_player_count"] == 0
    assert result["distribution"] == []
