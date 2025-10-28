#!/bin/bash

# MR游戏运营管理系统 - 账户管理脚本 (开发环境版)
# 用于本地开发环境的账户管理
# 适用于 docker-compose.yml (非生产环境)

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 容器名称（开发环境）
BACKEND_CONTAINER="mr_game_ops_backend"

# 检查后端容器是否运行
check_backend() {
    if ! docker ps --format '{{.Names}}' | grep -q "^${BACKEND_CONTAINER}$"; then
        echo -e "${RED}❌ 错误: 后端容器 ${BACKEND_CONTAINER} 未运行${NC}"
        echo -e "${YELLOW}请先启动开发环境: docker-compose up -d${NC}"
        exit 1
    fi
}

# 显示菜单
show_menu() {
    echo ""
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}   MR游戏运营管理系统 - 账户管理${NC}"
    echo -e "${BLUE}   (开发环境)${NC}"
    echo -e "${BLUE}=========================================${NC}"
    echo ""
    echo "1. 查看所有管理员账户"
    echo "2. 查看所有运营商账户"
    echo "3. 创建管理员账户"
    echo "4. 创建运营商账户"
    echo "5. 重置账户密码"
    echo "6. 启用/禁用账户"
    echo "7. 修改管理员角色"
    echo "8. 批量创建运营商"
    echo "9. 导出账户信息"
    echo "0. 退出"
    echo ""
    echo -e "${BLUE}=========================================${NC}"
}

# 列出所有管理员
list_admins() {
    echo -e "${YELLOW}正在查询管理员账户...${NC}"

    docker exec -i $BACKEND_CONTAINER python3 << 'EOFPYTHON'
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount

async def list_admins():
    init_db()
    async with get_db_context() as session:
        result = await session.execute(select(AdminAccount).order_by(AdminAccount.created_at.desc()))
        admins = result.scalars().all()

        if not admins:
            print("❌ 没有找到管理员账户")
            return

        print("\n" + "=" * 100)
        print(f"{'用户名':<15} {'姓名':<15} {'邮箱':<25} {'角色':<12} {'状态':<8} {'创建时间':<20}")
        print("=" * 100)

        for admin in admins:
            status = "✅ 激活" if admin.is_active else "❌ 禁用"
            created = admin.created_at.strftime('%Y-%m-%d %H:%M:%S')
            print(f"{admin.username:<15} {admin.full_name:<15} {admin.email:<25} {admin.role:<12} {status:<8} {created:<20}")

        print("=" * 100)
        print(f"\n共 {len(admins)} 个管理员账户\n")

asyncio.run(list_admins())
EOFPYTHON

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 查询成功${NC}"
    else
        echo -e "${RED}❌ 查询失败${NC}"
    fi
}

# 列出所有运营商
list_operators() {
    echo -e "${YELLOW}正在查询运营商账户...${NC}"

    docker exec -i $BACKEND_CONTAINER python3 << 'EOFPYTHON'
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import OperatorAccount

async def list_operators():
    init_db()
    async with get_db_context() as session:
        result = await session.execute(select(OperatorAccount).order_by(OperatorAccount.created_at.desc()))
        operators = result.scalars().all()

        if not operators:
            print("❌ 没有找到运营商账户")
            return

        print("\n" + "=" * 110)
        print(f"{'用户名':<15} {'姓名':<15} {'邮箱':<25} {'电话':<15} {'余额':<10} {'状态':<8} {'创建时间':<20}")
        print("=" * 110)

        for op in operators:
            status = "✅ 激活" if op.is_active else "❌ 禁用"
            created = op.created_at.strftime('%Y-%m-%d %H:%M:%S')
            print(f"{op.username:<15} {op.full_name:<15} {op.email:<25} {op.phone:<15} {float(op.balance):<10.2f} {status:<8} {created:<20}")

        print("=" * 110)
        print(f"\n共 {len(operators)} 个运营商账户\n")

asyncio.run(list_operators())
EOFPYTHON

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 查询成功${NC}"
    else
        echo -e "${RED}❌ 查询失败${NC}"
    fi
}

# 创建管理员账户
create_admin() {
    echo -e "${YELLOW}创建管理员账户${NC}"
    echo ""

    read -p "请输入用户名: " username
    read -sp "请输入密码: " password
    echo ""
    read -p "请输入姓名: " full_name
    read -p "请输入邮箱: " email
    read -p "请输入电话: " phone

    echo ""
    echo "请选择角色:"
    echo "1. super_admin (超级管理员)"
    echo "2. admin (普通管理员)"
    read -p "请选择 [1-2]: " role_choice

    case $role_choice in
        1) role="super_admin" ;;
        2) role="admin" ;;
        *) echo -e "${RED}❌ 无效选择${NC}"; return ;;
    esac

    echo -e "${YELLOW}正在创建管理员账户...${NC}"

    docker exec -i $BACKEND_CONTAINER python3 << EOFPYTHON
import asyncio
import sys
sys.path.insert(0, '/app')

from src.db.session import init_db, get_db_context
from src.models import AdminAccount
from src.core.utils.password import hash_password

async def create_admin():
    init_db()
    async with get_db_context() as session:
        # 检查用户名是否已存在
        from sqlalchemy import select
        result = await session.execute(
            select(AdminAccount).where(AdminAccount.username == "${username}")
        )
        if result.scalar_one_or_none():
            print("❌ 用户名已存在")
            sys.exit(1)

        # 创建管理员
        admin = AdminAccount(
            username="${username}",
            password_hash=hash_password("${password}"),
            full_name="${full_name}",
            email="${email}",
            phone="${phone}",
            role="${role}",
            is_active=True
        )

        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        print(f"\n✅ 管理员账户创建成功!")
        print(f"   用户名: {admin.username}")
        print(f"   姓名: {admin.full_name}")
        print(f"   角色: {admin.role}")

asyncio.run(create_admin())
EOFPYTHON

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 创建成功${NC}"
    else
        echo -e "${RED}❌ 创建失败${NC}"
    fi
}

# 创建运营商账户
create_operator() {
    echo -e "${YELLOW}创建运营商账户${NC}"
    echo ""

    read -p "请输入用户名: " username
    read -sp "请输入密码: " password
    echo ""
    read -p "请输入运营商名称: " full_name
    read -p "请输入邮箱: " email
    read -p "请输入电话: " phone
    read -p "请输入初始余额 (默认1000): " initial_balance
    initial_balance=${initial_balance:-1000}

    echo -e "${YELLOW}正在创建运营商账户...${NC}"

    docker exec -i $BACKEND_CONTAINER python3 << EOFPYTHON
import asyncio
import sys
import secrets
sys.path.insert(0, '/app')

from decimal import Decimal
from src.db.session import init_db, get_db_context
from src.models import OperatorAccount
from src.core.utils.password import hash_password

async def create_operator():
    init_db()
    async with get_db_context() as session:
        # 检查用户名是否已存在
        from sqlalchemy import select
        result = await session.execute(
            select(OperatorAccount).where(OperatorAccount.username == "${username}")
        )
        if result.scalar_one_or_none():
            print("❌ 用户名已存在")
            sys.exit(1)

        # 生成 API Key
        api_key = secrets.token_urlsafe(32)[:32]

        # 创建运营商
        operator = OperatorAccount(
            username="${username}",
            password_hash=hash_password("${password}"),
            full_name="${full_name}",
            email="${email}",
            phone="${phone}",
            balance=Decimal("${initial_balance}"),
            api_key=api_key,
            api_key_hash=hash_password(api_key),
            customer_tier="trial",
            is_active=True
        )

        session.add(operator)
        await session.commit()
        await session.refresh(operator)

        print(f"\n✅ 运营商账户创建成功!")
        print(f"   用户名: {operator.username}")
        print(f"   姓名: {operator.full_name}")
        print(f"   余额: {operator.balance} 元")
        print(f"   API Key: {api_key}")
        print(f"\n⚠️  请妥善保存 API Key，该密钥仅显示一次！")

asyncio.run(create_operator())
EOFPYTHON

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 创建成功${NC}"
    else
        echo -e "${RED}❌ 创建失败${NC}"
    fi
}

# 重置密码
reset_password() {
    echo -e "${YELLOW}重置账户密码${NC}"
    echo ""
    echo "请选择账户类型:"
    echo "1. 管理员"
    echo "2. 运营商"
    read -p "请选择 [1-2]: " account_type

    read -p "请输入用户名: " username
    read -sp "请输入新密码: " new_password
    echo ""

    echo -e "${YELLOW}正在重置密码...${NC}"

    case $account_type in
        1)
            model="AdminAccount"
            ;;
        2)
            model="OperatorAccount"
            ;;
        *)
            echo -e "${RED}❌ 无效选择${NC}"
            return
            ;;
    esac

    docker exec -i $BACKEND_CONTAINER python3 << EOFPYTHON
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import ${model}
from src.core.utils.password import hash_password

async def reset_password():
    init_db()
    async with get_db_context() as session:
        result = await session.execute(
            select(${model}).where(${model}.username == "${username}")
        )
        account = result.scalar_one_or_none()

        if not account:
            print("❌ 用户不存在")
            sys.exit(1)

        account.password_hash = hash_password("${new_password}")
        await session.commit()

        print(f"\n✅ 密码重置成功!")
        print(f"   用户名: {account.username}")

asyncio.run(reset_password())
EOFPYTHON

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 重置成功${NC}"
    else
        echo -e "${RED}❌ 重置失败${NC}"
    fi
}

# 启用/禁用账户
toggle_account() {
    echo -e "${YELLOW}启用/禁用账户${NC}"
    echo ""
    echo "请选择账户类型:"
    echo "1. 管理员"
    echo "2. 运营商"
    read -p "请选择 [1-2]: " account_type

    read -p "请输入用户名: " username

    echo "请选择操作:"
    echo "1. 启用"
    echo "2. 禁用"
    read -p "请选择 [1-2]: " action

    case $action in
        1) is_active="True" ;;
        2) is_active="False" ;;
        *) echo -e "${RED}❌ 无效选择${NC}"; return ;;
    esac

    case $account_type in
        1) model="AdminAccount" ;;
        2) model="OperatorAccount" ;;
        *) echo -e "${RED}❌ 无效选择${NC}"; return ;;
    esac

    echo -e "${YELLOW}正在更新账户状态...${NC}"

    docker exec -i $BACKEND_CONTAINER python3 << EOFPYTHON
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import ${model}

async def toggle_account():
    init_db()
    async with get_db_context() as session:
        result = await session.execute(
            select(${model}).where(${model}.username == "${username}")
        )
        account = result.scalar_one_or_none()

        if not account:
            print("❌ 用户不存在")
            sys.exit(1)

        account.is_active = ${is_active}
        await session.commit()

        status = "启用" if ${is_active} else "禁用"
        print(f"\n✅ 账户已{status}!")
        print(f"   用户名: {account.username}")

asyncio.run(toggle_account())
EOFPYTHON

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 操作成功${NC}"
    else
        echo -e "${RED}❌ 操作失败${NC}"
    fi
}

# 修改管理员角色
change_admin_role() {
    echo -e "${YELLOW}修改管理员角色${NC}"
    echo ""

    read -p "请输入管理员用户名: " username

    echo "请选择新角色:"
    echo "1. super_admin (超级管理员)"
    echo "2. admin (普通管理员)"
    read -p "请选择 [1-2]: " role_choice

    case $role_choice in
        1) role="super_admin" ;;
        2) role="admin" ;;
        *) echo -e "${RED}❌ 无效选择${NC}"; return ;;
    esac

    echo -e "${YELLOW}正在修改角色...${NC}"

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
            select(AdminAccount).where(AdminAccount.username == "${username}")
        )
        admin = result.scalar_one_or_none()

        if not admin:
            print("❌ 管理员不存在")
            sys.exit(1)

        admin.role = "${role}"
        await session.commit()

        print(f"\n✅ 角色修改成功!")
        print(f"   用户名: {admin.username}")
        print(f"   新角色: {admin.role}")

asyncio.run(change_role())
EOFPYTHON

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 修改成功${NC}"
    else
        echo -e "${RED}❌ 修改失败${NC}"
    fi
}

# 批量创建运营商
batch_create_operators() {
    echo -e "${YELLOW}批量创建运营商${NC}"
    echo ""

    read -p "请输入CSV文件路径: " csv_file

    if [ ! -f "$csv_file" ]; then
        echo -e "${RED}❌ 文件不存在: $csv_file${NC}"
        return
    fi

    echo -e "${YELLOW}正在批量创建运营商...${NC}"

    # 将CSV文件复制到容器中
    docker cp "$csv_file" $BACKEND_CONTAINER:/tmp/operators.csv

    docker exec -i $BACKEND_CONTAINER python3 << 'EOFPYTHON'
import asyncio
import csv
import sys
import secrets
sys.path.insert(0, '/app')

from decimal import Decimal
from src.db.session import init_db, get_db_context
from src.models import OperatorAccount
from src.core.utils.password import hash_password

async def batch_create():
    init_db()

    success_count = 0
    fail_count = 0

    with open('/tmp/operators.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                async with get_db_context() as session:
                    # 检查用户名是否已存在
                    from sqlalchemy import select
                    result = await session.execute(
                        select(OperatorAccount).where(OperatorAccount.username == row['username'])
                    )
                    if result.scalar_one_or_none():
                        print(f"⚠️  跳过已存在的用户: {row['username']}")
                        fail_count += 1
                        continue

                    # 生成 API Key
                    api_key = secrets.token_urlsafe(32)[:32]

                    # 创建运营商
                    operator = OperatorAccount(
                        username=row['username'],
                        password_hash=hash_password(row['password']),
                        full_name=row['full_name'],
                        email=row['email'],
                        phone=row['phone'],
                        balance=Decimal(row['initial_balance']),
                        api_key=api_key,
                        api_key_hash=hash_password(api_key),
                        customer_tier="trial",
                        is_active=True
                    )

                    session.add(operator)
                    await session.commit()

                    print(f"✅ 创建成功: {row['username']} (API Key: {api_key})")
                    success_count += 1

            except Exception as e:
                print(f"❌ 创建失败: {row['username']} - {str(e)}")
                fail_count += 1

    print(f"\n批量创建完成! 成功: {success_count}, 失败: {fail_count}")

asyncio.run(batch_create())
EOFPYTHON

    # 删除临时文件
    docker exec $BACKEND_CONTAINER rm /tmp/operators.csv

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 批量创建完成${NC}"
    else
        echo -e "${RED}❌ 批量创建失败${NC}"
    fi
}

# 导出账户信息
export_accounts() {
    echo -e "${YELLOW}导出账户信息${NC}"
    echo ""
    echo "请选择导出内容:"
    echo "1. 仅管理员"
    echo "2. 仅运营商"
    echo "3. 全部账户"
    read -p "请选择 [1-3]: " export_choice

    timestamp=$(date +%Y%m%d_%H%M%S)

    case $export_choice in
        1|3)
            echo -e "${YELLOW}正在导出管理员账户...${NC}"
            docker exec -i $BACKEND_CONTAINER python3 << 'EOFPYTHON' > "admins_${timestamp}.csv"
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount

async def export_admins():
    init_db()
    async with get_db_context() as session:
        result = await session.execute(select(AdminAccount).order_by(AdminAccount.created_at.desc()))
        admins = result.scalars().all()

        print("username,full_name,email,phone,role,is_active,created_at")
        for admin in admins:
            print(f"{admin.username},{admin.full_name},{admin.email},{admin.phone},{admin.role},{admin.is_active},{admin.created_at}")

asyncio.run(export_admins())
EOFPYTHON
            echo -e "${GREEN}✅ 管理员数据已导出到: admins_${timestamp}.csv${NC}"
            ;;
    esac

    case $export_choice in
        2|3)
            echo -e "${YELLOW}正在导出运营商账户...${NC}"
            docker exec -i $BACKEND_CONTAINER python3 << 'EOFPYTHON' > "operators_${timestamp}.csv"
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import OperatorAccount

async def export_operators():
    init_db()
    async with get_db_context() as session:
        result = await session.execute(select(OperatorAccount).order_by(OperatorAccount.created_at.desc()))
        operators = result.scalars().all()

        print("username,full_name,email,phone,balance,customer_tier,is_active,created_at")
        for op in operators:
            print(f"{op.username},{op.full_name},{op.email},{op.phone},{op.balance},{op.customer_tier},{op.is_active},{op.created_at}")

asyncio.run(export_operators())
EOFPYTHON
            echo -e "${GREEN}✅ 运营商数据已导出到: operators_${timestamp}.csv${NC}"
            ;;
    esac
}

# 主函数
main() {
    check_backend

    if [ $# -gt 0 ]; then
        # 命令行模式
        case $1 in
            list-admins) list_admins ;;
            list-operators) list_operators ;;
            create-admin) create_admin ;;
            create-operator) create_operator ;;
            reset-password) reset_password ;;
            *) echo -e "${RED}❌ 未知命令: $1${NC}"; exit 1 ;;
        esac
    else
        # 交互式菜单模式
        while true; do
            show_menu
            read -p "请选择 [0-9]: " choice

            case $choice in
                1) list_admins ;;
                2) list_operators ;;
                3) create_admin ;;
                4) create_operator ;;
                5) reset_password ;;
                6) toggle_account ;;
                7) change_admin_role ;;
                8) batch_create_operators ;;
                9) export_accounts ;;
                0) echo -e "${GREEN}再见!${NC}"; exit 0 ;;
                *) echo -e "${RED}❌ 无效选择，请重新输入${NC}" ;;
            esac

            read -p "按回车键继续..."
        done
    fi
}

main "$@"
