#!/bin/bash
# =============================================================================
# 服务器初始化脚本 - 首次部署前在Linux服务器上运行
# =============================================================================
# 用法:
# 1. 将此脚本上传到服务器
# 2. chmod +x setup-server.sh
# 3. sudo ./setup-server.sh
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# 检查是否以root运行
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 sudo 运行此脚本"
    exit 1
fi

log_info "=========================================="
log_info "MR游戏运营系统 - 服务器初始化"
log_info "=========================================="

# 配置变量
PROJECT_DIR="/opt/mr_gunking_user_system_spec"
DEPLOY_USER="deploy"
GITHUB_REPO="https://github.com/你的用户名/mr_gunking_user_system_spec.git"  # 修改为你的仓库地址
BRANCH="main"

# ==================== 1. 系统更新 ====================
log_info "步骤 1/10: 更新系统包..."
apt-get update -y
apt-get upgrade -y
log_success "系统更新完成"

# ==================== 2. 安装基础工具 ====================
log_info "步骤 2/10: 安装基础工具..."
apt-get install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    ufw \
    fail2ban \
    unzip \
    ca-certificates \
    gnupg \
    lsb-release

log_success "基础工具安装完成"

# ==================== 3. 安装Docker ====================
log_info "步骤 3/10: 安装Docker..."

if command -v docker &> /dev/null; then
    log_warning "Docker已安装,跳过"
else
    # 添加Docker官方GPG密钥
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # 设置Docker仓库
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # 安装Docker
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # 启动Docker
    systemctl start docker
    systemctl enable docker

    log_success "Docker安装完成"
fi

# 检查Docker版本
docker --version
docker compose version

# ==================== 4. 创建部署用户 ====================
log_info "步骤 4/10: 创建部署用户..."

if id "$DEPLOY_USER" &>/dev/null; then
    log_warning "用户 $DEPLOY_USER 已存在"
else
    # 创建用户
    useradd -m -s /bin/bash $DEPLOY_USER

    # 添加到docker组
    usermod -aG docker $DEPLOY_USER

    # 设置sudo权限(无需密码)
    echo "$DEPLOY_USER ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/$DEPLOY_USER

    log_success "用户 $DEPLOY_USER 创建完成"
fi

# ==================== 5. 配置SSH密钥 ====================
log_info "步骤 5/10: 配置SSH..."

# 创建.ssh目录
SSH_DIR="/home/$DEPLOY_USER/.ssh"
mkdir -p $SSH_DIR
chmod 700 $SSH_DIR

# 创建authorized_keys文件(如果不存在)
touch $SSH_DIR/authorized_keys
chmod 600 $SSH_DIR/authorized_keys
chown -R $DEPLOY_USER:$DEPLOY_USER $SSH_DIR

log_success "SSH目录配置完成"
log_warning "⚠️  重要: 请手动添加GitHub Actions的公钥到 $SSH_DIR/authorized_keys"
log_info "生成SSH密钥对的命令: ssh-keygen -t rsa -b 4096 -C 'github-actions'"

# ==================== 6. 克隆项目代码 ====================
log_info "步骤 6/10: 克隆项目代码..."

if [ -d "$PROJECT_DIR" ]; then
    log_warning "项目目录已存在: $PROJECT_DIR"
else
    git clone -b $BRANCH $GITHUB_REPO $PROJECT_DIR
    chown -R $DEPLOY_USER:$DEPLOY_USER $PROJECT_DIR
    log_success "项目代码克隆完成"
fi

# ==================== 7. 创建必要的目录 ====================
log_info "步骤 7/10: 创建必要的目录..."

mkdir -p /var/backups/mr_game_ops
mkdir -p /var/log/mr_game_ops
mkdir -p $PROJECT_DIR/backups
mkdir -p $PROJECT_DIR/nginx/ssl

chown -R $DEPLOY_USER:$DEPLOY_USER /var/backups/mr_game_ops
chown -R $DEPLOY_USER:$DEPLOY_USER /var/log/mr_game_ops
chown -R $DEPLOY_USER:$DEPLOY_USER $PROJECT_DIR

log_success "目录创建完成"

# ==================== 8. 配置防火墙 ====================
log_info "步骤 8/10: 配置防火墙..."

# 启用UFW
ufw --force enable

# 允许SSH
ufw allow 22/tcp

# 允许HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# 查看状态
ufw status

log_success "防火墙配置完成"

# ==================== 9. 配置环境变量 ====================
log_info "步骤 9/10: 配置环境变量..."

cd $PROJECT_DIR/backend

if [ ! -f ".env.production" ]; then
    cp .env.example .env.production
    log_warning "⚠️  已创建 .env.production，请立即修改其中的密钥!"
    log_info "生成密钥的命令:"
    echo "  python3 -c \"import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))\""
    echo "  python3 -c \"import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))\""
else
    log_info ".env.production 已存在"
fi

log_success "环境变量配置完成"

# ==================== 10. 系统优化 ====================
log_info "步骤 10/10: 系统优化..."

# 设置文件描述符限制
cat >> /etc/security/limits.conf << EOF
* soft nofile 65536
* hard nofile 65536
EOF

# 优化内核参数
cat >> /etc/sysctl.conf << EOF
# MR游戏运营系统优化
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 4096
net.ipv4.ip_local_port_range = 1024 65000
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
EOF

sysctl -p

log_success "系统优化完成"

# ==================== 完成 ====================
echo ""
log_success "=========================================="
log_success "🎉 服务器初始化完成!"
log_success "=========================================="
echo ""
log_info "下一步操作:"
echo "  1. 编辑 $PROJECT_DIR/backend/.env.production 配置文件"
echo "  2. 将GitHub Actions的公钥添加到 $SSH_DIR/authorized_keys"
echo "  3. 配置SSL证书(可选): 将证书放到 $PROJECT_DIR/nginx/ssl/"
echo "  4. 测试SSH连接: ssh $DEPLOY_USER@服务器IP"
echo "  5. 在GitHub仓库中配置Secrets(PROD_HOST, PROD_USER, PROD_SSH_KEY)"
echo "  6. 推送代码触发自动部署,或手动运行部署脚本"
echo ""
log_info "手动部署命令(在本地运行):"
echo "  bash .github/workflows/deploy.sh 服务器IP $DEPLOY_USER production main"
echo ""
log_warning "⚠️  重要提醒:"
echo "  - 务必修改 .env.production 中的所有密钥和密码"
echo "  - 配置SSL证书以启用HTTPS"
echo "  - 定期备份数据库"
echo "  - 监控服务器资源使用情况"
echo "=========================================="
