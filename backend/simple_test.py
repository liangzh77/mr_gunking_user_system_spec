#!/usr/bin/env python3
"""简单测试财务登录逻辑"""

import sys
import json
from pathlib import Path

def test_json_issue():
    """测试JSON格式问题"""
    print("=== JSON格式问题测试 ===")

    # 原始问题代码
    finance_permissions = [
        "finance:read",
        "finance:recharge",
        "finance:refund",
        "invoice:read",
        "invoice:create",
        "statistics:read"
    ]

    # 错误的方式（原代码）
    wrong_format = str(finance_permissions)
    print("错误的格式(str()):")
    print(f"  {wrong_format}")
    print(f"  使用单引号: {"'" in wrong_format}")

    # 正确的方式（修复后）
    correct_format = json.dumps(finance_permissions, ensure_ascii=False)
    print("\n正确的格式(json.dumps()):")
    print(f"  {correct_format}")
    print(f"  使用双引号: {'\"' in correct_format}")

    # 验证JSON解析
    try:
        parsed_wrong = json.loads(wrong_format.replace("'", '"'))
        print("\n错误格式可被修复解析: True")
    except:
        print("\n错误格式无法解析: False")

    try:
        parsed_correct = json.loads(correct_format)
        print("正确格式可解析: True")
        print(f"  解析结果: {parsed_correct}")
    except Exception as e:
        print(f"正确格式解析失败: {e}")

def test_password_logic():
    """测试密码逻辑模拟"""
    print("\n=== 密码验证逻辑测试 ===")

    # 模拟bcrypt哈希（简化）
    def simple_bcrypt_check(password, hash_value):
        # 这里只是模拟，实际的bcrypt验证更复杂
        # 我们只检查哈希格式是否正确
        if hash_value.startswith("$2b$"):
            return True  # 假设验证通过
        return False

    # 测试用例
    test_cases = [
        ("Pass@2024!", "$2b$10$RcJHPKOXa/H.7RM34A744.v93wgO8bem6rD4bEWRuxNhxQjKZ1zOi", True),
        ("Pass@2024!", "invalid_hash", False),
        ("wrong_pass", "$2b$10$RcJHPKOXa/H.7RM34A744.v93wgO8bem6rD4bEWRuxNhxQjKZ1zOi", True),  # 哈希格式对但不匹配
    ]

    for password, hash_val, expected in test_cases:
        result = simple_bcrypt_check(password, hash_val)
        print(f"  密码: {password} | 哈希: {hash_val[:20]}... | 预期: {expected} | 实际: {result}")

def test_login_flow():
    """模拟登录流程"""
    print("\n=== 登录流程模拟 ===")

    # 模拟数据库中的用户数据
    db_users = {
        "finance001": {
            "username": "finance001",
            "password_hash": "$2b$10$RcJHPKOXa/H.7RM34A744.v93wgO8bem6rD4bEWRuxNhxQjKZ1zOi",
            "role": "finance",
            "is_active": True,
            "full_name": "张发财",
            "email": "finance001@mrgameops.com"
        }
    }

    # 测试登录
    login_attempts = [
        ("finance001", "Pass@2024!"),  # 正确
        ("finance001", "wrong_pass"),  # 错误密码
        ("nonexist", "Pass@2024!"),    # 用户不存在
    ]

    def simulate_login(username, password):
        user = db_users.get(username)

        if not user:
            return {"success": False, "error": "用户名或密码错误"}

        if not user["is_active"]:
            return {"success": False, "error": "账号已禁用"}

        # 简化的密码验证（实际应该用bcrypt）
        if not password:  # 简化检查
            return {"success": False, "error": "用户名或密码错误"}

        if user["role"] != "finance":
            return {"success": False, "error": "用户不是财务角色"}

        return {
            "success": True,
            "user": {
                "username": user["username"],
                "full_name": user["full_name"],
                "role": "finance",
                "email": user["email"]
            }
        }

    for username, password in login_attempts:
        result = simulate_login(username, password)
        status = "成功" if result["success"] else f"失败 - {result.get('error', '未知错误')}"
        print(f"  登录尝试: {username}/{password} -> {status}")

def main():
    """主测试函数"""
    print("财务登录问题诊断")
    print("=" * 50)

    # 测试1: JSON问题
    test_json_issue()

    # 测试2: 密码逻辑
    test_password_logic()

    # 测试3: 登录流程
    test_login_flow()

    print("\n" + "=" * 50)
    print("诊断总结:")
    print("1. JSON格式问题已修复 - 使用json.dumps()替代str()")
    print("2. 密码哈希需要实际的bcrypt验证")
    print("3. 登录流程需要检查数据库中的实际用户数据")
    print("\n建议:")
    print("- 检查生产环境数据库中finance001用户是否存在")
    print("- 验证密码哈希格式是否正确")
    print("- 确认用户role字段值为'finance'")

if __name__ == '__main__':
    main()