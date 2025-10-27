"""
集成测试：财务报表生成 (T159)

测试财务报表生成的完整流程
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from src.models.finance import FinanceAccount
from src.models.operator import OperatorAccount
from src.models.transaction import TransactionRecord
from src.core.utils.password import get_password_hash


@pytest.fixture
async def finance_account(db_session: AsyncSession):
    """创建测试财务账号"""
    finance = FinanceAccount(
        username="finance_report_test",
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


@pytest.fixture
async def test_operator(db_session: AsyncSession):
    """创建测试运营商"""
    operator = OperatorAccount(
        username="operator_report_test",
        password_hash=get_password_hash("Password123"),
        company_name="测试公司",
        contact_name="张三",
        phone="13900139000",
        email="operator@test.com",
        balance=1000.00,
        is_active=True
    )
    db_session.add(operator)
    await db_session.commit()
    await db_session.refresh(operator)
    return operator


@pytest.fixture
async def finance_token(client: AsyncClient, finance_account: FinanceAccount):
    """获取财务人员 token"""
    response = await client.post(
        "/v1/auth/finance/login",
        json={
            "username": "finance_report_test",
            "password": "FinancePass123"
        }
    )
    return response.json()["access_token"]


@pytest.mark.asyncio
class TestFinanceReportGeneration:
    """财务报表生成集成测试"""

    async def test_generate_daily_report(self, 
                                        client: AsyncClient,
                                        finance_token: str,
                                        test_operator: OperatorAccount,
                                        db_session: AsyncSession):
        """测试生成日报"""
        # 创建测试交易记录
        today = datetime.utcnow().date()
        transaction = TransactionRecord(
            operator_id=test_operator.id,
            transaction_type="recharge",
            amount=500.00,
            balance_before=1000.00,
            balance_after=1500.00,
            description="测试充值"
        )
        db_session.add(transaction)
        await db_session.commit()

        # 生成日报
        response = await client.post(
            "/v1/finance/reports/generate",
            json={
                "report_type": "daily",
                "start_date": today.isoformat(),
                "end_date": today.isoformat()
            },
            headers={"Authorization": f"Bearer {finance_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data
        assert "status" in data
        assert data["status"] in ["pending", "completed"]


    async def test_generate_monthly_report(self,
                                          client: AsyncClient,
                                          finance_token: str):
        """测试生成月报"""
        today = datetime.utcnow()
        start_date = today.replace(day=1).date()
        end_date = today.date()

        response = await client.post(
            "/v1/finance/reports/generate",
            json={
                "report_type": "monthly",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            headers={"Authorization": f"Bearer {finance_token}"}
        )

        assert response.status_code == 200


    async def test_list_reports(self,
                               client: AsyncClient,
                               finance_token: str):
        """测试查询报表列表"""
        response = await client.get(
            "/v1/finance/reports",
            headers={"Authorization": f"Bearer {finance_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "reports" in data or isinstance(data, list)


    async def test_export_report(self,
                                 client: AsyncClient,
                                 finance_token: str):
        """测试导出报表"""
        # 先生成一个报表
        today = datetime.utcnow().date()
        generate_response = await client.post(
            "/v1/finance/reports/generate",
            json={
                "report_type": "daily",
                "start_date": today.isoformat(),
                "end_date": today.isoformat()
            },
            headers={"Authorization": f"Bearer {finance_token}"}
        )

        if generate_response.status_code == 200:
            report_data = generate_response.json()
            if "report_id" in report_data:
                report_id = report_data["report_id"]

                # 导出报表
                export_response = await client.get(
                    f"/v1/finance/reports/{report_id}/export",
                    headers={"Authorization": f"Bearer {finance_token}"}
                )

                # 导出可能返回 200 或重定向到下载链接
                assert export_response.status_code in [200, 302]


    async def test_generate_report_without_auth(self, client: AsyncClient):
        """测试未授权生成报表 - 应返回 401"""
        today = datetime.utcnow().date()
        response = await client.post(
            "/v1/finance/reports/generate",
            json={
                "report_type": "daily",
                "start_date": today.isoformat(),
                "end_date": today.isoformat()
            }
        )

        assert response.status_code == 401
