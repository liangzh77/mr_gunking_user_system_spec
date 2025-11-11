# 🚀 生产环境部署指南（使用现有阿里云证书）

## 📋 前提条件

✅ 您已拥有阿里云 SSL 证书：
- 证书文件：`deploy/21088616_mrgun.chu-jiao.com_nginx/mrgun.chu-jiao.com.pem`
- 私钥文件：`deploy/21088616_mrgun.chu-jiao.com_nginx/mrgun.chu-jiao.com.key`
- 有效期：2025-10-22 至 2026-01-19
- 支持域名：`mrgun.chu-jiao.com`, `www.mrgun.chu-jiao.com`
- **TLS 1.2/1.3**：已启用 ✅

---

## 🔧 快速部署步骤

### 1️⃣ 创建生产环境配置文件

在项目根目录创建 `.env.production` 文件：

```bash
# 复制示例文件
cp .env.example .env.production
```

编辑 `.env.production`，填写生产环境配置：

```bash
# =============================================================================
# 生产环境配置
# =============================================================================

# 应用配置
ENVIRONMENT=production
DEBUG=false
APP_NAME=MR游戏运营管理系统
APP_VERSION=1.0.0

# 数据库配置（⚠️ 修改为强密码）
POSTGRES_USER=mr_admin
POSTGRES_PASSWORD=your-super-strong-password-here-change-this
POSTGRES_DB=mr_game_ops
DATABASE_URL=postgresql+asyncpg://mr_admin:your-super-strong-password-here-change-this@postgres:5432/mr_game_ops

# Redis 配置（⚠️ 修改为强密码）
REDIS_PASSWORD=your-redis-strong-password-here
REDIS_URL=redis://:your-redis-strong-password-here@redis:6379/0

# JWT 认证配置（⚠️ 生成新的密钥）
# 生成方法: openssl rand -hex 32
JWT_SECRET_KEY=your-jwt-secret-key-generate-with-openssl-rand
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 加密密钥（⚠️ 生成新的密钥）
# 生成方法: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-encryption-key-here
SECRET_KEY=your-secret-key-here

# CORS 跨域配置
BACKEND_CORS_ORIGINS=https://mrgun.chu-jiao.com

# 日志配置
LOG_LEVEL=INFO

# 短信服务配置（阿里云）
SMS_PROVIDER=aliyun
# ⚠️ 请替换为您自己的阿里云 AccessKey
ALIYUN_ACCESS_KEY_ID=your-aliyun-access-key-id
ALIYUN_ACCESS_KEY_SECRET=your-aliyun-access-key-secret
ALIYUN_SMS_SIGN_NAME=您的短信签名
ALIYUN_SMS_TEMPLATE_CODE=SMS_123456789

# PgAdmin（可选）
PGADMIN_EMAIL=admin@mrgameops.com
PGADMIN_PASSWORD=your-pgadmin-password
```

### 2️⃣ 生成安全密钥

```bash
# 生成 JWT Secret Key
openssl rand -hex 32

# 生成 Encryption Key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 生成 Secret Key
openssl rand -hex 32
```

将生成的密钥填写到 `.env.production` 文件中。

### 3️⃣ 构建 Docker 镜像

```bash
# 构建后端镜像
docker-compose -f docker-compose.production.yml build backend

# 构建前端镜像
docker-compose -f docker-compose.production.yml build frontend
```

### 4️⃣ 启动生产环境

```bash
# 启动所有服务（使用生产配置）
docker-compose -f docker-compose.production.yml --env-file .env.production up -d

# 查看服务状态
docker-compose -f docker-compose.production.yml ps

# 查看日志
docker-compose -f docker-compose.production.yml logs -f
```

### 5️⃣ 验证部署

#### 检查服务健康状态

```bash
# 检查健康检查端点
curl -k https://mrgun.chu-jiao.com/health

# 预期输出（JSON格式）：
# {"status":"healthy","database":true,"version":"1.0.0","timestamp":"2025-..."}
```

#### 检查 TLS 配置

```bash
# 测试 TLS 1.2 连接
openssl s_client -connect mrgun.chu-jiao.com:443 -tls1_2

# 测试 TLS 1.3 连接
openssl s_client -connect mrgun.chu-jiao.com:443 -tls1_3

# 验证证书信息
openssl s_client -connect mrgun.chu-jiao.com:443 -showcerts </dev/null 2>/dev/null | openssl x509 -noout -dates
```

#### 浏览器测试

1. 访问 https://mrgun.chu-jiao.com
2. 检查地址栏是否显示安全锁图标
3. 点击锁图标查看证书详情
4. 确认 TLS 版本为 1.2 或 1.3

#### 在线安全测试

访问 **SSL Labs** 进行全面安全测试：
- URL: https://www.ssllabs.com/ssltest/
- 输入域名：`mrgun.chu-jiao.com`
- 期望评分：**A 或 A+**

---

## 🔐 证书管理

### 当前证书信息

```
颁发机构：阿里云
域名：mrgun.chu-jiao.com, www.mrgun.chu-jiao.com
有效期：2025-10-22 至 2026-01-19（约 3 个月）
TLS 支持：TLS 1.2, TLS 1.3 ✅
```

### 证书续期提醒

⚠️ **重要**：证书将在 **2026-01-19** 到期，请提前续期！

**续期步骤**：
1. 在阿里云 SSL 证书控制台申请续期
2. 下载新证书文件
3. 替换旧证书文件：
   ```bash
   # 备份旧证书
   cp deploy/21088616_mrgun.chu-jiao.com_nginx/mrgun.chu-jiao.com.pem \
      deploy/21088616_mrgun.chu-jiao.com_nginx/mrgun.chu-jiao.com.pem.bak

   # 上传新证书（覆盖旧文件）
   # ... 上传 mrgun.chu-jiao.com.pem 和 mrgun.chu-jiao.com.key

   # 重新加载 Nginx
   docker-compose -f docker-compose.production.yml exec nginx nginx -s reload
   ```

### 切换到 Let's Encrypt（可选，免费自动续期）

如果希望使用免费且自动续期的证书：

```bash
# 1. 安装 Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# 2. 申请证书
sudo certbot certonly --standalone -d mrgun.chu-jiao.com -d www.mrgun.chu-jiao.com

# 3. 修改 docker-compose.production.yml 中的证书路径
# 将证书路径改为：
#   - /etc/letsencrypt/live/mrgun.chu-jiao.com/fullchain.pem:/etc/nginx/ssl/mrgun.chu-jiao.com.pem:ro
#   - /etc/letsencrypt/live/mrgun.chu-jiao.com/privkey.pem:/etc/nginx/ssl/mrgun.chu-jiao.com.key:ro

# 4. 设置自动续期
sudo certbot renew --dry-run
```

---

## 📊 服务管理

### 常用命令

```bash
# 启动服务
docker-compose -f docker-compose.production.yml --env-file .env.production up -d

# 停止服务
docker-compose -f docker-compose.production.yml down

# 重启服务
docker-compose -f docker-compose.production.yml restart

# 查看日志
docker-compose -f docker-compose.production.yml logs -f

# 只查看后端日志
docker-compose -f docker-compose.production.yml logs -f backend

# 只查看 Nginx 日志
docker-compose -f docker-compose.production.yml logs -f nginx

# 进入容器
docker-compose -f docker-compose.production.yml exec backend sh
docker-compose -f docker-compose.production.yml exec nginx sh

# 更新服务（零停机）
docker-compose -f docker-compose.production.yml up -d --no-deps --build backend
```

### 数据备份

```bash
# 备份 PostgreSQL 数据库
docker-compose -f docker-compose.production.yml exec postgres \
  pg_dump -U mr_admin mr_game_ops > backup_$(date +%Y%m%d).sql

# 备份 Redis 数据
docker-compose -f docker-compose.production.yml exec redis \
  redis-cli --rdb /data/dump.rdb

# 备份用户上传文件
docker run --rm -v mr_gunking_user_system_spec_backend_uploads_prod:/data \
  -v $(pwd):/backup alpine tar czf /backup/uploads_$(date +%Y%m%d).tar.gz /data
```

### 恢复数据

```bash
# 恢复 PostgreSQL 数据库
docker-compose -f docker-compose.production.yml exec -T postgres \
  psql -U mr_admin mr_game_ops < backup_20251111.sql

# 恢复用户上传文件
docker run --rm -v mr_gunking_user_system_spec_backend_uploads_prod:/data \
  -v $(pwd):/backup alpine tar xzf /backup/uploads_20251111.tar.gz -C /
```

---

## 🛡️ 安全检查清单

部署后请完成以下安全检查：

- [ ] **证书有效**：浏览器无证书警告
- [ ] **TLS 1.2/1.3 启用**：`openssl s_client -tls1_2` 连接成功
- [ ] **TLS 1.0/1.1 禁用**：`openssl s_client -tls1_1` 连接失败
- [ ] **HTTP 重定向 HTTPS**：访问 http:// 自动跳转
- [ ] **HSTS 生效**：响应头包含 `Strict-Transport-Security`
- [ ] **强密码**：数据库、Redis、PgAdmin 使用强密码
- [ ] **API 文档禁用**：访问 `/docs` 返回 404
- [ ] **监控端点限制**：`/metrics` 仅内网可访问
- [ ] **防火墙配置**：只开放 80、443 端口
- [ ] **日志审计**：定期检查访问日志和错误日志
- [ ] **数据备份**：配置自动备份计划
- [ ] **SSL Labs 测试**：评分 A 或 A+

---

## 🔍 故障排查

### 问题 1：访问网站显示证书错误

**检查步骤**：
```bash
# 1. 验证证书文件存在且可读
ls -la deploy/21088616_mrgun.chu-jiao.com_nginx/

# 2. 检查证书有效期
openssl x509 -in deploy/21088616_mrgun.chu-jiao.com_nginx/mrgun.chu-jiao.com.pem -noout -dates

# 3. 检查 Nginx 配置
docker-compose -f docker-compose.production.yml exec nginx nginx -t

# 4. 查看 Nginx 错误日志
docker-compose -f docker-compose.production.yml logs nginx | grep -i error
```

### 问题 2：无法连接到后端 API

**检查步骤**：
```bash
# 1. 检查后端服务状态
docker-compose -f docker-compose.production.yml ps backend

# 2. 检查后端健康状态
curl http://localhost:8000/health

# 3. 检查后端日志
docker-compose -f docker-compose.production.yml logs backend | tail -50

# 4. 检查网络连接
docker-compose -f docker-compose.production.yml exec nginx ping backend
```

### 问题 3：短信验证码发送失败

**检查步骤**：
```bash
# 1. 检查环境变量
docker-compose -f docker-compose.production.yml exec backend env | grep SMS

# 2. 检查后端日志中的短信相关错误
docker-compose -f docker-compose.production.yml logs backend | grep -i sms

# 3. 验证阿里云 AccessKey 是否正确
# 在阿里云 RAM 控制台检查 AccessKey 状态
```

### 问题 4：数据库连接失败

**检查步骤**：
```bash
# 1. 检查 PostgreSQL 服务状态
docker-compose -f docker-compose.production.yml ps postgres

# 2. 测试数据库连接
docker-compose -f docker-compose.production.yml exec postgres \
  psql -U mr_admin -d mr_game_ops -c "SELECT version();"

# 3. 检查数据库日志
docker-compose -f docker-compose.production.yml logs postgres | tail -50
```

---

## 📈 性能优化

### 1. Nginx 性能优化

已在 `nginx-production.conf` 中配置：
- ✅ HTTP/2 支持
- ✅ Gzip 压缩
- ✅ 静态资源缓存
- ✅ SSL 会话复用
- ✅ OCSP Stapling

### 2. 后端性能优化

生产环境使用 4 个 worker 进程：
```yaml
command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

如需调整 worker 数量（建议：CPU 核心数 × 2 + 1）：
```bash
# 修改 docker-compose.production.yml
command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 8
```

### 3. Redis 内存优化

已配置内存限制和淘汰策略：
```yaml
command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### 4. 数据库连接池

后端使用 SQLAlchemy 连接池（默认配置）：
- 池大小：5
- 最大溢出：10
- 连接超时：30 秒

---

## ✅ 部署完成

恭喜！您的生产环境已成功部署，具备以下特性：

- ✅ **TLS 1.2/1.3 加密**：符合 PCI DSS 3.2+ 标准
- ✅ **阿里云 SSL 证书**：有效期至 2026-01-19
- ✅ **HTTPS 强制跳转**：所有 HTTP 请求自动重定向
- ✅ **HSTS 安全头**：防止协议降级攻击
- ✅ **前向保密**：使用 ECDHE/DHE 密钥交换
- ✅ **HTTP/2 支持**：提升页面加载速度
- ✅ **短信验证**：支持阿里云短信服务
- ✅ **高可用性**：自动重启和健康检查

**访问地址**：
- 主站：https://mrgun.chu-jiao.com
- API 文档（已禁用）：https://mrgun.chu-jiao.com/docs
- 健康检查：https://mrgun.chu-jiao.com/health

**下一步**：
1. 配置域名 DNS 解析到服务器 IP
2. 配置防火墙规则（只开放 80、443 端口）
3. 设置自动备份任务（cron job）
4. 配置监控告警（Prometheus + Grafana）
5. 在 2026-01-19 前续期 SSL 证书

如有任何问题，请参考本文档的故障排查部分。🚀
