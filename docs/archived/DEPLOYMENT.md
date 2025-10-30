# 生产环境部署指南

本文档提供MR游戏运营管理系统生产环境部署的详细说明。

## 目录

- [前置要求](#前置要求)
- [服务器准备](#服务器准备)
- [Docker部署](#docker部署)
- [传统部署](#传统部署)
- [SSL证书配置](#ssl证书配置)
- [数据库初始化](#数据库初始化)
- [监控和日志](#监控和日志)
- [备份策略](#备份策略)
- [安全检查清单](#安全检查清单)
- [常见问题](#常见问题)

---

## 前置要求

### 硬件要求

**最小配置**（小规模部署，< 100并发用户）：
- CPU: 2核
- 内存: 4GB
- 存储: 50GB SSD
- 带宽: 10Mbps

**推荐配置**（中等规模，100-500并发用户）：
- CPU: 4核
- 内存: 8GB
- 存储: 100GB SSD
- 带宽: 50Mbps

**高性能配置**（大规模，> 500并发用户）：
- CPU: 8核+
- 内存: 16GB+
- 存储: 200GB+ SSD
- 带宽: 100Mbps+

### 软件要求

- 操作系统: Ubuntu 20.04/22.04 LTS 或 CentOS 8+ (推荐Ubuntu)
- Docker: 20.10+ 和 Docker Compose 2.0+
- 或传统部署: Python 3.11+, PostgreSQL 14+, Redis 7+, Nginx 1.18+

### 网络要求

- 固定公网IP或域名
- 开放端口: 80 (HTTP), 443 (HTTPS)
- 可选: 22 (SSH)
- 内网端口（不对外开放）: 5432 (PostgreSQL), 6379 (Redis), 8000 (后端API)

---

## 服务器准备

### 1. 初始化服务器

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y git curl wget vim ufw fail2ban

# 配置防火墙
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# 配置时区
sudo timedatectl set-timezone Asia/Shanghai

# 创建应用用户
sudo useradd -m -s /bin/bash mruser
sudo usermod -aG sudo mruser
```

### 2. 安装Docker和Docker Compose

```bash
# 安装Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version

# 重新登录以应用docker组权限
exit
# 重新SSH登录
```

### 3. 克隆项目

```bash
# 切换到应用用户
su - mruser

# 克隆项目
git clone https://github.com/yourusername/mr_gunking_user_system_spec.git
cd mr_gunking_user_system_spec

# 检出生产分支（如果有）
git checkout production
```

---

## Docker部署

### 1. 配置环境变量

```bash
# 复制生产环境配置模板
cd backend
cp .env.production .env

# 编辑配置文件
vim .env
```

**⚠️ 必须修改的配置项**：

```bash
# 生成强随机密钥
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(24)[:32])"

# 修改数据库密码
DATABASE_URL=postgresql+asyncpg://mr_admin:YOUR_STRONG_DB_PASSWORD@postgres:5432/mr_game_ops

# 修改Redis密码
REDIS_URL=redis://:YOUR_STRONG_REDIS_PASSWORD@redis:6379/0
REDIS_PASSWORD=YOUR_STRONG_REDIS_PASSWORD

# 修改CORS允许的域名
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# 确保DEBUG关闭
DEBUG=false
ENVIRONMENT=production
```

### 2. 配置Nginx

```bash
cd ../nginx/conf.d

# 编辑站点配置
vim mr_game_ops.conf
```

修改以下内容：
- `server_name`: 改为你的实际域名
- SSL证书路径: 指向正确的证书位置

### 3. 构建和启动服务

```bash
# 返回项目根目录
cd ../..

# 设置环境变量（用于docker-compose.yml）
export POSTGRES_PASSWORD=YOUR_STRONG_DB_PASSWORD
export REDIS_PASSWORD=YOUR_STRONG_REDIS_PASSWORD
export VERSION=1.0.0

# 构建镜像
docker-compose -f docker-compose.yml build

# 启动服务
docker-compose -f docker-compose.yml up -d

# 查看服务状态
docker-compose -f docker-compose.yml ps

# 查看日志
docker-compose -f docker-compose.yml logs -f
```

### 4. 初始化数据库

```bash
# 进入后端容器
docker exec -it mr_game_ops_backend_prod bash

# 运行数据库迁移
alembic upgrade head

# 运行初始化脚本
python init_data.py

# 退出容器
exit
```

### 5. 验证部署

```bash
# 检查健康状态
curl http://localhost:8000/health

# 预期输出: {"status": "healthy"}

# 检查API文档（仅在测试时）
curl http://localhost:8000/api/docs
```

---

## 传统部署

### 1. 安装依赖

#### PostgreSQL 14

```bash
# 添加PostgreSQL仓库
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update

# 安装PostgreSQL
sudo apt install -y postgresql-14 postgresql-contrib-14

# 启动并启用服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql <<EOF
CREATE USER mr_admin WITH PASSWORD 'YOUR_STRONG_DB_PASSWORD';
CREATE DATABASE mr_game_ops OWNER mr_admin;
GRANT ALL PRIVILEGES ON DATABASE mr_game_ops TO mr_admin;
\q
EOF
```

#### Redis 7

```bash
# 安装Redis
sudo apt install -y redis-server

# 配置Redis
sudo vim /etc/redis/redis.conf
```

修改以下内容：
```
# 设置密码
requirepass YOUR_STRONG_REDIS_PASSWORD

# 启用持久化
appendonly yes
appendfsync everysec

# 内存限制
maxmemory 512mb
maxmemory-policy allkeys-lru
```

```bash
# 重启Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

#### Python 3.11+ 和后端

```bash
# 安装Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 创建虚拟环境
cd ~/mr_gunking_user_system_spec/backend
python3.11 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 配置环境变量
cp .env.production .env
vim .env
# 修改DATABASE_URL、REDIS_URL等配置

# 运行数据库迁移
alembic upgrade head

# 初始化数据
python init_data.py
```

#### Nginx

```bash
# 安装Nginx
sudo apt install -y nginx

# 复制配置文件
sudo cp ../nginx/conf.d/mr_game_ops.conf /etc/nginx/sites-available/mr_game_ops
sudo ln -s /etc/nginx/sites-available/mr_game_ops /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 2. 配置Systemd服务

创建后端服务：

```bash
sudo vim /etc/systemd/system/mr-game-ops-backend.service
```

内容：
```ini
[Unit]
Description=MR Game Ops Backend API
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=mruser
WorkingDirectory=/home/mruser/mr_gunking_user_system_spec/backend
Environment="PATH=/home/mruser/mr_gunking_user_system_spec/backend/.venv/bin"
ExecStart=/home/mruser/mr_gunking_user_system_spec/backend/.venv/bin/gunicorn \
    src.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --keepalive 5 \
    --access-logfile /var/log/mr_game_ops/access.log \
    --error-logfile /var/log/mr_game_ops/error.log

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 创建日志目录
sudo mkdir -p /var/log/mr_game_ops
sudo chown mruser:mruser /var/log/mr_game_ops

# 启动服务
sudo systemctl daemon-reload
sudo systemctl start mr-game-ops-backend
sudo systemctl enable mr-game-ops-backend

# 查看状态
sudo systemctl status mr-game-ops-backend
```

#### 前端构建和部署

```bash
# 安装Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# 构建前端
cd ~/mr_gunking_user_system_spec/frontend
npm ci
npm run build

# 复制到Nginx目录
sudo mkdir -p /var/www/mr_game_ops
sudo cp -r dist/* /var/www/mr_game_ops/
sudo chown -R www-data:www-data /var/www/mr_game_ops
```

---

## SSL证书配置

### 使用Let's Encrypt（免费）

```bash
# 安装Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 自动续期
sudo certbot renew --dry-run

# 添加续期cron任务
sudo crontab -e
# 添加以下行：
# 0 2 * * * /usr/bin/certbot renew --quiet
```

### 使用自签名证书（仅测试）

```bash
cd nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout privkey.pem \
    -out fullchain.pem \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=YourCompany/CN=yourdomain.com"
```

---

## 监控和日志

### 应用日志

```bash
# Docker部署
docker-compose -f docker-compose.yml logs -f backend
docker-compose -f docker-compose.yml logs -f frontend

# 传统部署
tail -f /var/log/mr_game_ops/app.log
tail -f /var/log/mr_game_ops/access.log
tail -f /var/log/mr_game_ops/error.log
tail -f /var/log/nginx/mr_game_ops_access.log
tail -f /var/log/nginx/mr_game_ops_error.log
```

### 配置日志轮转

```bash
sudo vim /etc/logrotate.d/mr-game-ops
```

内容：
```
/var/log/mr_game_ops/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 mruser mruser
    sharedscripts
    postrotate
        systemctl reload mr-game-ops-backend > /dev/null 2>&1 || true
    endscript
}
```

### 健康检查

```bash
# 创建健康检查脚本
vim ~/check_health.sh
```

内容：
```bash
#!/bin/bash
HEALTH_URL="http://localhost:8000/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "$(date): Service is healthy"
else
    echo "$(date): Service is unhealthy (HTTP $RESPONSE)"
    # 可选：发送告警邮件或重启服务
    # sudo systemctl restart mr-game-ops-backend
fi
```

```bash
chmod +x ~/check_health.sh

# 添加到cron（每5分钟检查一次）
crontab -e
# 添加：
# */5 * * * * ~/check_health.sh >> ~/health_check.log 2>&1
```

---

## 备份策略

### 自动数据库备份

Docker部署已包含自动备份（使用postgres-backup容器）。

传统部署需手动配置：

```bash
# 创建备份脚本
sudo mkdir -p /var/backups/mr_game_ops
sudo vim /usr/local/bin/backup_mr_db.sh
```

内容：
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/mr_game_ops"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/mr_game_ops_$DATE.sql.gz"

# 执行备份
PGPASSWORD=YOUR_STRONG_DB_PASSWORD pg_dump -h localhost -U mr_admin mr_game_ops | gzip > $BACKUP_FILE

# 保留最近30天的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

```bash
sudo chmod +x /usr/local/bin/backup_mr_db.sh

# 添加到cron（每天凌晨2点备份）
sudo crontab -e
# 添加：
# 0 2 * * * /usr/local/bin/backup_mr_db.sh >> /var/log/mr_game_ops/backup.log 2>&1
```

### 恢复数据库

```bash
# 解压并恢复
gunzip -c /var/backups/mr_game_ops/mr_game_ops_YYYYMMDD_HHMMSS.sql.gz | \
    PGPASSWORD=YOUR_STRONG_DB_PASSWORD psql -h localhost -U mr_admin mr_game_ops
```

---

## 安全检查清单

### 部署前检查

- [ ] 所有密码和密钥已修改为强随机值
- [ ] `.env.production` 文件权限设置为 600
- [ ] DEBUG模式已关闭
- [ ] CORS配置仅包含生产域名
- [ ] 数据库用户权限最小化
- [ ] Redis密码已设置
- [ ] 防火墙规则已配置（仅开放80/443/22）
- [ ] SSH禁用root登录
- [ ] 安装fail2ban防暴力破解
- [ ] SSL证书已配置且有效
- [ ] 日志轮转已配置
- [ ] 自动备份已配置

### 运行时检查

```bash
# 检查开放端口
sudo netstat -tulpn | grep LISTEN

# 检查服务状态
sudo systemctl status postgresql
sudo systemctl status redis-server
sudo systemctl status mr-game-ops-backend
sudo systemctl status nginx

# 检查磁盘空间
df -h

# 检查内存使用
free -h

# 检查Docker容器状态（Docker部署）
docker-compose -f docker-compose.yml ps

# 测试HTTPS
curl -I https://yourdomain.com

# 测试API
curl -X POST https://yourdomain.com/api/v1/auth/operators/login \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "Admin123"}'
```

---

## 常见问题

### 1. 数据库连接失败

**问题**: `FATAL: password authentication failed for user "mr_admin"`

**解决**:
- 检查 `.env` 文件中的 `DATABASE_URL` 密码是否正确
- 检查 PostgreSQL 配置 `/etc/postgresql/14/main/pg_hba.conf`
- 确保PostgreSQL服务运行中: `sudo systemctl status postgresql`

### 2. Redis连接失败

**问题**: `Error connecting to Redis`

**解决**:
- 检查 Redis 密码: `.env` 中的 `REDIS_PASSWORD`
- 检查 Redis 服务: `sudo systemctl status redis-server`
- 测试连接: `redis-cli -a YOUR_REDIS_PASSWORD ping`

### 3. Nginx 502 Bad Gateway

**问题**: Nginx返回502错误

**解决**:
- 检查后端服务是否运行: `sudo systemctl status mr-game-ops-backend`
- 检查端口是否监听: `netstat -tulpn | grep 8000`
- 查看后端日志: `tail -f /var/log/mr_game_ops/error.log`
- 检查防火墙: `sudo ufw status`

### 4. SSL证书错误

**问题**: 浏览器显示SSL证书无效

**解决**:
- 检查证书文件路径是否正确
- 重新获取Let's Encrypt证书: `sudo certbot renew --force-renewal`
- 检查域名DNS解析是否指向服务器IP
- 检查Nginx配置: `sudo nginx -t`

### 5. 内存不足

**问题**: 应用频繁重启或响应缓慢

**解决**:
- 检查内存使用: `free -h`
- 减少Docker/Gunicorn worker数量
- 增加swap空间:
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
- 升级服务器内存

### 6. 数据库性能问题

**问题**: 查询响应缓慢

**解决**:
- 检查数据库连接池配置
- 分析慢查询日志
- 添加必要的数据库索引
- 增加PostgreSQL缓存:
```bash
sudo vim /etc/postgresql/14/main/postgresql.conf
# 修改：
# shared_buffers = 256MB
# effective_cache_size = 1GB
```

---

## 性能优化建议

### 数据库优化

```sql
-- 创建常用索引
CREATE INDEX idx_operator_username ON operator_accounts(username);
CREATE INDEX idx_transaction_operator ON transactions(operator_id);
CREATE INDEX idx_usage_record_operator ON usage_records(operator_id);
CREATE INDEX idx_usage_record_time ON usage_records(usage_time);
```

### Redis缓存策略

- 缓存热点数据：应用列表、运营商配置
- 会话存储：JWT token黑名单
- 限流数据：API请求计数

### CDN配置

建议使用CDN加速静态资源：
- 前端静态文件（JS、CSS、图片）
- 发票PDF文件
- 上传的附件

---

## 更新和回滚

### 零停机更新

```bash
# 1. 拉取最新代码
git pull origin production

# 2. 构建新镜像
docker-compose -f docker-compose.yml build

# 3. 滚动更新
docker-compose -f docker-compose.yml up -d --no-deps --build backend

# 4. 运行数据库迁移
docker exec -it mr_game_ops_backend_prod alembic upgrade head

# 5. 验证
curl http://localhost:8000/health
```

### 回滚

```bash
# 1. 查看可用版本
docker images | grep mr_game_ops_backend

# 2. 回滚到指定版本
docker tag mr_game_ops_backend:1.0.0 mr_game_ops_backend:latest
docker-compose -f docker-compose.yml up -d --no-deps backend

# 3. 回滚数据库（如需要）
docker exec -it mr_game_ops_backend_prod alembic downgrade -1
```

---

## 联系和支持

- 项目文档: [GitHub](https://github.com/yourusername/mr_gunking_user_system_spec)
- Issue追踪: [GitHub Issues](https://github.com/yourusername/mr_gunking_user_system_spec/issues)
- 技术支持邮箱: support@yourdomain.com

---

**最后更新**: 2025-10-16
**文档版本**: 1.0.0
