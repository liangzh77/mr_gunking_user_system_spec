#!/bin/bash

# =============================================================================
# MR游戏运营管理系统 - 生产环境服务器初始化脚本
# =============================================================================
# 适用于: Ubuntu 22.04 LTS
# 说明: 此脚本用于配置生产服务器的基础环境
# =============================================================================

set -e

echo "🚀 开始配置MR游戏运营管理系统生产环境..."

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用root用户运行此脚本"
    exit 1
fi

# 更新系统包
echo "📦 更新系统包..."
apt update && apt upgrade -y

# 安装基础工具
echo "🔧 安装基础工具..."
apt install -y curl wget git vim htop unzip software-properties-common \
    apt-transport-https ca-certificates gnupg lsb-release

# 安装Docker
echo "🐳 安装Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 安装Docker Compose
echo "🔧 安装Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 启动并启用Docker服务
echo "🚀 启动Docker服务..."
systemctl start docker
systemctl enable docker

# 创建应用目录
echo "📁 创建应用目录..."
mkdir -p /opt/mr-game-ops
mkdir -p /opt/mr-game-ops/data/{postgres,redis,uploads,invoices,logs}
mkdir -p /opt/mr-game-ops/config/{nginx,ssl}
mkdir -p /opt/mr-game-ops/backups

# 设置目录权限
echo "🔐 设置目录权限..."
chown -R root:root /opt/mr-game-ops
chmod -R 755 /opt/mr-game-ops

# 安装Nginx (作为反向代理)
echo "🌐 安装Nginx..."
apt install -y nginx

# 配置防火墙
echo "🛡️ 配置防火墙..."
ufw --force reset
ufw allow ssh
ufw allow 80
ufw allow 443
ufw --force enable

# 安装监控工具
echo "📊 安装监控工具..."
apt install -y prometheus grafana

# 配置系统参数优化
echo "⚙️ 优化系统参数..."
cat >> /etc/sysctl.conf << EOF
# 网络优化
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.tcp_congestion_control = bbr

# 文件描述符限制
fs.file-max = 100000

# 虚拟内存优化
vm.swappiness = 10
EOF

sysctl -p

# 创建备份脚本
echo "💾 创建备份脚本..."
cat > /opt/mr-game-ops/scripts/backup.sh << 'EOF'
#!/bin/bash
# 数据库备份脚本
BACKUP_DIR="/opt/mr-game-ops/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL备份
docker exec mr_game_ops_db pg_dump -U mr_admin mr_game_ops > $BACKUP_DIR/postgres_$DATE.sql

# Redis备份
docker exec mr_game_ops_redis redis-cli --rdb /data/dump_$DATE.rdb

# 清理7天前的备份
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +7 -delete

echo "备份完成: $DATE"
EOF

chmod +x /opt/mr-game-ops/scripts/backup.sh

# 设置定时备份
echo "⏰ 设置定时备份..."
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/mr-game-ops/scripts/backup.sh >> /var/log/backup.log 2>&1") | crontab -

echo "✅ 服务器基础环境配置完成!"
echo "📝 下一步: 请上传应用代码并执行后续部署脚本"
echo "🌐 应用目录: /opt/mr-game-ops"
echo "🔑 Docker已安装并启动"
echo "🛡️ 防火墙已配置(SSH:22, HTTP:80, HTTPS:443)"