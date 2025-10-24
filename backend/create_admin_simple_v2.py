#!/usr/bin/env python3
"""创建管理员账户 - 简化版本"""

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

async def create_admin():
    """创建管理员账户"""

    db_url = "postgresql+asyncpg://mr_admin:mr_secure_password_2024@localhost:5432/mr_game_ops"
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # 检查是否已存在管理员
            result = await session.execute(
                text("SELECT COUNT(*) FROM admin_accounts WHERE username = 'admin'")
            )
            count = result.scalar()

            if count > 0:
                print("Admin account already exists")
                return True

            # 直接使用SQL插入管理员账户，避免模型关系问题
            admin_id = str(uuid.uuid4())
            password_hash = hash_password("admin123")
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
                'id': admin_id,
                'username': 'admin',
                'password_hash': password_hash,
                'full_name': '系统管理员',
                'email': 'admin@mrgameops.com',
                'phone': '13800138000',
                'role': 'super_admin',
                'permissions': '["*"]',
                'is_active': True,
                'created_at': current_time,
                'updated_at': current_time
            })

            await session.commit()

            print("Successfully created admin account")
            print(f"   Username: admin")
            print(f"   Password: admin123")
            print(f"   Role: super_admin")
            return True

    except Exception as e:
        print(f"Failed to create admin: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(create_admin())
    if success:
        print("Admin account creation completed!")
    else:
        print("Admin account creation failed!")