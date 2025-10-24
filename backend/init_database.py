#!/usr/bin/env python3
"""初始化数据库表结构和管理员账户"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.db.base import Base
from src.models.admin import AdminAccount
from src.core.utils.password import hash_password
from src.core.config import settings

async def init_database():
    """初始化数据库表结构和管理员账户"""

    print(f"连接数据库: {settings.DATABASE_URL}")

    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        # 创建所有表
        print("正在创建数据库表...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ 数据库表创建完成")

        # 创建管理员账户
        async with async_session() as session:
            from sqlalchemy import select

            # 检查是否已存在管理员
            result = await session.execute(
                select(AdminAccount).where(AdminAccount.username == "admin")
            )
            existing_admin = result.scalar_one_or_none()

            if existing_admin:
                print(f"管理员账户已存在: {existing_admin.username}")
            else:
                # 创建管理员账户
                admin = AdminAccount(
                    username="admin",
                    full_name="系统管理员",
                    email="admin@mrgameops.com",
                    phone="13800138000",
                    password_hash=hash_password("admin123"),
                    role="super_admin",
                    permissions=["*"],
                    is_active=True
                )

                session.add(admin)
                await session.commit()
                print(f"✅ 成功创建管理员账户: {admin.username}")
                print(f"   用户名: {admin.username}")
                print(f"   密码: admin123")
                print(f"   角色: {admin.role}")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()

    return True

if __name__ == "__main__":
    success = asyncio.run(init_database())
    if success:
        print("\n🎉 数据库初始化完成!")
    else:
        print("\n❌ 数据库初始化失败!")