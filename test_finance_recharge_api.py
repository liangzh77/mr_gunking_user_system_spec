#!/usr/bin/env python3
"""测试财务手动充值API"""

import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import asyncio
from httpx import AsyncClient
from src.main import app


async def test_finance_manual_recharge():
    """测试财务手动充值API"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        print("1. 测试未认证访问手动充值API...")
        response = await client.post("/v1/finance/recharge")
        print(f"   状态码: {response.status_code} (期望: 401)")

        print("\n2. 测试手动充值API端点是否存在...")
        # 由于需要财务认证，我们无法直接测试，但可以验证端点路由
        from src.api.v1.finance import router
        routes = [route.path for route in router.routes]
        if "/finance/recharge" in routes:
            print("   ✅ 手动充值API端点已注册")
        else:
            print("   ❌ 手动充值API端点未注册")

        print("\n3. 检查充值服务是否可用...")
        try:
            from src.services.finance_recharge_service import FinanceRechargeService
            print("   ✅ 充值服务已导入")

            # 检查服务方法是否存在
            service_methods = [method for method in dir(FinanceRechargeService) if not method.startswith('_')]
            if 'manual_recharge' in service_methods:
                print("   ✅ manual_recharge方法存在")
            else:
                print("   ❌ manual_recharge方法不存在")

        except ImportError as e:
            print(f"   ❌ 充值服务导入失败: {e}")

        print("\n4. 检查后端API实现...")
        from src.api.v1.finance import router
        recharge_route = None
        for route in router.routes:
            if hasattr(route, 'path') and route.path == "/finance/recharge":
                recharge_route = route
                break

        if recharge_route:
            print("   ✅ 手动充值API路由已配置")
            print(f"   方法: {recharge_route.methods}")
        else:
            print("   ❌ 手动充值API路由未找到")


if __name__ == "__main__":
    print("开始测试财务手动充值API...")
    asyncio.run(test_finance_manual_recharge())
    print("\n测试完成!")