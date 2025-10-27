#!/bin/bash

# =============================================================================
# PostgreSQL密码恢复脚本
# =============================================================================
# 用于查找或重置PostgreSQL数据库密码
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否以root权限运行
if [[ $EUID -ne 0 ]]; then
    log_error "此脚本需要root权限运行"
    exit 1
fi

log_info "开始PostgreSQL密码恢复流程..."

# =============================================================================
# 1. 查找现有数据库配置
# =============================================================================
log_info "步骤1: 查找现有数据库配置..."

# 可能的数据库配置文件位置
CONFIG_LOCATIONS=(
    "/opt/mr_game_ops/backend/.env.production"
    "/opt/mr_game_ops/backend/.env"
    "/opt/mr_game_ops/backend/.env.development"
    "/var/lib/pgsql/data/pg_hba.conf"
    "/etc/postgresql/*/main/pg_hba.conf"
)

FOUND_PASSWORD=""
FOUND_USER=""

for config in "${CONFIG_LOCATIONS[@]}"; do
    if [ -f "$config" ]; then
        log_info "检查配置文件: $config"

        # 查找数据库连接字符串
        if grep -q "DATABASE_URL=" "$config"; then
            DB_URL=$(grep "DATABASE_URL=" "$config" | head -1 | cut -d'=' -f2)
            log_info "找到数据库连接字符串: ${DB_URL:0:50}..."

            # 解析连接字符串
            if [[ $DB_URL =~ postgresql.*://([^:]+):([^@]+)@([^/]+)/(.+) ]]; then
                FOUND_USER="${BASH_REMATCH[1]}"
                FOUND_PASSWORD="${BASH_REMATCH[2]}"
                DB_HOST="${BASH_REMATCH[3]}"
                DB_NAME="${BASH_REMATCH[4]}"
                log_success "从配置文件找到数据库信息:"
                echo "  用户: $FOUND_USER"
                echo "  主机: $DB_HOST"
                echo "  数据库: $DB_NAME"
                echo "  密码: $FOUND_PASSWORD"
                break
            fi
        fi

        # 查找单独的密码配置
        if grep -q "DB_PASSWORD=" "$config"; then
            FOUND_PASSWORD=$(grep "DB_PASSWORD=" "$config" | head -1 | cut -d'=' -f2)
            log_success "找到数据库密码: $FOUND_PASSWORD"
        fi

        if grep -q "DB_USER=" "$config"; then
            FOUND_USER=$(grep "DB_USER=" "$config" | head -1 | cut -d'=' -f2)
            log_success "找到数据库用户: $FOUND_USER"
        fi
    fi
done

if [ -n "$FOUND_PASSWORD" ]; then
    log_success "找到现有数据库密码: $FOUND_PASSWORD"

    # 测试连接
    if PGPASSWORD="$FOUND_PASSWORD" psql -h "$DB_HOST" -U "$FOUND_USER" -d "$DB_NAME" -c "SELECT 1" &> /dev/null; then
        log_success "数据库连接测试成功！"
        echo ""
        echo "=========================================="
        echo "数据库连接信息:"
        echo "=========================================="
        echo "用户: $FOUND_USER"
        echo "密码: $FOUND_PASSWORD"
        echo "主机: $DB_HOST"
        echo "数据库: $DB_NAME"
        echo "=========================================="
        echo ""
        echo "你可以使用此信息更新 deploy_production.sh 脚本"
        exit 0
    else
        log_warning "找到密码但连接失败，可能需要重置密码"
    fi
fi

# =============================================================================
# 2. 尝试常见密码
# =============================================================================
log_info "步骤2: 尝试常见默认密码..."

COMMON_PASSWORDS=(
    "mr_secure_password_2024"
    "admin123456"
    "postgres"
    "password"
    "123456"
    "mr_admin"
    "root"
)

for password in "${COMMON_PASSWORDS[@]}"; do
    log_info "尝试密码: $password"
    if PGPASSWORD="$password" psql -h localhost -U postgres -d postgres -c "SELECT 1" &> /dev/null; then
        log_success "找到有效密码: $password (postgres用户)"
        FOUND_PASSWORD="$password"
        FOUND_USER="postgres"
        break
    fi

    if PGPASSWORD="$password" psql -h localhost -U mr_admin -d postgres -c "SELECT 1" &> /dev/null; then
        log_success "找到有效密码: $password (mr_admin用户)"
        FOUND_PASSWORD="$password"
        FOUND_USER="mr_admin"
        break
    fi
done

if [ -n "$FOUND_PASSWORD" ]; then
    log_success "找到有效密码: $FOUND_PASSWORD (用户: $FOUND_USER)"

    echo ""
    echo "=========================================="
    echo "数据库连接信息:"
    echo "=========================================="
    echo "用户: $FOUND_USER"
    echo "密码: $FOUND_PASSWORD"
    echo "=========================================="
    echo ""
    echo "你可以使用此信息更新 deploy_production.sh 脚本"
    exit 0
fi

# =============================================================================
# 3. 重置PostgreSQL密码
# =============================================================================
log_info "步骤3: 重置PostgreSQL密码..."

# 检查PostgreSQL服务状态
if systemctl is-active --quiet postgresql; then
    log_info "PostgreSQL服务正在运行"
else
    log_info "启动PostgreSQL服务"
    systemctl start postgresql
    sleep 5
fi

# 方法1: 使用postgres用户重置密码
log_info "尝试以postgres用户身份重置密码..."

# 切换到postgres用户并重置mr_admin密码
sudo -u postgres psql -c "ALTER USER mr_admin PASSWORD 'mr_secure_password_2024';" 2>/dev/null || {
    log_warning "无法以postgres用户身份重置，尝试其他方法..."

    # 方法2: 如果mr_admin用户不存在，创建它
    sudo -u postgres psql -c "CREATE USER mr_admin WITH PASSWORD 'mr_secure_password_2024' CREATEDB SUPERUSER;" 2>/dev/null || {
        log_error "无法创建或重置mr_admin用户"

        # 方法3: 重置postgres用户密码
        log_info "重置postgres用户密码..."
        sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres123456';" || {
            log_error "无法重置任何数据库密码，请手动检查PostgreSQL配置"
            exit 1
        }

        log_success "已重置postgres用户密码为: postgres123456"
        FOUND_USER="postgres"
        FOUND_PASSWORD="postgres123456"
    }
}

if [ -z "$FOUND_PASSWORD" ]; then
    log_success "已重置mr_admin用户密码为: mr_secure_password_2024"
    FOUND_USER="mr_admin"
    FOUND_PASSWORD="mr_secure_password_2024"
fi

# 测试新密码
if PGPASSWORD="$FOUND_PASSWORD" psql -h localhost -U "$FOUND_USER" -d postgres -c "SELECT 1" &> /dev/null; then
    log_success "新密码测试成功！"
else
    log_error "新密码测试失败，请手动检查"
    exit 1
fi

# =============================================================================
# 4. 创建mr_game_ops数据库（如果不存在）
# =============================================================================
log_info "步骤4: 检查并创建数据库..."

if PGPASSWORD="$FOUND_PASSWORD" psql -h localhost -U "$FOUND_USER" -lqt | cut -d \| -f 1 | grep -qw mr_game_ops; then
    log_info "数据库 mr_game_ops 已存在"
else
    log_info "创建数据库 mr_game_ops..."
    PGPASSWORD="$FOUND_PASSWORD" createdb -h localhost -U "$FOUND_USER" mr_game_ops
    log_success "数据库创建成功"
fi

# =============================================================================
# 5. 生成更新后的配置
# =============================================================================
log_info "步骤5: 生成部署脚本配置..."

echo ""
echo "=========================================="
echo "🎉 数据库密码恢复完成！"
echo "=========================================="
echo "数据库连接信息:"
echo "用户: $FOUND_USER"
echo "密码: $FOUND_PASSWORD"
echo "主机: localhost"
echo "端口: 5432"
echo "数据库: mr_game_ops"
echo ""

# 生成配置片段
echo "请将以下配置复制到 deploy_production.sh 脚本中:"
echo ""
echo "# 数据库配置"
echo "DB_HOST='localhost'"
echo "DB_PORT='5432'"
echo "DB_NAME='mr_game_ops'"
echo "DB_USER='$FOUND_USER'"
echo "DB_PASSWORD='$FOUND_PASSWORD'"
echo ""

# 生成DATABASE_URL
echo "或者使用以下连接字符串:"
echo "DATABASE_URL=postgresql+asyncpg://$FOUND_USER:$FOUND_PASSWORD@localhost:5432/mr_game_ops"
echo ""

echo "=========================================="
echo "下一步操作:"
echo "=========================================="
echo "1. 更新 deploy_production.sh 中的数据库配置"
echo "2. 运行: chmod +x deploy_production.sh"
echo "3. 运行: sudo ./deploy_production.sh"
echo "=========================================="

exit 0