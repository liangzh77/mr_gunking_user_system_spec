#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path
import uuid
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from src.core.utils.password import hash_password

async def create_admin():
    db_url = 'postgresql+asyncpg://mr_admin:CHANGE_THIS_PASSWORD@postgres:5432/mr_game_ops'
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM admin_accounts WHERE username = 'admin'")
            )
            count = result.scalar()

            if count > 0:
                print('管理员账号已存在')
                return True

            admin_id = str(uuid.uuid4())
            password_hash = hash_password('admin123')
            current_time = datetime.utcnow()

            await session.execute(text('''
                INSERT INTO admin_accounts (
                    id, username, password_hash, full_name, email, phone,
                    role, permissions, is_active, created_at, updated_at
                ) VALUES (
                    :id, :username, :password_hash, :full_name, :email, :phone,
                    :role, :permissions, :is_active, :created_at, :updated_at
                )
            '''), {
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
            print('管理员账号创建成功！')
            print('用户名: admin')
            print('密码: admin123')
            print('角色: super_admin')
            return True
    except Exception as e:
        print(f'创建失败: {e}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(create_admin())
