#!/bin/bash

# =============================================================================
# MR游戏运营管理系统 - 生产环境部署脚本
# =============================================================================
# 说明: 此脚本用于在生产服务器上部署应用
# 使用方法: ./02-deploy.sh
# =============================================================================

set -e

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

# 检查是否为root用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用root用户运行此脚本"
        exit 1
    fi
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先运行 01-server-setup.sh"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先运行 01-server-setup.sh"
        exit 1
    fi
}

# 检查环境变量文件
check_env_file() {
    if [ ! -f ".env.prod" ]; then
        log_error "环境变量文件 .env.prod 不存在"
        log_info "请复制 .env.prod.example 到 .env.prod 并修改配置"
        exit 1
    fi

    # 检查是否有默认密码
    if grep -q "CHANGE_ME" .env.prod; then
        log_warning "检测到默认密码，请修改 .env.prod 中的安全配置"
        read -p "是否继续部署? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 创建应用目录结构
create_directories() {
    log_info "创建应用目录结构..."

    mkdir -p /opt/mr-game-ops/{backend,frontend,config,scripts,data,logs}
    mkdir -p /opt/mr-game-ops/data/{postgres,redis,uploads,invoices}
    mkdir -p /opt/mr-game-ops/config/{nginx,ssl,prometheus}
    mkdir -p /opt/mr-game-ops/backups
    mkdir -p /opt/mr-game-ops/logs/{nginx,app}

    chown -R root:root /opt/mr-game-ops
    chmod -R 755 /opt/mr-game-ops

    log_success "目录结构创建完成"
}

# 生成SSL证书 (自签名，生产环境请使用Let's Encrypt)
generate_ssl_cert() {
    log_info "生成SSL证书..."

    if [ ! -f "/opt/mr-game-ops/config/ssl/cert.pem" ]; then
        # 生成自签名证书 (仅用于测试)
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout /opt/mr-game-ops/config/ssl/key.pem \
            -out /opt/mr-game-ops/config/ssl/cert.pem \
            -subj "/C=CN/ST=State/L=City/O=Organization/CN=yourdomain.com"

        log_warning "已生成自签名SSL证书，生产环境请使用Let's Encrypt或其他CA证书"
    else
        log_info "SSL证书已存在，跳过生成"
    fi
}

# 配置Prometheus
configure_prometheus() {
    log_info "配置Prometheus监控..."

    cat > /opt/mr-game-ops/config/prometheus/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'mr-game-ops-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']
    metrics_path: '/metrics'
    scrape_interval: 30s
EOF

    log_success "Prometheus配置完成"
}

# 构建和启动服务
deploy_services() {
    log_info "构建和启动服务..."

    # 进入应用目录
    cd /opt/mr-game-ops

    # 停止可能运行的服务
    log_info "停止现有服务..."
    docker-compose -f docker-compose.prod.yml down || true

    # 拉取最新镜像
    log_info "拉取最新Docker镜像..."
    docker-compose -f docker-compose.prod.yml pull

    # 构建应用镜像
    log_info "构建应用镜像..."
    docker-compose -f docker-compose.prod.yml build --no-cache

    # 启动服务
    log_info "启动服务..."
    docker-compose -f docker-compose.prod.yml up -d

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30

    # 检查服务状态
    log_info "检查服务状态..."
    docker-compose -f docker-compose.prod.yml ps

    log_success "服务部署完成"
}

# 初始化数据库
init_database() {
    log_info "初始化数据库..."

    # 等待数据库启动
    log_info "等待数据库启动..."
    while ! docker exec mr_game_ops_db_prod pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} >/dev/null 2>&1; do
        echo "等待PostgreSQL启动..."
        sleep 5
    done

    log_success "数据库启动完成"

    # 创建管理员账户
    log_info "创建管理员账户..."
    docker exec mr_game_ops_backend_prod python -c "
import asyncio
import sys
sys.path.insert(0, '/app')
from src.core.utils.password import hash_password
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import uuid
from datetime import datetime

async def create_admin():
    db_url = 'postgresql+asyncpg://mr_admin_prod:MR_SECURE_PASSWORD_PROD_2024_CHANGE_ME@postgres:5432/mr_game_ops_prod'
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            result = await session.execute(text(\"SELECT COUNT(*) FROM admin_accounts WHERE username = 'admin'\"))
            count = result.scalar()

            if count == 0:
                admin_id = str(uuid.uuid4())
                password_hash = hash_password('AdminSecure123!2024')
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
                    'email': 'admin@yourdomain.com',
                    'phone': '13800138000',
                    'role': 'super_admin',
                    'permissions': '[\"*\"]',
                    'is_active': True,
                    'created_at': current_time,
                    'updated_at': current_time
                })

                await session.commit()
                print('管理员账户创建成功')
                print('用户名: admin')
                print('密码: AdminSecure123!2024')
            else:
                print('管理员账户已存在')

    except Exception as e:
        print(f'创建管理员账户失败: {e}')
    finally:
        await engine.dispose()

asyncio.run(create_admin())
"

    log_success "数据库初始化完成"
}

# 运行健康检查
health_check() {
    log_info "运行健康检查..."

    # 检查后端服务
    if curl -f http://localhost/health >/dev/null 2>&1; then
        log_success "后端服务健康检查通过"
    else
        log_error "后端服务健康检查失败"
        return 1
    fi

    # 检查前端服务
    if curl -f http://localhost >/dev/null 2>&1; then
        log_success "前端服务健康检查通过"
    else
        log_warning "前端服务健康检查失败，可能需要等待更长时间"
    fi

    return 0
}

# 显示部署信息
show_deployment_info() {
    log_success "🎉 部署完成！"
    echo
    echo "==================================="
    echo "📋 部署信息"
    echo "==================================="
    echo "🌐 应用地址: https://yourdomain.com"
    echo "👤 管理员账户: admin / AdminSecure123!2024"
    echo "📊 监控面板: http://your-server-ip:3001 (admin / GRAFANA_ADMIN_PASSWORD_CHANGE_ME)"
    echo "📈 Prometheus: http://your-server-ip:9090"
    echo "📁 应用目录: /opt/mr-game-ops"
    echo "📝 日志目录: /opt/mr-game-ops/logs"
    echo "💾 备份目录: /opt/mr-game-ops/backups"
    echo
    echo "🔧 管理命令:"
    echo "  查看服务状态: cd /opt/mr-game-ops && docker-compose -f docker-compose.prod.yml ps"
    echo "  查看日志: cd /opt/mr-game-ops && docker-compose -f docker-compose.prod.yml logs -f"
    echo "  重启服务: cd /opt/mr-game-ops && docker-compose -f docker-compose.prod.yml restart"
    echo "  停止服务: cd /opt/mr-game-ops && docker-compose -f docker-compose.prod.yml down"
    echo
    echo "⚠️  重要提醒:"
    echo "1. 请修改 .env.prod 中的所有默认密码和密钥"
    echo "2. 请配置有效的SSL证书"
    echo "3. 请配置域名解析指向此服务器"
    echo "4. 请定期检查备份和数据安全"
    echo "==================================="
}

# 主函数
main() {
    log_info "🚀 开始部署MR游戏运营管理系统..."

    check_root
    check_docker
    check_env_file
    create_directories
    generate_ssl_cert
    configure_prometheus
    deploy_services
    init_database

    # 等待服务完全启动
    log_info "等待服务完全启动..."
    sleep 60

    if health_check; then
        show_deployment_info
    else
        log_error "部署失败，请检查日志"
        exit 1
    fi
}

# 加载环境变量
if [ -f ".env.prod" ]; then
    set -a
    source .env.prod
    set +a
fi

# 执行主函数
main "$@"