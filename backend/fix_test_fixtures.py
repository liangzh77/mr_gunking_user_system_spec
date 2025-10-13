#!/usr/bin/env python3
"""批量修复测试文件中的模型创建缺少必填字段的问题"""

import re
from pathlib import Path

# 需要修复的测试文件列表
test_files = [
    "tests/integration/test_concurrent_billing.py",
    "tests/integration/test_insufficient_balance.py",
    "tests/integration/test_player_count_validation.py",
    "tests/integration/test_session_id_validation.py",
    "tests/integration/test_session_idempotency.py",
    "tests/unit/services/test_auth_service.py",
    "tests/unit/services/test_billing_service.py",
]

def fix_admin_account(content: str) -> str:
    """修复AdminAccount创建，添加必填字段"""
    # 匹配 AdminAccount( 开始，但不包含 full_name 的情况
    pattern = r'(AdminAccount\s*\(\s*\n\s*username="[^"]+",\s*\n\s*password_hash="[^"]+",\s*\n)(\s*role=)'

    replacement = r'\1        full_name="Test Admin",\n        email="admin@test.com",\n        phone="13800138000",\n\2'

    content = re.sub(pattern, replacement, content)

    return content

def fix_operator_account(content: str) -> str:
    """修复OperatorAccount创建，添加必填字段"""
    # 查找所有OperatorAccount的创建，在username后添加缺失字段
    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]
        result.append(line)

        # 检测到OperatorAccount创建
        if 'OperatorAccount(' in line:
            # 查找接下来的几行，找到username行
            j = i + 1
            has_full_name = False
            username_idx = None

            # 扫描接下来最多20行
            for k in range(j, min(j + 20, len(lines))):
                if 'full_name=' in lines[k]:
                    has_full_name = True
                    break
                if 'username=' in lines[k]:
                    username_idx = k
                if ')' in lines[k] and 'api_key=' not in lines[k]:
                    break

            # 如果没有full_name，需要在username后添加
            if not has_full_name and username_idx:
                # 继续输出到username行
                for k in range(i + 1, username_idx + 1):
                    result.append(lines[k])
                    i = k

                # 添加缺失的字段
                indent = '        '
                result.append(f'{indent}full_name="Test Operator",')
                result.append(f'{indent}email="operator@test.com",')
                result.append(f'{indent}phone="13900139000",')
                result.append(f'{indent}password_hash="hashed_password",')

        i += 1

    return '\n'.join(result)

def fix_operation_site(content: str) -> str:
    """修复OperationSite创建，添加address字段"""
    # 在name=后面添加address
    pattern = r'(OperationSite\s*\([^)]*name="[^"]+",\s*\n)(\s*)(server_identifier=|is_active=)'

    replacement = r'\1\2address="测试地址",\n\2\3'

    content = re.sub(pattern, replacement, content)

    return content

def main():
    for file_path in test_files:
        path = Path(file_path)

        if not path.exists():
            print(f"⚠️  文件不存在: {file_path}")
            continue

        print(f"🔧 修复文件: {file_path}")

        # 读取文件
        content = path.read_text(encoding='utf-8')
        original_content = content

        # 应用修复
        content = fix_admin_account(content)
        content = fix_operator_account(content)
        content = fix_operation_site(content)

        # 如果有修改，写回文件
        if content != original_content:
            path.write_text(content, encoding='utf-8')
            print(f"   ✅ 已修复")
        else:
            print(f"   ℹ️  无需修改")

if __name__ == "__main__":
    main()
    print("\n✅ 批量修复完成！")
