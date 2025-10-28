# MR游戏运营管理系统 - 生产环境部署指南

**版本**: 1.0.0  
**日期**: 2025-10-28  
**目标**: MVP快速发布

---

## 📋 目录

1. [部署前准备](#部署前准备)
2. [环境配置](#环境配置)
3. [部署步骤](#部署步骤)
4. [验证和测试](#验证和测试)
5. [监控和维护](#监控和维护)
6. [故障排除](#故障排除)
7. [回滚流程](#回滚流程)

---

## 🔧 部署前准备

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2核 | 4核+ |
| 内存 | 4GB | 8GB+ |
| 硬盘 | 20GB | 50GB+ SSD |
| 网络 | 10Mbps | 100Mbps+ |

### 软件要求

- **操作系统**: Linux (Ubuntu 20.04+ / CentOS 7+ / Debian 10+)
- **Docker**: 20.10.0+
- **Docker Compose**: 2.0.0+
- **Git**: 2.20.0+
- **可选**: Nginx (如需SSL/反向代理)

### 安装Docker和Docker Compose

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

---

## ⚙️ 环境配置

### 1. 克隆代码仓库

```bash
git clone https://github.com/liangzh77/mr_gunking_user_system_spec.git
cd mr_gunking_user_system_spec
git checkout 001-mr-v2
```

### 2. 配置环境变量

复制环境变量模板并配置：

```bash
cp .env.production.template .env.production
```

编辑 `.env.production` 文件，**必须修改**以下配置：

#### ⚠️ 必须修改的配置项

```bash
# 数据库密码 - 使用强密码
DB_PASSWORD=CHANGE_THIS_TO_STRONG_PASSWORD_32CHARS

# Redis密码 - 使用强密码
REDIS_PASSWORD=CHANGE_THIS_TO_STRONG_REDIS_PASSWORD

# 生成安全密钥
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -base64 32)

# CORS配置 - 修改为实际域名
BACKEND_CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# 前端API地址 - 修改为实际域名
VITE_API_BASE_URL=https://yourdomain.com/api/v1
```

#### 生成安全密钥命令

```bash
# 生成64字符十六进制密钥
openssl rand -hex 32

# 生成32字节base64密钥
openssl rand -base64 32

# 或使用Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. 配置检查清单

完成配置后，确认以下项目：

- [ ] `DB_PASSWORD` - 已修改为强密码（至少32字符）
- [ ] `REDIS_PASSWORD` - 已修改为强密码
- [ ] `SECRET_KEY` - 已使用 `openssl rand -hex 32` 生成
- [ ] `JWT_SECRET_KEY` - 已使用 `openssl rand -hex 32` 生成
- [ ] `ENCRYPTION_KEY` - 已生成32字节密钥
- [ ] `BACKEND_CORS_ORIGINS` - 已配置为实际域名
- [ ] `VITE_API_BASE_URL` - 已配置为实际API地址
- [ ] `.env.production` 已添加到 `.gitignore` （项目已包含）

---

## 🚀 部署步骤

### 方法1: 使用自动部署脚本（推荐）

```bash
# 使部署脚本可执行
chmod +x deploy.sh backup_db.sh

# 执行部署
./deploy.sh
```

部署脚本会自动执行以下步骤：
1. 检查前提条件
2. 可选数据库备份
3. 构建Docker镜像
4. 停止旧容器
5. 启动新容器
6. 健康检查
7. 清理旧镜像

### 方法2: 手动部署

```bash
# 1. 设置构建参数
export BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
export VERSION=1.0.0

# 2. 构建镜像
docker-compose -f docker-compose.prod.yml build --no-cache

# 3. 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 4. 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

---

## ✅ 验证和测试

### 1. 检查容器状态

```bash
docker-compose -f docker-compose.prod.yml ps
```

所有容器应显示为 `Up` 状态。

### 2. 健康检查

#### 后端健康检查

```bash
# 容器内部检查
docker exec mr_game_ops_backend_prod curl -f http://localhost:8000/health

# 外部检查（如果暴露端口）
curl http://localhost/api/v1/health
```

预期响应：
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

#### 前端健康检查

```bash
curl -I http://localhost
```

预期响应: `200 OK`

### 3. 功能测试清单

使用 E2E 测试报告中的测试用例进行验证：

- [ ] 管理员登录功能正常
- [ ] 财务端登录功能正常
- [ ] 运营商登录功能正常
- [ ] API响应时间 < 500ms
- [ ] 数据库连接正常
- [ ] Redis缓存正常

### 4. 性能测试

```bash
# 简单的性能测试
ab -n 100 -c 10 http://localhost/api/v1/health
```

---

## 📊 监控和维护

### 日志查看

```bash
# 查看所有服务日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend

# 查看最近100行日志
docker-compose -f docker-compose.prod.yml logs --tail=100 backend
```

### 数据库备份

#### 手动备份

```bash
./backup_db.sh
```

#### 自动备份 (Cron任务)

```bash
# 编辑crontab
crontab -e

# 添加每天凌晨2点自动备份
0 2 * * * /path/to/mr_gunking_user_system_spec/backup_db.sh >> /var/log/db_backup.log 2>&1
```

#### 备份恢复

```bash
# 查看可用备份
ls -lh backups/

# 恢复备份
gunzip -c backups/backup_mr_game_ops_20251028_020000.sql.gz | \
  docker exec -i mr_game_ops_db_prod psql -U mr_admin -d mr_game_ops
```

### 容器资源监控

```bash
# 查看容器资源使用情况
docker stats

# 查看特定容器
docker stats mr_game_ops_backend_prod mr_game_ops_frontend_prod
```

---

## 🔍 故障排除

### 常见问题

#### 1. 容器无法启动

**症状**: 容器状态显示 `Exited` 或 `Restarting`

**解决方法**:
```bash
# 查看容器日志
docker logs mr_game_ops_backend_prod --tail=50

# 检查环境变量配置
docker exec mr_game_ops_backend_prod env | grep -E "DATABASE|REDIS"

# 检查网络连接
docker network inspect mr_network
```

#### 2. 数据库连接失败

**症状**: 后端日志显示 "Connection refused" 或 "Authentication failed"

**解决方法**:
```bash
# 检查数据库容器状态
docker ps | grep postgres

# 检查数据库日志
docker logs mr_game_ops_db_prod --tail=50

# 测试数据库连接
docker exec mr_game_ops_db_prod psql -U mr_admin -d mr_game_ops -c "SELECT 1"

# 验证密码配置
grep DB_PASSWORD .env.production
```

#### 3. 前端无法访问后端API

**症状**: 前端页面显示 "Network Error" 或 API请求失败

**解决方法**:
```bash
# 检查Nginx配置
docker exec mr_game_ops_frontend_prod cat /etc/nginx/nginx.conf

# 检查后端容器网络
docker exec mr_game_ops_frontend_prod ping backend

# 检查CORS配置
grep BACKEND_CORS_ORIGINS .env.production
```

#### 4. 性能问题

**症状**: 响应时间过长，系统卡顿

**解决方法**:
```bash
# 检查容器资源使用
docker stats

# 检查数据库性能
docker exec mr_game_ops_db_prod psql -U mr_admin -d mr_game_ops -c "SELECT * FROM pg_stat_activity;"

# 检查Redis性能
docker exec mr_game_ops_redis_prod redis-cli info stats
```

### 日志级别调整

如需更详细的日志用于调试：

```bash
# 临时修改日志级别
docker-compose -f docker-compose.prod.yml exec backend \
  /bin/bash -c 'export LOG_LEVEL=DEBUG && uvicorn src.main:app --reload'
```

---

## 🔄 回滚流程

### 快速回滚

如果新版本出现问题，执行以下步骤回滚：

```bash
# 1. 停止当前服务
docker-compose -f docker-compose.prod.yml down

# 2. 切换到上一个稳定版本
git checkout <上一个稳定版本的commit>

# 3. 恢复数据库备份（如需要）
gunzip -c backups/backup_mr_game_ops_<timestamp>.sql.gz | \
  docker exec -i mr_game_ops_db_prod psql -U mr_admin -d mr_game_ops

# 4. 重新部署
./deploy.sh
```

### 版本管理

```bash
# 查看可用版本
git tag

# 回滚到特定版本
git checkout tags/v1.0.0
./deploy.sh
```

---

## 📝 维护操作

### 更新部署

```bash
# 1. 备份当前数据
./backup_db.sh

# 2. 拉取最新代码
git pull origin 001-mr-v2

# 3. 重新部署
./deploy.sh
```

### 清理操作

```bash
# 清理未使用的镜像
docker image prune -f

# 清理未使用的容器
docker container prune -f

# 清理未使用的卷（⚠️ 谨慎使用）
docker volume prune -f

# 清理旧的日志文件
find backend/logs -name "*.log" -mtime +30 -delete
```

### 停止服务

```bash
# 停止所有服务
docker-compose -f docker-compose.prod.yml down

# 停止并删除卷（⚠️ 会删除所有数据）
docker-compose -f docker-compose.prod.yml down -v
```

---

## 🔒 安全建议

1. **定期更新密码**: 每90天更换一次数据库和Redis密码
2. **启用防火墙**: 只开放必要的端口(80, 443)
3. **SSL/TLS**: 使用Let's Encrypt配置HTTPS
4. **日志审计**: 定期检查访问日志和错误日志
5. **备份策略**: 保持至少7天的数据库备份
6. **资源限制**: 使用Docker资源限制防止资源耗尽

---

## 📞 支持和联系

- **文档**: 查看项目 `specs/` 目录下的详细文档
- **问题反馈**: 通过GitHub Issues反馈问题
- **紧急联系**: [联系方式]

---

## 📚 相关文档

- [E2E测试报告](./E2E_TEST_REPORT.md)
- [MVP发布计划](./MVP_RELEASE_PLAN.md)
- [测试数据创建记录](./TEST_DATA_CREATION.md)
- [任务清单](./tasks.md)
- [功能规格说明](./spec.md)
- [实现计划](./plan.md)

---

**最后更新**: 2025-10-28  
**版本**: 1.0.0
