"""单元测试：IPMonitorService (T278b)

测试IP检测规则引擎的核心逻辑：
1. 失败计数器功能
2. API Key追踪功能
3. 锁定触发逻辑
4. 时间窗口自动清理
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
import time

from src.services.security.ip_monitor import IPActivityTracker, IPMonitorService
from src.models.operator import OperatorAccount
from src.models.admin import AdminAccount
from src.core.utils.password import hash_password


@pytest.fixture
def tracker():
    """创建独立的跟踪器实例（用于测试）"""
    return IPActivityTracker()


@pytest.fixture
async def test_operator_for_ip_monitor(test_db):
    """创建测试运营商"""
    operator = OperatorAccount(
        id=uuid4(),
        username=f"ip_test_op_{uuid4().hex[:8]}",
        password_hash=hash_password("Pass123"),
        full_name="IP监控测试运营商",
        phone="13800138000",
        email=f"ip_test_{uuid4().hex[:8]}@test.com",
        api_key=f"api_key_{uuid4().hex}",
        api_key_hash=hash_password(f"api_key_{uuid4().hex}"),
        balance=1000.00,
        customer_tier="standard",
        is_active=True,
        is_locked=False
    )
    test_db.add(operator)
    await test_db.commit()
    await test_db.refresh(operator)
    return operator


@pytest.fixture
async def test_admin_for_ip_monitor(test_db):
    """创建测试管理员"""
    admin = AdminAccount(
        id=uuid4(),
        username=f"ip_test_admin_{uuid4().hex[:8]}",
        password_hash=hash_password("AdminPass123"),
        full_name="IP监控测试管理员",
        email=f"ip_admin_{uuid4().hex[:8]}@test.com",
        phone="13900139000",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


# ==================== IPActivityTracker 单元测试 ====================

def test_tracker_record_single_failure(tracker):
    """测试记录单次失败"""
    ip = "192.168.1.100"

    count = tracker.record_failure(ip)

    assert count == 1
    assert len(tracker.failure_timestamps[ip]) == 1


def test_tracker_record_multiple_failures(tracker):
    """测试记录多次失败"""
    ip = "192.168.1.100"

    for i in range(5):
        count = tracker.record_failure(ip)

    assert count == 5
    assert len(tracker.failure_timestamps[ip]) == 5


def test_tracker_failure_window_cleanup(tracker):
    """测试5分钟时间窗口自动清理"""
    ip = "192.168.1.100"

    # 模拟5分钟前的失败（手动插入旧时间戳）
    old_time = datetime.now(timezone.utc) - timedelta(minutes=6)
    tracker.failure_timestamps[ip].append(old_time)

    # 记录新失败，应该清理旧记录
    count = tracker.record_failure(ip)

    assert count == 1  # 只剩新记录
    assert len(tracker.failure_timestamps[ip]) == 1


def test_tracker_record_api_key_usage(tracker):
    """测试记录API Key使用"""
    ip = "192.168.1.100"
    api_key = "test_api_key_12345678"

    count = tracker.record_api_key_usage(ip, api_key)

    assert count == 1
    assert len(tracker.api_key_usage[ip]) == 1


def test_tracker_record_multiple_api_keys(tracker):
    """测试记录多个不同API Key"""
    ip = "192.168.1.100"

    # 使用前8位不同的key
    keys = [f"key{i:05d}_rest" for i in range(7)]
    for key in keys:
        count = tracker.record_api_key_usage(ip, key)

    assert count == 7
    # 验证存储的是前8位
    stored_keys = {key for key, _ in tracker.api_key_usage[ip]}
    assert len(stored_keys) == 7


def test_tracker_api_key_deduplication(tracker):
    """测试相同API Key不重复计数"""
    ip = "192.168.1.100"
    api_key = "test_api_key_12345678"

    # 记录同一个API Key 3次
    for _ in range(3):
        tracker.record_api_key_usage(ip, api_key)

    # 应该只计数1个唯一Key（但有3个时间戳记录）
    unique_keys = {key for key, _ in tracker.api_key_usage[ip]}
    assert len(unique_keys) == 1
    assert len(tracker.api_key_usage[ip]) == 3


def test_tracker_api_key_window_cleanup(tracker):
    """测试1分钟时间窗口自动清理"""
    ip = "192.168.1.100"

    # 模拟1分钟前的记录
    old_time = datetime.now(timezone.utc) - timedelta(minutes=2)
    tracker.api_key_usage[ip].append(("old_key", old_time))

    # 记录新API Key，应该清理旧记录
    count = tracker.record_api_key_usage(ip, "new_key_12345678")

    assert count == 1
    stored_keys = {key for key, _ in tracker.api_key_usage[ip]}
    assert "old_key" not in stored_keys
    assert "new_key_" in stored_keys


def test_tracker_associate_operators_with_ip(tracker):
    """测试关联IP和运营商"""
    ip = "192.168.1.100"
    operator_id1 = uuid4()
    operator_id2 = uuid4()

    # 记录失败并关联运营商
    tracker.record_failure(ip, operator_id1)
    tracker.record_failure(ip, operator_id2)

    # 验证关联
    operators = tracker.get_associated_operators(ip)
    assert len(operators) == 2
    assert operator_id1 in operators
    assert operator_id2 in operators


def test_tracker_clear_ip_records(tracker):
    """测试清除IP记录"""
    ip = "192.168.1.100"

    # 添加各种记录
    tracker.record_failure(ip)
    tracker.record_api_key_usage(ip, "test_key_12345678")
    tracker.ip_operators[ip].add(uuid4())

    # 清除记录
    tracker.clear_ip_records(ip)

    # 验证已清除
    assert ip not in tracker.failure_timestamps
    assert ip not in tracker.api_key_usage
    assert ip not in tracker.ip_operators


# ==================== IPMonitorService 单元测试 ====================

@pytest.mark.asyncio
async def test_check_failure_rate_below_threshold(test_db, test_operator_for_ip_monitor):
    """测试失败率低于阈值"""
    service = IPMonitorService(test_db)
    ip = "192.168.1.100"

    # 记录10次失败（低于阈值20）
    for _ in range(10):
        result = await service.check_failure_rate(ip, test_operator_for_ip_monitor.id)

    # 验证未触发异常
    assert result["is_anomaly"] is False
    assert result["failure_count"] == 10
    assert result["locked_operators"] == []


@pytest.mark.asyncio
async def test_check_failure_rate_exceeds_threshold(
    test_db,
    test_operator_for_ip_monitor,
    test_admin_for_ip_monitor
):
    """测试失败率超过阈值触发锁定"""
    service = IPMonitorService(test_db)
    ip = "192.168.1.101"

    # 记录21次失败（超过阈值20）
    for i in range(21):
        result = await service.check_failure_rate(ip, test_operator_for_ip_monitor.id)

    # 验证触发异常
    assert result["is_anomaly"] is True
    assert result["failure_count"] == 21
    assert len(result["locked_operators"]) == 1

    # 验证账户已被锁定
    await test_db.refresh(test_operator_for_ip_monitor)
    assert test_operator_for_ip_monitor.is_locked is True


@pytest.mark.asyncio
async def test_check_api_key_switching_below_threshold(test_db, test_operator_for_ip_monitor):
    """测试API Key切换低于阈值"""
    service = IPMonitorService(test_db)
    ip = "192.168.1.102"

    # 使用3个不同API Key（低于阈值5），确保前8位不同
    for i in range(3):
        api_key = f"key{i:05d}_testsuffix"
        result = await service.check_api_key_switching(
            ip, api_key, test_operator_for_ip_monitor.id
        )

    # 验证未触发异常
    assert result["is_anomaly"] is False
    assert result["unique_key_count"] == 3
    assert result["locked_operators"] == []


@pytest.mark.asyncio
async def test_check_api_key_switching_exceeds_threshold(
    test_db,
    test_operator_for_ip_monitor,
    test_admin_for_ip_monitor
):
    """测试API Key切换超过阈值触发锁定"""
    service = IPMonitorService(test_db)
    ip = "192.168.1.103"

    # 使用6个不同API Key（超过阈值5），确保前8位不同
    for i in range(6):
        api_key = f"key{i:05d}_testsuffix"
        result = await service.check_api_key_switching(
            ip, api_key, test_operator_for_ip_monitor.id
        )

    # 验证触发异常
    assert result["is_anomaly"] is True
    assert result["unique_key_count"] == 6
    assert len(result["locked_operators"]) == 1

    # 验证账户已被锁定
    await test_db.refresh(test_operator_for_ip_monitor)
    assert test_operator_for_ip_monitor.is_locked is True


@pytest.mark.asyncio
async def test_unlock_operator(test_db, test_operator_for_ip_monitor):
    """测试解锁运营商账户"""
    service = IPMonitorService(test_db)

    # 先锁定账户
    test_operator_for_ip_monitor.is_locked = True
    test_db.add(test_operator_for_ip_monitor)
    await test_db.commit()

    # 解锁账户
    success = await service.unlock_operator(test_operator_for_ip_monitor.id)

    # 验证解锁成功
    assert success is True
    await test_db.refresh(test_operator_for_ip_monitor)
    assert test_operator_for_ip_monitor.is_locked is False


@pytest.mark.asyncio
async def test_unlock_operator_not_found(test_db):
    """测试解锁不存在的运营商"""
    service = IPMonitorService(test_db)

    # 尝试解锁不存在的运营商
    success = await service.unlock_operator(uuid4())

    # 验证返回False
    assert success is False


@pytest.mark.asyncio
async def test_unlock_already_unlocked_operator(test_db, test_operator_for_ip_monitor):
    """测试解锁已解锁的运营商"""
    service = IPMonitorService(test_db)

    # 账户已经是解锁状态
    assert test_operator_for_ip_monitor.is_locked is False

    # 尝试解锁
    success = await service.unlock_operator(test_operator_for_ip_monitor.id)

    # 验证返回False（因为已经是解锁状态）
    assert success is False


def test_clear_ip_tracking(test_db):
    """测试清除IP跟踪记录"""
    service = IPMonitorService(test_db)
    ip = "192.168.1.104"

    # 添加跟踪记录
    service.tracker.record_failure(ip)
    service.tracker.record_api_key_usage(ip, "test_key_12345678")

    # 清除跟踪
    service.clear_ip_tracking(ip)

    # 验证已清除
    assert ip not in service.tracker.failure_timestamps
    assert ip not in service.tracker.api_key_usage


@pytest.mark.asyncio
async def test_multiple_operators_locked_from_same_ip(
    test_db,
    test_admin_for_ip_monitor
):
    """测试同一IP关联的多个运营商都被锁定"""
    service = IPMonitorService(test_db)
    ip = "192.168.1.105"

    # 创建2个运营商
    operators = []
    for i in range(2):
        operator = OperatorAccount(
            id=uuid4(),
            username=f"multi_op_{i}_{uuid4().hex[:8]}",
            password_hash=hash_password("Pass123"),
            full_name=f"测试运营商{i}",
            phone=f"1380013800{i}",
            email=f"multi_op_{i}_{uuid4().hex[:8]}@test.com",
            api_key=f"api_key_{uuid4().hex}",
            api_key_hash=hash_password(f"api_key_{uuid4().hex}"),
            balance=1000.00,
            customer_tier="standard",
            is_active=True,
            is_locked=False
        )
        test_db.add(operator)
        operators.append(operator)

    await test_db.commit()

    # 触发失败检测（关联两个运营商）
    for _ in range(21):
        await service.check_failure_rate(ip, operators[0].id)
        await service.check_failure_rate(ip, operators[1].id)

    # 验证两个运营商都被锁定
    for operator in operators:
        await test_db.refresh(operator)
        assert operator.is_locked is True
