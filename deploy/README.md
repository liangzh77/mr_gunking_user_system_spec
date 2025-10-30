# 🚀 MR游戏运营管理系统生产环境部署指南

## 📋 目录

- [系统要求](#系统要求)
- [部署流程](#部署流程)
- [详细步骤](#详细步骤)
- [配置说明](#配置说明)
- [管理命令](#管理命令)
- [故障排除](#故障排除)

## 🔧 系统要求

### 服务器配置
- **操作系统**: Ubuntu 22.04 LTS (推荐) / CentOS 8+ / RHEL 8+
- **CPU**: 4核心 (推荐) / 2核心 (最小)
- **内存**: 8GB RAM (推荐) / 4GB RAM (最小)
- **存储**: 100GB SSD (推荐) / 50GB SSD (最小)
- **网络**: 1Gbps (推荐) / 100Mbps (最小)

### 软件要求
- Docker 20.10+
- Docker Compose 2.0+
- Git 2.25+
- 域名解析 (可选，用于HTTPS)

## 📋 部署流程

### 快速部署 (推荐)

1. **准备服务器**
   ```bash
   # 上传部署文件到服务器
   scp -r deploy/ root@your-server:/root/

   # 连接到服务器
   ssh root@your-server
   ```

2. **运行部署脚本**
   ```bash
   # 进入部署目录
   cd /root/deploy

   # 设置执行权限
   chmod +x *.sh

   # 步骤1: 配置服务器基础环境
   ./01-server-setup.sh

   # 步骤2: 部署应用
   ./02-deploy.sh

   # 步骤3: 配置SSL证书 (可选)
   ./03-setup-ssl.sh yourdomain.com
   ```

## 📝 详细步骤

### 步骤1: 服务器基础环境配置

运行 `01-server-setup.sh` 脚本会自动完成以下配置：

- ✅ 更新系统包
- ✅ 安装Docker和Docker Compose
- ✅ 创建应用目录结构
- ✅ 配置防火墙
- ✅ 优化系统参数
- ✅ 设置自动备份
- ✅ 安装监控工具

### 步骤2: 应用部署

运行 `02-deploy.sh` 脚本会完成：

- ✅ 检查环境配置
- ✅ 构建Docker镜像
- ✅ 启动所有服务
- ✅ 初始化数据库
- ✅ 创建管理员账户
- ✅ 配置监控系统

### 步骤3: SSL证书配置 (可选)

运行 `03-setup-ssl.sh yourdomain.com` 脚本会：

- ✅ 安装Certbot
- ✅ 申请Let's Encrypt免费SSL证书
- ✅ 配置自动续期
- ✅ 更新Nginx配置
- ✅ 测试SSL连接

## ⚙️ 配置说明

### 环境变量配置

编辑 `.env.prod` 文件，修改以下关键配置：

```bash
# 数据库密码 (必须修改)
POSTGRES_PASSWORD=your_secure_password_here

# Redis密码 (必须修改)
REDIS_PASSWORD=your_redis_password_here

# 加密密钥 (必须修改，32位)
ENCRYPTION_KEY=your_32_byte_encryption_key_here

# JWT密钥 (必须修改)
JWT_SECRET_KEY=your_jwt_secret_key_here

# CORS域名 (修改为实际域名)
CORS_ORIGINS=https://yourdomain.com

# API地址
API_BASE_URL=https://yourdomain.com/api/v1

# Grafana密码
GRAFANA_PASSWORD=your_grafana_password_here
```

### Nginx配置

主要配置文件：`config/nginx/nginx.conf`

- **HTTPS重定向**: HTTP自动跳转到HTTPS
- **反向代理**: API和前端请求分发
- **安全头**: 添加安全相关的HTTP头
- **速率限制**: 防止API滥用
- **静态文件缓存**: 优化前端性能

### 监控配置

- **Prometheus**: 系统指标收集
- **Grafana**: 数据可视化面板
- **日志收集**: 结构化日志记录

## 🔧 管理命令

### Docker Compose命令

```bash
# 进入应用目录
cd /opt/mr-game-ops

# 查看服务状态
docker-compose -f docker-compose.yml ps

# 查看服务日志
docker-compose -f docker-compose.yml logs -f

# 重启所有服务
docker-compose -f docker-compose.yml restart

# 重启特定服务
docker-compose -f docker-compose.yml restart backend

# 停止所有服务
docker-compose -f docker-compose.yml down

# 更新服务
docker-compose -f docker-compose.yml pull
docker-compose -f docker-compose.yml up -d --force-recreate
```

### 数据库管理

```bash
# 连接数据库
docker exec -it mr_game_ops_db_prod psql -U mr_admin_prod -d mr_game_ops_prod

# 数据库备份
./scripts/backup.sh

# 查看数据库状态
docker exec mr_game_ops_db_prod pg_isready -U mr_admin_prod -d mr_game_ops_prod
```

### 日志管理

```bash
# 查看应用日志
tail -f /opt/mr-game-logs/app/app.log

# 查看Nginx日志
tail -f /opt/mr-game-logs/nginx/access.log
tail -f /opt/mr-game-logs/nginx/error.log

# 查看Docker日志
docker-compose -f docker-compose.yml logs backend
```

## 📊 监控面板

### Grafana监控面板

- **地址**: http://your-server-ip:3001
- **用户名**: admin
- **密码**: 环境变量中配置的 `GRAFANA_PASSWORD`

### Prometheus指标

- **地址**: http://your-server-ip:9090
- **指标**: 系统性能、API响应时间、数据库状态

## 🔐 安全配置

### 必须修改的配置

1. **数据库密码**: `.env.prod` 中的 `POSTGRES_PASSWORD`
2. **Redis密码**: `.env.prod` 中的 `REDIS_PASSWORD`
3. **加密密钥**: `.env.prod` 中的 `ENCRYPTION_KEY` (32位)
4. **JWT密钥**: `.env.prod` 中的 `JWT_SECRET_KEY`
5. **管理员密码**: 部署后立即修改默认密码

### SSL/TLS配置

- 生产环境必须配置HTTPS
- 推荐使用Let's Encrypt免费证书
- 确保证书自动续期
- 配置HSTS头部增强安全性

### 防火墙配置

```bash
# 查看防火墙状态
ufw status

# 添加规则
ufw allow 22/tcp  # SSH
ufw allow 80/tcp  # HTTP
ufw allow 443/tcp # HTTPS

# 启用防火墙
ufw enable
```

## 🔍 故障排除

### 常见问题

#### 1. 服务启动失败

```bash
# 检查服务状态
docker-compose -f docker-compose.yml ps

# 查看错误日志
docker-compose -f docker-compose.yml logs

# 检查资源使用
docker stats
```

#### 2. 数据库连接失败

```bash
# 检查数据库容器状态
docker exec mr_game_ops_db_prod pg_isready -U mr_admin_prod -d mr_game_ops_prod

# 检查数据库日志
docker logs mr_game_ops_db_prod
```

#### 3. SSL证书问题

```bash
# 检查证书状态
certbot certificates

# 手动续期
certbot renew

# 测试SSL配置
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

#### 4. 性能问题

```bash
# 检查系统资源
htop
free -h
df -h

# 检查Docker资源
docker stats --no-stream

# 优化建议
- 增加内存和CPU资源
- 调整Worker数量
- 启用缓存优化
```

## 📞 技术支持

### 日志位置

- **应用日志**: `/opt/mr-game-ops/logs/`
- **Nginx日志**: `/opt/mr-game-ops/logs/nginx/`
- **Docker日志**: `docker-compose logs`

### 备份策略

- **数据库备份**: 每天凌晨2点自动备份
- **备份位置**: `/opt/mr-game-ops/backups/`
- **保留期限**: 7天

### 更新升级

```bash
# 1. 备份数据
./scripts/backup.sh

# 2. 更新代码
git pull origin main

# 3. 重新部署
./02-deploy.sh

# 4. 验证升级
curl -f https://yourdomain.com/health
```

---

## 📱 许可证

本部署方案基于MIT许可证开源，可自由使用和修改。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进部署方案。

---

**🎉 祝您部署成功！**

如有问题，请查看日志文件或联系技术支持。