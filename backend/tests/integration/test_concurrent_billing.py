"""集成测试：并发扣费冲突处理 (T034)

测试并发场景下的余额扣费安全性:
1. 使用行级锁(SELECT FOR UPDATE)防止并发扣费冲突
2. 多个并发请求扣费,余额计算正确
3. 不会出现超额扣费(余额为负)
4. 最后一笔可能因余额不足失败
5. 事务隔离性保证

测试方法:
- 使用asyncio.gather模拟并发请求
- 验证最终余额正确
- 验证成功/失败请求数量合理
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from fastapi import status

from src.main import app
from src.models.admin import AdminAccount
from src.models.operator import OperatorAccount
from src.models.application import Application
from src.models.site import OperationSite
from src.models.authorization import OperatorAppAuthorization
from src.models.usage_record import UsageRecord
from src.models.transaction import TransactionRecord


@pytest.fixture
async def concurrent_test_data(test_db):
    """准备并发测试数据"""
    # 创建管理员
    admin = AdminAccount(
        username="admin_concurrent",
        password_hash="hashed_pw",
        full_name="Test Admin",
        email="admin@test.com",
        phone="13800138000",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    await test_db.flush()

    # 创建运营商 - 余额限制为测试并发冲突
    operator = OperatorAccount(
        username="op_concurrent_001",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="l" * 64,
        api_key_hash="hashed_secret",
        balance=Decimal("100.00"),  # 只能支付2次(2 × 50 = 100)
        customer_tier="standard",
        is_active=True,
        is_locked=False,
        created_by=admin.id
    )
    test_db.add(operator)
    await test_db.flush()

    # 创建运营点
    site = OperationSite(
        operator_id=operator.id,
        name="并发测试运营点",
        address="测试地址",
        server_identifier="server_concurrent_001",
        is_active=True
    )
    test_db.add(site)
    await test_db.flush()

    # 创建应用
    application = Application(
        app_code="app_concurrent_001",
        app_name="并发测试游戏",
        price_per_player=Decimal("10.00"),
        min_players=2,
        max_players=8,
        is_active=True,
        created_by=admin.id
    )
    test_db.add(application)
    await test_db.flush()

    # 创建授权关系
    authorization = OperatorAppAuthorization(
        operator_id=operator.id,
        application_id=application.id,
        authorized_by=admin.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )
    test_db.add(authorization)
    await test_db.commit()

    return {
        "admin": admin,
        "operator": operator,
        "site": site,
        "application": application,
        "authorization": authorization
    }


async def make_authorization_request(
    operator_api_key: str,
    app_id: str,
    site_id: str,
    player_count: int,
    session_id: str,
    base_url: str = "http://test"
) -> dict:
    """发起单个授权请求"""
    current_timestamp = int(datetime.utcnow().timestamp())

    async with AsyncClient(app=app, base_url=base_url) as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": app_id,
                "site_id": site_id,
                "player_count": player_count
            },
            headers={
                "X-API-Key": operator_api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id
            }
        )

    return {
        "status_code": response.status_code,
        "session_id": session_id,
        "response": response.json() if response.status_code in [200, 400, 402] else None
    }


@pytest.mark.asyncio
async def test_concurrent_requests_balance_correctness(concurrent_test_data, test_db):
    """测试并发请求余额计算正确

    场景:
    - 初始余额: 100元
    - 3个并发请求,每个50元
    - 只有2个能成功(100 / 50 = 2)
    - 最终余额: 0元
    - 验证没有超额扣费(余额不为负)
    """
    operator = concurrent_test_data["operator"]
    site = concurrent_test_data["site"]
    application = concurrent_test_data["application"]

    initial_balance = operator.balance  # 100元

    current_timestamp = int(datetime.utcnow().timestamp())

    # 创建3个并发请求
    tasks = []
    for i in range(3):
        session_id = f"{operator.id}_{current_timestamp}_{i:016d}"
        tasks.append(
            make_authorization_request(
                operator_api_key=operator.api_key,
                app_id=str(application.id),
                site_id=str(site.id),
                player_count=5,  # 50元
                session_id=session_id
            )
        )

    # 并发执行
    results = await asyncio.gather(*tasks)

    # 统计结果
    success_count = sum(1 for r in results if r["status_code"] == 200)
    insufficient_balance_count = sum(1 for r in results if r["status_code"] == 402)

    # 验证: 只有2个成功,1个因余额不足失败
    assert success_count == 2, f"应该有2个请求成功,实际: {success_count}"
    assert insufficient_balance_count == 1, f"应该有1个请求因余额不足失败,实际: {insufficient_balance_count}"

    # 验证最终余额
    await test_db.refresh(operator)
    final_balance = operator.balance

    assert final_balance == Decimal("0.00"), \
        f"最终余额应为0元,实际: {final_balance}"

    # 验证没有超额扣费
    assert final_balance >= Decimal("0.00"), \
        f"余额不应为负,实际: {final_balance}"


@pytest.mark.asyncio
async def test_concurrent_requests_no_negative_balance(concurrent_test_data, test_db):
    """测试并发请求不会导致余额为负

    场景:
    - 初始余额: 100元
    - 10个并发请求,每个50元
    - 只有2个能成功
    - 其余8个因余额不足失败
    - 验证余额始终 >= 0
    """
    operator = concurrent_test_data["operator"]
    site = concurrent_test_data["site"]
    application = concurrent_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())

    # 创建10个并发请求
    tasks = []
    for i in range(10):
        session_id = f"{operator.id}_{current_timestamp}_{'n' * 15}{i}"
        tasks.append(
            make_authorization_request(
                operator_api_key=operator.api_key,
                app_id=str(application.id),
                site_id=str(site.id),
                player_count=5,  # 50元
                session_id=session_id
            )
        )

    # 并发执行
    results = await asyncio.gather(*tasks)

    # 统计结果
    success_count = sum(1 for r in results if r["status_code"] == 200)
    failed_count = sum(1 for r in results if r["status_code"] == 402)

    # 验证
    assert success_count == 2, f"应该有2个请求成功,实际: {success_count}"
    assert failed_count == 8, f"应该有8个请求失败,实际: {failed_count}"

    # 验证余额为0且不为负
    await test_db.refresh(operator)
    assert operator.balance == Decimal("0.00")
    assert operator.balance >= Decimal("0.00"), "余额不应为负"


@pytest.mark.asyncio
async def test_concurrent_requests_transaction_records_count(concurrent_test_data, test_db):
    """测试并发请求创建正确数量的交易记录

    验证:
    - 只有成功的请求创建交易记录
    - 失败的请求不创建交易记录
    """
    operator = concurrent_test_data["operator"]
    site = concurrent_test_data["site"]
    application = concurrent_test_data["application"]

    # 记录初始交易记录数量
    stmt = select(TransactionRecord).where(
        TransactionRecord.operator_id == operator.id,
        TransactionRecord.transaction_type == "consumption"
    )
    result = await test_db.execute(stmt)
    initial_transaction_count = len(result.scalars().all())

    current_timestamp = int(datetime.utcnow().timestamp())

    # 创建5个并发请求
    tasks = []
    for i in range(5):
        session_id = f"{operator.id}_{current_timestamp}_{'o' * 15}{i}"
        tasks.append(
            make_authorization_request(
                operator_api_key=operator.api_key,
                app_id=str(application.id),
                site_id=str(site.id),
                player_count=5,  # 50元
                session_id=session_id
            )
        )

    # 并发执行
    results = await asyncio.gather(*tasks)

    success_count = sum(1 for r in results if r["status_code"] == 200)

    # 查询最终交易记录数量
    result = await test_db.execute(stmt)
    final_transaction_count = len(result.scalars().all())

    # 验证交易记录数量增加等于成功请求数
    new_transaction_count = final_transaction_count - initial_transaction_count
    assert new_transaction_count == success_count, \
        f"新增交易记录数({new_transaction_count})应等于成功请求数({success_count})"


@pytest.mark.asyncio
async def test_concurrent_requests_usage_records_count(concurrent_test_data, test_db):
    """测试并发请求创建正确数量的使用记录

    验证:
    - 只有成功的请求创建使用记录
    - 失败的请求不创建使用记录
    """
    operator = concurrent_test_data["operator"]
    site = concurrent_test_data["site"]
    application = concurrent_test_data["application"]

    # 记录初始使用记录数量
    stmt = select(UsageRecord).where(UsageRecord.operator_id == operator.id)
    result = await test_db.execute(stmt)
    initial_usage_count = len(result.scalars().all())

    current_timestamp = int(datetime.utcnow().timestamp())

    # 创建5个并发请求
    tasks = []
    for i in range(5):
        session_id = f"{operator.id}_{current_timestamp}_{'p' * 15}{i}"
        tasks.append(
            make_authorization_request(
                operator_api_key=operator.api_key,
                app_id=str(application.id),
                site_id=str(site.id),
                player_count=5,
                session_id=session_id
            )
        )

    # 并发执行
    results = await asyncio.gather(*tasks)

    success_count = sum(1 for r in results if r["status_code"] == 200)

    # 查询最终使用记录数量
    result = await test_db.execute(stmt)
    final_usage_count = len(result.scalars().all())

    # 验证使用记录数量增加等于成功请求数
    new_usage_count = final_usage_count - initial_usage_count
    assert new_usage_count == success_count, \
        f"新增使用记录数({new_usage_count})应等于成功请求数({success_count})"


@pytest.mark.asyncio
async def test_sequential_requests_all_succeed(concurrent_test_data, test_db):
    """对比测试：顺序请求全部成功

    场景:
    - 初始余额: 100元
    - 2个顺序请求,每个50元
    - 全部应该成功
    - 最终余额: 0元
    """
    operator = concurrent_test_data["operator"]
    site = concurrent_test_data["site"]
    application = concurrent_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())

    # 第一个请求
    session_id_1 = f"{operator.id}_{current_timestamp}_{'q' * 16}"
    result_1 = await make_authorization_request(
        operator_api_key=operator.api_key,
        app_id=str(application.id),
        site_id=str(site.id),
        player_count=5,
        session_id=session_id_1
    )

    assert result_1["status_code"] == 200

    # 第二个请求
    session_id_2 = f"{operator.id}_{current_timestamp}_{'r' * 16}"
    result_2 = await make_authorization_request(
        operator_api_key=operator.api_key,
        app_id=str(application.id),
        site_id=str(site.id),
        player_count=5,
        session_id=session_id_2
    )

    assert result_2["status_code"] == 200

    # 验证最终余额
    await test_db.refresh(operator)
    assert operator.balance == Decimal("0.00")


@pytest.mark.asyncio
async def test_concurrent_mixed_amounts(test_db):
    """测试并发请求不同金额

    场景:
    - 初始余额: 100元
    - 请求1: 20元 (2人 × 10元)
    - 请求2: 30元 (3人 × 10元)
    - 请求3: 40元 (4人 × 10元)
    - 请求4: 50元 (5人 × 10元)
    - 总需求: 140元,但只有100元
    - 验证扣费顺序合理,不会超额
    """
    # 创建测试数据
    admin = AdminAccount(
        username="admin_mixed",
        password_hash="hashed_pw",
        full_name="Test Admin",
        email="admin@test.com",
        phone="13800138000",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    await test_db.flush()

    operator = OperatorAccount(
        username="op_mixed_001",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="m" * 64,
        api_key_hash="hashed_secret",
        balance=Decimal("100.00"),
        customer_tier="standard",
        is_active=True,
        is_locked=False,
        created_by=admin.id
    )
    test_db.add(operator)
    await test_db.flush()

    site = OperationSite(
        operator_id=operator.id,
        name="混合金额测试运营点",
        address="测试地址",
        server_identifier="server_mixed_001",
        is_active=True
    )
    test_db.add(site)
    await test_db.flush()

    application = Application(
        app_code="app_mixed_001",
        app_name="混合金额测试游戏",
        price_per_player=Decimal("10.00"),
        min_players=2,
        max_players=8,
        is_active=True,
        created_by=admin.id
    )
    test_db.add(application)
    await test_db.flush()

    authorization = OperatorAppAuthorization(
        operator_id=operator.id,
        application_id=application.id,
        authorized_by=admin.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )
    test_db.add(authorization)
    await test_db.commit()

    current_timestamp = int(datetime.utcnow().timestamp())

    # 创建不同金额的并发请求
    tasks = [
        make_authorization_request(
            operator.api_key, str(application.id), str(site.id), 2,
            f"{operator.id}_{current_timestamp}_{'s' * 16}"  # 20元
        ),
        make_authorization_request(
            operator.api_key, str(application.id), str(site.id), 3,
            f"{operator.id}_{current_timestamp}_{'t' * 16}"  # 30元
        ),
        make_authorization_request(
            operator.api_key, str(application.id), str(site.id), 4,
            f"{operator.id}_{current_timestamp}_{'u' * 16}"  # 40元
        ),
        make_authorization_request(
            operator.api_key, str(application.id), str(site.id), 5,
            f"{operator.id}_{current_timestamp}_{'v' * 16}"  # 50元
        ),
    ]

    # 并发执行
    results = await asyncio.gather(*tasks)

    # 统计结果
    success_count = sum(1 for r in results if r["status_code"] == 200)
    failed_count = sum(1 for r in results if r["status_code"] == 402)

    # 验证至少有2个成功(20+30=50, 或20+40=60, 或其他组合)
    assert success_count >= 2, f"至少应有2个请求成功,实际: {success_count}"

    # 计算成功请求的总金额
    total_charged = sum(
        Decimal(r["response"]["data"]["total_cost"])
        for r in results
        if r["status_code"] == 200 and r["response"] is not None
    )

    # 验证总扣费不超过初始余额
    assert total_charged <= Decimal("100.00"), \
        f"总扣费({total_charged})不应超过初始余额(100.00)"

    # 验证最终余额
    await test_db.refresh(operator)
    expected_balance = Decimal("100.00") - total_charged
    assert operator.balance == expected_balance, \
        f"最终余额应为{expected_balance},实际: {operator.balance}"

    # 验证余额不为负
    assert operator.balance >= Decimal("0.00"), "余额不应为负"


@pytest.mark.asyncio
async def test_concurrent_same_session_id_idempotency(concurrent_test_data, test_db):
    """测试并发相同会话ID的幂等性保护

    场景:
    - 5个并发请求使用相同的会话ID
    - 只应创建1条使用记录
    - 只扣费1次(50元)
    - 验证幂等性保护在并发场景下有效
    """
    operator = concurrent_test_data["operator"]
    site = concurrent_test_data["site"]
    application = concurrent_test_data["application"]

    initial_balance = operator.balance

    current_timestamp = int(datetime.utcnow().timestamp())
    same_session_id = f"{operator.id}_{current_timestamp}_{'w' * 16}"

    # 创建5个使用相同会话ID的并发请求
    tasks = []
    for i in range(5):
        tasks.append(
            make_authorization_request(
                operator_api_key=operator.api_key,
                app_id=str(application.id),
                site_id=str(site.id),
                player_count=5,
                session_id=same_session_id  # 相同会话ID
            )
        )

    # 并发执行
    results = await asyncio.gather(*tasks)

    # 验证所有请求都返回成功或冲突状态
    for result in results:
        assert result["status_code"] in [200, 409], \
            f"相同会话ID应返回200或409,实际: {result['status_code']}"

    # 验证只扣费1次
    await test_db.refresh(operator)
    expected_balance = initial_balance - Decimal("50.00")
    assert operator.balance == expected_balance, \
        f"相同会话ID只应扣费1次,余额应为{expected_balance},实际: {operator.balance}"

    # 验证只创建1条使用记录
    stmt = select(UsageRecord).where(UsageRecord.session_id == same_session_id)
    result = await test_db.execute(stmt)
    usage_records = result.scalars().all()

    assert len(usage_records) == 1, \
        f"相同会话ID只应创建1条使用记录,实际创建了{len(usage_records)}条"
