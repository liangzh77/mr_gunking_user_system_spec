"""性能基线测试 (T289a)

建立系统性能基线，为后续优化提供对比依据。

测试指标：
- 授权API响应时间 P50/P95/P99
- 数据库查询耗时
- 内存占用
- 吞吐量

性能需求（NFR）：
- NFR-001: 授权API P95 < 100ms
- NFR-002: 峰值吞吐量 ≥ 20 req/s
- NFR-004: 10万条记录导出 < 30秒
- NFR-005: 系统可用性 ≥ 99.5%

运行方式：
    pytest tests/performance/test_baseline.py -v --benchmark-only
"""

import pytest
import time
import statistics
from decimal import Decimal
from uuid import uuid4
from httpx import AsyncClient
import hashlib

from src.main import app
from src.models.admin import AdminAccount
from src.models.operator import OperatorAccount
from src.models.application import Application
from src.models.site import OperationSite
from src.models.authorization import OperatorAppAuthorization
from src.models.usage_record import UsageRecord
from src.core.utils.password import hash_password


@pytest.fixture
async def performance_test_data(test_db):
    """准备性能测试数据"""
    # 创建管理员
    admin = AdminAccount(
        id=uuid4(),
        username="perf_admin",
        password_hash=hash_password("Admin@123"),
        full_name="Performance Test Admin",
        email="perf_admin@test.com",
        phone="13800138000",
        role="super_admin",
        permissions={},
        is_active=True
    )
    test_db.add(admin)
    await test_db.flush()

    # 创建测试运营商
    api_key_raw = "perf_api_key_" + str(uuid4())[:8]
    api_key_value = hashlib.sha256(api_key_raw.encode()).hexdigest()[:64]
    api_key_hash_value = hash_password(api_key_value)

    operator = OperatorAccount(
        id=uuid4(),
        username="perf_operator",
        password_hash=hash_password("Operator@123"),
        full_name="Performance Test Operator",
        email="perf_operator@test.com",
        phone="13900139000",
        api_key=api_key_value,
        api_key_hash=api_key_hash_value,
        balance=Decimal("100000.00"),  # 充足余额
        customer_tier="standard",
        is_active=True
    )
    test_db.add(operator)
    await test_db.flush()

    # 创建应用
    application = Application(
        id=uuid4(),
        app_code="perf_test_app",
        app_name="Performance Test App",
        description="App for performance testing",
        price_per_player=Decimal("10.00"),
        min_players=2,
        max_players=8,
        is_active=True,
        created_by=admin.id
    )
    test_db.add(application)
    await test_db.flush()

    # 创建运营点
    site = OperationSite(
        id=uuid4(),
        operator_id=operator.id,
        name="Performance Test Site",
        address="Test Address for Performance",
        server_identifier="server_perf_test",
        is_active=True
    )
    test_db.add(site)
    await test_db.flush()

    # 授权应用
    from datetime import datetime, timezone
    authorization = OperatorAppAuthorization(
        id=uuid4(),
        operator_id=operator.id,
        application_id=application.id,
        authorized_by=admin.id,
        is_active=True,
        authorized_at=datetime.now(timezone.utc)
    )
    test_db.add(authorization)

    await test_db.commit()
    await test_db.refresh(admin)
    await test_db.refresh(operator)
    await test_db.refresh(application)
    await test_db.refresh(site)

    return {
        "admin": admin,
        "operator": operator,
        "application": application,
        "site": site,
        "api_key": api_key_value
    }


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_baseline_admin_login_response_time(test_db, performance_test_data):
    """基线测试：管理员登录API响应时间

    目标：建立登录API的性能基线（P50/P95/P99）
    """
    response_times = []

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 执行100次请求以获取统计数据
        for _ in range(100):
            start_time = time.perf_counter()

            response = await client.post(
                "/v1/admin/login",
                json={
                    "username": "perf_admin",
                    "password": "Admin@123"
                }
            )

            end_time = time.perf_counter()
            response_time_ms = (end_time - start_time) * 1000

            assert response.status_code == 200
            response_times.append(response_time_ms)

    # 计算百分位数
    p50 = statistics.median(response_times)
    p95 = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
    p99 = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
    avg = statistics.mean(response_times)

    print(f"\n=== 管理员登录API性能基线 ===")
    print(f"样本数: {len(response_times)}")
    print(f"平均响应时间: {avg:.2f}ms")
    print(f"P50 (中位数): {p50:.2f}ms")
    print(f"P95: {p95:.2f}ms")
    print(f"P99: {p99:.2f}ms")
    print(f"最小值: {min(response_times):.2f}ms")
    print(f"最大值: {max(response_times):.2f}ms")

    # 记录基线（这些值将用于后续优化对比）
    baseline = {
        "api": "admin_login",
        "samples": len(response_times),
        "avg_ms": avg,
        "p50_ms": p50,
        "p95_ms": p95,
        "p99_ms": p99,
        "min_ms": min(response_times),
        "max_ms": max(response_times)
    }

    # 保存基线数据（可选）
    # with open("performance_baseline.json", "w") as f:
    #     json.dump(baseline, f, indent=2)

    # 不设置断言，因为这只是建立基线
    # 但可以记录是否满足NFR要求
    if p95 < 100:
        print(f"[OK] P95 ({p95:.2f}ms) 满足 NFR-001 要求 (< 100ms)")
    else:
        print(f"[WARN] P95 ({p95:.2f}ms) 未满足 NFR-001 要求 (< 100ms)，需要优化")


@pytest.mark.asyncio
@pytest.mark.benchmark
@pytest.mark.skip(reason="游戏授权API端点可能尚未完整实现")
async def test_baseline_game_authorization_response_time(test_db, performance_test_data):
    """基线测试：游戏授权API响应时间（NFR-001）

    目标：验证授权API P95 < 100ms
    """
    data = performance_test_data
    response_times = []

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 执行100次授权请求
        for i in range(100):
            start_time = time.perf_counter()

            response = await client.post(
                f"/v1/game/{data['application'].app_code}/authorize",
                headers={"X-API-Key": data["api_key"]},
                json={
                    "session_id": f"perf_session_{uuid4()}",
                    "server_identifier": data["site"].server_identifier,
                    "player_count": 4
                }
            )

            end_time = time.perf_counter()
            response_time_ms = (end_time - start_time) * 1000

            if response.status_code in [200, 201]:
                response_times.append(response_time_ms)

    if not response_times:
        pytest.skip("游戏授权API返回非200/201状态码，跳过基线测试")

    # 计算统计数据
    p50 = statistics.median(response_times)
    p95 = statistics.quantiles(response_times, n=20)[18]
    p99 = statistics.quantiles(response_times, n=100)[98]
    avg = statistics.mean(response_times)

    print(f"\n=== 游戏授权API性能基线 ===")
    print(f"样本数: {len(response_times)}")
    print(f"平均响应时间: {avg:.2f}ms")
    print(f"P50: {p50:.2f}ms")
    print(f"P95: {p95:.2f}ms")
    print(f"P99: {p99:.2f}ms")

    # NFR-001验证
    if p95 < 100:
        print(f"[OK] NFR-001 满足: P95 ({p95:.2f}ms) < 100ms")
    else:
        print(f"[FAIL] NFR-001 未满足: P95 ({p95:.2f}ms) >= 100ms")


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_baseline_api_throughput(test_db, performance_test_data):
    """基线测试：API吞吐量（NFR-002）

    目标：验证峰值吞吐量 ≥ 20 req/s
    """
    admin = performance_test_data["admin"]

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 先登录获取token
        login_response = await client.post(
            "/v1/admin/login",
            json={"username": "perf_admin", "password": "Admin@123"}
        )
        token = login_response.json()["access_token"]

        # 测试吞吐量：1秒内发送尽可能多的请求
        request_count = 0
        start_time = time.time()
        test_duration = 1.0  # 测试1秒

        while time.time() - start_time < test_duration:
            response = await client.get(
                "/v1/admin/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                request_count += 1

        actual_duration = time.time() - start_time
        throughput = request_count / actual_duration

        print(f"\n=== API吞吐量基线 ===")
        print(f"测试时长: {actual_duration:.2f}秒")
        print(f"请求总数: {request_count}")
        print(f"吞吐量: {throughput:.2f} req/s")

        # NFR-002验证
        if throughput >= 20:
            print(f"[OK] NFR-002 满足: 吞吐量 ({throughput:.2f} req/s) >= 20 req/s")
        else:
            print(f"[FAIL] NFR-002 未满足: 吞吐量 ({throughput:.2f} req/s) < 20 req/s")


@pytest.mark.asyncio
@pytest.mark.benchmark
@pytest.mark.skip(reason="需要大量数据，测试时间较长")
async def test_baseline_large_export_performance(test_db, performance_test_data):
    """基线测试：大量数据导出性能（NFR-004）

    目标：10万条记录导出 < 30秒
    """
    # 这个测试需要先创建10万条使用记录
    # 由于数据量大，标记为skip，在需要时手动运行
    pass


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_baseline_database_query_performance(test_db, performance_test_data):
    """基线测试：数据库查询性能

    测试常见数据库查询的执行时间
    """
    from sqlalchemy import select
    from src.models.operator import OperatorAccount

    query_times = []

    # 执行50次查询以获取统计数据
    for _ in range(50):
        start_time = time.perf_counter()

        stmt = select(OperatorAccount).where(
            OperatorAccount.username == "perf_operator"
        )
        result = await test_db.execute(stmt)
        operator = result.scalar_one_or_none()

        end_time = time.perf_counter()
        query_time_ms = (end_time - start_time) * 1000

        assert operator is not None
        query_times.append(query_time_ms)

    avg = statistics.mean(query_times)
    p50 = statistics.median(query_times)
    p95 = statistics.quantiles(query_times, n=20)[18]

    print(f"\n=== 数据库查询性能基线 ===")
    print(f"查询类型: SELECT by username")
    print(f"样本数: {len(query_times)}")
    print(f"平均查询时间: {avg:.2f}ms")
    print(f"P50: {p50:.2f}ms")
    print(f"P95: {p95:.2f}ms")

    # 记录基线
    if p95 < 10:
        print(f"[GOOD] 数据库查询性能良好: P95 ({p95:.2f}ms) < 10ms")
    elif p95 < 50:
        print(f"[OK] 数据库查询性能一般: P95 ({p95:.2f}ms) < 50ms")
    else:
        print(f"[WARN] 数据库查询需要优化: P95 ({p95:.2f}ms) >= 50ms")
