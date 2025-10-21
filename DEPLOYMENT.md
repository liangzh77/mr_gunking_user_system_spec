# MR游戏运营管理系统 - 生产环境部署指南

## 📋 目录
1. [部署前准备](#部署前准备)
2. [服务器初始化](#服务器初始化)
3. [配置GitHub Secrets](#配置github-secrets)
4. [自动部署流程](#自动部署流程)
5. [手动部署](#手动部署)
6. [SSL证书配置](#ssl证书配置)
7. [监控和日志](#监控和日志)
8. [故障排查](#故障排查)
9. [回滚操作](#回滚操作)

---

## 部署前准备

### 服务器要求

**最低配置**(小型业务):
- CPU: 2核
- 内存: 4GB
- 硬盘: 50GB SSD
- 带宽: 10Mbps
- 操作系统: Ubuntu 20.04 LTS 或 22.04 LTS

**推荐配置**(中大型业务):
- CPU: 4-8核
- 内存: 8-16GB
- 硬盘: 100GB SSD + 500GB HDD(备份)
- 带宽: 100Mbps
- 操作系统: Ubuntu 22.04 LTS

### 域名准备
- 购买域名并配置DNS解析
- 主域名: `yourdomain.com`
- API子域名(可选): `api.yourdomain.com`

---

## 服务器初始化

### 步骤1: 上传初始化脚本到服务器

```bash
# 在本地执行
scp .github/workflows/setup-server.sh root@your-server-ip:/tmp/

# SSH登录服务器
ssh root@your-server-ip

# 赋予执行权限并运行
chmod +x /tmp/setup-server.sh
sudo /tmp/setup-server.sh
```

初始化脚本会自动完成:
- ✅ 安装Docker和Docker Compose
- ✅ 创建部署用户(deploy)
- ✅ 克隆项目代码
- ✅ 配置防火墙
- ✅ 系统优化

### 步骤2: 配置生产环境变量

```bash
# 切换到部署用户
su - deploy

# 进入项目目录
cd /opt/mr_gunking_user_system_spec/backend

# 编辑生产环境配置
vim .env.production
```

**必须修改的关键配置**:

```bash
# 生成强随机密钥
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 数据库配置
DATABASE_URL=postgresql+asyncpg://mr_admin:你的强密码@postgres:5432/mr_game_ops
POSTGRES_PASSWORD=你的强密码  # 同上

# Redis配置
REDIS_URL=redis://:你的Redis密码@redis:6379/0
REDIS_PASSWORD=你的Redis密码

# 安全密钥(⚠️ 必改!)
SECRET_KEY=生成的32字节随机密钥
JWT_SECRET_KEY=生成的32字节随机密钥
ENCRYPTION_KEY=生成的32字节随机密钥

# 应用配置
DEBUG=false  # ⚠️ 生产环境必须false!
ENVIRONMENT=production
CORS_ORIGINS=https://yourdomain.com

# 工作进程数(建议: CPU核心数)
WORKERS=4
```

### 步骤3: 配置SSH密钥认证

```bash
# 在本地生成SSH密钥对(如果还没有)
ssh-keygen -t rsa -b 4096 -C "github-actions-deploy"

# 查看公钥
cat ~/.ssh/id_rsa.pub

# 将公钥添加到服务器
# 方法1: 使用ssh-copy-id
ssh-copy-id deploy@your-server-ip

# 方法2: 手动添加
# 在服务器上执行:
echo "你的公钥内容" >> /home/deploy/.ssh/authorized_keys
```

测试SSH连接:
```bash
ssh deploy@your-server-ip
```

---

## 配置GitHub Secrets

进入GitHub仓库 → Settings → Secrets and variables → Actions

添加以下Secrets:

### Docker Hub凭证(用于推送镜像)
```
DOCKER_USERNAME = 你的Docker Hub用户名
DOCKER_PASSWORD = 你的Docker Hub访问令牌
```

获取Docker Hub令牌:
1. 登录 https://hub.docker.com
2. Account Settings → Security → New Access Token

### Staging环境配置(可选)
```
STAGING_HOST = staging.yourdomain.com 或 IP地址
STAGING_USER = deploy
STAGING_SSH_KEY = 你的SSH私钥内容(cat ~/.ssh/id_rsa)
```

### Production环境配置
```
PROD_HOST = yourdomain.com 或 IP地址
PROD_USER = deploy
PROD_SSH_KEY = 你的SSH私钥内容(cat ~/.ssh/id_rsa)
```

**⚠️ 重要提示**:
- SSH_KEY是**私钥**内容,包含`-----BEGIN RSA PRIVATE KEY-----`等完整内容
- 不要泄露私钥给任何人

---

## 自动部署流程

### CI/CD工作流程

```
代码Push → GitHub Actions触发 → 代码质量检查 → 自动化测试
→ 安全扫描 → Docker镜像构建 → 部署到环境
```

### 触发条件

| 分支 | 触发操作 | 部署目标 |
|------|---------|---------|
| `main` | Push | Production(需审批) |
| `develop` | Push | Staging(自动) |
| `001-mr` | Push | CI测试(不部署) |

### 部署流程步骤

1. **环境检查** - 验证Docker、服务器状态
2. **数据库备份** - 自动备份PostgreSQL
3. **代码更新** - Git拉取最新代码
4. **配置检查** - 验证.env.production
5. **镜像构建** - 构建Docker镜像
6. **服务停止** - 优雅停止旧服务
7. **服务启动** - 启动新服务
8. **数据库迁移** - 执行Alembic迁移
9. **健康检查** - 验证服务状态
10. **清理资源** - 删除未使用镜像

---

## 手动部署

如果需要手动部署(不通过GitHub Actions):

### 本地手动触发部署

```bash
# 在本地项目目录执行
bash .github/workflows/deploy.sh \
  your-server-ip \
  deploy \
  production \
  main
```

### 直接在服务器上部署

```bash
# SSH到服务器
ssh deploy@your-server-ip

# 进入项目目录
cd /opt/mr_gunking_user_system_spec

# 拉取最新代码
git pull origin main

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 构建镜像
docker-compose -f docker-compose.prod.yml build

# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 执行数据库迁移
docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

---

## SSL证书配置

### 方法1: Let's Encrypt免费证书(推荐)

```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot certonly --standalone \
  -d yourdomain.com \
  -d www.yourdomain.com \
  --email your-email@example.com \
  --agree-tos

# 复制证书到项目目录
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem \
  /opt/mr_gunking_user_system_spec/nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem \
  /opt/mr_gunking_user_system_spec/nginx/ssl/

# 设置权限
sudo chown deploy:deploy /opt/mr_gunking_user_system_spec/nginx/ssl/*
```

### 方法2: 自签名证书(仅用于测试)

```bash
cd /opt/mr_gunking_user_system_spec/nginx/ssl/

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout privkey.pem \
  -out fullchain.pem \
  -subj "/CN=yourdomain.com"
```

### 证书自动续期

Let's Encrypt证书90天过期,设置自动续期:

```bash
# 编辑crontab
sudo crontab -e

# 添加定时任务(每月1号凌晨2点检查并续期)
0 2 1 * * certbot renew --quiet && \
  cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /opt/mr_gunking_user_system_spec/nginx/ssl/ && \
  cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /opt/mr_gunking_user_system_spec/nginx/ssl/ && \
  docker-compose -f /opt/mr_gunking_user_system_spec/docker-compose.prod.yml restart nginx
```

---

## 监控和日志

### 查看服务状态

```bash
cd /opt/mr_gunking_user_system_spec

# 查看所有容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看资源使用
docker stats
```

### 查看日志

```bash
# 实时查看所有日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend
docker-compose -f docker-compose.prod.yml logs -f nginx

# 查看最近100行日志
docker-compose -f docker-compose.prod.yml logs --tail=100 backend
```

### 监控指标

访问Prometheus metrics(仅内网):
```
http://your-server-ip/metrics
```

---

## 故障排查

### 问题1: 容器无法启动

```bash
# 检查容器日志
docker-compose -f docker-compose.prod.yml logs backend

# 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 重启服务
docker-compose -f docker-compose.prod.yml restart backend
```

### 问题2: 数据库连接失败

```bash
# 检查PostgreSQL状态
docker-compose -f docker-compose.prod.yml exec postgres pg_isready

# 查看数据库日志
docker-compose -f docker-compose.prod.yml logs postgres

# 进入PostgreSQL容器
docker-compose -f docker-compose.prod.yml exec postgres psql -U mr_admin -d mr_game_ops
```

### 问题3: 前端无法访问API

1. 检查Nginx配置
```bash
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
```

2. 检查网络连接
```bash
docker network ls
docker network inspect mr_network_prod
```

### 问题4: 磁盘空间不足

```bash
# 清理Docker资源
docker system prune -a --volumes

# 查看磁盘使用
df -h

# 查看Docker占用
docker system df
```

---

## 回滚操作

### 自动回滚到上一个版本

```bash
# 在本地执行
bash .github/workflows/rollback.sh your-server-ip deploy
```

### 回滚到指定版本

```bash
# 查看提交历史
git log --oneline -10

# 回滚到指定commit
bash .github/workflows/rollback.sh your-server-ip deploy abc1234
```

### 数据库回滚

```bash
# 查看迁移历史
docker-compose -f docker-compose.prod.yml exec backend alembic history

# 回滚到指定版本
docker-compose -f docker-compose.prod.yml exec backend alembic downgrade <revision_id>
```

### 从备份恢复数据库

```bash
# 查看可用备份
ls -lh /var/backups/mr_game_ops/

# 解压备份
gunzip /var/backups/mr_game_ops/db_backup_20250120_020000.sql.gz

# 恢复数据库
docker-compose -f docker-compose.prod.yml exec -T postgres psql \
  -U mr_admin \
  -d mr_game_ops \
  < /var/backups/mr_game_ops/db_backup_20250120_020000.sql
```

---

## 常用命令速查

```bash
# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 停止所有服务
docker-compose -f docker-compose.prod.yml down

# 重启单个服务
docker-compose -f docker-compose.prod.yml restart backend

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 进入容器
docker-compose -f docker-compose.prod.yml exec backend bash

# 数据库迁移
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 清理资源
docker system prune -a --volumes
```

---

## 安全建议

1. ✅ 修改所有默认密码
2. ✅ 启用防火墙,仅开放必要端口
3. ✅ 配置SSL证书,强制HTTPS
4. ✅ 定期更新系统和Docker镜像
5. ✅ 配置自动备份
6. ✅ 启用fail2ban防止暴力破解
7. ✅ 使用SSH密钥认证,禁用密码登录
8. ✅ 定期审查日志和监控告警

---

## 性能优化建议

1. 启用Redis缓存
2. 配置Nginx gzip压缩
3. 使用CDN加速静态资源
4. 数据库查询优化和索引
5. 配置数据库连接池
6. 使用Docker多阶段构建减小镜像体积

---

## 联系支持

如遇问题,请查看:
- [GitHub Issues](https://github.com/你的仓库/issues)
- [项目文档](https://docs.yourdomain.com)

---

**最后更新**: 2025-01-20
