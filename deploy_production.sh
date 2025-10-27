#!/bin/bash

# =============================================================================
# MR游戏运营管理系统 - 生产环境直接部署脚本
# =============================================================================
# 使用说明：
# 1. 上传此脚本到生产服务器
# 2. chmod +x deploy_production.sh
# 3. ./deploy_production.sh
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
PROJECT_DIR="/opt/mr_game_ops"
BACKUP_DIR="/opt/mr_game_ops/backups"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="mr_game_ops"
DB_USER="mr_admin"
DB_PASSWORD="your_secure_password_here"  # 请修改为实际密码
BACKEND_PORT="8000"
FRONTEND_PORT="3000"

# 检查是否以root权限运行
if [[ $EUID -ne 0 ]]; then
    log_error "此脚本需要root权限运行"
    exit 1
fi

# 创建备份目录
mkdir -p "$BACKUP_DIR"
mkdir -p "$PROJECT_DIR"

log_info "开始MR游戏运营管理系统生产环境部署..."

# =============================================================================
# 1. 检查系统依赖
# =============================================================================
log_info "检查系统依赖..."

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

# 检查Python
if ! command -v python3 &> /dev/null; then
    log_error "Python3未安装，请先安装Python3"
    exit 1
fi

log_success "系统依赖检查完成"

# =============================================================================
# 2. 备份现有数据
# =============================================================================
log_info "备份现有数据..."

# 备份数据库
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" &> /dev/null; then
    BACKUP_FILE="$BACKUP_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"
    PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"
    log_success "数据库备份完成: $BACKUP_FILE"
else
    log_warning "数据库连接失败，跳过备份"
fi

# =============================================================================
# 3. 更新代码
# =============================================================================
log_info "更新项目代码..."

cd "$PROJECT_DIR"

# 如果是git仓库，拉取最新代码
if [ -d ".git" ]; then
    git pull origin 001-mr
    log_success "代码更新完成"
else
    log_error "项目目录不是git仓库，请先克隆项目"
    exit 1
fi

# =============================================================================
# 4. 重建数据库
# =============================================================================
log_info "重建数据库架构..."

# 删除现有数据库架构
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
-- 删除现有架构
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

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

log_success "数据库架构重建完成"

# =============================================================================
# 5. 插入种子数据
# =============================================================================
log_info "插入种子数据..."

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
);

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
);

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
);

-- 系统配置
INSERT INTO system_configs (config_key, config_value, value_type, category, description, is_editable, created_at, updated_at)
VALUES
    ('balance_threshold', '100.00', 'float', 'business', '账户余额预警阈值（元）', true, NOW(), NOW()),
    ('session_timeout', '1800', 'integer', 'security', '会话超时时间（秒）', true, NOW(), NOW()),
    ('payment_timeout', '300', 'integer', 'business', '支付超时时间（秒）', true, NOW(), NOW());
EOF

log_success "种子数据插入完成"

# =============================================================================
# 6. 部署后端服务
# =============================================================================
log_info "部署后端服务..."

cd "$PROJECT_DIR/backend"

# 停止现有后端服务
if pgrep -f "uvicorn.*main:app" > /dev/null; then
    pkill -f "uvicorn.*main:app"
    log_info "停止现有后端服务"
fi

# 创建Python虚拟环境
if [ ! -d "venv" ]; then
    python3 -m venv venv
    log_info "创建Python虚拟环境"
fi

# 激活虚拟环境并安装依赖
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 配置环境变量
if [ ! -f ".env.production" ]; then
    log_warning "未找到.env.production文件，使用默认配置"
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
CORS_ORIGINS=https://your-domain.com  # 请修改为实际域名
EOF
fi

# 启动后端服务
nohup uvicorn src.main:app --host 0.0.0.0 --port $BACKEND_PORT --env-file .env.production > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > logs/backend.pid

log_success "后端服务启动完成 (PID: $BACKEND_PID)"

# =============================================================================
# 7. 部署前端服务
# =============================================================================
log_info "部署前端服务..."

cd "$PROJECT_DIR/frontend"

# 停止现有前端服务
if pgrep -f "vite.*--port" > /dev/null; then
    pkill -f "vite.*--port"
    log_info "停止现有前端服务"
fi

# 安装依赖
npm install

# 构建生产版本
npm run build

# 配置环境变量
if [ ! -f ".env.production" ]; then
    cat > .env.production << EOF
VITE_BACKEND_URL=http://localhost:$BACKEND_PORT
VITE_API_BASE_URL=http://localhost:$BACKEND_PORT/api/v1
EOF
fi

# 启动前端服务 (使用serve或者nginx)
if command -v serve &> /dev/null; then
    nohup serve -s dist -l $FRONTEND_PORT > logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
else
    # 如果没有serve，使用开发模式（生产环境建议配置nginx）
    log_warning "未安装serve，使用开发模式，建议配置nginx"
    nohup npm run dev -- --port $FRONTEND_PORT --host 0.0.0.0 > logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
fi

echo $FRONTEND_PID > logs/frontend.pid

log_success "前端服务启动完成 (PID: $FRONTEND_PID)"

# =============================================================================
# 8. 验证部署
# =============================================================================
log_info "验证部署状态..."

# 等待服务启动
sleep 10

# 检查后端服务
if curl -f -s "http://localhost:$BACKEND_PORT/health" > /dev/null; then
    log_success "后端服务验证通过"
else
    log_error "后端服务验证失败"
    exit 1
fi

# 检查前端服务
if curl -f -s "http://localhost:$FRONTEND_PORT" > /dev/null; then
    log_success "前端服务验证通过"
else
    log_error "前端服务验证失败"
    exit 1
fi

# =============================================================================
# 9. 创建systemd服务文件
# =============================================================================
log_info "创建systemd服务文件..."

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
ExecStart=$PROJECT_DIR/backend/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port $BACKEND_PORT --env-file .env.production
Restart=always
RestartSec=10

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
# 10. 完成
# =============================================================================
log_success "🎉 MR游戏运营管理系统生产环境部署完成！"

echo ""
echo "=========================================="
echo "部署信息总结："
echo "=========================================="
echo "项目目录: $PROJECT_DIR"
echo "后端服务: http://localhost:$BACKEND_PORT"
echo "前端服务: http://localhost:$FRONTEND_PORT"
echo "备份目录: $BACKUP_DIR"
echo ""
echo "登录凭据："
echo "管理员: superadmin / admin123456"
echo "财务: finance_wang / finance123456"
echo "运营商: operator_vip / operator123456"
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
echo "=========================================="

log_warning "请确保："
echo "1. 修改脚本中的数据库密码为实际密码"
echo "2. 更新CORS配置中的域名为实际域名"
echo "3. 配置防火墙规则开放端口 $BACKEND_PORT 和 $FRONTEND_PORT"
echo "4. 建议配置nginx反向代理"
echo "5. 定期备份数据库"

exit 0