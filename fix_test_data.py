#!/usr/bin/env python3
"""修复测试数据中的balance_before字段缺失问题"""

import re

def fix_test_file():
    file_path = "backend/tests/contract/test_finance_dashboard.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复第一个交易记录
    content = re.sub(
        r'(tx1 = TransactionRecord\([^}]+?amount=Decimal\("500\.00"\),\s*)\n\s*balance_after=',
        r'\1\n        balance_before=Decimal("1000.00"),\n        balance_after=',
        content
    )

    # 修复第二个交易记录
    content = re.sub(
        r'(tx2 = TransactionRecord\([^}]+?amount=Decimal\("200\.00"\),\s*)\n\s*balance_after=',
        r'\1\n        balance_before=Decimal("1500.00"),\n        balance_after=',
        content
    )

    # 修复第三个交易记录
    content = re.sub(
        r'(tx3 = TransactionRecord\([^}]+?amount=Decimal\("300\.00"\),\s*)\n\s*balance_after=',
        r'\1\n        balance_before=Decimal("500.00"),\n        balance_after=',
        content
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("测试文件已修复")

if __name__ == "__main__":
    fix_test_file()