"""完整用户旅程集成测试

这个测试文件验证从运营商注册到游戏授权、计费、财务审核的完整业务流程。
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from httpx import AsyncClient

from src.main import app
from tests.conftest import (
    get_test_admin_token,
    get_test_finance_token,
    reset_database,
    create_test_applications,
    create_test_transactions
)
from tests.contract.test_admin_auth import admin_login
from tests.contract.test_finance_login import finance_login
from tests.contract.test_operator_auth import operator_register, operator_login


class TestCompleteUserJourney:
    """完整用户旅程测试类"""

    @pytest.mark.asyncio
    async def test_complete_operator_journey(self, test_db):
        """测试完整的运营商业务旅程"""

        # 重置数据库
        await reset_database(test_db)

        # 创建测试应用
        await create_test_applications(test_db)

        async with AsyncClient(app=app, base_url="http://test") as client:

            # 第1步: 运营商注册
            print("🚀 开始运营商注册...")
            register_data = {
                "username": "journey_operator",
                "password": "Journey@2025",
                "name": "旅程测试运营商",
                "email": "journey@test.com",
                "phone": "13800138000",
                "company_name": "旅程测试公司"
            }

            reg_response = await client.post("/v1/auth/operators/register", json=register_data)
            assert reg_response.status_code == 201
            reg_data = reg_response.json()
            operator_id = reg_data["operator_id"]

            print(f"✅ 运营商注册成功: {operator_id}")

            # 第2步: 运营商登录
            print("🔐 运营商登录...")
            login_response = await client.post("/v1/auth/operators/login", json={
                "username": "journey_operator",
                "password": "Journey@2025"
            })
            assert login_response.status_code == 200
            login_data = login_response.json()
            operator_token = login_data["access_token"]

            print(f"✅ 运营商登录成功，余额: ¥{login_data['balance']}")

            # 第3步: 查看余额和交易记录
            headers = {"Authorization": f"Bearer {operator_token}"}

            balance_response = await client.get("/v1/balance", headers=headers)
            assert balance_response.status_code == 200
            balance_data = balance_response.json()
            initial_balance = balance_data["balance"]

            print(f"✅ 余额查询成功: ¥{initial_balance}")

            # 第4步: 在线充值
            print("💰 开始在线充值...")
            recharge_data = {
                "amount": "500.00",
                "payment_method": "alipay"
            }

            recharge_response = await client.post(
                "/v1/recharge/orders",
                json=recharge_data,
                headers=headers
            )
            assert recharge_response.status_code == 201
            order_data = recharge_response.json()
            order_id = order_data["order_id"]

            print(f"✅ 充值订单创建成功: {order_id}")

            # 模拟支付回调
            callback_data = {
                "order_id": order_id,
                "status": "success",
                "trade_no": f"ALIPAY_{int(datetime.now().timestamp())}",
                "amount": "500.00"
            }

            callback_response = await client.post(
                "/v1/recharge/callback",
                json=callback_data
            )
            assert callback_response.status_code == 200

            print("✅ 支付回调处理成功")

            # 第5步: 验证余额更新
            new_balance_response = await client.get("/v1/balance", headers=headers)
            assert new_balance_response.status_code == 200
            new_balance = new_balance_response.json()["balance"]

            expected_balance = float(initial_balance) + 500.00
            assert abs(new_balance - expected_balance) < 0.01  # 允许小数精度误差

            print(f"✅ 余额更新成功: ¥{new_balance}")

            # 第6步: 创建运营点
            print("🏢 创建运营点...")
            site_data = {
                "site_name": "旅程测试运营点",
                "contact_person": "张测试",
                "contact_phone": "13800138001",
                "address": "北京市朝阳区测试街道123号"
            }

            site_response = await client.post(
                "/v1/sites",
                json=site_data,
                headers=headers
            )
            assert site_response.status_code == 201
            site_data = site_response.json()
            site_id = site_data["site_id"]

            print(f"✅ 运营点创建成功: {site_id}")

            # 第7步: 游戏授权测试
            print("🎮 开始游戏授权测试...")
            app_id = 1  # 假设应用ID 1存在
            session_id = f"test_session_{int(datetime.now().timestamp())}"

            auth_request = {
                "app_id": app_id,
                "player_count": 4,
                "session_id": session_id,
                "site_id": site_id
            }

            auth_response = await client.post(
                "/v1/games/authorize",
                json=auth_request,
                headers=headers
            )
            assert auth_response.status_code == 200
            auth_data = auth_response.json()

            assert auth_data["success"] is True
            assert "auth_token" in auth_data
            assert auth_data["player_count"] == 4

            print(f"✅ 游戏授权成功: {auth_data['session_id']}")

            # 模拟游戏运行
            await asyncio.sleep(2)

            # 第8步: 结束游戏会话
            print("🏁 结束游戏会话...")
            end_request = {
                "app_id": app_id,
                "session_id": session_id,
                "player_count": 4,
                "site_id": site_id
            }

            end_response = await client.post(
                "/v1/games/end-session",
                json=end_request,
                headers=headers
            )
            assert end_response.status_code == 200
            end_data = end_response.json()

            assert end_data["success"] is True
            assert end_data["total_cost"] > 0

            print(f"✅ 会话结束成功，费用: ¥{end_data['total_cost']}")

            # 第9步: 查看交易记录
            print("📊 查看交易记录...")
            transactions_response = await client.get(
                "/v1/transactions",
                headers=headers,
                params={"page": 1, "page_size": 10}
            )
            assert transactions_response.status_code == 200
            transactions_data = transactions_response.json()

            assert transactions_data["total"] >= 3  # 注册奖励、充值、游戏消费
            print(f"✅ 找到 {transactions_data['total']} 条交易记录")

            # 第10步: 申请退款
            print("💸 申请退款...")
            refund_data = {
                "reason": "测试退款流程",
                "amount": "50.00"
            }

            refund_response = await client.post(
                "/v1/refunds",
                json=refund_data,
                headers=headers
            )
            assert refund_response.status_code == 201
            refund_request_id = refund_response.json()["refund_request_id"]

            print(f"✅ 退款申请提交成功: {refund_request_id}")

    @pytest.mark.asyncio
    async def test_admin_approval_workflow(self, test_db):
        """测试管理员审批工作流程"""

        async with AsyncClient(app=app, base_url="http://test") as client:

            # 管理员登录
            admin_token = await admin_login(client)
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            print("👑 管理员登录成功")

            # 查看待审核的退款申请
            refunds_response = await client.get(
                "/v1/admin/refunds",
                headers=admin_headers,
                params={"status": "pending"}
            )
            assert refunds_response.status_code == 200

            refunds_data = refunds_response.json()
            if refunds_data["items"]:
                refund_request_id = refunds_data["items"][0]["refund_request_id"]

                # 审批退款
                approve_data = {
                    "status": "approved",
                    "review_note": "测试审批流程"
                }

                approve_response = await client.post(
                    f"/v1/admin/refunds/{refund_request_id}/review",
                    json=approve_data,
                    headers=admin_headers
                )
                assert approve_response.status_code == 200

                print(f"✅ 退款审批成功: {refund_request_id}")
            else:
                print("ℹ️  暂无待审核的退款申请")

    @pytest.mark.asyncio
    async def test_finance_dashboard_workflow(self, test_db):
        """测试财务后台工作流程"""

        async with AsyncClient(app=app, base_url="http://test") as client:

            # 财务人员登录
            finance_token = await finance_login(client)
            finance_headers = {"Authorization": f"Bearer {finance_token}"}

            print("💰 财务人员登录成功")

            # 查看财务仪表盘
            dashboard_response = await client.get(
                "/v1/finance/dashboard",
                headers=finance_headers
            )
            assert dashboard_response.status_code == 200

            dashboard_data = dashboard_response.json()

            assert "today_revenue" in dashboard_data
            "today_orders" in dashboard_data
            "total_balance" in dashboard_data

            print(f"✅ 财务仪表盘加载成功")
            print(f"   今日收入: ¥{dashboard_data.get('today_revenue', 0)}")
            print(f"   今日订单: {dashboard_data.get('today_orders', 0)}")
            print(f"   总余额: ¥{dashboard_data.get('total_balance', 0)}")

            # 查看客户统计
            customers_response = await client.get(
                "/v1/finance/top-customers",
                headers=finance_headers,
                params={"limit": 10}
            )
            assert customers_response.status_code == 200

            customers_data = customers_response.json()
            print(f"✅ 客户统计加载成功，Top {len(customers_data.get('items', []))} 位客户")

    @pytest.mark.asyncio
    async def test_system_integration_stress(self, test_db):
        """测试系统集成压力测试"""

        async with AsyncClient(app=app, base_url="http://test") as client:

            # 创建多个运营商账户
            operators = []
            for i in range(3):
                register_data = {
                    "username": f"stress_operator_{i}",
                    "password": f"Stress@2025{i}",
                    "name": f"压力测试运营商{i}",
                    "email": f"stress{i}@test.com",
                    "phone": f"1380013800{i}",
                    "company_name": f"压力测试公司{i}"
                }

                reg_response = await client.post("/v1/auth/operators/register", json=register_data)
                assert reg_response.status_code == 201

                login_response = await client.post("/v1/auth/operators/login", json={
                    "username": f"stress_operator_{i}",
                    "password": f"Stress@2025{i}"
                })
                assert login_response.status_code == 200

                operators.append({
                    "username": f"stress_operator_{i}",
                    "token": login_response.json()["access_token"],
                    "operator_id": reg_response.json()["operator_id"]
                })

            print(f"✅ 创建了 {len(operators)} 个运营商账户")

            # 并发游戏授权测试
            auth_tasks = []
            for i, operator in enumerate(operators):
                for j in range(2):  # 每个运营商2个并发会话
                    task = self._create_game_session(
                        client, operator["token"],
                        operator["operator_id"],
                        i, j
                    )
                    auth_tasks.append(task)

            # 并发执行游戏授权
            auth_results = await asyncio.gather(*auth_tasks, return_exceptions=True)

            # 统计成功结果
            successful_auths = sum(1 for result in auth_results if isinstance(result, bool) and result)
            failed_auths = len(auth_results) - successful_auths

            print(f"✅ 并发游戏授权测试完成")
            print(f"   成功授权: {successful_auths}")
            print(f"   失败授权: {failed_auths}")

            # 验证成功率
            success_rate = successful_auths / len(auth_tasks)
            assert success_rate >= 0.8, f"授权成功率过低: {success_rate:.2%}"
            print(f"   成功率: {success_rate:.2%} ✅")

    async def _create_game_session(self, client, token, operator_id, operator_index, session_index):
        """创建单个游戏会话的辅助方法"""
        try:
            headers = {"Authorization": f"Bearer {token}"}

            session_id = f"stress_{operator_index}_{session_index}_{int(datetime.now().timestamp())}"
            app_id = 1

            # 游戏授权
            auth_response = await client.post(
                "/v1/games/authorize",
                json={
                    "app_id": app_id,
                    "player_count": 3,
                    "session_id": session_id
                },
                headers=headers
            )

            if auth_response.status_code == 200:
                auth_data = auth_response.json()

                # 等待一会
                await asyncio.sleep(1)

                # 结束会话
                end_response = await client.post(
                    "/v1/games/end-session",
                    json={
                        "app_id": app_id,
                        "session_id": session_id,
                        "player_count": 3
                    },
                    headers=headers
                )

                return end_response.status_code == 200

            return False

        except Exception as e:
            print(f"会话创建异常: {e}")
            return False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])