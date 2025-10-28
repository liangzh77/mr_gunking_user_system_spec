"""
契约测试: 发票查询接口 (T077)

测试目标:
- 验证 GET /v1/operators/me/invoices 接口契约
- 确保响应格式符合contract定义
- 覆盖分页查询、空列表等场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 查询参数: page, page_size
- 返回格式: {success: true, data: {page, page_size, total, items: [Invoice]}}
"""
import pytest
from httpx import AsyncClient
from decimal import Decimal

from src.main import app


# ========== 辅助函数 ==========

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


async def add_recharge_transaction(db, operator_id: str, amount: float):
    """添加充值交易记录(用于测试)"""
    from src.models.transaction import TransactionRecord
    from src.models.operator import OperatorAccount
    from sqlalchemy import select
    from uuid import UUID

    # 解析operator_id
    if operator_id.startswith("op_"):
        uuid_str = operator_id[3:]
    else:
        uuid_str = operator_id

    # 查询运营商
    stmt = select(OperatorAccount).where(OperatorAccount.id == UUID(uuid_str))
    result = await db.execute(stmt)
    operator = result.scalar_one_or_none()

    if operator:
        # 创建充值交易记录
        balance_before = operator.balance
        balance_after = operator.balance + Decimal(str(amount))

        transaction = TransactionRecord(
            operator_id=UUID(uuid_str),
            transaction_type="recharge",
            amount=Decimal(str(amount)),
            balance_before=balance_before,
            balance_after=balance_after,
            payment_channel="wechat"
        )
        db.add(transaction)

        # 更新余额
        operator.balance = balance_after
        await db.commit()


async def create_invoice(client: AsyncClient, token: str, amount: str, title: str, tax_id: str):
    """创建发票申请"""
    response = await client.post(
        "/v1/operators/me/invoices",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": amount,
            "invoice_title": title,
            "tax_id": tax_id
        }
    )
    return response


# ========== GET /v1/operators/me/invoices 测试 ==========

@pytest.mark.asyncio
async def test_get_invoices_empty_list(test_db):
    """测试查询空发票列表"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_list_user_1")

        response = await client.get(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "data" in data
    assert data["data"]["page"] == 1
    assert data["data"]["page_size"] == 20
    assert data["data"]["total"] == 0
    assert data["data"]["items"] == []


@pytest.mark.asyncio
async def test_get_invoices_with_data(test_db):
    """测试查询有数据的发票列表"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_list_user_2")

        # 添加充值记录
        from src.core.security.jwt import verify_token
        payload = verify_token(token)
        operator_id = payload["sub"]
        await add_recharge_transaction(test_db, operator_id, 1000.00)

        # 创建3个发票申请
        await create_invoice(client, token, "100.00", "公司A", "91110000111111111A")
        await create_invoice(client, token, "200.00", "公司B", "91110000222222222B")
        await create_invoice(client, token, "300.00", "公司C", "91110000333333333C")

        # 查询发票列表
        response = await client.get(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert data["data"]["page"] == 1
    assert data["data"]["page_size"] == 20
    assert data["data"]["total"] == 3
    assert len(data["data"]["items"]) == 3

    # 验证第一条记录(最新的应该在前)
    first_invoice = data["data"]["items"][0]
    assert first_invoice["invoice_id"].startswith("inv_")
    assert first_invoice["invoice_title"] == "公司C"  # 最后创建的
    assert first_invoice["amount"] == "300.00"
    assert first_invoice["status"] == "pending"


@pytest.mark.asyncio
async def test_get_invoices_pagination(test_db):
    """测试分页功能"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_list_user_3")

        # 添加充值记录
        from src.core.security.jwt import verify_token
        payload = verify_token(token)
        operator_id = payload["sub"]
        await add_recharge_transaction(test_db, operator_id, 2000.00)

        # 创建5个发票申请
        for i in range(5):
            await create_invoice(
                client, token,
                f"{(i+1)*100}.00",
                f"公司{i+1}",
                f"9111000{i}{i}{i}{i}{i}{i}{i}{i}{i}{i}{i}A"
            )

        # 查询第1页(每页2条)
        response1 = await client.get(
            "/v1/operators/me/invoices?page=1&page_size=2",
            headers={"Authorization": f"Bearer {token}"}
        )

        # 查询第2页
        response2 = await client.get(
            "/v1/operators/me/invoices?page=2&page_size=2",
            headers={"Authorization": f"Bearer {token}"}
        )

        # 查询第3页
        response3 = await client.get(
            "/v1/operators/me/invoices?page=3&page_size=2",
            headers={"Authorization": f"Bearer {token}"}
        )

    # 验证第1页
    assert response1.status_code == 200
    data1 = response1.json()["data"]
    assert data1["page"] == 1
    assert data1["page_size"] == 2
    assert data1["total"] == 5
    assert len(data1["items"]) == 2

    # 验证第2页
    assert response2.status_code == 200
    data2 = response2.json()["data"]
    assert data2["page"] == 2
    assert data2["page_size"] == 2
    assert len(data2["items"]) == 2

    # 验证第3页
    assert response3.status_code == 200
    data3 = response3.json()["data"]
    assert data3["page"] == 3
    assert len(data3["items"]) == 1  # 最后一页只有1条


@pytest.mark.asyncio
async def test_get_invoices_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/operators/me/invoices")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_invoices_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/operators/me/invoices",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_invoices_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_list_user_4")

        # 添加充值记录并创建发票
        from src.core.security.jwt import verify_token
        payload = verify_token(token)
        operator_id = payload["sub"]
        await add_recharge_transaction(test_db, operator_id, 500.00)

        await create_invoice(client, token, "250.00", "格式测试公司", "91110000999999999Z")

        response = await client.get(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # 验证顶层格式
    assert isinstance(data["success"], bool)
    assert data["success"] is True
    assert isinstance(data["data"], dict)

    # 验证data结构
    assert isinstance(data["data"]["page"], int)
    assert isinstance(data["data"]["page_size"], int)
    assert isinstance(data["data"]["total"], int)
    assert isinstance(data["data"]["items"], list)

    # 验证items内部结构
    if data["data"]["items"]:
        invoice = data["data"]["items"][0]
        assert isinstance(invoice["invoice_id"], str)
        assert isinstance(invoice["amount"], str)
        assert isinstance(invoice["invoice_title"], str)
        assert isinstance(invoice["tax_id"], str)
        assert isinstance(invoice["status"], str)
        assert isinstance(invoice["created_at"], str)
        # email可能为None或str
        assert invoice["email"] is None or isinstance(invoice["email"], str)
        # pdf_url, reviewed_by, reviewed_at在pending状态下应为None
        assert invoice["pdf_url"] is None
        assert invoice["reviewed_by"] is None
        assert invoice["reviewed_at"] is None


@pytest.mark.asyncio
async def test_get_invoices_order_by_created_at_desc(test_db):
    """测试结果按创建时间降序排列"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_list_user_5")

        # 添加充值记录
        from src.core.security.jwt import verify_token
        payload = verify_token(token)
        operator_id = payload["sub"]
        await add_recharge_transaction(test_db, operator_id, 1000.00)

        # 按顺序创建3个发票
        await create_invoice(client, token, "100.00", "第一个", "91110000111111111A")
        await create_invoice(client, token, "200.00", "第二个", "91110000222222222B")
        await create_invoice(client, token, "300.00", "第三个", "91110000333333333C")

        response = await client.get(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    items = response.json()["data"]["items"]

    # 验证顺序(最新的在前)
    assert items[0]["invoice_title"] == "第三个"
    assert items[1]["invoice_title"] == "第二个"
    assert items[2]["invoice_title"] == "第一个"


@pytest.mark.asyncio
async def test_get_invoices_default_pagination(test_db):
    """测试默认分页参数"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_list_user_6")

        # 不提供page和page_size参数
        response = await client.get(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()["data"]

    # 验证默认值
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_get_invoices_isolation_between_operators(test_db):
    """测试运营商之间的数据隔离"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建两个运营商
        token1 = await create_and_login_operator(client, "invoice_list_user_7a")
        token2 = await create_and_login_operator(client, "invoice_list_user_7b")

        # 为运营商1添加充值并创建发票
        from src.core.security.jwt import verify_token
        payload1 = verify_token(token1)
        operator_id1 = payload1["sub"]
        await add_recharge_transaction(test_db, operator_id1, 500.00)
        await create_invoice(client, token1, "200.00", "运营商1的发票", "91110000111111111A")

        # 为运营商2添加充值并创建发票
        payload2 = verify_token(token2)
        operator_id2 = payload2["sub"]
        await add_recharge_transaction(test_db, operator_id2, 500.00)
        await create_invoice(client, token2, "300.00", "运营商2的发票", "91110000222222222B")

        # 运营商1查询自己的发票
        response1 = await client.get(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token1}"}
        )

        # 运营商2查询自己的发票
        response2 = await client.get(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token2}"}
        )

    # 验证数据隔离
    data1 = response1.json()["data"]
    data2 = response2.json()["data"]

    assert data1["total"] == 1
    assert data1["items"][0]["invoice_title"] == "运营商1的发票"

    assert data2["total"] == 1
    assert data2["items"][0]["invoice_title"] == "运营商2的发票"
