# 生产环境部署指南

本文档说明如何将 MR 游戏运营管理系统部署到生产环境。

## 目录

- [系统要求](#系统要求)
- [部署前准备](#部署前准备)
- [Docker Compose 部署](#docker-compose-部署)
- [配置说明](#配置说明)
- [SSL/TLS 配置](#ssltls-配置)
- [监控和日志](#监控和日志)
- [备份和恢复](#备份和恢复)
- [故障排查](#故障排查)

---

## 系统要求

### 硬件要求

**最低配置**:
- CPU: 2核
- 内存: 4GB
- 磁盘: 50GB SSD
- 网络: 10Mbps

**推荐配置**:
- CPU: 4核
- 内存: 8GB
- 磁盘: 100GB SSD
- 网络: 100Mbps

### 软件要求

- **操作系统**: Ubuntu 20.04 LTS / 22.04 LTS（推荐）
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 2.25+

---

## 部署前准备

### 1. 安装 Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 添加当前用户到 docker 组
sudo usermod -aG docker $USER
newgrp docker

# 验证安装
docker --version
docker-compose --version
```

### 2. 克隆项目

```bash
git clone <repository-url>
cd mr_gunking_user_system_spec
git checkout 001-mr  # 或主分支
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.production.example .env.production

# 编辑配置文件
nano .env.production
```

**必须修改的配置**:

```bash
# 数据库密码（使用强密码）
POSTGRES_PASSWORD=your_strong_password_here

# Redis 密码
REDIS_PASSWORD=your_redis_password_here

# JWT 密钥（32字符以上）
JWT_SECRET_KEY=$(openssl rand -base64 32)

# 加密密钥（正好32字符）
ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(24)[:32])")

# CORS 域名（替换为实际域名）
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Grafana 管理员密码
GRAFANA_ADMIN_PASSWORD=your_grafana_password
```

### 4. 创建数据目录

```bash
# 创建持久化数据目录
sudo mkdir -p /var/lib/mr-game-ops/{postgres,redis}
sudo chown -R $USER:$USER /var/lib/mr-game-ops

# 创建备份目录
mkdir -p backups
```

---

## Docker Compose 部署

### 1. 构建镜像

```bash
# 构建生产镜像
docker-compose -f docker-compose.prod.yml build

# 查看镜像
docker images | grep mr_game_ops
```

### 2. 启动服务

```bash
# 后台启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 3. 数据库初始化

```bash
# 应用数据库迁移
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 创建管理员账户
docker-compose -f docker-compose.prod.yml exec backend python scripts/create_admin.py

# 验证数据库
docker-compose -f docker-compose.prod.yml exec postgres psql -U mr_admin -d mr_game_ops -c "\dt"
```

### 4. 验证部署

```bash
# 健康检查
curl http://localhost:8000/health

# 预期输出:
# {"status": "healthy", "version": "0.1.0", ...}

# 检查 Prometheus 指标
curl http://localhost:8000/metrics

# 访问 Grafana
# http://your-server-ip:3000
# 默认账户: admin / (你设置的密码)
```

---

## 配置说明

### Nginx 反向代理

生产环境需要配置 Nginx 作为反向代理。

#### 1. 复制配置文件

```bash
sudo cp backend/deployment/nginx.conf /etc/nginx/sites-available/mr-game-ops.conf

# 编辑配置文件，替换域名
sudo nano /etc/nginx/sites-available/mr-game-ops.conf

# 创建符号链接
sudo ln -s /etc/nginx/sites-available/mr-game-ops.conf /etc/nginx/sites-enabled/
```

#### 2. 测试配置

```bash
sudo nginx -t
```

#### 3. 重新加载 Nginx

```bash
sudo systemctl reload nginx
```

### 防火墙配置

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# 验证规则
sudo ufw status
```

---

## SSL/TLS 配置

### 使用 Let's Encrypt

#### 1. 安装 Certbot

```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx
```

#### 2. 获取证书

```bash
# 自动配置（推荐）
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 手动配置
sudo certbot certonly --webroot -w /var/www/certbot \
    -d yourdomain.com -d www.yourdomain.com
```

#### 3. 自动续期

```bash
# 测试续期
sudo certbot renew --dry-run

# Certbot 自动配置了续期 cron job
# 查看: sudo systemctl list-timers | grep certbot
```

---

## 监控和日志

### Prometheus 监控

**访问**: http://your-server-ip:9090

**关键指标**:
- `mr_auth_requests_total` - 授权请求总数
- `mr_auth_latency_seconds` - 授权延迟
- `mr_operator_balance_yuan` - 运营商余额
- `mr_db_connection_pool_active` - 数据库连接池

### Grafana 可视化

**访问**: http://your-server-ip:3000

**默认账户**: admin / (你设置的密码)

**预配置仪表板**:
- 系统概览
- API 性能
- 数据库监控
- 业务指标

### 日志管理

#### 查看实时日志

```bash
# 所有服务
docker-compose -f docker-compose.prod.yml logs -f

# 特定服务
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f postgres
```

#### 日志轮转

日志已配置自动轮转：
- 后端日志: 最多 7 个文件，每个 50MB
- Nginx 日志: 最多 5 个文件，每个 20MB
- 数据库日志: 最多 3 个文件，每个 10MB

#### 导出日志

```bash
# 导出最近24小时的日志
docker-compose -f docker-compose.prod.yml logs --since 24h backend > backend_logs.txt
```

---

## 备份和恢复

### 自动备份

系统已配置自动备份服务（`postgres-backup`容器）：
- 备份频率: 每天凌晨 2 点
- 保留策略: 30天日备份 + 8周周备份 + 6月月备份
- 备份位置: `./backups/`

### 手动备份

#### 数据库备份

```bash
# 创建备份
docker-compose -f docker-compose.prod.yml exec postgres \
    pg_dump -U mr_admin mr_game_ops | gzip > backup_$(date +%Y%m%d).sql.gz

# 验证备份
gunzip -c backup_$(date +%Y%m%d).sql.gz | head -20
```

#### 完整备份

```bash
# 备份所有数据卷
docker run --rm \
    -v mr_game_ops_postgres_data_prod:/source:ro \
    -v $(pwd)/backups:/backup \
    alpine \
    tar -czf /backup/postgres_data_$(date +%Y%m%d).tar.gz -C /source .
```

### 数据恢复

#### 从备份恢复数据库

```bash
# 停止后端服务
docker-compose -f docker-compose.prod.yml stop backend

# 恢复数据库
gunzip -c backup_20251018.sql.gz | \
    docker-compose -f docker-compose.prod.yml exec -T postgres \
    psql -U mr_admin mr_game_ops

# 重启服务
docker-compose -f docker-compose.prod.yml start backend
```

---

## 故障排查

### 常见问题

#### 1. 服务无法启动

**检查日志**:
```bash
docker-compose -f docker-compose.prod.yml logs backend
```

**常见原因**:
- 端口被占用: 修改 docker-compose.prod.yml 中的端口映射
- 环境变量错误: 检查 .env.production 配置
- 权限问题: 确保数据目录有正确权限

#### 2. 数据库连接失败

**检查数据库状态**:
```bash
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U mr_admin
```

**解决方法**:
- 检查 `DATABASE_URL` 环境变量
- 确认 PostgreSQL 容器健康
- 查看数据库日志

#### 3. Redis 连接失败

**检查 Redis**:
```bash
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a your_redis_password ping
```

**解决方法**:
- 检查 `REDIS_URL` 和 `REDIS_PASSWORD`
- 确认 Redis 容器健康

#### 4. 性能问题

**检查资源使用**:
```bash
docker stats
```

**优化建议**:
- 增加 Gunicorn workers 数量
- 调整数据库连接池大小
- 启用 Redis 缓存
- 优化数据库查询

### 健康检查脚本

```bash
#!/bin/bash
# health_check.sh

echo "=== 服务健康检查 ==="

# 检查后端
echo -n "后端服务: "
curl -sf http://localhost:8000/health > /dev/null && echo "OK" || echo "FAIL"

# 检查数据库
echo -n "数据库: "
docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U mr_admin && echo "OK" || echo "FAIL"

# 检查 Redis
echo -n "Redis: "
docker-compose -f docker-compose.prod.yml exec -T redis redis-cli -a ${REDIS_PASSWORD} ping && echo "OK" || echo "FAIL"

# 检查 Nginx
echo -n "Nginx: "
curl -sf http://localhost:80 > /dev/null && echo "OK" || echo "FAIL"

echo "=== 检查完成 ==="
```

---

## 维护操作

### 更新应用

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建镜像
docker-compose -f docker-compose.prod.yml build

# 3. 应用数据库迁移
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 4. 重启服务（零停机）
docker-compose -f docker-compose.prod.yml up -d --no-deps --build backend
```

### 扩容

```bash
# 增加后端 workers
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# 或修改 .env.production 中的 GUNICORN_WORKERS
```

### 清理

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的卷
docker volume prune

# 清理未使用的网络
docker network prune
```

---

## 安全建议

### 1. 定期更新

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 更新 Docker 镜像
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### 2. 监控告警

- 配置 Prometheus Alertmanager
- 设置关键指标告警
- 配置告警通知（邮件/钉钉/Slack）

### 3. 访问控制

- 使用防火墙限制端口访问
- 配置 fail2ban 防止暴力破解
- 定期审查访问日志

### 4. 数据安全

- 定期测试备份恢复
- 加密敏感数据
- 使用 HTTPS 加密传输

---

## 参考资源

- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

---

**部署完成后**，访问以下地址验证：

- 🌐 **应用**: https://yourdomain.com
- 📊 **Grafana**: http://your-server-ip:3000
- 📈 **Prometheus**: http://your-server-ip:9090
- 📖 **API 文档**: https://yourdomain.com/api/docs (仅开发环境)

---

**文档版本**: 1.0
**最后更新**: 2025-10-18
