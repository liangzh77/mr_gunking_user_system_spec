"""单元测试：NotificationService (T223)

测试NotificationService的通知推送功能：
1. send_system_announcement - 发送系统公告（所有运营商或指定运营商）
2. send_balance_low_alert - 发送余额不足提醒
3. send_price_change_notification - 发送价格变更通知
4. send_authorization_expiry_alert - 发送授权到期提醒
5. send_custom_notification - 发送自定义通知

测试策略：
- 使用真实数据库会话(test_db fixture)
- 测试通知发送的成功和失败场景
- 验证批量发送的成功/失败计数
- 验证消息内容的正确性
- 验证授权运营商的精准推送
"""

import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from src.services.notification import NotificationService
from src.services.message_service import MessageService
from src.models.operator import OperatorAccount
from src.models.admin import AdminAccount
from src.models.application import Application
from src.models.authorization import OperatorAppAuthorization
from src.core.utils.password import hash_password


@pytest.fixture
async def notification_test_data(test_db):
    """准备NotificationService测试数据"""
    # 创建管理员
    admin = AdminAccount(
        id=uuid4(),
        username=f"notification_admin_{uuid4().hex[:8]}",
        password_hash=hash_password("AdminPass123"),
        full_name="通知测试管理员",
        email=f"notification_admin_{uuid4().hex[:8]}@test.com",
        role="admin",
        is_active=True
    )
    test_db.add(admin)

    # 创建3个运营商
    operators = []
    for i in range(1, 4):
        operator = OperatorAccount(
            id=uuid4(),
            username=f"notification_op{i}_{uuid4().hex[:8]}",
            password_hash=hash_password("Pass123"),
            full_name=f"通知测试运营商{i}",
            phone=f"1380013800{i}",
            email=f"notification_op{i}_{uuid4().hex[:8]}@test.com",
            api_key=f"api_key_{uuid4().hex}",
            api_key_hash=hash_password(f"api_key_{uuid4().hex}"),
            balance=Decimal("500.00") if i <= 2 else Decimal("50.00"),  # op3余额不足
            customer_tier="standard",
            is_active=True
        )
        test_db.add(operator)
        operators.append(operator)

    # 创建应用
    app = Application(
        id=uuid4(),
        app_code=f"APP_{datetime.now().strftime('%Y%m%d')}_{uuid4().hex[:3].upper()}",
        app_name="通知测试应用",
        price_per_player=Decimal("50.00"),
        min_players=2,
        max_players=8,
        is_active=True
    )
    test_db.add(app)

    await test_db.commit()
    await test_db.refresh(admin)
    for op in operators:
        await test_db.refresh(op)
    await test_db.refresh(app)

    # 授权应用给op1和op2（op3未授权）
    auth1 = OperatorAppAuthorization(
        id=uuid4(),
        operator_id=operators[0].id,
        application_id=app.id,
        authorized_by=admin.id,
        authorized_at=datetime.now(timezone.utc),
        is_active=True
    )
    auth2 = OperatorAppAuthorization(
        id=uuid4(),
        operator_id=operators[1].id,
        application_id=app.id,
        authorized_by=admin.id,
        authorized_at=datetime.now(timezone.utc),
        is_active=True
    )
    test_db.add(auth1)
    test_db.add(auth2)

    await test_db.commit()

    return {
        "admin": admin,
        "operators": operators,
        "app": app
    }


@pytest.mark.asyncio
async def test_send_system_announcement_to_all(test_db, notification_test_data):
    """测试发送系统公告给所有运营商"""
    service = NotificationService(test_db)
    message_service = MessageService(test_db)

    result = await service.send_system_announcement(
        title="系统维护通知",
        content="系统将于今晚22:00-23:00进行维护，请合理安排使用时间。",
        importance="high"
    )

    # 验证发送结果
    assert result["success_count"] == 3  # 3个运营商
    assert result["failed_count"] == 0
    assert result["total_count"] == 3

    # 验证每个运营商都收到了消息
    operators = notification_test_data["operators"]
    for operator in operators:
        messages, total = await message_service.get_messages(operator_id=operator.id)
        assert total == 1
        assert messages[0].title == "系统维护通知"
        assert messages[0].message_type == "system_announcement"


@pytest.mark.asyncio
async def test_send_system_announcement_to_specific_operators(test_db, notification_test_data):
    """测试发送系统公告给指定运营商"""
    service = NotificationService(test_db)
    message_service = MessageService(test_db)
    operators = notification_test_data["operators"]

    # 只发送给op1和op2
    target_operator_ids = [operators[0].id, operators[1].id]

    result = await service.send_system_announcement(
        title="VIP客户专属通知",
        content="感谢您的支持，您已成为VIP客户。",
        importance="normal",
        operator_ids=target_operator_ids
    )

    # 验证发送结果
    assert result["success_count"] == 2
    assert result["failed_count"] == 0
    assert result["total_count"] == 2

    # 验证op1和op2收到了消息
    for i in range(2):
        messages, total = await message_service.get_messages(operator_id=operators[i].id)
        assert total == 1
        assert messages[0].title == "VIP客户专属通知"

    # 验证op3没有收到消息
    op3_messages, op3_total = await message_service.get_messages(operator_id=operators[2].id)
    assert op3_total == 0


@pytest.mark.asyncio
async def test_send_balance_low_alert(test_db, notification_test_data):
    """测试发送余额不足提醒"""
    service = NotificationService(test_db)
    message_service = MessageService(test_db)
    operator = notification_test_data["operators"][2]  # op3余额不足

    await service.send_balance_low_alert(
        operator_id=operator.id,
        current_balance=Decimal("50.00"),
        threshold=Decimal("100.00")
    )

    # 验证消息创建成功
    messages, total = await message_service.get_messages(operator_id=operator.id)
    assert total == 1
    assert messages[0].title == "余额不足提醒"
    assert messages[0].message_type == "balance_low"
    assert "当前余额: ¥50.00" in messages[0].content
    assert "预警阈值: ¥100.00" in messages[0].content


@pytest.mark.asyncio
async def test_send_price_change_notification_to_authorized_operators(test_db, notification_test_data):
    """测试发送价格变更通知给授权运营商"""
    service = NotificationService(test_db)
    message_service = MessageService(test_db)
    operators = notification_test_data["operators"]
    app = notification_test_data["app"]

    result = await service.send_price_change_notification(
        application_id=app.id,
        app_name=app.app_name,
        old_price=Decimal("50.00"),
        new_price=Decimal("60.00")
    )

    # 验证发送结果（只发送给授权的op1和op2）
    assert result["success_count"] == 2
    assert result["failed_count"] == 0
    assert result["total_count"] == 2

    # 验证op1和op2收到了通知
    for i in range(2):
        messages, total = await message_service.get_messages(operator_id=operators[i].id)
        assert total == 1
        assert "价格调整通知" in messages[0].title
        assert app.app_name in messages[0].title
        assert "原价格: ¥50.00/人" in messages[0].content
        assert "新价格: ¥60.00/人" in messages[0].content
        assert "价格上调" in messages[0].content
        assert messages[0].message_type == "price_change"
        assert messages[0].related_type == "application"
        assert messages[0].related_id == app.id

    # 验证op3未授权，未收到通知
    op3_messages, op3_total = await message_service.get_messages(operator_id=operators[2].id)
    assert op3_total == 0


@pytest.mark.asyncio
async def test_send_price_change_notification_price_decrease(test_db, notification_test_data):
    """测试价格下调通知"""
    service = NotificationService(test_db)
    message_service = MessageService(test_db)
    operators = notification_test_data["operators"]
    app = notification_test_data["app"]

    result = await service.send_price_change_notification(
        application_id=app.id,
        app_name=app.app_name,
        old_price=Decimal("60.00"),
        new_price=Decimal("45.00")
    )

    assert result["success_count"] == 2

    # 验证op1收到价格下调通知
    messages, total = await message_service.get_messages(operator_id=operators[0].id)
    assert total == 1
    assert "原价格: ¥60.00/人" in messages[0].content
    assert "新价格: ¥45.00/人" in messages[0].content
    assert "价格下调" in messages[0].content


@pytest.mark.asyncio
async def test_send_price_change_notification_no_authorized_operators(test_db, notification_test_data):
    """测试发送价格变更通知（无授权运营商）"""
    service = NotificationService(test_db)

    # 创建一个未授权给任何运营商的应用
    app = Application(
        id=uuid4(),
        app_code=f"APP_{datetime.now().strftime('%Y%m%d')}_{uuid4().hex[:3].upper()}",
        app_name="未授权应用",
        price_per_player=Decimal("30.00"),
        min_players=2,
        max_players=8,
        is_active=True
    )
    test_db.add(app)
    await test_db.commit()
    await test_db.refresh(app)

    result = await service.send_price_change_notification(
        application_id=app.id,
        app_name=app.app_name,
        old_price=Decimal("30.00"),
        new_price=Decimal("35.00")
    )

    # 验证无运营商收到通知
    assert result["success_count"] == 0
    assert result["failed_count"] == 0
    assert result["total_count"] == 0


@pytest.mark.asyncio
async def test_send_authorization_expiry_alert(test_db, notification_test_data):
    """测试发送授权到期提醒"""
    service = NotificationService(test_db)
    message_service = MessageService(test_db)
    operator = notification_test_data["operators"][0]
    app = notification_test_data["app"]

    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    await service.send_authorization_expiry_alert(
        operator_id=operator.id,
        app_name=app.app_name,
        expires_at=expires_at,
        days_remaining=7
    )

    # 验证消息创建成功
    messages, total = await message_service.get_messages(operator_id=operator.id)
    assert total == 1
    assert f"应用授权即将到期 - {app.app_name}" == messages[0].title
    assert messages[0].message_type == "authorization_expiry"
    assert "剩余天数: 7天" in messages[0].content
    assert app.app_name in messages[0].content


@pytest.mark.asyncio
async def test_send_custom_notification_success(test_db, notification_test_data):
    """测试发送自定义通知"""
    service = NotificationService(test_db)
    message_service = MessageService(test_db)
    operators = notification_test_data["operators"]

    # 发送自定义通知给op1和op2
    target_operator_ids = [operators[0].id, operators[1].id]

    result = await service.send_custom_notification(
        operator_ids=target_operator_ids,
        message_type="custom_promotion",
        title="限时优惠活动",
        content="本月充值满1000元，赠送100元余额！",
        related_type="promotion",
        related_id=uuid4()
    )

    # 验证发送结果
    assert result["success_count"] == 2
    assert result["failed_count"] == 0
    assert result["total_count"] == 2

    # 验证op1和op2收到了通知
    for i in range(2):
        messages, total = await message_service.get_messages(operator_id=operators[i].id)
        assert total == 1
        assert messages[0].title == "限时优惠活动"
        assert messages[0].message_type == "custom_promotion"
        assert messages[0].content == "本月充值满1000元，赠送100元余额！"
        assert messages[0].related_type == "promotion"

    # 验证op3未收到通知
    op3_messages, op3_total = await message_service.get_messages(operator_id=operators[2].id)
    assert op3_total == 0


@pytest.mark.asyncio
async def test_send_custom_notification_empty_list(test_db, notification_test_data):
    """测试发送自定义通知给空列表"""
    service = NotificationService(test_db)

    result = await service.send_custom_notification(
        operator_ids=[],
        message_type="test",
        title="测试标题",
        content="测试内容"
    )

    # 验证无通知发送
    assert result["success_count"] == 0
    assert result["failed_count"] == 0
    assert result["total_count"] == 0


@pytest.mark.asyncio
async def test_send_custom_notification_with_invalid_operator(test_db, notification_test_data):
    """测试发送自定义通知包含无效运营商ID"""
    service = NotificationService(test_db)
    operators = notification_test_data["operators"]

    # 包含一个有效ID和一个无效ID
    target_operator_ids = [operators[0].id, uuid4()]

    result = await service.send_custom_notification(
        operator_ids=target_operator_ids,
        message_type="test",
        title="测试标题",
        content="测试内容"
    )

    # 验证结果（一个成功，一个失败）
    assert result["success_count"] == 1
    assert result["failed_count"] == 1
    assert result["total_count"] == 2


@pytest.mark.asyncio
async def test_multiple_notifications_to_same_operator(test_db, notification_test_data):
    """测试同一运营商接收多条不同类型的通知"""
    service = NotificationService(test_db)
    message_service = MessageService(test_db)
    operator = notification_test_data["operators"][0]
    app = notification_test_data["app"]

    # 发送多种类型的通知
    # 1. 系统公告
    await service.send_system_announcement(
        title="系统公告",
        content="公告内容",
        operator_ids=[operator.id]
    )

    # 2. 余额提醒
    await service.send_balance_low_alert(
        operator_id=operator.id,
        current_balance=Decimal("80.00"),
        threshold=Decimal("100.00")
    )

    # 3. 价格变更通知
    await service.send_price_change_notification(
        application_id=app.id,
        app_name=app.app_name,
        old_price=Decimal("50.00"),
        new_price=Decimal("55.00")
    )

    # 4. 授权到期提醒
    expires_at = datetime.now(timezone.utc) + timedelta(days=3)
    await service.send_authorization_expiry_alert(
        operator_id=operator.id,
        app_name=app.app_name,
        expires_at=expires_at,
        days_remaining=3
    )

    # 5. 自定义通知
    await service.send_custom_notification(
        operator_ids=[operator.id],
        message_type="custom",
        title="自定义通知",
        content="自定义内容"
    )

    # 验证运营商收到5条消息
    messages, total = await message_service.get_messages(operator_id=operator.id)
    assert total == 5

    # 验证消息类型
    message_types = [msg.message_type for msg in messages]
    assert "system_announcement" in message_types
    assert "balance_low" in message_types
    assert "price_change" in message_types
    assert "authorization_expiry" in message_types
    assert "custom" in message_types


@pytest.mark.asyncio
async def test_notification_message_isolation(test_db, notification_test_data):
    """测试通知消息的运营商隔离"""
    service = NotificationService(test_db)
    message_service = MessageService(test_db)
    operators = notification_test_data["operators"]

    # 给不同运营商发送不同通知
    await service.send_system_announcement(
        title="给op1的公告",
        content="内容1",
        operator_ids=[operators[0].id]
    )

    await service.send_system_announcement(
        title="给op2的公告",
        content="内容2",
        operator_ids=[operators[1].id]
    )

    await service.send_system_announcement(
        title="给op3的公告",
        content="内容3",
        operator_ids=[operators[2].id]
    )

    # 验证每个运营商只能看到自己的消息
    for i, operator in enumerate(operators):
        messages, total = await message_service.get_messages(operator_id=operator.id)
        assert total == 1
        assert messages[0].title == f"给op{i+1}的公告"
