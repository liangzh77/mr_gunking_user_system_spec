#!/usr/bin/env python3
"""列出所有账户"""
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount, OperatorAccount, FinanceAccount

async def list_all_accounts():
    init_db()
    async with get_db_context() as session:
        # 查询所有管理员
        admins_result = await session.execute(select(AdminAccount).order_by(AdminAccount.created_at.desc()))
        admins = admins_result.scalars().all()

        # 查询所有运营商
        operators_result = await session.execute(select(OperatorAccount).order_by(OperatorAccount.created_at.desc()))
        operators = operators_result.scalars().all()

        # 查询所有财务人员
        finance_result = await session.execute(select(FinanceAccount).order_by(FinanceAccount.created_at.desc()))
        finance_accounts = finance_result.scalars().all()

        # 显示管理员账户
        print("\n" + "=" * 120)
        print("【管理员账户】")
        print("=" * 120)
        if admins:
            print(f"{'用户名':^15} {'姓名':^15} {'邮箱':^30} {'角色':^15} {'状态':^8} {'创建时间':^20}")
            print("-" * 120)
            for admin in admins:
                status = "✅ 激活" if admin.is_active else "❌ 禁用"
                created = admin.created_at.strftime('%Y-%m-%d %H:%M:%S')
                print(f"{admin.username:^15} {admin.full_name:^15} {admin.email:^30} {admin.role:^15} {status:^8} {created:^20}")
            print(f"\n共 {len(admins)} 个管理员账户")
        else:
            print("❌ 没有管理员账户")

        # 显示运营商账户
        print("\n" + "=" * 120)
        print("【运营商账户】")
        print("=" * 120)
        if operators:
            print(f"{'用户名':^15} {'名称':^15} {'邮箱':^30} {'余额':^15} {'状态':^8} {'站点数':^8}")
            print("-" * 120)
            for op in operators:
                status = "✅ 激活" if op.is_active else "❌ 禁用"
                balance = f"¥{float(op.balance):.2f}"
                site_count = len(op.operation_sites) if op.operation_sites else 0
                print(f"{op.username:^15} {op.full_name:^15} {op.email:^30} {balance:^15} {status:^8} {site_count:^8}")
            print(f"\n共 {len(operators)} 个运营商账户")
        else:
            print("❌ 没有运营商账户")

        # 显示财务账户
        print("\n" + "=" * 120)
        print("【财务账户】")
        print("=" * 120)
        if finance_accounts:
            print(f"{'用户名':^15} {'姓名':^15} {'邮箱':^30} {'角色':^15} {'状态':^8} {'创建时间':^20}")
            print("-" * 120)
            for finance in finance_accounts:
                status = "✅ 激活" if finance.is_active else "❌ 禁用"
                created = finance.created_at.strftime('%Y-%m-%d %H:%M:%S')
                print(f"{finance.username:^15} {finance.full_name:^15} {finance.email:^30} {finance.role:^15} {status:^8} {created:^20}")
            print(f"\n共 {len(finance_accounts)} 个财务账户")
        else:
            print("❌ 没有财务账户")

        print("\n" + "=" * 120)
        total = len(admins) + len(operators) + len(finance_accounts)
        print(f"账户总数: {total} (管理员:{len(admins)} + 运营商:{len(operators)} + 财务:{len(finance_accounts)})")
        print("=" * 120 + "\n")

if __name__ == "__main__":
    asyncio.run(list_all_accounts())
