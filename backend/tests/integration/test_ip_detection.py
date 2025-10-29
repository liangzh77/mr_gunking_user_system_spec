"""集成测试：异常IP检测与锁定 (T278a)

模拟真实的暴力攻击场景，验证IP监控服务能正确：
1. 检测连续失败25次（超过阈值20）
2. 检测切换6个API Key（超过阈值5）
3. 自动锁定关联的运营商账户
4. 发送告警通知
"""

import pytest
from uuid import uuid4
from decimal import Decimal

from src.services.security.ip_monitor import IPMonitorService
from src.models.operator import OperatorAccount
from src.models.admin import AdminAccount
from src.core.utils.password import hash_password


@pytest.fixture
async def ip_test_admin(test_db):
    """创建测试管理员"""
    admin = AdminAccount(
        id=uuid4(),
        username=f"ip_int_admin_{uuid4().hex[:8]}",
        password_hash=hash_password("AdminPass123"),
        full_name="IP集成测试管理员",
        email=f"ip_int_admin_{uuid4().hex[:8]}@test.com",
        phone="13900139000",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


@pytest.fixture
async def ip_test_operators(test_db):
    """创建多个测试运营商"""
    operators = []
    for i in range(3):
        operator = OperatorAccount(
            id=uuid4(),
            username=f"ip_int_op{i}_{uuid4().hex[:8]}",
            password_hash=hash_password("Pass123"),
            full_name=f"IP集成测试运营商{i}",
            phone=f"1380013800{i}",
            email=f"ip_int_op{i}_{uuid4().hex[:8]}@test.com",
            api_key=f"intkey{i:02d}_{uuid4().hex[:20]}",
            api_key_hash=hash_password(f"intkey{i:02d}_{uuid4().hex[:20]}"),
            balance=Decimal("1000.00"),
            customer_tier="standard",
            is_active=True,
            is_locked=False
        )
        test_db.add(operator)
        operators.append(operator)

    await test_db.commit()

    for operator in operators:
        await test_db.refresh(operator)

    return operators


@pytest.mark.asyncio
async def test_continuous_failures_trigger_lockout(test_db, ip_test_admin, ip_test_operators):
    """测试连续失败触发账户锁定（场景1：暴力破解）

    场景：攻击者尝试暴力破解，连续失败25次
    预期：账户被锁定，is_locked=True
    """
    service = IPMonitorService(test_db)
    attacker_ip = "203.0.113.100"  # 测试用IP地址
    target_operator = ip_test_operators[0]

    # 模拟连续失败25次（超过阈值20）
    first_lock_result = None
    for i in range(25):
        result = await service.check_failure_rate(attacker_ip, target_operator.id)

        # 前20次不应触发异常
        if i < 20:
            assert result["is_anomaly"] is False
            assert result["locked_operators"] == []
        # 第21次应触发异常并锁定（记录这次结果）
        elif i == 20:
            assert result["is_anomaly"] is True
            first_lock_result = result
        # 第22次及以后应触发异常但不再锁定（已锁定）
        else:
            assert result["is_anomaly"] is True

    # 验证第21次触发了锁定
    assert first_lock_result is not None
    assert first_lock_result["is_anomaly"] is True
    assert first_lock_result["failure_count"] == 21
    assert len(first_lock_result["locked_operators"]) == 1
    assert str(target_operator.id) in first_lock_result["locked_operators"]

    # 验证账户已被锁定
    await test_db.refresh(target_operator)
    assert target_operator.is_locked is True


@pytest.mark.asyncio
async def test_api_key_switching_trigger_lockout(test_db, ip_test_admin, ip_test_operators):
    """测试API Key快速切换触发账户锁定（场景2：撞库攻击）

    场景：攻击者在1分钟内尝试6个不同的API Key
    预期：账户被锁定，is_locked=True
    """
    service = IPMonitorService(test_db)
    attacker_ip = "203.0.113.101"
    target_operator = ip_test_operators[1]

    # 使用6个不同的API Key（超过阈值5）
    # 每个key前8位不同
    api_keys = [f"atkkey{i:02d}_{uuid4().hex[:20]}" for i in range(6)]

    for i, api_key in enumerate(api_keys):
        result = await service.check_api_key_switching(
            attacker_ip, api_key, target_operator.id
        )

        # 前5次不应触发异常
        if i < 5:
            assert result["is_anomaly"] is False
            assert result["locked_operators"] == []
        # 第6次应触发异常并锁定
        else:
            assert result["is_anomaly"] is True

    # 验证最后一次确实触发了锁定
    assert result["is_anomaly"] is True
    assert result["unique_key_count"] == 6
    assert len(result["locked_operators"]) == 1
    assert str(target_operator.id) in result["locked_operators"]

    # 验证账户已被锁定
    await test_db.refresh(target_operator)
    assert target_operator.is_locked is True


@pytest.mark.asyncio
async def test_multiple_operators_from_same_ip_all_locked(
    test_db,
    ip_test_admin,
    ip_test_operators
):
    """测试同一IP关联的多个运营商都被锁定

    场景：同一IP先后使用不同运营商的凭证，然后触发异常
    预期：所有关联的运营商都被锁定
    """
    service = IPMonitorService(test_db)
    attacker_ip = "203.0.113.102"

    # 前10次失败使用运营商1
    for _ in range(10):
        await service.check_failure_rate(attacker_ip, ip_test_operators[0].id)

    # 中间10次失败使用运营商2
    for _ in range(10):
        await service.check_failure_rate(attacker_ip, ip_test_operators[1].id)

    # 最后6次失败使用运营商3，第21次会触发锁定
    first_lock_result = None
    for i in range(6):
        result = await service.check_failure_rate(attacker_ip, ip_test_operators[2].id)
        if i == 0:  # 第21次总失败（前面20次）
            first_lock_result = result

    # 验证触发异常
    assert first_lock_result is not None
    assert first_lock_result["is_anomaly"] is True
    assert first_lock_result["failure_count"] == 21

    # 验证第一次触发时所有3个运营商都被锁定
    assert len(first_lock_result["locked_operators"]) == 3

    for operator in ip_test_operators[:3]:
        await test_db.refresh(operator)
        assert operator.is_locked is True


@pytest.mark.asyncio
async def test_locked_account_can_be_unlocked(test_db, ip_test_admin, ip_test_operators):
    """测试被锁定的账户可以被管理员解锁

    场景：账户被锁定后，管理员手动解锁
    预期：账户恢复正常，is_locked=False
    """
    service = IPMonitorService(test_db)
    operator = ip_test_operators[0]

    # 先锁定账户
    operator.is_locked = True
    test_db.add(operator)
    await test_db.commit()

    # 验证已锁定
    await test_db.refresh(operator)
    assert operator.is_locked is True

    # 管理员解锁
    success = await service.unlock_operator(operator.id)

    # 验证解锁成功
    assert success is True
    await test_db.refresh(operator)
    assert operator.is_locked is False


@pytest.mark.asyncio
async def test_ip_tracking_can_be_cleared(test_db, ip_test_admin, ip_test_operators):
    """测试IP跟踪记录可以被清除

    场景：管理员清除某个IP的跟踪记录
    预期：该IP的失败计数和API Key记录被清空
    """
    service = IPMonitorService(test_db)
    ip = "203.0.113.103"
    operator = ip_test_operators[0]

    # 记录一些失败和API Key使用
    await service.check_failure_rate(ip, operator.id)
    await service.check_api_key_switching(ip, "testkey_123", operator.id)

    # 验证有记录
    assert len(service.tracker.failure_timestamps[ip]) > 0
    assert len(service.tracker.api_key_usage[ip]) > 0

    # 清除跟踪记录
    service.clear_ip_tracking(ip)

    # 验证记录已清空
    assert ip not in service.tracker.failure_timestamps
    assert ip not in service.tracker.api_key_usage


@pytest.mark.asyncio
async def test_mixed_attack_scenario(test_db, ip_test_admin, ip_test_operators):
    """测试混合攻击场景（同时触发两种检测规则）

    场景：攻击者既连续失败又频繁切换API Key
    预期：任一规则触发都会导致锁定
    """
    service = IPMonitorService(test_db)
    attacker_ip = "203.0.113.104"
    operator = ip_test_operators[0]

    # 先记录15次失败（未触发）
    for _ in range(15):
        await service.check_failure_rate(attacker_ip, operator.id)

    # 然后快速切换6个API Key（触发）
    for i in range(6):
        api_key = f"mixkey{i:02d}_{uuid4().hex[:20]}"
        result = await service.check_api_key_switching(attacker_ip, api_key, operator.id)

    # 验证API Key切换触发了锁定
    assert result["is_anomaly"] is True
    await test_db.refresh(operator)
    assert operator.is_locked is True


@pytest.mark.asyncio
async def test_time_window_expiration(test_db, ip_test_admin, ip_test_operators):
    """测试时间窗口过期后不触发异常

    场景：失败次数虽多，但分散在6分钟以上，不应触发
    预期：不触发异常检测（实际测试中通过模拟时间实现）
    """
    service = IPMonitorService(test_db)
    ip = "203.0.113.105"
    operator = ip_test_operators[0]

    # 记录10次失败
    for _ in range(10):
        await service.check_failure_rate(ip, operator.id)

    # 清空时间戳（模拟时间过期）
    service.tracker.failure_timestamps[ip].clear()

    # 再记录10次失败（新的时间窗口）
    for _ in range(10):
        result = await service.check_failure_rate(ip, operator.id)

    # 验证未触发异常（因为只有10次在当前窗口内）
    assert result["is_anomaly"] is False
    assert result["failure_count"] == 10

    # 验证账户未被锁定
    await test_db.refresh(operator)
    assert operator.is_locked is False


@pytest.mark.asyncio
async def test_already_locked_account_not_locked_again(test_db, ip_test_admin, ip_test_operators):
    """测试已锁定的账户不会重复锁定

    场景：账户已经被锁定，后续异常不再重复锁定
    预期：locked_operators列表为空（因为账户已锁定）
    """
    service = IPMonitorService(test_db)
    ip = "203.0.113.106"
    operator = ip_test_operators[0]

    # 先锁定账户
    operator.is_locked = True
    test_db.add(operator)
    await test_db.commit()

    # 触发失败检测
    for _ in range(25):
        result = await service.check_failure_rate(ip, operator.id)

    # 验证触发了异常，但没有新的锁定操作（因为已经锁定）
    assert result["is_anomaly"] is True
    # locked_operators应该为空，因为运营商已经是锁定状态
    assert result["locked_operators"] == []
