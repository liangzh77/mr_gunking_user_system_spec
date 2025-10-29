#!/usr/bin/env python3
"""批量创建运营商"""
import asyncio
import sys
import csv
import secrets
sys.path.insert(0, '/app')

from decimal import Decimal
from src.db.session import init_db, get_db_context
from src.models import OperatorAccount
from src.core.utils.password import hash_password

async def batch_create_operators(csv_file_path):
    init_db()
    success_count = 0
    fail_count = 0

    async with get_db_context() as session:
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        # 生成API密钥
                        api_key = secrets.token_urlsafe(32)

                        operator = OperatorAccount(
                            username=row['username'],
                            password_hash=hash_password(row['password']),
                            full_name=row['full_name'],
                            email=row['email'],
                            phone=row['phone'],
                            balance=Decimal(row['initial_balance']),
                            api_key=api_key,
                            api_key_hash=hash_password(api_key),
                            is_active=True,
                        )
                        session.add(operator)
                        print(f"✅ 创建成功: {row['username']} - {row['full_name']}")
                        success_count += 1
                    except Exception as e:
                        print(f"❌ 创建失败: {row['username']} - {str(e)}")
                        fail_count += 1

            await session.commit()

            print(f"\n批量创建完成！成功: {success_count}, 失败: {fail_count}")

        except FileNotFoundError:
            print(f"❌ 文件不存在: {csv_file_path}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 批量创建失败: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python batch_create_operators.py <csv_file_path>")
        print("CSV format: username,password,full_name,email,phone,initial_balance")
        sys.exit(1)

    asyncio.run(batch_create_operators(sys.argv[1]))
