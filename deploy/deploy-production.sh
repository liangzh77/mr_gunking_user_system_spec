#!/bin/bash

# =============================================================================
# MR游戏运营管理系统 - 一键生产环境部署脚本
# =============================================================================
# 适用于: Ubuntu 24.04 LTS
# 说明: 保姆级部署脚本，详细解释每一步
# =============================================================================

set -e  # 遇到错误立即停止

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    print_error "请使用root用户运行此脚本"
    echo "执行: sudo su"
    exit 1
fi

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║         MR游戏运营管理系统 - 生产环境一键部署                      ║"
echo "║                   Ubuntu 24.04 LTS                                ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# 步骤1: 系统环境检查
# ============================================================================
print_step "【步骤1/10】检查系统环境..."

echo "- 操作系统版本:"
lsb_release -d | awk '{print "  " $0}'

echo "- CPU核心数:"
nproc | awk '{print "  " $0 " 核"}'

echo "- 内存大小:"
free -h | grep Mem | awk '{print "  总计: " $2 ", 可用: " $7}'

echo "- 磁盘空间:"
df -h / | tail -1 | awk '{print "  总计: " $2 ", 已用: " $3 ", 可用: " $4 ", 使用率: " $5}'

# 检查最低配置
TOTAL_MEM=$(free -g | grep Mem | awk '{print $2}')
if [ "$TOTAL_MEM" -lt 3 ]; then
    print_warning "内存小于4GB，可能影响性能"
fi

AVAILABLE_DISK=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$AVAILABLE_DISK" -lt 20 ]; then
    print_error "可用磁盘空间小于20GB，无法继续部署"
    exit 1
fi

print_success "系统环境检查通过"
sleep 2

# ============================================================================
# 步骤2: 更新系统
# ============================================================================
print_step "【步骤2/10】更新系统包..."

apt update -qq
print_success "系统包列表更新完成"

# ============================================================================
# 步骤3: 安装基础工具
# ============================================================================
print_step "【步骤3/10】安装基础工具..."

apt install -y -qq curl wget git vim htop unzip software-properties-common \
    apt-transport-https ca-certificates gnupg lsb-release > /dev/null 2>&1

print_success "基础工具安装完成"

# ============================================================================
# 步骤4: 安装Docker
# ============================================================================
print_step "【步骤4/10】安装Docker..."

# 检查Docker是否已安装
if command -v docker &> /dev/null; then
    print_warning "Docker已安装，跳过安装步骤"
    docker --version
else
    # 添加Docker官方GPG密钥
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    # 添加Docker仓库
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null

    # 安装Docker
    apt update -qq
    apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin > /dev/null 2>&1

    # 启动Docker服务
    systemctl start docker
    systemctl enable docker > /dev/null 2>&1

    print_success "Docker安装完成"
    docker --version
fi

# 验证Docker是否正常工作
if ! docker ps > /dev/null 2>&1; then
    print_error "Docker未正常运行"
    exit 1
fi

# ============================================================================
# 步骤5: 创建应用目录
# ============================================================================
print_step "【步骤5/10】创建应用目录结构..."

# 创建主目录
mkdir -p /opt/mr-game-ops

# 创建数据目录
mkdir -p /opt/mr-game-ops/data/postgres
mkdir -p /opt/mr-game-ops/data/redis
mkdir -p /opt/mr-game-ops/data/uploads
mkdir -p /opt/mr-game-ops/data/invoices
mkdir -p /opt/mr-game-ops/data/prometheus
mkdir -p /opt/mr-game-ops/data/grafana

# 创建日志目录
mkdir -p /opt/mr-game-ops/logs/app
mkdir -p /opt/mr-game-ops/logs/nginx

# 创建配置目录
mkdir -p /opt/mr-game-ops/config/nginx
mkdir -p /opt/mr-game-ops/config/ssl
mkdir -p /opt/mr-game-ops/config/prometheus

# 创建备份目录
mkdir -p /opt/mr-game-ops/backups

# 创建脚本目录
mkdir -p /opt/mr-game-ops/scripts

print_success "应用目录创建完成"
echo "  主目录: /opt/mr-game-ops"

# ============================================================================
# 步骤6: 复制部署文件
# ============================================================================
print_step "【步骤6/10】复制部署文件到应用目录..."

# 获取当前脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 复制docker-compose配置
cp "$SCRIPT_DIR/docker-compose.prod.yml" /opt/mr-game-ops/
print_success "Docker Compose配置文件已复制"

# 复制环境变量配置
if [ ! -f "$SCRIPT_DIR/.env.prod" ]; then
    print_error "未找到.env.prod配置文件"
    exit 1
fi
cp "$SCRIPT_DIR/.env.prod" /opt/mr-game-ops/
print_success "环境变量配置文件已复制"

# 复制Nginx配置（如果存在）
if [ -d "$SCRIPT_DIR/config/nginx" ]; then
    cp -r "$SCRIPT_DIR/config/nginx/"* /opt/mr-game-ops/config/nginx/
    print_success "Nginx配置文件已复制"
fi

# ============================================================================
# 步骤7: 配置防火墙
# ============================================================================
print_step "【步骤7/10】配置防火墙..."

# 检查ufw是否安装
if ! command -v ufw &> /dev/null; then
    apt install -y ufw > /dev/null 2>&1
fi

# 配置防火墙规则
ufw --force reset > /dev/null 2>&1
ufw default deny incoming > /dev/null 2>&1
ufw default allow outgoing > /dev/null 2>&1
ufw allow 22/tcp comment 'SSH' > /dev/null 2>&1
ufw allow 80/tcp comment 'HTTP' > /dev/null 2>&1
ufw allow 443/tcp comment 'HTTPS' > /dev/null 2>&1
ufw --force enable > /dev/null 2>&1

print_success "防火墙配置完成"
echo "  已开放端口: 22(SSH), 80(HTTP), 443(HTTPS)"

# ============================================================================
# 步骤8: 构建和启动Docker容器
# ============================================================================
print_step "【步骤8/10】构建和启动Docker容器（这可能需要5-10分钟）..."

cd /opt/mr-game-ops

# 检查backend和frontend源码目录
if [ ! -d "$SCRIPT_DIR/../backend" ]; then
    print_error "未找到backend源码目录"
    print_warning "请确保backend目录与deploy目录在同一父目录下"
    exit 1
fi

if [ ! -d "$SCRIPT_DIR/../frontend" ]; then
    print_error "未找到frontend源码目录"
    print_warning "请确保frontend目录与deploy目录在同一父目录下"
    exit 1
fi

# 复制源码到应用目录
print_step "复制应用源码..."
cp -r "$SCRIPT_DIR/../backend" /opt/mr-game-ops/
cp -r "$SCRIPT_DIR/../frontend" /opt/mr-game-ops/
print_success "应用源码已复制"

# 加载环境变量
set -a
source .env.prod
set +a

# 停止可能存在的旧容器
docker compose -f docker-compose.prod.yml down -v > /dev/null 2>&1 || true

# 构建并启动容器
print_step "构建Docker镜像（请稍候）..."
docker compose -f docker-compose.prod.yml build --no-cache

print_step "启动所有服务..."
docker compose -f docker-compose.prod.yml up -d

# 等待容器启动
print_step "等待服务启动（60秒）..."
sleep 60

print_success "Docker容器启动完成"

# ============================================================================
# 步骤9: 验证部署
# ============================================================================
print_step "【步骤9/10】验证部署..."

echo ""
echo "容器状态:"
docker compose -f docker-compose.prod.yml ps

echo ""
echo "正在检查各服务健康状态..."

# 检查PostgreSQL
if docker exec mr_game_ops_db_prod pg_isready -U $POSTGRES_USER -d $POSTGRES_DB > /dev/null 2>&1; then
    print_success "PostgreSQL数据库运行正常"
else
    print_error "PostgreSQL数据库未正常运行"
fi

# 检查Redis
if docker exec mr_game_ops_redis_prod redis-cli -a "$REDIS_PASSWORD" ping > /dev/null 2>&1; then
    print_success "Redis缓存运行正常"
else
    print_error "Redis缓存未正常运行"
fi

# 检查Backend API
sleep 10
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_success "后端API运行正常"
else
    print_warning "后端API可能还在启动中，请稍后手动检查"
fi

# ============================================================================
# 步骤10: 创建管理脚本
# ============================================================================
print_step "【步骤10/10】创建管理脚本..."

# 创建备份脚本
cat > /opt/mr-game-ops/scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/mr-game-ops/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 加载环境变量
cd /opt/mr-game-ops
source .env.prod

# PostgreSQL备份
docker exec mr_game_ops_db_prod pg_dump -U $POSTGRES_USER -d $POSTGRES_DB > $BACKUP_DIR/postgres_$DATE.sql

# 压缩备份
gzip $BACKUP_DIR/postgres_$DATE.sql

# 清理7天前的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "备份完成: postgres_$DATE.sql.gz"
EOF

chmod +x /opt/mr-game-ops/scripts/backup.sh
print_success "备份脚本已创建"

# 设置定时备份
(crontab -l 2>/dev/null | grep -v backup.sh; echo "0 2 * * * /opt/mr-game-ops/scripts/backup.sh >> /var/log/mr-backup.log 2>&1") | crontab -
print_success "自动备份已配置（每天凌晨2点）"

# ============================================================================
# 部署完成
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                    🎉 部署成功完成！                               ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# 获取服务器IP
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "无法获取")

echo "📋 部署信息摘要:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  应用目录:      /opt/mr-game-ops"
echo "  配置文件:      /opt/mr-game-ops/.env.prod"
echo "  日志目录:      /opt/mr-game-ops/logs"
echo "  备份目录:      /opt/mr-game-ops/backups"
echo "  服务器IP:      $SERVER_IP"
echo ""
echo "🌐 访问地址:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  后端API:       http://$SERVER_IP:8000"
echo "  健康检查:      http://$SERVER_IP:8000/health"
echo "  API文档:       http://$SERVER_IP:8000/docs"
echo "  Grafana监控:   http://$SERVER_IP:3001 (用户名: admin)"
echo "  Prometheus:    http://$SERVER_IP:9090"
echo ""
echo "🔧 常用管理命令:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  查看服务状态:  cd /opt/mr-game-ops && docker compose -f docker-compose.prod.yml ps"
echo "  查看日志:      cd /opt/mr-game-ops && docker compose -f docker-compose.prod.yml logs -f"
echo "  重启服务:      cd /opt/mr-game-ops && docker compose -f docker-compose.prod.yml restart"
echo "  停止服务:      cd /opt/mr-game-ops && docker compose -f docker-compose.prod.yml down"
echo "  手动备份:      /opt/mr-game-ops/scripts/backup.sh"
echo ""
echo "⚠️  下一步操作:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  1. 配置域名DNS解析到: $SERVER_IP"
echo "  2. 配置SSL证书（执行: ./03-setup-ssl.sh 你的域名.com）"
echo "  3. 初始化数据库并创建管理员账户"
echo "  4. 测试所有功能是否正常"
echo ""
echo "📞 如遇问题，请查看日志:"
echo "  docker compose -f /opt/mr-game-ops/docker-compose.prod.yml logs"
echo ""
