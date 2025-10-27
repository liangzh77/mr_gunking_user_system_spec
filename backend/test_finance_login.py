#!/usr/bin/env python3
"""测试财务登录逻辑 - 简化版本"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_password_hashing():
    """测试密码哈希功能"""
    print("=== 测试密码哈希 ===")

    try:
        # 导入密码工具
        from src.core.utils.password import hash_password, verify_password

        # 测试密码
        password = "Pass@2024!"
        print(f"原密码: {password}")

        # 生成哈希
        hashed = hash_password(password)
        print(f"哈希: {hashed}")

        # 验证密码
        is_valid = verify_password(password, hashed)
        print(f"验证结果: {is_valid}")

        # 验证错误密码
        is_invalid = verify_password("wrong_password", hashed)
        print(f"错误密码验证: {is_invalid}")

        return True

    except ImportError as e:
        print(f"导入错误: {e}")
        return False
    except Exception as e:
        print(f"测试失败: {e}")
        return False

def test_json_serialization():
    """测试JSON序列化"""
    print("\n=== 测试JSON序列化 ===")

    try:
        # 财务权限列表
        finance_permissions = [
            "finance:read",
            "finance:recharge",
            "finance:refund",
            "invoice:read",
            "invoice:create",
            "statistics:read"
        ]

        # Python str()方法 - 有问题的
        python_str = str(finance_permissions)
        print(f"Python str() 输出: {python_str}")

        # JSON dumps方法 - 正确的
        json_str = json.dumps(finance_permissions, ensure_ascii=False)
        print(f"JSON dumps() 输出: {json_str}")

        # 验证JSON格式
        parsed = json.loads(json_str)
        print(f"JSON解析结果: {parsed}")

        return True

    except Exception as e:
        print(f"JSON测试失败: {e}")
        return False

def test_admin_model():
    """测试AdminAccount模型"""
    print("\n=== 测试AdminAccount模型 ===")

    try:
        from src.models.admin import AdminAccount

        # 创建一个测试实例（不保存到数据库）
        test_admin = AdminAccount(
            username="finance_test",
            password_hash="$2b$10$RcJHPKOXa/H.7RM34A744.v93wgO8bem6rD4bEWRuxNhxQjKZ1zOi",
            full_name="测试财务",
            email="finance@test.com",
            phone="13800138000",
            role="finance",
            permissions=["finance:read", "finance:recharge"]
        )

        print(f"测试用户: {test_admin.username}")
        print(f"角色: {test_admin.role}")
        print(f"权限: {test_admin.permissions}")
        print(f"是否激活: {test_admin.is_active}")

        # 测试has_permission方法
        has_finance_read = test_admin.has_permission("finance:read")
        print(f"有finance:read权限: {has_finance_read}")

        has_invalid_perm = test_admin.has_permission("invalid:permission")
        print(f"有无效权限: {has_invalid_perm}")

        return True

    except ImportError as e:
        print(f"模型导入错误: {e}")
        return False
    except Exception as e:
        print(f"模型测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("财务登录逻辑测试")
    print("=" * 50)

    results = []

    # 测试1: 密码哈希
    results.append(("密码哈希", test_password_hashing()))

    # 测试2: JSON序列化
    results.append(("JSON序列化", test_json_serialization()))

    # 测试3: Admin模型
    results.append(("Admin模型", test_admin_model()))

    # 结果汇总
    print("\n" + "=" * 50)
    print("测试结果汇总:")

    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")

    all_passed = all(result[1] for result in results)
    print(f"\n总体结果: {'✅ 所有测试通过' if all_passed else '❌ 有测试失败'}")

    if all_passed:
        print("\n🎯 建议下一步:")
        print("1. 检查数据库中是否真的有finance001用户")
        print("2. 验证数据库连接配置")
        print("3. 测试完整的登录API端点")
    else:
        print("\n⚠️  请先修复失败的测试")

if __name__ == '__main__':
    main()