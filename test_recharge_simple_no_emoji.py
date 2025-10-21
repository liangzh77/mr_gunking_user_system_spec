#!/usr/bin/env python3
"""简单测试手动充值API"""

import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.api.v1.finance import router


def test_recharge_endpoint():
    """测试充值API端点是否已正确注册"""

    print("检查手动充值API端点配置...")

    # 检查路由是否已注册
    routes = [route.path for route in router.routes]
    if "/finance/recharge" in routes:
        print("[OK] 手动充值API端点已注册")
    else:
        print("[ERROR] 手动充值API端点未注册")
        return False

    # 查找充值路由详情
    recharge_route = None
    for route in router.routes:
        if hasattr(route, 'path') and route.path == "/finance/recharge":
            recharge_route = route
            break

    if recharge_route:
        print("[OK] 手动充值API路由已配置")
        print("   方法:", recharge_route.methods)
        print("   路径:", recharge_route.path)

        # 检查是否有对应的函数
        if hasattr(recharge_route, 'endpoint'):
            print("   端点函数:", recharge_route.endpoint.__name__)
        else:
            print("   [WARNING] 端点函数信息不可用")
    else:
        print("[ERROR] 手动充值API路由未找到")
        return False

    print("\n检查充值服务是否可用...")
    try:
        from src.services.finance_recharge_service import FinanceRechargeService
        print("[OK] 充值服务已导入")

        # 检查服务方法是否存在
        service_methods = [method for method in dir(FinanceRechargeService) if not method.startswith('_')]
        required_methods = ['manual_recharge']

        for method in required_methods:
            if method in service_methods:
                print("[OK]", method, "方法存在")
            else:
                print("[ERROR]", method, "方法不存在")
                return False

    except ImportError as e:
        print("[ERROR] 充值服务导入失败:", e)
        return False

    print("\n[OK] 手动充值API配置检查完成!")
    return True


if __name__ == "__main__":
    print("开始验证手动充值API配置...")
    success = test_recharge_endpoint()
    if success:
        print("\n[SUCCESS] 手动充值API已正确配置，可以正常使用!")
    else:
        print("\n[FAILED] 手动充值API配置存在问题，需要修复!")