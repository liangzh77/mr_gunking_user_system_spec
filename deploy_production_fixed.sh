#!/bin/bash

# =============================================================================
# MR游戏运营管理系统 - 生产环境部署脚本（版本兼容性修复版）
# =============================================================================
# 确保Python版本与开发环境一致 (Python 3.11)
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
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

# 配置变量
PROJECT_DIR="/opt/mr_gunking_user_system_spec"
BACKUP_DIR="/opt/mr_gunking_user_system_spec/backups"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="mr_game_ops"
DB_USER="mr_admin"
DB_PASSWORD="mr_secure_password_2024"
BACKEND_PORT="8000"
FRONTEND_PORT="3000"
PYTHON_VERSION="3.11"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --db-password)
            DB_PASSWORD="$2"
            shift 2
            ;;
        --db-user)
            DB_USER="$2"
            shift 2
            ;;
        --python-version)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        --backend-port)
            BACKEND_PORT="$2"
            shift 2
            ;;
        --frontend-port)
            FRONTEND_PORT="$2"
            shift 2
            ;;
        --skip-db-reset)
            SKIP_DB_RESET=true
            shift
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo "选项:"
            echo "  --db-password PASSWORD     数据库密码"
            echo "  --db-user USER             数据库用户名"
            echo "  --python-version VERSION  Python版本 (默认: 3.11)"
            echo "  --backend-port PORT        后端端口 (默认: 8000)"
            echo "  --frontend-port PORT       前端端口 (默认: 3000)"
            echo "  --skip-db-reset            跳过数据库重置"
            echo "  --help                     显示帮助信息"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

# 检查是否以root权限运行
if [[ $EUID -ne 0 ]]; then
    log_error "此脚本需要root权限运行"
    exit 1
fi

log_info "开始MR游戏运营管理系统生产环境部署（版本兼容性修复版）..."
log_info "使用配置："
echo "  项目目录: $PROJECT_DIR"
echo "  Python版本: $PYTHON_VERSION"
echo "  数据库用户: $DB_USER"
echo "  数据库密码: $DB_PASSWORD"
echo "  后端端口: $BACKEND_PORT"
echo "  前端端口: $FRONTEND_PORT"

# =============================================================================
# 1. 检查系统依赖
# =============================================================================
log_info "步骤1: 检查系统和依赖..."

# 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    log_error "项目目录不存在: $PROJECT_DIR"
    exit 1
fi

# 创建必要目录
mkdir -p "$BACKUP_DIR"
mkdir -p "$PROJECT_DIR/logs"

# 检查PostgreSQL
if ! command -v psql &> /dev/null; then
    log_error "PostgreSQL未安装，请先安装PostgreSQL"
    exit 1
fi

# 检查Node.js
if ! command -v node &> /dev/null; then
    log_error "Node.js未安装，请先安装Node.js"
    exit 1
fi

log_success "系统依赖检查完成"

# =============================================================================
# 2. 安装Python 3.11（如果需要）
# =============================================================================
log_info "步骤2: 检查并安装Python $PYTHON_VERSION..."

# 检查当前Python版本
CURRENT_PYTHON=$(python3 --version 2>&1 | awk '{print $2}')
if [[ "$CURRENT_PYTHON" == "$PYTHON_VERSION"* ]]; then
    log_success "Python $PYTHON_VERSION 已安装"
else
    log_warning "当前Python版本: $CURRENT_PYTHON，需要安装Python $PYTHON_VERSION"

    # 根据系统类型安装Python 3.11
    if command -v apt &> /dev/null; then
        # Ubuntu/Debian
        log_info "在Ubuntu/Debian系统上安装Python $PYTHON_VERSION..."
        apt update
        apt install -y software-properties-common
        add-apt-repository ppa:deadsnakes/ppa -y
        apt update
        apt install -y python$PYTHON_VERSION python$PYTHON_VERSION-venv python$PYTHON_VERSION-dev
        update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.$PYTHON_VERSION 1
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        log_info "在CentOS/RHEL系统上安装Python $PYTHON_VERSION..."
        yum install -y epel-release
        yum install -y python$PYTHON_VERSION python$PYTHON_VERSION-pip python$PYTHON_VERSION-devel
    else
        log_error "不支持的系统，请手动安装Python $PYTHON_VERSION"
        exit 1
    fi

    # 验证安装
    if python3 --version 2>&1 | grep -q "$PYTHON_VERSION"; then
        log_success "Python $PYTHON_VERSION 安装成功"
    else
        log_error "Python $PYTHON_VERSION 安装失败"
        exit 1
    fi
fi

# =============================================================================
# 3. 更新代码
# =============================================================================
log_info "步骤3: 更新项目代码..."

cd "$PROJECT_DIR"

# 检查git状态
if [ -d ".git" ]; then
    log_info "Git仓库存在，拉取最新代码..."
    git pull origin 001-mr || log_warning "拉取代码失败，使用现有代码"
else
    log_warning "不是Git仓库，跳过代码更新"
fi

log_success "代码更新完成"

# =============================================================================
# 4. 准备数据库
# =============================================================================
log_info "步骤4: 准备数据库..."

# 确保PostgreSQL服务运行
if ! systemctl is-active --quiet postgresql; then
    log_info "启动PostgreSQL服务..."
    systemctl start postgresql
    sleep 5
fi

# 测试数据库连接
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT 1" &> /dev/null; then
    log_success "数据库连接正常"
else
    log_warning "数据库连接失败，尝试创建用户..."

    # 尝试以postgres用户身份创建mr_admin用户
    sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';" | grep -q "$DB_USER" || {
        log_info "创建数据库用户: $DB_USER"
        sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD' CREATEDB SUPERUSER;"
    }

    # 测试新创建的用户
    if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT 1" &> /dev/null; then
        log_error "无法创建或连接数据库用户，请检查PostgreSQL配置"
        exit 1
    fi
fi

# 重置数据库（如果需要）
if [ "$SKIP_DB_RESET" != "true" ]; then
    log_info "重置数据库..."

    # 删除现有数据库
    PGPASSWORD="$DB_PASSWORD" dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>/dev/null || log_info "数据库不存在，跳过删除"

    # 重新创建数据库
    PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"
    log_success "数据库重置完成"
else
    # 确保数据库存在
    PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>/dev/null || log_info "数据库已存在"
fi

# 初始化数据库架构
log_info "初始化数据库架构..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 创建系统配置表
CREATE TABLE IF NOT EXISTS system_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(128) NOT NULL UNIQUE,
    config_value TEXT NOT NULL,
    value_type VARCHAR(32) NOT NULL DEFAULT 'string',
    category VARCHAR(64) NOT NULL,
    description TEXT,
    is_editable BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
EOF

log_success "数据库架构初始化完成"

# =============================================================================
# 5. 插入种子数据
# =============================================================================
log_info "步骤5: 插入种子数据..."

PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
-- 管理员账户 (密码: admin123456)
INSERT INTO admin_accounts (id, username, password_hash, full_name, email, phone, role, permissions, is_active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'superadmin',
    '$2b$12$Vx7X1BhBCDhR9i3EnKftwuXrWgbpFqrVfc3vbOIacp.8y3D0Y3mWG',
    '系统管理员',
    'admin@example.com',
    '13800138000',
    'super_admin',
    '["*"]'::jsonb,
    true,
    NOW(),
    NOW()
) ON CONFLICT (username) DO NOTHING;

-- 财务账户 (密码: finance123456)
INSERT INTO finance_accounts (id, username, password_hash, full_name, email, phone, role, permissions, is_active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'finance_wang',
    '$2b$12$CchkwqCQkLYZtS25roVS4epzwRG428SmaHr6/2xo7qhxXNFSqh/Vm',
    '王财务',
    'wang@example.com',
    '13800138003',
    'specialist',
    '["recharge:approve", "invoice:read", "finance:read"]'::jsonb,
    true,
    NOW(),
    NOW()
) ON CONFLICT (username) DO NOTHING;

-- 运营商账户 (密码: operator123456)
INSERT INTO operator_accounts (id, username, password_hash, full_name, email, phone, api_key, api_key_hash, balance, customer_tier, is_active, is_locked, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'operator_vip',
    '$2b$12$XfuFqZdnDgW2iLxO5qjchufN6C6FeRNhbseU/SkKG7Tk3Sh.hy1t6',
    '赵总(VIP游戏公司)',
    'zhao@vipgame.com',
    '13900139000',
    'vip_' || encode(gen_random_bytes(24), 'hex'),
    '$2b$12$XfuFqZdnDgW2iLxO5qjchufN6C6FeRNhbseU/SkKG7Tk3Sh.hy1t6',
    5000.00,
    'vip',
    true,
    false,
    NOW(),
    NOW()
) ON CONFLICT (username) DO NOTHING;

-- 系统配置
INSERT INTO system_configs (config_key, config_value, value_type, category, description, is_editable, created_at, updated_at)
VALUES
    ('balance_threshold', '100.00', 'float', 'business', '账户余额预警阈值（元）', true, NOW(), NOW()),
    ('session_timeout', '1800', 'integer', 'security', '会话超时时间（秒）', true, NOW(), NOW()),
    ('payment_timeout', '300', 'integer', 'business', '支付超时时间（秒）', true, NOW(), NOW())
ON CONFLICT (config_key) DO NOTHING;
EOF

log_success "种子数据插入完成"

# =============================================================================
# 6. 部署后端服务（使用Python 3.11）
# =============================================================================
log_info "步骤6: 部署后端服务（Python $PYTHON_VERSION）..."

cd "$PROJECT_DIR/backend"

# 停止现有后端服务
if pgrep -f "uvicorn.*main:app" > /dev/null; then
    log_info "停止现有后端服务..."
    pkill -f "uvicorn.*main:app"
    sleep 3
fi

# 停止systemd后端服务
if systemctl is-active --quiet mr-game-ops-backend; then
    log_info "停止systemd后端服务..."
    systemctl stop mr-game-ops-backend
fi

# 删除旧的虚拟环境
if [ -d "venv" ]; then
    log_info "删除旧的虚拟环境..."
    rm -rf venv
fi

# 使用Python 3.11创建新的虚拟环境
log_info "使用Python $PYTHON_VERSION创建虚拟环境..."
python$PYTHON_VERSION -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级pip
log_info "升级pip..."
python -m pip install --upgrade pip

# 安装兼容的包版本
log_info "安装Python依赖（兼容版本）..."
pip install "fastapi==0.115.0" "pydantic==2.9.0" "pydantic-settings==2.6.0"
pip install "uvicorn[standard]==0.24.0.post1" "sqlalchemy==2.0.23" "alembic>=1.12.1"
pip install "asyncpg>=0.29.0" "python-jose[cryptography]>=3.3.0" "passlib[bcrypt]>=1.7.4"
pip install "python-multipart>=0.0.6" "python-dotenv>=1.0.0" "email-validator>=2.1.0"
pip install "httpx>=0.25.2" "slowapi>=0.1.9" "redis>=5.0.1" "structlog>=23.2.0"
pip install "prometheus-client>=0.19.0" "aiofiles>=23.2.1" "openpyxl>=3.1.2" "reportlab>=4.0.7"
pip install "pytest==7.4.3" "pytest-asyncio==0.21.1" "pytest-cov==4.1.0"
pip install "black==23.12.0" "ruff==0.1.9" "mypy==1.7.1"

# 验证关键包版本
log_info "验证包版本..."
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import pydantic; print(f'Pydantic: {pydantic.__version__}')"

# 配置环境变量
log_info "配置后端环境变量..."
cat > .env.production << EOF
# 生产环境配置
DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=$BACKEND_PORT
CORS_ORIGINS=http://localhost:$FRONTEND_PORT,https://your-domain.com
EOF

# 测试导入
log_info "测试后端模块导入..."
python -c "from src.main import app; print('后端模块导入成功')"

# 启动后端服务
log_info "启动后端服务..."
nohup uvicorn src.main:app --host 0.0.0.0 --port $BACKEND_PORT --env-file .env.production > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > logs/backend.pid

log_success "后端服务启动完成 (PID: $BACKEND_PID)"

# =============================================================================
# 7. 部署前端服务
# =============================================================================
log_info "步骤7: 部署前端服务..."

cd "$PROJECT_DIR/frontend"

# 停止现有前端服务
if pgrep -f "serve.*-s dist" > /dev/null; then
    log_info "停止现有前端服务..."
    pkill -f "serve.*-s dist"
    sleep 3
fi

# 停止systemd前端服务
if systemctl is-active --quiet mr-game-ops-frontend; then
    log_info "停止systemd前端服务..."
    systemctl stop mr-game-ops-frontend
fi

# 安装依赖
log_info "安装Node.js依赖..."
npm install

# 构建生产版本
log_info "构建前端生产版本..."
npm run build

# 安装serve（如果未安装）
if ! command -v serve &> /dev/null; then
    log_info "安装serve包..."
    npm install -g serve
fi

# 配置环境变量
log_info "配置前端环境变量..."
cat > .env.production << EOF
VITE_BACKEND_URL=http://localhost:$BACKEND_PORT
VITE_API_BASE_URL=http://localhost:$BACKEND_PORT/api/v1
EOF

# 启动前端服务
log_info "启动前端服务..."
nohup serve -s dist -l $FRONTEND_PORT > logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > logs/frontend.pid

log_success "前端服务启动完成 (PID: $FRONTEND_PID)"

# =============================================================================
# 8. 创建systemd服务文件
# =============================================================================
log_info "步骤8: 创建systemd服务文件..."

# 后端服务文件
cat > /etc/systemd/system/mr-game-ops-backend.service << EOF
[Unit]
Description=MR Game Operations Backend
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR/backend
Environment=PATH=$PROJECT_DIR/backend/venv/bin
ExecStart=$PROJECT_DIR/backend/venv/bin/python$PYTHON_VERSION -m uvicorn src.main:app --host 0.0.0.0 --port $BACKEND_PORT --env-file .env.production
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 前端服务文件
cat > /etc/systemd/system/mr-game-ops-frontend.service << EOF
[Unit]
Description=MR Game Operations Frontend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR/frontend
ExecStart=$(which serve) -s dist -l $FRONTEND_PORT
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 重新加载systemd
systemctl daemon-reload

# 启用服务
systemctl enable mr-game-ops-backend
systemctl enable mr-game-ops-frontend

log_success "systemd服务文件创建完成"

# =============================================================================
# 9. 验证服务
# =============================================================================
log_info "步骤9: 验证服务状态..."

# 等待服务启动
log_info "等待服务启动..."
sleep 15

# 检查后端服务
MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s "http://localhost:$BACKEND_PORT/health" > /dev/null; then
        log_success "后端服务验证通过"
        break
    else
        log_info "等待后端服务启动... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
        sleep 5
        RETRY_COUNT=$((RETRY_COUNT + 1))
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    log_error "后端服务验证失败，请检查日志: $PROJECT_DIR/backend/logs/backend.log"
    log_error "最后几行日志:"
    tail -10 "$PROJECT_DIR/backend/logs/backend.log"
    exit 1
fi

# 检查前端服务
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s "http://localhost:$FRONTEND_PORT" > /dev/null; then
        log_success "前端服务验证通过"
        break
    else
        log_info "等待前端服务启动... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
        sleep 5
        RETRY_COUNT=$((RETRY_COUNT + 1))
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    log_error "前端服务验证失败，请检查日志: $PROJECT_DIR/frontend/logs/frontend.log"
    log_error "最后几行日志:"
    tail -10 "$PROJECT_DIR/frontend/logs/frontend.log"
    exit 1
fi

# =============================================================================
# 10. 完成
# =============================================================================
log_success "🎉 MR游戏运营管理系统部署完成！"

echo ""
echo "=========================================="
echo "服务状态总结："
echo "=========================================="
echo "后端服务: http://localhost:$BACKEND_PORT"
echo "前端服务: http://localhost:$FRONTEND_PORT"
echo "项目目录: $PROJECT_DIR"
echo "Python版本: $PYTHON_VERSION"
echo ""
echo "数据库配置："
echo "用户: $DB_USER"
echo "密码: $DB_PASSWORD"
echo "数据库: $DB_NAME"
echo ""
echo "登录凭据："
echo "管理员: superadmin / admin123456"
echo "财务: finance_wang / finance123456"
echo "运营商: operator_vip / operator123456"
echo ""
echo "进程信息："
echo "后端PID: $(cat $PROJECT_DIR/backend/logs/backend.pid 2>/dev/null || echo '未知')"
echo "前端PID: $(cat $PROJECT_DIR/frontend/logs/frontend.pid 2>/dev/null || echo '未知')"
echo ""
echo "服务管理命令："
echo "启动后端: systemctl start mr-game-ops-backend"
echo "停止后端: systemctl stop mr-game-ops-backend"
echo "启动前端: systemctl start mr-game-ops-frontend"
echo "停止前端: systemctl stop mr-game-ops-frontend"
echo "查看状态: systemctl status mr-game-ops-*"
echo ""
echo "日志查看："
echo "后端日志: tail -f $PROJECT_DIR/backend/logs/backend.log"
echo "前端日志: tail -f $PROJECT_DIR/frontend/logs/frontend.log"
echo "系统日志: journalctl -u mr-game-ops-backend -f"
echo "=========================================="

log_warning "重要提醒："
echo "1. 请更新CORS配置中的域名为实际域名"
echo "2. 配置防火墙规则开放端口 $BACKEND_PORT 和 $FRONTEND_PORT"
echo "3. 建议配置nginx反向代理"
echo "4. 生产环境建议使用HTTPS"
echo "5. 定期备份数据库"
echo ""
echo "✅ Python版本已确保为 $PYTHON_VERSION，兼容性问题已解决！"

exit 0