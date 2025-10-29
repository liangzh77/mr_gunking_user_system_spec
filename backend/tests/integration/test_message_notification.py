"""
集成测试: 消息通知流程 (T208)

测试目标:
- 验证完整的消息通知流程: 发布公告 → 接收消息 → 标记已读
- 测试余额不足提醒流程
- 测试价格调整通知流程
- 验证多运营商消息隔离
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from src.main import app
from src.models.operator_account import OperatorAccount
from src.models.admin_account import AdminAccount
from src.models.application import Application
from src.models.operator_app_authorization import OperatorAppAuthorization
from src.services.notification import NotificationService
from src.core.utils.password import hash_password


# ========== 辅助函数 ==========

async def create_admin(db) -> AdminAccount:
    """创建测试管理员"""
    admin = AdminAccount(
        id=uuid4(),
        username=f"test_admin_{uuid4().hex[:8]}",
        password_hash=hash_password("AdminPass123"),
        full_name="测试管理员",
        email=f"admin_{uuid4().hex[:8]}@test.com",
        role="admin"
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin


async def create_operator(db, username: str, balance: str = "500.00") -> OperatorAccount:
    """创建测试运营商"""
    operator = OperatorAccount(
        id=uuid4(),
        username=username,
        password_hash=hash_password("Pass123"),
        full_name=f"测试运营商{username}",
        phone="13800138000",
        email=f"{username}@test.com",
        api_key=f"api_key_{uuid4().hex}",
        api_key_hash=hash_password(f"api_key_{uuid4().hex}"),
        balance=Decimal(balance),
        customer_tier="standard"
    )
    db.add(operator)
    await db.commit()
    await db.refresh(operator)
    return operator


async def login_operator(client: AsyncClient, username: str) -> str:
    """运营商登录并返回token"""
    response = await client.post(
        "/v1/auth/operators/login",
        json={
            "username": username,
            "password": "Pass123"
        }
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


async def create_application(db, app_name: str, price: str) -> Application:
    """创建测试应用"""
    app = Application(
        id=uuid4(),
        app_code=f"APP_{datetime.now().strftime('%Y%m%d')}_{uuid4().hex[:3].upper()}",
        app_name=app_name,
        price_per_player=Decimal(price),
        min_players=2,
        max_players=8,
        is_active=True
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


async def authorize_app_to_operator(db, operator_id, app_id, admin_id) -> OperatorAppAuthorization:
    """授权应用给运营商"""
    auth = OperatorAppAuthorization(
        id=uuid4(),
        operator_id=operator_id,
        application_id=app_id,
        authorized_by=admin_id,
        authorized_at=datetime.now(timezone.utc),
        is_active=True
    )
    db.add(auth)
    await db.commit()
    await db.refresh(auth)
    return auth


# ========== 集成测试 ==========

@pytest.mark.asyncio
async def test_system_announcement_flow(test_db):
    """测试系统公告完整流程: 发布公告 → 接收消息 → 标记已读"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 第1步: 创建2个运营商
        op1 = await create_operator(test_db, "announcement_op1")
        op2 = await create_operator(test_db, "announcement_op2")

        # 第2步: 运营商1登录
        token1 = await login_operator(client, "announcement_op1")

        # 第3步: 发送系统公告
        notification_service = NotificationService(test_db)
        result = await notification_service.send_system_announcement(
            title="春节假期运营时间调整",
            content="尊敬的运营商：春节期间（2月10日-2月17日）系统正常运营，祝您生意兴隆！",
            importance="normal"
        )

        # 验证发送结果
        assert result["success_count"] == 2
        assert result["failed_count"] == 0
        assert result["total_count"] == 2

        # 第4步: 运营商1查询未读消息数量
        unread_response = await client.get(
            "/v1/messages/unread-count",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert unread_response.status_code == 200
        assert unread_response.json()["unread_count"] == 1

        # 第5步: 运营商1查询消息列表
        list_response = await client.get(
            "/v1/messages",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert list_response.status_code == 200
        messages = list_response.json()["items"]
        assert len(messages) == 1
        assert messages[0]["title"] == "春节假期运营时间调整"
        assert messages[0]["is_read"] is False
        message_id = messages[0]["message_id"]

        # 第6步: 运营商1标记消息为已读
        read_response = await client.post(
            f"/v1/messages/{message_id}/read",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert read_response.status_code == 200

        # 第7步: 验证未读数量变为0
        unread_response2 = await client.get(
            "/v1/messages/unread-count",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert unread_response2.status_code == 200
        assert unread_response2.json()["unread_count"] == 0

        # 第8步: 运营商2应该也收到相同的消息
        token2 = await login_operator(client, "announcement_op2")
        list_response2 = await client.get(
            "/v1/messages",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert list_response2.status_code == 200
        messages2 = list_response2.json()["items"]
        assert len(messages2) == 1
        assert messages2[0]["title"] == "春节假期运营时间调整"


@pytest.mark.asyncio
async def test_balance_low_alert_flow(test_db):
    """测试余额不足提醒流程"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 第1步: 创建余额不足的运营商
        op = await create_operator(test_db, "balance_low_op", balance="50.00")

        # 第2步: 发送余额不足提醒
        notification_service = NotificationService(test_db)
        await notification_service.send_balance_low_alert(
            operator_id=op.id,
            current_balance=Decimal("50.00"),
            threshold=Decimal("100.00")
        )

        # 第3步: 运营商登录查看消息
        token = await login_operator(client, "balance_low_op")

        list_response = await client.get(
            "/v1/messages",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert list_response.status_code == 200
        messages = list_response.json()["items"]
        assert len(messages) == 1
        assert "余额不足提醒" in messages[0]["title"]
        assert "当前余额: ¥50.00" in messages[0]["content"]
        assert "预警阈值: ¥100.00" in messages[0]["content"]


@pytest.mark.asyncio
async def test_price_change_notification_flow(test_db):
    """测试价格调整通知流程"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 第1步: 创建管理员、运营商和应用
        admin = await create_admin(test_db)
        op1 = await create_operator(test_db, "price_change_op1")
        op2 = await create_operator(test_db, "price_change_op2")
        app = await create_application(test_db, "太空探险", "50.00")

        # 第2步: 授权应用给运营商1（运营商2未授权）
        await authorize_app_to_operator(test_db, op1.id, app.id, admin.id)

        # 第3步: 发送价格调整通知
        notification_service = NotificationService(test_db)
        result = await notification_service.send_price_change_notification(
            application_id=app.id,
            app_name="太空探险",
            old_price=Decimal("50.00"),
            new_price=Decimal("60.00")
        )

        # 验证发送结果（只发给授权的运营商1）
        assert result["success_count"] == 1
        assert result["total_count"] == 1

        # 第4步: 运营商1应该收到通知
        token1 = await login_operator(client, "price_change_op1")
        list_response1 = await client.get(
            "/v1/messages",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert list_response1.status_code == 200
        messages1 = list_response1.json()["items"]
        assert len(messages1) == 1
        assert "价格调整通知" in messages1[0]["title"]
        assert "太空探险" in messages1[0]["title"]
        assert "原价格: ¥50.00/人" in messages1[0]["content"]
        assert "新价格: ¥60.00/人" in messages1[0]["content"]

        # 第5步: 运营商2不应该收到通知（未授权）
        token2 = await login_operator(client, "price_change_op2")
        list_response2 = await client.get(
            "/v1/messages",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert list_response2.status_code == 200
        messages2 = list_response2.json()["items"]
        assert len(messages2) == 0


@pytest.mark.asyncio
async def test_message_isolation_between_operators(test_db):
    """测试运营商之间的消息隔离"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 第1步: 创建2个运营商
        op1 = await create_operator(test_db, "isolation_op1")
        op2 = await create_operator(test_db, "isolation_op2")

        # 第2步: 发送定向消息给运营商1
        notification_service = NotificationService(test_db)
        await notification_service.send_custom_notification(
            operator_ids=[op1.id],
            message_type="custom_notification",
            title="专属通知",
            content="这是只发给运营商1的消息"
        )

        # 第3步: 运营商1应该能看到消息
        token1 = await login_operator(client, "isolation_op1")
        list_response1 = await client.get(
            "/v1/messages",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert list_response1.status_code == 200
        assert len(list_response1.json()["items"]) == 1

        # 第4步: 运营商2不应该看到运营商1的消息
        token2 = await login_operator(client, "isolation_op2")
        list_response2 = await client.get(
            "/v1/messages",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert list_response2.status_code == 200
        assert len(list_response2.json()["items"]) == 0


@pytest.mark.asyncio
async def test_mark_all_messages_as_read(test_db):
    """测试标记所有消息为已读"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 第1步: 创建运营商
        op = await create_operator(test_db, "mark_all_op")

        # 第2步: 发送3条消息
        notification_service = NotificationService(test_db)
        for i in range(3):
            await notification_service.send_custom_notification(
                operator_ids=[op.id],
                message_type="test_message",
                title=f"测试消息{i+1}",
                content=f"这是第{i+1}条测试消息"
            )

        # 第3步: 运营商登录查看未读数量
        token = await login_operator(client, "mark_all_op")
        unread_response = await client.get(
            "/v1/messages/unread-count",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert unread_response.status_code == 200
        assert unread_response.json()["unread_count"] == 3

        # 第4步: 标记所有消息为已读
        mark_all_response = await client.post(
            "/v1/messages/read-all",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert mark_all_response.status_code == 200
        assert mark_all_response.json()["marked_count"] == 3

        # 第5步: 验证未读数量变为0
        unread_response2 = await client.get(
            "/v1/messages/unread-count",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert unread_response2.status_code == 200
        assert unread_response2.json()["unread_count"] == 0
