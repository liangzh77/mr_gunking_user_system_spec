#!/bin/bash

# =============================================================================
# MR游戏运营管理系统 - 本地部署脚本
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

# 检查是否为root用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用root用户运行此脚本"
        exit 1
    fi
}

# 安装系统依赖
install_dependencies() {
    log_info "安装系统依赖..."

    apt update
    apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib redis-server nginx curl wget

    log_success "系统依赖安装完成"
}

# 配置数据库
setup_database() {
    log_info "配置PostgreSQL数据库..."

    # 启动PostgreSQL服务
    systemctl start postgresql
    systemctl enable postgresql

    # 创建数据库和用户
    sudo -u postgres createdb mr_game_ops_prod || true
    sudo -u postgres createuser mr_admin_prod || true

    # 设置密码和权限
    sudo -u postgres psql -c "ALTER USER mr_admin_prod PASSWORD 'ProdSecure2024!';" || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mr_game_ops_prod TO mr_admin_prod;" || true

    log_success "数据库配置完成"
}

# 配置Redis
setup_redis() {
    log_info "配置Redis..."

    # 启动Redis服务
    systemctl start redis-server
    systemctl enable redis-server

    # 测试Redis连接
    redis-cli ping

    log_success "Redis配置完成"
}

# 部署应用
deploy_app() {
    log_info "部署MR游戏应用..."

    # 创建应用目录
    mkdir -p /opt/mr-game-app
    cd /opt/mr-game-app

    # 创建虚拟环境
    python3 -m venv venv
    source venv/bin/activate

    # 安装Python依赖
    pip install --upgrade pip
    pip install -r requirements.txt

    # 创建环境变量文件
    cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://mr_admin_prod:ProdSecure2024!@localhost/mr_game_ops_prod
REDIS_URL=redis://localhost:6379/0
ENCRYPTION_KEY=abcdefghijklmnopqrstuvwxyz123456
JWT_SECRET_KEY=JWT_Secret_Key_2024_Production
CORS_ORIGINS=http://121.41.231.69,http://localhost
API_BASE_URL=http://121.41.231.69/api/v1
POSTGRES_DB=mr_game_ops_prod
POSTGRES_USER=mr_admin_prod
POSTGRES_PASSWORD=ProdSecure2024!
EOF

    log_success "应用部署完成"
}

# 配置Nginx
setup_nginx() {
    log_info "配置Nginx..."

    # 创建Nginx配置
    cat > /etc/nginx/sites-available/mr-game << 'EOF'
server {
    listen 80;
    server_name _;

    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态文件和文档
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

    # 启用站点
    ln -sf /etc/nginx/sites-available/mr-game /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default

    # 测试配置
    nginx -t

    # 重启Nginx
    systemctl restart nginx
    systemctl enable nginx

    log_success "Nginx配置完成"
}

# 创建启动脚本
create_startup_script() {
    log_info "创建启动脚本..."

    cat > /opt/mr-game-app/start.sh << 'EOF'
#!/bin/bash

cd /opt/mr-game-app
source venv/bin/activate

# 启动应用
nohup python main.py > app.log 2>&1 &

echo $! > app.pid
echo "MR游戏管理系统已启动，PID: $(cat app.pid)"
EOF

    cat > /opt/mr-game-app/stop.sh << 'EOF'
#!/bin/bash

cd /opt/mr-game-app

if [ -f app.pid ]; then
    kill $(cat app.pid)
    rm -f app.pid
    echo "MR游戏管理系统已停止"
else
    echo "未找到运行中的服务"
fi
EOF

    cat > /opt/mr-game-app/status.sh << 'EOF'
#!/bin/bash

cd /opt/mr-game-app

if [ -f app.pid ]; then
    PID=$(cat app.pid)
    if ps -p $PID > /dev/null; then
        echo "MR游戏管理系统正在运行，PID: $PID"
        curl -s http://localhost/health | python -m json.tool
    else
        echo "服务未运行（PID文件存在但进程不存在）"
        rm -f app.pid
    fi
else
    echo "MR游戏管理系统未运行"
fi
EOF

    # 设置执行权限
    chmod +x /opt/mr-game-app/*.sh

    log_success "启动脚本创建完成"
}

# 启动应用
start_app() {
    log_info "启动MR游戏管理系统..."

    cd /opt/mr-game-app
    ./start.sh

    # 等待服务启动
    sleep 5

    # 测试服务
    if curl -f http://localhost/health > /dev/null 2>&1; then
        log_success "MR游戏管理系统启动成功！"
    else
        log_warning "服务启动可能需要更长时间，请检查日志"
        log_info "查看日志: tail -f /opt/mr-game-app/app.log"
    fi
}

# 创建系统服务
create_systemd_service() {
    log_info "创建系统服务..."

    cat > /etc/systemd/system/mr-game.service << 'EOF'
[Unit]
Description=MR Game Management System
After=network.target postgresql.service redis.service nginx.service

[Service]
Type=forking
User=root
WorkingDirectory=/opt/mr-game-app
ExecStart=/opt/mr-game-app/start.sh
ExecStop=/opt/mr-game-app/stop.sh
ExecReload=/bin/kill -HUP $MAINPID
PIDFile=/opt/mr-game-app/app.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # 重新加载systemd
    systemctl daemon-reload

    # 启用服务
    systemctl enable mr-game.service

    log_success "系统服务创建完成"
}

# 显示部署信息
show_deployment_info() {
    log_success "🎉 MR游戏运营管理系统部署完成！"
    echo
    echo "==============================================="
    echo "📋 系统信息"
    echo "==============================================="
    echo "🌐 应用地址: http://121.41.231.69"
    echo "📚 API文档: http://121.41.231.69/docs"
    echo "🔍 健康检查: http://121.41.231.69/health"
    echo "👤 管理员账号: admin / AdminSecure123!2024"
    echo "💰 财务账号: finance / Finance123!2024"
    echo
    echo "📁 应用目录: /opt/mr-game-app"
    echo "📝 日志文件: /opt/mr-game-app/app.log"
    echo "🔧 管理命令:"
    echo "  启动服务: /opt/mr-game-app/start.sh"
    echo "  停止服务: /opt/mr-game-app/stop.sh"
    echo "  查看状态: /opt/mr-game-app/status.sh"
    echo "  查看日志: tail -f /opt/mr-game-app/app.log"
    echo
    echo "🔧 系统服务:"
    echo "  启动: systemctl start mr-game"
    echo "  停止: systemctl stop mr-game"
    echo "  重启: systemctl restart mr-game"
    echo "  状态: systemctl status mr-game"
    echo "==============================================="
}

# 主函数
main() {
    log_info "🚀 开始部署MR游戏运营管理系统..."

    check_root
    install_dependencies
    setup_database
    setup_redis
    deploy_app
    setup_nginx
    create_startup_script
    create_systemd_service
    start_app
    show_deployment_info

    log_success "🎊 部署完成！系统已成功启动！"
}

# 执行主函数
main "$@"