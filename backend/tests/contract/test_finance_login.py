"""
契约测试：财务人员登录接口 (T155)

测试 POST /v1/auth/finance/login 接口的契约符合性

Contract: specs/001-mr-v2/contracts/auth.yaml /auth/finance/login
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.finance import FinanceAccount
from src.core.utils.password import get_password_hash


@pytest.fixture
async def finance_account(db_session: AsyncSession):
    """创建测试财务账号"""
    finance = FinanceAccount(
        username="finance_test",
        password_hash=get_password_hash("FinancePass123"),
        full_name="测试财务",
        phone="13800138000",
        email="finance@test.com",
        role="specialist",
        is_active=True
    )
    db_session.add(finance)
    await db_session.commit()
    await db_session.refresh(finance)
    return finance


@pytest.mark.asyncio
class TestFinanceLoginContract:
    """财务登录接口契约测试"""

    async def test_successful_login(self, client: AsyncClient, finance_account: FinanceAccount):
        """成功登录 - 返回 200 和 token"""
        response = await client.post(
            "/v1/auth/finance/login",
            json={
                "username": "finance_test",
                "password": "FinancePass123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # 验证响应结构
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "finance_info" in data

        # 验证 token 类型
        assert data["token_type"] == "bearer"
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

        # 验证财务信息
        finance_info = data["finance_info"]
        assert finance_info["id"] == str(finance_account.id)
        assert finance_info["username"] == "finance_test"
        assert finance_info["full_name"] == "测试财务"
        assert finance_info["role"] == "specialist"


    async def test_login_with_wrong_password(self, client: AsyncClient, finance_account: FinanceAccount):
        """错误密码 - 返回 401"""
        response = await client.post(
            "/v1/auth/finance/login",
            json={
                "username": "finance_test",
                "password": "WrongPassword123"
            }
        )

        assert response.status_code == 401


    async def test_login_with_nonexistent_user(self, client: AsyncClient):
        """不存在的用户名 - 返回 401"""
        response = await client.post(
            "/v1/auth/finance/login",
            json={
                "username": "nonexistent_finance",
                "password": "AnyPassword123"
            }
        )

        assert response.status_code == 401
