# MR游戏运营管理系统 - Docker 部署指南

## 📋 系统要求

- Docker Desktop 或 Docker Engine 20.10+
- Docker Compose V2
- 操作系统: Windows 10+, macOS, 或 Linux
- 最小内存: 4GB RAM
- 最小磁盘: 10GB 可用空间

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/liangzh77/mr_gunking_user_system_spec.git
cd mr_gunking_user_system_spec
```

### 2. 启动所有服务

```bash
docker-compose up -d
```

### 3. 等待服务启动

首次启动需要下载镜像和初始化数据库，大约需要 3-5 分钟。

### 4. 访问系统

- **前端管理后台**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/api/docs
- **数据库管理**: http://localhost:5050
- **Redis 管理**: http://localhost:8081

## 🔐 默认账户

### 管理员账户
- 用户名: `admin`
- 密码: `Admin@123456`
- 登录地址: http://localhost:5173/admin/login

### 数据库连接（pgAdmin）
- 主机: postgres
- 端口: 5432
- 用户名: mr_admin
- 密码: （在 docker-compose.yml 中配置）
- 数据库: mr_game_ops

## 📦 服务说明

### 核心服务

| 服务名 | 容器名 | 端口 | 说明 |
|--------|--------|------|------|
| postgres | mr_game_ops_db | 5432 | PostgreSQL 14 数据库 |
| redis | mr_game_ops_redis | 6379 | Redis 7 缓存 |
| backend | mr_game_ops_backend | 8000 | FastAPI 后端 |
| frontend | mr_game_ops_frontend | 5173 | Vue.js + Vite 前端 |

### 管理工具

| 服务名 | 容器名 | 端口 | 说明 |
|--------|--------|------|------|
| pgadmin | mr_game_ops_pgadmin | 5050 | PostgreSQL 管理工具 |
| redis-commander | mr_game_ops_redis_commander | 8081 | Redis 管理工具 |

## 🛠️ 常用命令

### 启动服务
```bash
docker-compose up -d
```

### 停止服务
```bash
docker-compose down
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 重启服务
```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
```

### 查看服务状态
```bash
docker-compose ps
```

### 进入容器
```bash
# 进入后端容器
docker-compose exec backend bash

# 进入数据库容器
docker-compose exec postgres psql -U mr_admin -d mr_game_ops
```

## 🔄 数据库管理

### 初始化数据库

数据库会在首次启动时自动初始化。如果需要重新初始化：

```bash
# 停止服务并删除所有数据
docker-compose down -v

# 重新启动
docker-compose up -d
```

### 创建管理员账户

如果需要重新创建管理员账户：

```bash
docker-compose exec backend python -c "
from passlib.context import CryptContext
import uuid

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto', bcrypt__rounds=10)
admin_id = str(uuid.uuid4())
password_hash = pwd_context.hash('Admin@123456')
print(f'ID: {admin_id}')
print(f'Hash: {password_hash}')
"
```

## 🐛 故障排除

### 服务无法启动

**问题**: 容器启动失败
```bash
# 查看详细日志
docker-compose logs backend
docker-compose logs frontend
```

**解决方案**:
1. 检查端口是否被占用
2. 检查 Docker 资源配置
3. 重新构建镜像: `docker-compose build --no-cache`

### 数据库连接失败

**问题**: 后端无法连接数据库

**解决方案**:
```bash
# 检查数据库是否健康
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres

# 重启数据库
docker-compose restart postgres
```

### 前端页面空白

**问题**: 浏览器显示空白页面

**解决方案**:
```bash
# 检查前端日志
docker-compose logs frontend

# 检查 Vite 是否正常运行
curl http://localhost:5173

# 重新构建前端镜像
docker-compose build frontend
docker-compose up -d frontend
```

### 端口冲突

**问题**: 端口已被占用

**解决方案**:
修改 `docker-compose.yml` 中的端口映射:
```yaml
services:
  frontend:
    ports:
      - "5174:5173"  # 将 5173 改为其他可用端口
```

## 📊 性能优化

### 调整资源限制

编辑 `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### 使用国内镜像加速

已在 Dockerfile 中配置:
- **Python 包**: 清华大学 PyPI 镜像
- **npm 包**: 淘宝 npm 镜像
- **apt 包**: 阿里云 Debian 镜像

## 🔐 安全建议

### 生产环境部署

1. **修改默认密码**: 更改所有默认密码
2. **配置环境变量**: 使用 `.env` 文件管理敏感信息
3. **启用 HTTPS**: 配置 SSL 证书
4. **限制端口访问**: 使用防火墙限制外部访问
5. **定期备份**: 备份数据库和上传文件

### 创建 .env 文件

```bash
cp .env.example .env
# 编辑 .env 文件，修改敏感配置
```

## 📚 更多文档

- [API 文档](http://localhost:8000/api/docs)
- [系统运维手册](./system_operations_manual.md)
- [后端 API 文档](../backend/docs/API_DOCUMENTATION.md)

## 🆘 获取帮助

如有问题，请：
1. 查看日志文件
2. 检查 GitHub Issues
3. 联系技术支持

---

**最后更新**: 2025-10-28
**Docker Compose 版本**: V2
**系统版本**: 0.1.0
