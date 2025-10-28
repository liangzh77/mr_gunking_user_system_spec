#!/bin/bash
# =============================================================================
# MR游戏运营管理系统 - 生产环境账户管理脚本
# =============================================================================
# 使用方法：
#   ./manage_accounts.sh                    # 显示交互式菜单
#   ./manage_accounts.sh list-admins        # 列出所有管理员
#   ./manage_accounts.sh list-operators     # 列出所有运营商
#   ./manage_accounts.sh create-admin       # 创建管理员
#   ./manage_accounts.sh create-operator    # 创建运营商
#   ./manage_accounts.sh reset-password     # 重置密码
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 容器名称
BACKEND_CONTAINER="mr_game_ops_backend_prod"
DB_CONTAINER="mr_game_ops_db_prod"

# 检查容器是否运行
check_container() {
    if ! docker ps | grep -q "$BACKEND_CONTAINER"; then
        echo -e "${RED}错误: 后端容器未运行${NC}"
        echo "请先启动服务: docker-compose -f docker-compose.prod.yml up -d"
        exit 1
    fi
}

# 显示菜单
show_menu() {
    clear
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}   MR游戏运营管理系统 - 账户管理${NC}"
    echo -e "${BLUE}=========================================${NC}"
    echo ""
    echo "1. 查看所有账户"
    echo "2. 创建管理员账户"
    echo "3. 创建运营商账户"
    echo "4. 创建财务账户"
    echo "5. 删除账户"
    echo "6. 重置账户密码"
    echo "7. 启用/禁用账户"
    echo "8. 修改管理员角色"
    echo "9. 批量创建运营商"
    echo "0. 退出"
    echo ""
    echo -e "${BLUE}=========================================${NC}"
}

# 查看所有账户
list_all_accounts() {
    echo -e "${YELLOW}正在查询所有账户...${NC}"

    docker exec -i $BACKEND_CONTAINER python3 << 'EOFPYTHON'
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
            print(f"{'用户名':<15} {'姓名':<15} {'邮箱':<30} {'角色':<15} {'状态':<8} {'创建时间':<20}")
            print("-" * 120)
            for admin in admins:
                status = "✅ 激活" if admin.is_active else "❌ 禁用"
                created = admin.created_at.strftime('%Y-%m-%d %H:%M:%S')
                print(f"{admin.username:<15} {admin.full_name:<15} {admin.email:<30} {admin.role:<15} {status:<8} {created:<20}")
            print(f"\n共 {len(admins)} 个管理员账户")
        else:
            print("❌ 没有管理员账户")

        # 显示运营商账户
        print("\n" + "=" * 120)
        print("【运营商账户】")
        print("=" * 120)
        if operators:
            print(f"{'用户名':<15} {'名称':<15} {'邮箱':<30} {'余额':<15} {'状态':<8} {'站点数':<8}")
            print("-" * 120)
            for op in operators:
                status = "✅ 激活" if op.is_active else "❌ 禁用"
                balance = f"¥{float(op.balance):.2f}"
                site_count = len(op.sites) if op.sites else 0
                print(f"{op.username:<15} {op.full_name:<15} {op.email:<30} {balance:<15} {status:<8} {site_count:<8}")
            print(f"\n共 {len(operators)} 个运营商账户")
        else:
            print("❌ 没有运营商账户")

        # 显示财务账户
        print("\n" + "=" * 120)
        print("【财务账户】")
        print("=" * 120)
        if finance_accounts:
            print(f"{'用户名':<15} {'姓名':<15} {'邮箱':<30} {'角色':<15} {'状态':<8} {'创建时间':<20}")
            print("-" * 120)
            for finance in finance_accounts:
                status = "✅ 激活" if finance.is_active else "❌ 禁用"
                created = finance.created_at.strftime('%Y-%m-%d %H:%M:%S')
                print(f"{finance.username:<15} {finance.full_name:<15} {finance.email:<30} {finance.role:<15} {status:<8} {created:<20}")
            print(f"\n共 {len(finance_accounts)} 个财务账户")
        else:
            print("❌ 没有财务账户")

        print("\n" + "=" * 120)
        total = len(admins) + len(operators) + len(finance_accounts)
        print(f"账户总数: {total} (管理员:{len(admins)} + 运营商:{len(operators)} + 财务:{len(finance_accounts)})")
        print("=" * 120 + "\n")

asyncio.run(list_all_accounts())
EOFPYTHON
}

# 创建管理员账户
create_admin() {
    echo -e "${GREEN}=== 创建管理员账户 ===${NC}\n"

    read -p "用户名: " username
    read -s -p "密码: " password
    echo ""
    read -p "姓名: " full_name
    read -p "邮箱: " email
    read -p "电话: " phone

    echo ""
    echo "角色选择:"
    echo "  1. super_admin (超级管理员)"
    echo "  2. admin (普通管理员)"
    read -p "请选择 [1/2]: " role_choice

    if [ "$role_choice" == "1" ]; then
        role="super_admin"
    else
        role="admin"
    fi

    echo -e "\n${YELLOW}正在创建管理员账户...${NC}"

    docker exec -i $BACKEND_CONTAINER python3 << EOFPYTHON
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount
from src.core.utils.password import hash_password

async def create_admin():
    init_db()
    async with get_db_context() as session:
        # 检查用户名是否存在
        result = await session.execute(
            select(AdminAccount).where(AdminAccount.username == "$username")
        )
        if result.scalar_one_or_none():
            print("❌ 用户名已存在！")
            sys.exit(1)

        # 创建管理员
        admin = AdminAccount(
            username="$username",
            password_hash=hash_password("$password"),
            full_name="$full_name",
            email="$email",
            phone="$phone",
            role="$role",
            permissions=[],
            is_active=True,
        )

        session.add(admin)
        await session.commit()

        print("✅ 管理员账户创建成功！")
        print(f"  用户名: $username")
        print(f"  姓名: $full_name")
        print(f"  角色: $role")

asyncio.run(create_admin())
EOFPYTHON

    echo ""
    read -p "按回车键继续..."
}

# 创建运营商账户
create_operator() {
    echo -e "${GREEN}=== 创建运营商账户 ===${NC}\n"

    read -p "用户名: " username
    read -s -p "密码: " password
    echo ""
    read -p "运营商名称: " full_name
    read -p "邮箱: " email
    read -p "电话: " phone
    read -p "初始余额 [默认1000]: " initial_balance
    initial_balance=${initial_balance:-1000}

    echo -e "\n${YELLOW}正在创建运营商账户...${NC}"

    docker exec -i $BACKEND_CONTAINER python3 << EOFPYTHON
import asyncio
import sys
sys.path.insert(0, '/app')

from decimal import Decimal
from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import OperatorAccount
from src.core.utils.password import hash_password

async def create_operator():
    init_db()
    async with get_db_context() as session:
        # 检查用户名是否存在
        result = await session.execute(
            select(OperatorAccount).where(OperatorAccount.username == "$username")
        )
        if result.scalar_one_or_none():
            print("❌ 用户名已存在！")
            sys.exit(1)

        # 创建运营商
        operator = OperatorAccount(
            username="$username",
            password_hash=hash_password("$password"),
            full_name="$full_name",
            email="$email",
            phone="$phone",
            balance=Decimal("$initial_balance"),
            is_active=True,
        )

        session.add(operator)
        await session.commit()

        print("✅ 运营商账户创建成功！")
        print(f"  用户名: $username")
        print(f"  姓名: $full_name")
        print(f"  初始余额: ¥$initial_balance")

asyncio.run(create_operator())
EOFPYTHON

    echo ""
    read -p "按回车键继续..."
}

# 创建财务账户
create_finance_account() {
    echo -e "${GREEN}=== 创建财务账户 ===${NC}\n"

    read -p "用户名: " username
    read -s -p "密码: " password
    echo ""
    read -p "姓名: " full_name
    read -p "邮箱: " email
    read -p "电话: " phone

    echo ""
    echo "角色选择:"
    echo "  1. specialist (专员)"
    echo "  2. manager (经理)"
    echo "  3. auditor (审计员)"
    read -p "请选择 [1/2/3]: " role_choice

    if [ "$role_choice" == "1" ]; then
        role="specialist"
    elif [ "$role_choice" == "2" ]; then
        role="manager"
    else
        role="auditor"
    fi

    echo -e "\n${YELLOW}正在创建财务账户...${NC}"

    docker exec -i $BACKEND_CONTAINER python3 << EOFPYTHON
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import FinanceAccount
from src.core.utils.password import hash_password

async def create_finance():
    init_db()
    async with get_db_context() as session:
        # 检查用户名是否存在
        result = await session.execute(
            select(FinanceAccount).where(FinanceAccount.username == "$username")
        )
        if result.scalar_one_or_none():
            print("❌ 用户名已存在！")
            sys.exit(1)

        # 创建财务账户
        finance = FinanceAccount(
            username="$username",
            password_hash=hash_password("$password"),
            full_name="$full_name",
            email="$email",
            phone="$phone",
            role="$role",
            permissions=[],
            is_active=True,
        )

        session.add(finance)
        await session.commit()

        print("✅ 财务账户创建成功！")
        print(f"  用户名: $username")
        print(f"  姓名: $full_name")
        print(f"  角色: $role")

asyncio.run(create_finance())
EOFPYTHON

    echo ""
    read -p "按回车键继续..."
}

# 删除账户
delete_account() {
    echo -e "${RED}=== 删除账户 ===${NC}\n"
    echo -e "${YELLOW}警告: 此操作不可恢复！${NC}\n"

    echo "账户类型:"
    echo "  1. 管理员"
    echo "  2. 运营商"
    echo "  3. 财务人员"
    read -p "请选择 [1/2/3]: " account_type

    read -p "用户名: " username

    if [ "$account_type" == "1" ]; then
        model="AdminAccount"
        type_name="管理员"
    elif [ "$account_type" == "2" ]; then
        model="OperatorAccount"
        type_name="运营商"
    else
        model="FinanceAccount"
        type_name="财务人员"
    fi

    echo -e "\n${YELLOW}正在查询账户信息...${NC}"

    # 先显示账户信息
    docker exec -i $BACKEND_CONTAINER python3 << EOFPYTHON
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount, OperatorAccount, FinanceAccount

async def show_account():
    init_db()
    async with get_db_context() as session:
        Model = $model
        result = await session.execute(
            select(Model).where(Model.username == "$username")
        )
        account = result.scalar_one_or_none()

        if not account:
            print("❌ 账户不存在！")
            sys.exit(1)

        print("\n账户信息:")
        print(f"  用户名: {account.username}")
        print(f"  姓名: {account.full_name}")
        print(f"  邮箱: {account.email}")
        if hasattr(account, 'role'):
            print(f"  角色: {account.role}")
        if hasattr(account, 'balance'):
            print(f"  余额: ¥{float(account.balance):.2f}")
        print(f"  状态: {'激活' if account.is_active else '禁用'}")

asyncio.run(show_account())
EOFPYTHON

    if [ $? -ne 0 ]; then
        read -p "按回车键继续..."
        return
    fi

    echo ""
    read -p "确认删除这个${type_name}账户? [y/N]: " confirm

    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo -e "${GREEN}已取消删除${NC}"
        read -p "按回车键继续..."
        return
    fi

    echo -e "\n${YELLOW}正在删除账户...${NC}"

    docker exec -i $BACKEND_CONTAINER python3 << EOFPYTHON
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount, OperatorAccount, FinanceAccount

async def delete_account():
    init_db()
    async with get_db_context() as session:
        Model = $model
        result = await session.execute(
            select(Model).where(Model.username == "$username")
        )
        account = result.scalar_one_or_none()

        if not account:
            print("❌ 账户不存在！")
            sys.exit(1)

        await session.delete(account)
        await session.commit()

        print("✅ 账户删除成功！")
        print(f"  用户名: $username")

asyncio.run(delete_account())
EOFPYTHON

    echo ""
    read -p "按回车键继续..."
}

# 重置密码
reset_password() {
    echo -e "${GREEN}=== 重置账户密码 ===${NC}\n"

    echo "账户类型:"
    echo "  1. 管理员"
    echo "  2. 运营商"
    read -p "请选择 [1/2]: " account_type

    read -p "用户名: " username
    read -s -p "新密码: " new_password
    echo ""

    if [ "$account_type" == "1" ]; then
        model="AdminAccount"
        table="admin_accounts"
    else
        model="OperatorAccount"
        table="operator_accounts"
    fi

    echo -e "\n${YELLOW}正在重置密码...${NC}"

    docker exec -i $BACKEND_CONTAINER python3 << EOFPYTHON
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount
from src.models import OperatorAccount
from src.core.utils.password import hash_password

async def reset_password():
    init_db()
    async with get_db_context() as session:
        Model = $model
        result = await session.execute(
            select(Model).where(Model.username == "$username")
        )
        account = result.scalar_one_or_none()

        if not account:
            print("❌ 账户不存在！")
            sys.exit(1)

        account.password_hash = hash_password("$new_password")
        await session.commit()

        print("✅ 密码重置成功！")
        print(f"  用户名: $username")

asyncio.run(reset_password())
EOFPYTHON

    echo ""
    read -p "按回车键继续..."
}

# 启用/禁用账户
toggle_account() {
    echo -e "${GREEN}=== 启用/禁用账户 ===${NC}\n"

    echo "账户类型:"
    echo "  1. 管理员"
    echo "  2. 运营商"
    read -p "请选择 [1/2]: " account_type

    read -p "用户名: " username

    echo "操作:"
    echo "  1. 启用"
    echo "  2. 禁用"
    read -p "请选择 [1/2]: " action

    if [ "$action" == "1" ]; then
        is_active="True"
        action_text="启用"
    else
        is_active="False"
        action_text="禁用"
    fi

    if [ "$account_type" == "1" ]; then
        model="AdminAccount"
    else
        model="OperatorAccount"
    fi

    echo -e "\n${YELLOW}正在${action_text}账户...${NC}"

    docker exec -i $BACKEND_CONTAINER python3 << EOFPYTHON
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount
from src.models import OperatorAccount

async def toggle_account():
    init_db()
    async with get_db_context() as session:
        Model = $model
        result = await session.execute(
            select(Model).where(Model.username == "$username")
        )
        account = result.scalar_one_or_none()

        if not account:
            print("❌ 账户不存在！")
            sys.exit(1)

        account.is_active = $is_active
        await session.commit()

        print("✅ 账户${action_text}成功！")
        print(f"  用户名: $username")

asyncio.run(toggle_account())
EOFPYTHON

    echo ""
    read -p "按回车键继续..."
}

# 修改管理员角色
change_admin_role() {
    echo -e "${GREEN}=== 修改管理员角色 ===${NC}\n"

    read -p "用户名: " username

    echo "新角色:"
    echo "  1. super_admin (超级管理员)"
    echo "  2. admin (普通管理员)"
    read -p "请选择 [1/2]: " role_choice

    if [ "$role_choice" == "1" ]; then
        new_role="super_admin"
    else
        new_role="admin"
    fi

    echo -e "\n${YELLOW}正在修改角色...${NC}"

    docker exec -i $BACKEND_CONTAINER python3 << EOFPYTHON
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount

async def change_role():
    init_db()
    async with get_db_context() as session:
        result = await session.execute(
            select(AdminAccount).where(AdminAccount.username == "$username")
        )
        admin = result.scalar_one_or_none()

        if not admin:
            print("❌ 管理员不存在！")
            sys.exit(1)

        admin.role = "$new_role"
        await session.commit()

        print("✅ 角色修改成功！")
        print(f"  用户名: $username")
        print(f"  新角色: $new_role")

asyncio.run(change_role())
EOFPYTHON

    echo ""
    read -p "按回车键继续..."
}

# 批量创建运营商
batch_create_operators() {
    echo -e "${GREEN}=== 批量创建运营商 ===${NC}\n"
    echo "请准备一个 CSV 文件，格式如下："
    echo "username,password,full_name,email,phone,initial_balance"
    echo "operator1,Pass123!,运营商一,op1@example.com,13800000001,1000"
    echo ""
    read -p "CSV 文件路径: " csv_file

    if [ ! -f "$csv_file" ]; then
        echo -e "${RED}文件不存在！${NC}"
        read -p "按回车键继续..."
        return
    fi

    echo -e "\n${YELLOW}正在批量创建...${NC}"

    # 复制 CSV 到容器
    docker cp "$csv_file" $BACKEND_CONTAINER:/tmp/operators.csv

    docker exec -i $BACKEND_CONTAINER python3 << 'EOFPYTHON'
import asyncio
import sys
import csv
sys.path.insert(0, '/app')

from decimal import Decimal
from src.db.session import init_db, get_db_context
from src.models import OperatorAccount
from src.core.utils.password import hash_password

async def batch_create():
    init_db()
    success_count = 0
    fail_count = 0

    async with get_db_context() as session:
        with open('/tmp/operators.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    operator = OperatorAccount(
                        username=row['username'],
                        password_hash=hash_password(row['password']),
                        full_name=row['full_name'],
                        email=row['email'],
                        phone=row['phone'],
                        balance=Decimal(row['initial_balance']),
                        is_active=True,
                    )
                    session.add(operator)
                    print(f"✅ 创建成功: {row['username']}")
                    success_count += 1
                except Exception as e:
                    print(f"❌ 创建失败: {row['username']} - {str(e)}")
                    fail_count += 1

        await session.commit()

    print(f"\n批量创建完成！成功: {success_count}, 失败: {fail_count}")

asyncio.run(batch_create())
EOFPYTHON

    echo ""
    read -p "按回车键继续..."
}

# 导出账户信息
export_accounts() {
    echo -e "${GREEN}=== 导出账户信息 ===${NC}\n"

    echo "导出选项:"
    echo "  1. 导出管理员账户"
    echo "  2. 导出运营商账户"
    echo "  3. 导出所有账户"
    read -p "请选择 [1/2/3]: " export_choice

    timestamp=$(date +%Y%m%d_%H%M%S)

    if [ "$export_choice" == "1" ] || [ "$export_choice" == "3" ]; then
        echo -e "\n${YELLOW}导出管理员账户...${NC}"
        docker exec $DB_CONTAINER psql -U mr_admin -d mr_game_ops -c "\COPY (SELECT username, full_name, email, phone, role, is_active, created_at FROM admin_accounts ORDER BY created_at) TO '/tmp/admins_${timestamp}.csv' WITH CSV HEADER"
        docker cp $DB_CONTAINER:/tmp/admins_${timestamp}.csv ./admins_${timestamp}.csv
        echo -e "${GREEN}✅ 已导出到: ./admins_${timestamp}.csv${NC}"
    fi

    if [ "$export_choice" == "2" ] || [ "$export_choice" == "3" ]; then
        echo -e "\n${YELLOW}导出运营商账户...${NC}"
        docker exec $DB_CONTAINER psql -U mr_admin -d mr_game_ops -c "\COPY (SELECT username, full_name, email, phone, balance, is_active, created_at FROM operator_accounts ORDER BY created_at) TO '/tmp/operators_${timestamp}.csv' WITH CSV HEADER"
        docker cp $DB_CONTAINER:/tmp/operators_${timestamp}.csv ./operators_${timestamp}.csv
        echo -e "${GREEN}✅ 已导出到: ./operators_${timestamp}.csv${NC}"
    fi

    echo ""
    read -p "按回车键继续..."
}

# 主程序
main() {
    check_container

    # 如果有参数，直接执行对应功能
    if [ $# -gt 0 ]; then
        case "$1" in
            list-admins)
                list_admins
                ;;
            list-operators)
                list_operators
                ;;
            create-admin)
                create_admin
                ;;
            create-operator)
                create_operator
                ;;
            reset-password)
                reset_password
                ;;
            *)
                echo "未知命令: $1"
                echo "可用命令: list-admins, list-operators, create-admin, create-operator, reset-password"
                exit 1
                ;;
        esac
        exit 0
    fi

    # 交互式菜单
    while true; do
        show_menu
        read -p "请选择 [0-9]: " choice

        case $choice in
            1)
                list_all_accounts
                read -p "按回车键继续..."
                ;;
            2)
                create_admin
                ;;
            3)
                create_operator
                ;;
            4)
                create_finance_account
                ;;
            5)
                delete_account
                ;;
            6)
                reset_password
                ;;
            7)
                toggle_account
                ;;
            8)
                change_admin_role
                ;;
            9)
                batch_create_operators
                ;;
            0)
                echo -e "\n${GREEN}再见！${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}无效选择！${NC}"
                read -p "按回车键继续..."
                ;;
        esac
    done
}

# 运行主程序
main "$@"
