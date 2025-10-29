"""单元测试：MessageService (T222)

测试MessageService的消息通知功能：
1. create_message - 创建通用消息
2. create_refund_approved_notification - 退款批准通知
3. create_refund_rejected_notification - 退款拒绝通知
4. create_invoice_approved_notification - 发票批准通知
5. create_invoice_rejected_notification - 发票拒绝通知
6. get_messages - 获取消息列表（支持筛选和分页）
7. mark_as_read - 标记消息为已读
8. mark_all_as_read - 批量标记所有消息为已读
9. get_unread_count - 获取未读消息数量
10. delete_message - 删除消息

测试策略：
- 使用真实数据库会话(test_db fixture)
- 测试每个方法的成功场景和边界情况
- 验证消息内容的正确性
- 验证权限控制（运营商只能访问自己的消息）
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from src.services.message_service import MessageService
from src.models.message import OperatorMessage
from src.models.operator import OperatorAccount
from src.core import NotFoundException, BadRequestException
from src.core.utils.password import hash_password


@pytest.fixture
async def test_operators(test_db):
    """创建测试运营商"""
    operator1 = OperatorAccount(
        id=uuid4(),
        username=f"msg_test_op1_{uuid4().hex[:8]}",
        password_hash=hash_password("Pass123"),
        full_name="消息测试运营商1",
        phone="13800138001",
        email=f"msg_op1_{uuid4().hex[:8]}@test.com",
        api_key=f"api_key_{uuid4().hex}",
        api_key_hash=hash_password(f"api_key_{uuid4().hex}"),
        balance=500.00,
        customer_tier="standard",
        is_active=True
    )

    operator2 = OperatorAccount(
        id=uuid4(),
        username=f"msg_test_op2_{uuid4().hex[:8]}",
        password_hash=hash_password("Pass123"),
        full_name="消息测试运营商2",
        phone="13800138002",
        email=f"msg_op2_{uuid4().hex[:8]}@test.com",
        api_key=f"api_key_{uuid4().hex}",
        api_key_hash=hash_password(f"api_key_{uuid4().hex}"),
        balance=300.00,
        customer_tier="standard",
        is_active=True
    )

    test_db.add(operator1)
    test_db.add(operator2)
    await test_db.commit()
    await test_db.refresh(operator1)
    await test_db.refresh(operator2)

    return {"op1": operator1, "op2": operator2}


@pytest.mark.asyncio
async def test_create_message(test_db, test_operators):
    """测试创建通用消息"""
    service = MessageService(test_db)
    operator = test_operators["op1"]

    message = await service.create_message(
        operator_id=operator.id,
        message_type="system_announcement",
        title="系统公告测试",
        content="这是一条测试公告",
        related_type="announcement",
        related_id=uuid4()
    )
    await test_db.commit()

    # 验证消息创建成功
    assert message.id is not None
    assert message.operator_id == operator.id
    assert message.message_type == "system_announcement"
    assert message.title == "系统公告测试"
    assert message.content == "这是一条测试公告"
    assert message.is_read is False
    assert message.read_at is None
    assert message.related_type == "announcement"


@pytest.mark.asyncio
async def test_create_refund_approved_notification(test_db, test_operators):
    """测试创建退款批准通知"""
    service = MessageService(test_db)
    operator = test_operators["op1"]
    refund_id = uuid4()

    message = await service.create_refund_approved_notification(
        operator_id=operator.id,
        refund_id=refund_id,
        refund_amount="100.00",
        actual_amount="95.00",
        note="已扣除手续费5元"
    )
    await test_db.commit()

    # 验证消息内容
    assert message.message_type == "refund_approved"
    assert message.title == "退款申请已批准"
    assert "申请金额: ¥100.00" in message.content
    assert "实际退款: ¥95.00" in message.content
    assert "已扣除手续费5元" in message.content
    assert message.related_type == "refund"
    assert message.related_id == refund_id
    assert message.is_read is False


@pytest.mark.asyncio
async def test_create_refund_rejected_notification(test_db, test_operators):
    """测试创建退款拒绝通知"""
    service = MessageService(test_db)
    operator = test_operators["op1"]
    refund_id = uuid4()

    message = await service.create_refund_rejected_notification(
        operator_id=operator.id,
        refund_id=refund_id,
        refund_amount="100.00",
        reject_reason="提交材料不全"
    )
    await test_db.commit()

    # 验证消息内容
    assert message.message_type == "refund_rejected"
    assert message.title == "退款申请被拒绝"
    assert "申请金额: ¥100.00" in message.content
    assert "拒绝原因: 提交材料不全" in message.content
    assert message.related_type == "refund"
    assert message.related_id == refund_id


@pytest.mark.asyncio
async def test_create_invoice_approved_notification(test_db, test_operators):
    """测试创建发票批准通知"""
    service = MessageService(test_db)
    operator = test_operators["op1"]
    invoice_id = uuid4()

    message = await service.create_invoice_approved_notification(
        operator_id=operator.id,
        invoice_id=invoice_id,
        invoice_amount="500.00",
        invoice_number="INV202510290001",
        pdf_url="https://example.com/invoices/INV202510290001.pdf",
        note="请妥善保管电子发票"
    )
    await test_db.commit()

    # 验证消息内容
    assert message.message_type == "invoice_approved"
    assert message.title == "发票已开具"
    assert "发票金额: ¥500.00" in message.content
    assert "发票号码: INV202510290001" in message.content
    assert "https://example.com/invoices/INV202510290001.pdf" in message.content
    assert "请妥善保管电子发票" in message.content
    assert message.related_type == "invoice"
    assert message.related_id == invoice_id


@pytest.mark.asyncio
async def test_create_invoice_rejected_notification(test_db, test_operators):
    """测试创建发票拒绝通知"""
    service = MessageService(test_db)
    operator = test_operators["op1"]
    invoice_id = uuid4()

    message = await service.create_invoice_rejected_notification(
        operator_id=operator.id,
        invoice_id=invoice_id,
        invoice_amount="500.00",
        reject_reason="税号格式错误"
    )
    await test_db.commit()

    # 验证消息内容
    assert message.message_type == "invoice_rejected"
    assert message.title == "发票申请被拒绝"
    assert "发票金额: ¥500.00" in message.content
    assert "拒绝原因: 税号格式错误" in message.content
    assert message.related_type == "invoice"
    assert message.related_id == invoice_id


@pytest.mark.asyncio
async def test_get_messages_all(test_db, test_operators):
    """测试获取所有消息"""
    service = MessageService(test_db)
    operator = test_operators["op1"]

    # 创建5条消息
    for i in range(5):
        await service.create_message(
            operator_id=operator.id,
            message_type="system_announcement",
            title=f"公告{i+1}",
            content=f"内容{i+1}"
        )
    await test_db.commit()

    # 查询所有消息
    messages, total = await service.get_messages(
        operator_id=operator.id,
        page=1,
        page_size=10
    )

    assert total == 5
    assert len(messages) == 5
    # 验证按时间倒序排列
    assert messages[0].title == "公告5"
    assert messages[4].title == "公告1"


@pytest.mark.asyncio
async def test_get_messages_pagination(test_db, test_operators):
    """测试消息分页"""
    service = MessageService(test_db)
    operator = test_operators["op1"]

    # 创建10条消息
    for i in range(10):
        await service.create_message(
            operator_id=operator.id,
            message_type="test_message",
            title=f"消息{i+1}",
            content=f"内容{i+1}"
        )
    await test_db.commit()

    # 第1页，每页3条
    messages_p1, total_p1 = await service.get_messages(
        operator_id=operator.id,
        page=1,
        page_size=3
    )

    assert total_p1 == 10
    assert len(messages_p1) == 3
    assert messages_p1[0].title == "消息10"

    # 第2页
    messages_p2, total_p2 = await service.get_messages(
        operator_id=operator.id,
        page=2,
        page_size=3
    )

    assert total_p2 == 10
    assert len(messages_p2) == 3
    assert messages_p2[0].title == "消息7"


@pytest.mark.asyncio
async def test_get_messages_filter_by_read_status(test_db, test_operators):
    """测试按已读状态筛选消息"""
    service = MessageService(test_db)
    operator = test_operators["op1"]

    # 创建3条消息
    msg1 = await service.create_message(
        operator_id=operator.id,
        message_type="test",
        title="消息1",
        content="内容1"
    )
    msg2 = await service.create_message(
        operator_id=operator.id,
        message_type="test",
        title="消息2",
        content="内容2"
    )
    msg3 = await service.create_message(
        operator_id=operator.id,
        message_type="test",
        title="消息3",
        content="内容3"
    )
    await test_db.commit()

    # 标记msg2为已读
    await service.mark_as_read(msg2.id, operator.id)
    await test_db.commit()

    # 查询未读消息
    unread_messages, unread_total = await service.get_messages(
        operator_id=operator.id,
        is_read=False
    )

    assert unread_total == 2
    assert len(unread_messages) == 2

    # 查询已读消息
    read_messages, read_total = await service.get_messages(
        operator_id=operator.id,
        is_read=True
    )

    assert read_total == 1
    assert len(read_messages) == 1
    assert read_messages[0].id == msg2.id


@pytest.mark.asyncio
async def test_get_messages_filter_by_type(test_db, test_operators):
    """测试按消息类型筛选"""
    service = MessageService(test_db)
    operator = test_operators["op1"]

    # 创建不同类型的消息
    await service.create_message(
        operator_id=operator.id,
        message_type="system_announcement",
        title="系统公告",
        content="公告内容"
    )
    await service.create_message(
        operator_id=operator.id,
        message_type="refund_approved",
        title="退款批准",
        content="退款内容"
    )
    await service.create_message(
        operator_id=operator.id,
        message_type="refund_approved",
        title="退款批准2",
        content="退款内容2"
    )
    await test_db.commit()

    # 查询退款类型消息
    refund_messages, refund_total = await service.get_messages(
        operator_id=operator.id,
        message_type="refund_approved"
    )

    assert refund_total == 2
    assert len(refund_messages) == 2

    # 查询系统公告
    announcement_messages, announcement_total = await service.get_messages(
        operator_id=operator.id,
        message_type="system_announcement"
    )

    assert announcement_total == 1
    assert len(announcement_messages) == 1


@pytest.mark.asyncio
async def test_get_messages_isolation(test_db, test_operators):
    """测试消息隔离（运营商只能看到自己的消息）"""
    service = MessageService(test_db)
    op1 = test_operators["op1"]
    op2 = test_operators["op2"]

    # 给op1创建2条消息
    await service.create_message(
        operator_id=op1.id,
        message_type="test",
        title="运营商1的消息1",
        content="内容1"
    )
    await service.create_message(
        operator_id=op1.id,
        message_type="test",
        title="运营商1的消息2",
        content="内容2"
    )

    # 给op2创建1条消息
    await service.create_message(
        operator_id=op2.id,
        message_type="test",
        title="运营商2的消息",
        content="内容"
    )
    await test_db.commit()

    # op1查询消息
    op1_messages, op1_total = await service.get_messages(operator_id=op1.id)
    assert op1_total == 2

    # op2查询消息
    op2_messages, op2_total = await service.get_messages(operator_id=op2.id)
    assert op2_total == 1


@pytest.mark.asyncio
async def test_mark_as_read_success(test_db, test_operators):
    """测试成功标记消息为已读"""
    service = MessageService(test_db)
    operator = test_operators["op1"]

    # 创建消息
    message = await service.create_message(
        operator_id=operator.id,
        message_type="test",
        title="测试消息",
        content="内容"
    )
    await test_db.commit()

    assert message.is_read is False
    assert message.read_at is None

    # 标记为已读
    updated_message = await service.mark_as_read(message.id, operator.id)
    await test_db.commit()

    assert updated_message.is_read is True
    assert updated_message.read_at is not None


@pytest.mark.asyncio
async def test_mark_as_read_not_found(test_db, test_operators):
    """测试标记不存在的消息为已读"""
    service = MessageService(test_db)
    operator = test_operators["op1"]

    with pytest.raises(NotFoundException) as exc_info:
        await service.mark_as_read(uuid4(), operator.id)

    assert "消息不存在或无权限访问" in str(exc_info.value)


@pytest.mark.asyncio
async def test_mark_as_read_no_permission(test_db, test_operators):
    """测试标记其他运营商的消息为已读（无权限）"""
    service = MessageService(test_db)
    op1 = test_operators["op1"]
    op2 = test_operators["op2"]

    # op1创建消息
    message = await service.create_message(
        operator_id=op1.id,
        message_type="test",
        title="测试消息",
        content="内容"
    )
    await test_db.commit()

    # op2尝试标记op1的消息（应该失败）
    with pytest.raises(NotFoundException):
        await service.mark_as_read(message.id, op2.id)


@pytest.mark.asyncio
async def test_mark_as_read_already_read(test_db, test_operators):
    """测试标记已读消息为已读（应该报错）"""
    service = MessageService(test_db)
    operator = test_operators["op1"]

    # 创建并标记为已读
    message = await service.create_message(
        operator_id=operator.id,
        message_type="test",
        title="测试消息",
        content="内容"
    )
    await test_db.commit()

    await service.mark_as_read(message.id, operator.id)
    await test_db.commit()

    # 再次标记为已读（应该报错）
    with pytest.raises(BadRequestException) as exc_info:
        await service.mark_as_read(message.id, operator.id)

    assert "消息已读" in str(exc_info.value)


@pytest.mark.asyncio
async def test_mark_all_as_read(test_db, test_operators):
    """测试批量标记所有消息为已读"""
    service = MessageService(test_db)
    operator = test_operators["op1"]

    # 创建5条未读消息
    for i in range(5):
        await service.create_message(
            operator_id=operator.id,
            message_type="test",
            title=f"消息{i+1}",
            content=f"内容{i+1}"
        )
    await test_db.commit()

    # 验证未读数量
    unread_count_before = await service.get_unread_count(operator.id)
    assert unread_count_before == 5

    # 标记所有为已读
    marked_count = await service.mark_all_as_read(operator.id)
    await test_db.commit()

    assert marked_count == 5

    # 验证未读数量为0
    unread_count_after = await service.get_unread_count(operator.id)
    assert unread_count_after == 0


@pytest.mark.asyncio
async def test_mark_all_as_read_empty(test_db, test_operators):
    """测试标记所有消息为已读（无未读消息）"""
    service = MessageService(test_db)
    operator = test_operators["op1"]

    # 不创建任何消息
    marked_count = await service.mark_all_as_read(operator.id)
    await test_db.commit()

    assert marked_count == 0


@pytest.mark.asyncio
async def test_get_unread_count(test_db, test_operators):
    """测试获取未读消息数量"""
    service = MessageService(test_db)
    operator = test_operators["op1"]

    # 初始未读数量为0
    unread_count = await service.get_unread_count(operator.id)
    assert unread_count == 0

    # 创建3条消息
    msg1 = await service.create_message(
        operator_id=operator.id,
        message_type="test",
        title="消息1",
        content="内容1"
    )
    msg2 = await service.create_message(
        operator_id=operator.id,
        message_type="test",
        title="消息2",
        content="内容2"
    )
    msg3 = await service.create_message(
        operator_id=operator.id,
        message_type="test",
        title="消息3",
        content="内容3"
    )
    await test_db.commit()

    # 未读数量为3
    unread_count = await service.get_unread_count(operator.id)
    assert unread_count == 3

    # 标记msg1为已读
    await service.mark_as_read(msg1.id, operator.id)
    await test_db.commit()

    # 未读数量为2
    unread_count = await service.get_unread_count(operator.id)
    assert unread_count == 2


@pytest.mark.asyncio
async def test_delete_message_success(test_db, test_operators):
    """测试成功删除消息"""
    service = MessageService(test_db)
    operator = test_operators["op1"]

    # 创建消息
    message = await service.create_message(
        operator_id=operator.id,
        message_type="test",
        title="待删除的消息",
        content="内容"
    )
    await test_db.commit()

    message_id = message.id

    # 删除消息
    await service.delete_message(message_id, operator.id)
    await test_db.commit()

    # 验证消息已删除
    messages, total = await service.get_messages(operator_id=operator.id)
    assert total == 0


@pytest.mark.asyncio
async def test_delete_message_not_found(test_db, test_operators):
    """测试删除不存在的消息"""
    service = MessageService(test_db)
    operator = test_operators["op1"]

    with pytest.raises(NotFoundException) as exc_info:
        await service.delete_message(uuid4(), operator.id)

    assert "消息不存在或无权限访问" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_message_no_permission(test_db, test_operators):
    """测试删除其他运营商的消息（无权限）"""
    service = MessageService(test_db)
    op1 = test_operators["op1"]
    op2 = test_operators["op2"]

    # op1创建消息
    message = await service.create_message(
        operator_id=op1.id,
        message_type="test",
        title="测试消息",
        content="内容"
    )
    await test_db.commit()

    # op2尝试删除op1的消息（应该失败）
    with pytest.raises(NotFoundException):
        await service.delete_message(message.id, op2.id)
