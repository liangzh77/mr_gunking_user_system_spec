"""
契约测试: 发票申请接口 (T076)

测试目标:
- 验证 POST /v1/operators/me/invoices 接口契约
- 确保请求/响应格式符合contract定义
- 覆盖正常申请、金额超限、参数验证场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 请求体: amount, invoice_title, tax_id, email(可选)
- 返回格式: {success: true, message: str, data: Invoice}
- 开票金额超过已充值金额时返回400错误
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


# ========== POST /v1/operators/me/invoices 测试 ==========

@pytest.mark.asyncio
async def test_apply_invoice_success(test_db):
    """测试成功申请发票"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_user_1")

        # 添加充值记录(1000元)
        from src.core.security.jwt import verify_token
        payload = verify_token(token)
        operator_id = payload["sub"]
        await add_recharge_transaction(test_db, operator_id, 1000.00)

        # 申请发票
        response = await client.post(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "500.00",
                "invoice_title": "北京星空娱乐有限公司",
                "tax_id": "91110000123456789X",
                "email": "finance@example.com"
            }
        )

    assert response.status_code == 201
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "message" in data
    assert data["message"] == "发票申请已提交，等待财务审核"
    assert "data" in data

    # 验证发票数据
    invoice = data["data"]
    assert "invoice_id" in invoice
    assert invoice["invoice_id"].startswith("inv_")
    assert invoice["amount"] == "500.00"
    assert invoice["invoice_title"] == "北京星空娱乐有限公司"
    assert invoice["tax_id"] == "91110000123456789X"
    assert invoice["email"] == "finance@example.com"
    assert invoice["status"] == "pending"
    assert invoice["pdf_url"] is None  # 待审核时没有PDF
    assert "created_at" in invoice


@pytest.mark.asyncio
async def test_apply_invoice_amount_exceeds_recharged(test_db):
    """测试开票金额超过已充值金额"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_user_2")

        # 添加充值记录(500元)
        from src.core.security.jwt import verify_token
        payload = verify_token(token)
        operator_id = payload["sub"]
        await add_recharge_transaction(test_db, operator_id, 500.00)

        # 尝试开1000元发票(超过充值金额)
        response = await client.post(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "1000.00",
                "invoice_title": "测试公司",
                "tax_id": "91110000123456789X"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert "error_code" in data
    assert data["error_code"] == "INVALID_PARAMS"
    assert "不能超过已充值金额" in data["message"]


@pytest.mark.asyncio
async def test_apply_invoice_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/operators/me/invoices",
            json={
                "amount": "500.00",
                "invoice_title": "测试公司",
                "tax_id": "91110000123456789X"
            }
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_apply_invoice_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/operators/me/invoices",
            headers={"Authorization": "Bearer invalid_token_12345"},
            json={
                "amount": "500.00",
                "invoice_title": "测试公司",
                "tax_id": "91110000123456789X"
            }
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_apply_invoice_tax_id_too_short(test_db):
    """测试税号太短(小于15位)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_user_3")

        response = await client.post(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "100.00",
                "invoice_title": "测试公司",
                "tax_id": "12345"  # 只有5位
            }
        )

    assert response.status_code == 400  # Validation error (converted by exception_handler)


@pytest.mark.asyncio
async def test_apply_invoice_tax_id_too_long(test_db):
    """测试税号太长(超过20位)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_user_4")

        response = await client.post(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "100.00",
                "invoice_title": "测试公司",
                "tax_id": "123456789012345678901"  # 21位
            }
        )

    assert response.status_code == 400  # Validation error (converted by exception_handler)


@pytest.mark.asyncio
async def test_apply_invoice_tax_id_invalid_chars(test_db):
    """测试税号包含非法字符"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_user_5")

        response = await client.post(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "100.00",
                "invoice_title": "测试公司",
                "tax_id": "9111000012345-abc"  # 包含'-'
            }
        )

    assert response.status_code == 400  # Validation error (converted by exception_handler)


@pytest.mark.asyncio
async def test_apply_invoice_missing_amount(test_db):
    """测试缺少amount字段"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_user_6")

        response = await client.post(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "invoice_title": "测试公司",
                "tax_id": "91110000123456789X"
            }
        )

    assert response.status_code == 400  # Validation error (converted by exception_handler)


@pytest.mark.asyncio
async def test_apply_invoice_missing_invoice_title(test_db):
    """测试缺少invoice_title字段"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_user_7")

        response = await client.post(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "100.00",
                "tax_id": "91110000123456789X"
            }
        )

    assert response.status_code == 400  # Validation error (converted by exception_handler)


@pytest.mark.asyncio
async def test_apply_invoice_missing_tax_id(test_db):
    """测试缺少tax_id字段"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_user_8")

        response = await client.post(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "100.00",
                "invoice_title": "测试公司"
            }
        )

    assert response.status_code == 400  # Validation error (converted by exception_handler)


@pytest.mark.asyncio
async def test_apply_invoice_without_email(test_db):
    """测试不提供email(应使用账户邮箱)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_user_9")

        # 添加充值记录
        from src.core.security.jwt import verify_token
        payload = verify_token(token)
        operator_id = payload["sub"]
        await add_recharge_transaction(test_db, operator_id, 200.00)

        # 不提供email
        response = await client.post(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "100.00",
                "invoice_title": "测试公司",
                "tax_id": "91110000123456789X"
            }
        )

    assert response.status_code == 201
    invoice = response.json()["data"]
    # 应该使用账户邮箱(invoice_user_9@example.com)
    assert invoice["email"] == "invoice_user_9@example.com"


@pytest.mark.asyncio
async def test_apply_invoice_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_user_10")

        # 添加充值记录
        from src.core.security.jwt import verify_token
        payload = verify_token(token)
        operator_id = payload["sub"]
        await add_recharge_transaction(test_db, operator_id, 300.00)

        response = await client.post(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "150.00",
                "invoice_title": "响应格式测试公司",
                "tax_id": "91110000987654321Y",
                "email": "test@example.com"
            }
        )

    assert response.status_code == 201
    data = response.json()

    # 验证顶层格式
    assert isinstance(data["success"], bool)
    assert data["success"] is True
    assert isinstance(data["message"], str)
    assert isinstance(data["data"], dict)

    # 验证data内部结构
    invoice = data["data"]
    assert isinstance(invoice["invoice_id"], str)
    assert isinstance(invoice["amount"], str)
    assert isinstance(invoice["invoice_title"], str)
    assert isinstance(invoice["tax_id"], str)
    assert isinstance(invoice["email"], str)
    assert isinstance(invoice["status"], str)
    assert isinstance(invoice["created_at"], str)

    # 验证可选字段(首次申请时应为None)
    assert invoice["pdf_url"] is None
    assert invoice["reviewed_by"] is None
    assert invoice["reviewed_at"] is None


@pytest.mark.asyncio
async def test_apply_invoice_multiple_times(test_db):
    """测试多次申请发票(验证是否允许重复申请)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_user_11")

        # 添加充值记录
        from src.core.security.jwt import verify_token
        payload = verify_token(token)
        operator_id = payload["sub"]
        await add_recharge_transaction(test_db, operator_id, 1000.00)

        # 第一次申请
        response1 = await client.post(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "200.00",
                "invoice_title": "第一次申请",
                "tax_id": "91110000111111111A"
            }
        )

        # 第二次申请
        response2 = await client.post(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "300.00",
                "invoice_title": "第二次申请",
                "tax_id": "91110000222222222B"
            }
        )

    # 两次申请都应该成功(业务规则允许多次申请)
    assert response1.status_code == 201
    assert response2.status_code == 201

    # 验证两次申请的invoice_id不同
    invoice_id_1 = response1.json()["data"]["invoice_id"]
    invoice_id_2 = response2.json()["data"]["invoice_id"]
    assert invoice_id_1 != invoice_id_2


@pytest.mark.asyncio
async def test_apply_invoice_invoice_id_format(test_db):
    """测试invoice_id格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "invoice_user_12")

        # 添加充值记录
        from src.core.security.jwt import verify_token
        payload = verify_token(token)
        operator_id = payload["sub"]
        await add_recharge_transaction(test_db, operator_id, 500.00)

        response = await client.post(
            "/v1/operators/me/invoices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "250.00",
                "invoice_title": "验证ID格式公司",
                "tax_id": "91110000333333333C"
            }
        )

    assert response.status_code == 201
    invoice_id = response.json()["data"]["invoice_id"]

    # 验证格式: inv_<uuid>
    assert invoice_id.startswith("inv_")
    assert len(invoice_id) > 4  # "inv_" + UUID部分
