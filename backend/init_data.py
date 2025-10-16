"""数据初始化脚本

创建初始的管理员账户和MR游戏应用数据
"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from decimal import Decimal

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.db.session import init_db, get_db_session
from src.models.admin import AdminAccount
from src.models.application import Application
from src.core.utils.password import hash_password


async def create_admin_account():
    """创建管理员账户"""
    async for session in get_db_session():
        # 检查是否已存在admin用户
        from sqlalchemy import select
        result = await session.execute(
            select(AdminAccount).where(AdminAccount.username == "admin")
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print("[OK] 管理员账户已存在")
            print(f"  用户名: {existing_admin.username}")
            print(f"  角色: {existing_admin.role}")
            return existing_admin

        # 创建新管理员
        admin = AdminAccount(
            id=uuid4(),
            username="admin",
            full_name="系统管理员",
            email="admin@mrgunking.com",
            phone="13800138000",  # 管理员联系电话
            password_hash=hash_password("Admin123"),  # 密码: Admin123
            role="super_admin",
            permissions={
                "operator_management": True,
                "app_management": True,
                "finance_management": True,
                "system_settings": True
            },
            is_active=True
        )

        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        print("[OK] 创建管理员账户成功")
        print(f"  用户名: admin")
        print(f"  密码: Admin123")
        print(f"  角色: super_admin")

        return admin


async def create_applications(admin_id):
    """创建测试应用数据"""
    async for session in get_db_session():
        # 检查是否已存在应用
        from sqlalchemy import select
        result = await session.execute(select(Application))
        existing_apps = result.scalars().all()

        if existing_apps:
            print(f"\n[OK] 已存在 {len(existing_apps)} 个应用")
            for app in existing_apps:
                print(f"  - {app.app_name} ({app.app_code}): {app.price_per_player}元/人")
            return existing_apps

        # 创建测试应用
        apps_data = [
            {
                "app_code": "mr_gunking_01",
                "app_name": "MR枪王争霸",
                "description": "多人对战射击游戏，支持2-4人同时游戏",
                "price_per_player": Decimal("10.00"),
                "min_players": 2,
                "max_players": 4
            },
            {
                "app_code": "mr_adventure_01",
                "app_name": "MR冒险岛",
                "description": "合作探险游戏，支持1-6人组队",
                "price_per_player": Decimal("15.00"),
                "min_players": 1,
                "max_players": 6
            },
            {
                "app_code": "mr_racing_01",
                "app_name": "MR极速赛车",
                "description": "竞速赛车游戏，支持单人或多人模式",
                "price_per_player": Decimal("12.00"),
                "min_players": 1,
                "max_players": 8
            }
        ]

        apps = []
        for app_data in apps_data:
            app = Application(
                id=uuid4(),
                **app_data,
                is_active=True,
                created_by=admin_id
            )
            session.add(app)
            apps.append(app)

        await session.commit()

        print("\n[OK] 创建应用数据成功")
        for app in apps:
            await session.refresh(app)
            print(f"  - {app.app_name} ({app.app_code})")
            print(f"    价格: {app.price_per_player}元/人")
            print(f"    玩家数: {app.min_players}-{app.max_players}人")

        return apps


async def main():
    """主函数"""
    print("=" * 60)
    print("数据初始化开始")
    print("=" * 60)

    # 初始化数据库
    init_db()
    print("\n[OK] 数据库连接成功")

    # 创建管理员账户
    print("\n[1/2] 创建管理员账户...")
    admin = await create_admin_account()

    # 创建应用数据
    print("\n[2/2] 创建应用数据...")
    apps = await create_applications(admin.id)

    print("\n" + "=" * 60)
    print("数据初始化完成！")
    print("=" * 60)
    print("\n[登录信息]")
    print("  管理员账户: admin / Admin123")
    print("  运营商账户: test / (你刚才注册的密码)")
    print("\n[可用游戏]")
    print(f"  共 {len(apps)} 个应用已创建")
    print("\n[下一步]")
    print("  1. 使用运营商账户登录")
    print("  2. 创建运营点")
    print("  3. 申请游戏授权")
    print("  4. 使用管理员账户审批授权")
    print("  5. 测试充值和游戏会话")


if __name__ == "__main__":
    asyncio.run(main())
