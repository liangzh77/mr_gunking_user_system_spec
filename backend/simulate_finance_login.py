#!/usr/bin/env python3
"""模拟财务登录完整流程测试"""

import sys
import json
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def simulate_api_response():
    """模拟API响应逻辑"""
    print("=== 模拟财务登录API响应 ===")

    # 模拟请求数据
    request_data = {
        "username": "finance001",
        "password": "Pass@2024!"
    }

    print(f"1. 收到登录请求: {request_data}")

    # 模拟数据库查询结果
    mock_db_user = {
        "id": "35d5594e-98f6-4d6d-aef2-2b16c7266bdc",
        "username": "finance001",
        "password_hash": "$2b$10$RcJHPKOXa/H.7RM34A744.v93wgO8bem6rD4bEWRuxNhxQjKZ1zOi",
        "full_name": "张发财",
        "email": "finance001@mrgameops.com",
        "role": "finance",
        "is_active": True,
        "permissions": ["finance:read", "finance:recharge", "finance:refund"]
    }

    print(f"2. 数据库查询结果: 找到用户 {mock_db_user['username']}")
    print(f"   - 角色: {mock_db_user['role']}")
    print(f"   - 激活状态: {mock_db_user['is_active']}")
    print(f"   - 密码哈希: {mock_db_user['password_hash'][:20]}...")

    # 模拟密码验证
    def mock_verify_password(password, hash_value):
        # 模拟bcrypt验证逻辑
        if password == "Pass@2024!" and hash_value.startswith("$2b$"):
            return True
        return False

    password_valid = mock_verify_password(request_data["password"], mock_db_user["password_hash"])
    print(f"3. 密码验证结果: {'通过' if password_valid else '失败'}")

    if not password_valid:
        return {
            "success": False,
            "error": "用户名或密码错误"
        }

    # 模拟角色验证
    if mock_db_user["role"] != "finance":
        return {
            "success": False,
            "error": "用户不是财务角色，无法访问财务系统"
        }

    print("4. 角色验证: 通过 (finance)")

    # 模拟JWT Token生成
    mock_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzNWQ1NTk0ZS05OGY2LTRkNmQtYWVmMi0yYjE2YzcyNzZiZGMiLCJ1c2VyX3R5cGUiOiJmaW5hbmNlIiwidXNlcm5hbWUiOiJmaW5hbmNlMDAxIiwicm9sZSI6ImZpbmFuY2UiLCJleHAiOjE3MjI3MzY4MDB9.signature"

    # 返回成功响应
    response = {
        "access_token": mock_token,
        "token_type": "bearer",
        "expires_in": 86400,
        "finance": {
            "finance_id": mock_db_user["id"],
            "username": mock_db_user["username"],
            "name": mock_db_user["full_name"],
            "full_name": mock_db_user["full_name"],
            "role": "finance",
            "email": mock_db_user["email"]
        }
    }

    print("5. 生成JWT Token: 成功")
    print("6. 返回登录响应: 成功")

    return response

def test_problem_scenarios():
    """测试问题场景"""
    print("\n=== 测试问题场景 ===")

    scenarios = [
        {
            "name": "用户不存在",
            "db_user": None,
            "request": {"username": "nonexist", "password": "Pass@2024!"},
            "expected_error": "用户名或密码错误"
        },
        {
            "name": "密码错误",
            "db_user": {"username": "finance001", "password_hash": "$2b$10$...", "role": "finance", "is_active": True},
            "request": {"username": "finance001", "password": "wrong_password"},
            "expected_error": "用户名或密码错误"
        },
        {
            "name": "用户未激活",
            "db_user": {"username": "finance001", "password_hash": "$2b$10$...", "role": "finance", "is_active": False},
            "request": {"username": "finance001", "password": "Pass@2024!"},
            "expected_error": "账号已禁用"
        },
        {
            "name": "角色错误",
            "db_user": {"username": "finance001", "password_hash": "$2b$10$...", "role": "admin", "is_active": True},
            "request": {"username": "finance001", "password": "Pass@2024!"},
            "expected_error": "用户不是财务角色"
        }
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n场景 {i}: {scenario['name']}")

        if scenario["db_user"] is None:
            print(f"  ❌ 数据库查询结果: 用户不存在")
        elif not scenario["db_user"]["is_active"]:
            print(f"  ❌ 用户状态: 未激活")
        elif scenario["db_user"]["role"] != "finance":
            print(f"  ❌ 用户角色: {scenario['db_user']['role']} (需要finance)")
        else:
            print(f"  ❌ 密码验证: 失败")

        print(f"  ✅ 预期错误: {scenario['expected_error']}")

def analyze_login_flow():
    """分析登录流程"""
    print("\n=== 登录流程分析 ===")

    steps = [
        "1. 接收POST /v1/auth/finance/login请求",
        "2. 解析请求体 {username, password}",
        "3. 使用AdminAuthService查找admin_accounts表",
        "4. 验证用户存在且is_active=true",
        "5. 使用bcrypt验证密码",
        "6. 验证用户role='finance'",
        "7. 生成JWT Token (user_type='finance')",
        "8. 返回成功响应"
    ]

    print("正常登录流程:")
    for step in steps:
        print(f"  ✅ {step}")

    print("\n可能的问题点:")
    problems = [
        "🔍 admin_accounts表中没有finance001用户",
        "🔍 用户存在但is_active=false",
        "🔍 用户的role字段不是'finance'",
        "🔍 密码哈希格式错误或密码不匹配",
        "🔍 数据库连接问题",
        "🔍 AdminAuthService导入或初始化失败"
    ]

    for problem in problems:
        print(f"  {problem}")

def main():
    """主测试函数"""
    print("财务登录完整流程模拟测试")
    print("=" * 60)

    # 正常流程测试
    print("📋 测试1: 正常登录流程")
    response = simulate_api_response()

    if response:
        print("\n✅ 登录成功响应:")
        print(json.dumps(response, indent=2, ensure_ascii=False))
    else:
        print("\n❌ 登录失败")

    # 问题场景测试
    test_problem_scenarios()

    # 流程分析
    analyze_login_flow()

    print("\n" + "=" * 60)
    print("🎯 诊断建议:")
    print("1. 确认生产环境数据库连接正常")
    print("2. 检查admin_accounts表中finance001用户是否存在")
    print("3. 验证用户的role、is_active、password_hash字段")
    print("4. 确认代码修复已部署到生产环境")
    print("5. 检查API服务日志中的具体错误信息")

    print("\n🔧 立即可执行的检查命令:")
    print("docker exec mr_game_ops_backend_prod python -c \\\"")
    print("import asyncio, asyncpg")
    print("async def check():")
    print("    conn = await asyncpg.connect('postgresql://mr_admin:CHANGE_THIS_PASSWORD@postgres:5432/mr_game_ops')")
    print("    user = await conn.fetchrow('SELECT * FROM admin_accounts WHERE username = \\\\$1', 'finance001')")
    print("    if user: print(f'用户存在: {user}')")
    print("    else: print('用户不存在')")
    print("    await conn.close()")
    print("asyncio.run(check())\\\"")

if __name__ == '__main__':
    main()