# 生产环境部署实战指南

本指南提供两种生产部署方案，请根据实际情况选择。

---

## 🎯 方案选择

### 方案A：完整生产部署（推荐）
**适用场景**：
- ✅ 已有域名（如 example.com）
- ✅ 需要HTTPS加密访问
- ✅ 面向公网用户
- ✅ 需要完整的安全防护

**预计时间**：30-60分钟

### 方案B：简化生产部署
**适用场景**：
- ✅ 内网环境或VPN访问
- ✅ 暂时没有域名
- ✅ 快速验证功能
- ⚠️ 使用HTTP（不推荐长期使用）

**预计时间**：15-30分钟

---

## 📦 方案A：完整生产部署

### 前置要求

```bash
# 1. 服务器要求
- OS: Ubuntu 20.04/22.04 LTS
- CPU: 2核+
- RAM: 4GB+
- Disk: 40GB+
- 网络: 公网IP + 域名

# 2. 软件要求
- Docker 20.10+
- Docker Compose 1.29+
- Git
```

### 步骤1：服务器基础配置

登录到你的生产服务器，执行：

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要软件
sudo apt install -y git curl docker.io docker-compose ufw certbot

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户加入docker组（需要重新登录生效）
sudo usermod -aG docker $USER

# 配置防火墙
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw --force enable
```

**⚠️ 重要：执行完上述命令后，请退出SSH重新登录，使docker组权限生效**

### 步骤2：克隆项目代码

```bash
# 克隆项目（替换为你的实际仓库地址）
cd ~
git clone <你的仓库URL> mr_game_ops
cd mr_game_ops

# 如果有生产分支，切换到生产分支
# git checkout production
```

### 步骤3：生成密钥和密码

```bash
# 生成强密钥（保存这些输出结果）
echo "=== SECRET_KEY ==="
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

echo "=== JWT_SECRET_KEY ==="
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

echo "=== ENCRYPTION_KEY (32字符) ==="
python3 -c "import secrets; print(secrets.token_urlsafe(24)[:32])"

echo "=== POSTGRES_PASSWORD ==="
python3 -c "import secrets; print(secrets.token_urlsafe(16))"

echo "=== REDIS_PASSWORD ==="
python3 -c "import secrets; print(secrets.token_urlsafe(16))"
```

**⚠️ 重要：请将上述输出的所有密钥保存到安全的地方（如密码管理器）**

### 步骤4：配置环境变量

```bash
# 进入backend目录
cd backend

# 复制生产环境配置模板
cp .env.production .env

# 编辑配置文件
nano .env  # 或使用 vim .env
```

**必须修改的配置项**（用步骤3生成的值替换）：

```bash
# === 数据库配置 ===
DATABASE_URL=postgresql+asyncpg://mr_admin:你的POSTGRES_PASSWORD@postgres:5432/mr_game_ops

# === Redis配置 ===
REDIS_URL=redis://:你的REDIS_PASSWORD@redis:6379/0
REDIS_PASSWORD=你的REDIS_PASSWORD

# === 安全密钥 ===
SECRET_KEY=你的SECRET_KEY
JWT_SECRET_KEY=你的JWT_SECRET_KEY
ENCRYPTION_KEY=你的ENCRYPTION_KEY（必须32字符）

# === CORS配置 ===
CORS_ORIGINS=["https://你的域名.com"]

# === 环境标识 ===
DEBUG=false
ENVIRONMENT=production
```

**保存并退出**（nano: Ctrl+X, 然后Y, 然后Enter）

### 步骤5：配置SSL证书

#### 方式1：使用Let's Encrypt（推荐，免费）

```bash
# 返回项目根目录
cd ..

# 申请SSL证书（替换为你的实际域名）
sudo certbot certonly --standalone -d 你的域名.com

# 证书申请成功后，复制证书到nginx目录
sudo cp /etc/letsencrypt/live/你的域名.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/你的域名.com/privkey.pem nginx/ssl/

# 修改证书文件权限
sudo chmod 644 nginx/ssl/fullchain.pem
sudo chmod 600 nginx/ssl/privkey.pem
```

#### 方式2：使用自签名证书（仅测试）

```bash
cd nginx/ssl

# 生成自签名证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout privkey.pem \
    -out fullchain.pem \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=YourCompany/CN=你的域名.com"

cd ../..
```

### 步骤6：修改Nginx配置

```bash
# 编辑Nginx站点配置
nano nginx/conf.d/mr_game_ops.conf

# 修改以下配置：
# 1. 找到 server_name 行，替换为你的实际域名：
#    server_name 你的域名.com;
#
# 2. 确认SSL证书路径正确：
#    ssl_certificate /etc/nginx/ssl/fullchain.pem;
#    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
```

### 步骤7：设置Docker环境变量

```bash
# 返回项目根目录
cd ~/mr_game_ops

# 设置数据库和Redis密码环境变量（使用步骤3生成的密码）
export POSTGRES_PASSWORD=你的POSTGRES_PASSWORD
export REDIS_PASSWORD=你的REDIS_PASSWORD

# 建议：将这些环境变量添加到 ~/.bashrc 以持久化
echo "export POSTGRES_PASSWORD=你的POSTGRES_PASSWORD" >> ~/.bashrc
echo "export REDIS_PASSWORD=你的REDIS_PASSWORD" >> ~/.bashrc
```

### 步骤8：启动服务

```bash
# 拉取并构建镜像（首次部署需要几分钟）
docker-compose -f docker-compose.yml build

# 启动所有服务
docker-compose -f docker-compose.yml up -d

# 查看服务状态
docker-compose -f docker-compose.yml ps
```

预期输出：所有服务状态应该是 `Up` 或 `Up (healthy)`

### 步骤9：初始化数据库

```bash
# 等待30秒让服务完全启动
sleep 30

# 运行数据库迁移
docker exec mr_game_ops_backend_prod alembic upgrade head

# 初始化系统数据（创建默认管理员等）
docker exec mr_game_ops_backend_prod python init_data.py
```

### 步骤10：验证部署

```bash
# 1. 检查后端健康状态
curl http://localhost:8000/health

# 预期输出: {"status":"healthy"}

# 2. 测试管理员登录
curl -X POST http://localhost:8000/api/v1/auth/admins/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin123"}'

# 预期输出: 包含 "access_token" 的JSON

# 3. 通过浏览器访问
# https://你的域名.com
```

### 步骤11：配置SSL证书自动更新

```bash
# 添加自动更新任务到crontab
sudo crontab -e

# 添加以下行（每天凌晨2点检查证书更新）
0 2 * * * /usr/bin/certbot renew --quiet && cd ~/mr_game_ops && docker-compose -f docker-compose.yml restart nginx
```

### ✅ 部署完成！

**访问地址：**
- 前端应用：https://你的域名.com
- API文档：https://你的域名.com/api/docs
- 后端健康检查：https://你的域名.com/api/health

**默认管理员账户：**
- 用户名：`admin`
- 密码：`Admin123`

**⚠️ 安全提醒：首次登录后立即修改管理员密码！**

---

## 📦 方案B：简化生产部署（无SSL）

### 适用场景
- 内网环境
- 通过VPN访问
- 快速功能验证
- 暂时没有域名

### 步骤1-3：同方案A

参考方案A的步骤1-3（服务器配置、克隆代码、生成密钥）

### 步骤4：配置环境变量

```bash
cd ~/mr_game_ops/backend
cp .env.production .env
nano .env

# 修改以下配置（使用步骤3生成的值）：
DATABASE_URL=postgresql+asyncpg://mr_admin:你的POSTGRES_PASSWORD@postgres:5432/mr_game_ops
REDIS_URL=redis://:你的REDIS_PASSWORD@redis:6379/0
REDIS_PASSWORD=你的REDIS_PASSWORD
SECRET_KEY=你的SECRET_KEY
JWT_SECRET_KEY=你的JWT_SECRET_KEY
ENCRYPTION_KEY=你的ENCRYPTION_KEY

# CORS配置改为允许所有（仅测试环境）
CORS_ORIGINS=["*"]

DEBUG=false
ENVIRONMENT=production
```

### 步骤5：创建简化版Docker配置

```bash
cd ~/mr_game_ops

# 创建不包含Nginx的简化配置
cat > docker-compose.simple-prod.yml <<'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    container_name: mr_game_ops_db_simple
    environment:
      POSTGRES_USER: mr_admin
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: mr_game_ops
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mr_admin"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: mr_game_ops_redis_simple
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --appendonly yes
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: mr_game_ops_backend_simple
    command: gunicorn src.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    env_file:
      - ./backend/.env
    ports:
      - "8000:8000"
    volumes:
      - ./backend/logs:/app/logs
      - ./backend/uploads:/app/uploads
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: mr_game_ops_frontend_simple
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
EOF
```

### 步骤6：启动服务

```bash
# 设置环境变量
export POSTGRES_PASSWORD=你的POSTGRES_PASSWORD
export REDIS_PASSWORD=你的REDIS_PASSWORD

# 启动服务
docker-compose -f docker-compose.simple-prod.yml up -d

# 查看状态
docker-compose -f docker-compose.simple-prod.yml ps
```

### 步骤7：初始化数据库

```bash
# 等待30秒
sleep 30

# 运行迁移
docker exec mr_game_ops_backend_simple alembic upgrade head

# 初始化数据
docker exec mr_game_ops_backend_simple python init_data.py
```

### 步骤8：验证部署

```bash
# 检查健康状态
curl http://localhost:8000/health

# 测试登录
curl -X POST http://localhost:8000/api/v1/auth/admins/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin123"}'

# 浏览器访问（替换为你的服务器IP）
# http://你的服务器IP
# http://你的服务器IP:8000/api/docs
```

### ✅ 简化部署完成！

**访问地址：**
- 前端：http://服务器IP
- API文档：http://服务器IP:8000/api/docs
- 健康检查：http://服务器IP:8000/health

**默认账户：** admin / Admin123

---

## 🔍 常用管理命令

### 查看日志
```bash
# 方案A
docker-compose -f docker-compose.yml logs -f backend

# 方案B
docker-compose -f docker-compose.simple-prod.yml logs -f backend
```

### 重启服务
```bash
# 方案A
docker-compose -f docker-compose.yml restart backend

# 方案B
docker-compose -f docker-compose.simple-prod.yml restart backend
```

### 停止所有服务
```bash
# 方案A
docker-compose -f docker-compose.yml down

# 方案B
docker-compose -f docker-compose.simple-prod.yml down
```

### 数据库备份
```bash
# 方案A
docker exec mr_game_ops_db_prod pg_dump -U mr_admin mr_game_ops | gzip > backup_$(date +%Y%m%d).sql.gz

# 方案B
docker exec mr_game_ops_db_simple pg_dump -U mr_admin mr_game_ops | gzip > backup_$(date +%Y%m%d).sql.gz
```

### 查看资源使用
```bash
docker stats
```

---

## 🚨 常见问题排查

### 问题1：服务启动失败

```bash
# 检查日志
docker-compose -f docker-compose.yml logs backend

# 常见原因：
# - 环境变量未设置（POSTGRES_PASSWORD, REDIS_PASSWORD）
# - 端口被占用（8000, 5432, 6379）
# - 内存不足
```

### 问题2：无法访问前端

```bash
# 检查Nginx状态
docker-compose -f docker-compose.yml logs nginx

# 检查防火墙
sudo ufw status

# 确保80和443端口开放
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### 问题3：数据库连接失败

```bash
# 检查PostgreSQL状态
docker exec mr_game_ops_db_prod pg_isready -U mr_admin

# 检查密码是否匹配
# backend/.env 中的 DATABASE_URL 密码
# 必须与 POSTGRES_PASSWORD 环境变量一致
```

### 问题4：SSL证书错误

```bash
# 检查证书文件
ls -la nginx/ssl/

# 应该有：
# fullchain.pem
# privkey.pem

# 验证证书
openssl x509 -in nginx/ssl/fullchain.pem -noout -dates
```

---

## 📞 获取帮助

- **完整部署文档**：`docs/DEPLOYMENT.md`
- **快速参考**：`docs/PRODUCTION_QUICKSTART.md`
- **验证报告**：`docs/DEPLOYMENT_VALIDATION_REPORT.md`

---

**最后更新**：2025-10-16
