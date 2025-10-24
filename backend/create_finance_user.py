#!/usr/bin/env python3
"""创建财务人员账户"""

import asyncio
import sys
from pathlib import Path
import uuid
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from src.core.utils.password import hash_password

async def create_finance_user():
    """创建财务人员账户"""

    db_url = "postgresql+asyncpg://mr_admin:mr_secure_password_2024@localhost:5432/mr_game_ops"
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # 检查是否已存在财务用户
            result = await session.execute(
                text("SELECT COUNT(*) FROM admin_accounts WHERE username = 'finance'")
            )
            count = result.scalar()

            if count > 0:
                print("Finance user already exists")
                return True

            # 直接使用SQL插入财务账户
            finance_id = str(uuid.uuid4())
            password_hash = hash_password("Finance123!")
            current_time = datetime.utcnow()

            await session.execute(text("""
                INSERT INTO admin_accounts (
                    id, username, password_hash, full_name, email, phone,
                    role, permissions, is_active, created_at, updated_at
                ) VALUES (
                    :id, :username, :password_hash, :full_name, :email, :phone,
                    :role, :permissions, :is_active, :created_at, :updated_at
                )
            """), {
                'id': finance_id,
                'username': 'finance',
                'password_hash': password_hash,
                'full_name': '财务专员',
                'email': 'finance@mrgameops.com',
                'phone': '13800138002',
                'role': 'finance',
                'permissions': '["finance:*", "report:view"]',
                'is_active': True,
                'created_at': current_time,
                'updated_at': current_time
            })

            await session.commit()

            print("Successfully created finance user account")
            print(f"   Username: finance")
            print(f"   Password: Finance123!")
            print(f"   Role: finance")
            return True

    except Exception as e:
        print(f"Failed to create finance user: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(create_finance_user())
    if success:
        print("Finance user account creation completed!")
    else:
        print("Finance user account creation failed!")