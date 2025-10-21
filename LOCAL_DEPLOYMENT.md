# 本地Docker部署指南

## 📋 前置要求

1. **安装Docker Desktop**
   - Windows: 下载 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
   - 确保Docker Desktop正在运行
   - 验证安装: `docker --version` 和 `docker-compose --version`

2. **系统要求**
   - Windows 10/11 Pro/Enterprise (支持WSL2)
   - 至少 4GB 可用内存
   - 至少 10GB 可用磁盘空间

## 🚀 快速启动（推荐）

### 方法一：使用启动脚本（最简单）

```bash
# 双击运行
start-local.bat
```

### 方法二：手动命令行

```bash
# 1. 构建镜像
docker-compose build

# 2. 启动所有服务
docker-compose up -d

# 3. 查看服务状态
docker-compose ps

# 4. 查看日志
docker-compose logs -f
```

## 📦 启动的服务

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 5173 | Vue 3前端应用 |
| 后端 | 8000 | FastAPI后端API |
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存服务 |
| PgAdmin | 5050 | 数据库管理工具 |
| Redis Commander | 8081 | Redis管理工具 |

## 🌐 访问地址

- **前端应用**: http://localhost:5173
- **后端API文档**: http://localhost:8000/docs
- **后端健康检查**: http://localhost:8000/health
- **PgAdmin**: http://localhost:5050
  - 用户名: `admin@mrgameops.com`
  - 密码: `admin_password`
- **Redis Commander**: http://localhost:8081

## 🔐 默认登录账号

系统会自动创建测试账号：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| superadmin | Admin123!@# | 超级管理员 |
| testadmin | Test123!@# | 普通管理员 |

## 📝 常用命令

### 启动和停止

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启特定服务
docker-compose restart backend
docker-compose restart frontend

# 停止并删除所有数据（慎用！）
docker-compose down -v
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres

# 查看最近100行日志
docker-compose logs --tail=100 backend
```

### 进入容器

```bash
# 进入后端容器
docker-compose exec backend bash

# 进入数据库容器
docker-compose exec postgres psql -U mr_admin -d mr_game_ops

# 执行数据库迁移
docker-compose exec backend alembic upgrade head

# 创建新的迁移
docker-compose exec backend alembic revision --autogenerate -m "描述"
```

### 重新构建

```bash
# 重新构建所有镜像
docker-compose build

# 重新构建特定服务
docker-compose build backend

# 强制重新构建（不使用缓存）
docker-compose build --no-cache

# 重新构建并启动
docker-compose up -d --build
```

## 🔧 故障排查

### 问题1: Docker Desktop未启动

**症状**: 运行命令时报错 `Cannot connect to the Docker daemon`

**解决**:
1. 打开Docker Desktop
2. 等待Docker完全启动（任务栏图标不再旋转）
3. 重新运行命令

### 问题2: 端口已被占用

**症状**: 启动时报错 `port is already allocated`

**解决**:
```bash
# 查看端口占用
netstat -ano | findstr :8000
netstat -ano | findstr :5173

# 停止占用端口的进程
taskkill /PID <进程ID> /F

# 或修改docker-compose.yml中的端口映射
```

### 问题3: 容器启动失败

**症状**: `docker-compose ps` 显示容器状态为 `Exit 1`

**解决**:
```bash
# 查看错误日志
docker-compose logs backend

# 常见原因:
# - 数据库未就绪: 等待一会儿后重启
# - 环境变量配置错误: 检查.env.development
# - 代码语法错误: 检查最近的代码修改
```

### 问题4: 数据库连接失败

**症状**: 后端日志显示 `could not connect to server`

**解决**:
```bash
# 检查PostgreSQL容器是否运行
docker-compose ps postgres

# 查看PostgreSQL日志
docker-compose logs postgres

# 重启数据库
docker-compose restart postgres

# 等待健康检查通过
docker-compose ps
```

### 问题5: 前端无法访问后端API

**症状**: 浏览器控制台显示CORS错误或404

**解决**:
1. 确认后端服务正常运行: http://localhost:8000/docs
2. 检查前端环境变量: `frontend/.env.development`
3. 确认VITE_API_BASE_URL正确: `http://localhost:8000/api/v1`

## 🗄️ 数据库管理

### 使用PgAdmin连接数据库

1. 访问 http://localhost:5050
2. 登录 (admin@mrgameops.com / admin_password)
3. 添加新服务器:
   - 名称: MR Game Ops
   - 主机: postgres
   - 端口: 5432
   - 数据库: mr_game_ops
   - 用户名: mr_admin
   - 密码: mr_secure_password_2024

### 数据库迁移

```bash
# 查看当前版本
docker-compose exec backend alembic current

# 升级到最新版本
docker-compose exec backend alembic upgrade head

# 降级一个版本
docker-compose exec backend alembic downgrade -1

# 查看迁移历史
docker-compose exec backend alembic history
```

### 备份和恢复

```bash
# 备份数据库
docker-compose exec -T postgres pg_dump -U mr_admin mr_game_ops > backup.sql

# 恢复数据库
docker-compose exec -T postgres psql -U mr_admin mr_game_ops < backup.sql
```

## 🧹 清理资源

```bash
# 停止并删除容器（保留数据）
docker-compose down

# 停止并删除容器和数据卷（删除所有数据！）
docker-compose down -v

# 清理未使用的Docker资源
docker system prune -a --volumes

# 仅清理未使用的镜像
docker image prune -a
```

## 🔄 开发工作流

### 前端热重载

前端代码修改后会自动重新加载，无需重启容器。

### 后端热重载

后端代码修改后会自动重新加载（uvicorn的--reload模式）。

### 数据库模型修改

```bash
# 1. 修改 backend/src/models/*.py

# 2. 生成迁移文件
docker-compose exec backend alembic revision --autogenerate -m "添加新字段"

# 3. 应用迁移
docker-compose exec backend alembic upgrade head

# 4. 重启后端（如需要）
docker-compose restart backend
```

## 📊 性能监控

### 查看资源使用

```bash
# 实时查看容器资源使用
docker stats

# 查看特定容器
docker stats mr_game_ops_backend
```

### 查看容器信息

```bash
# 查看容器详细信息
docker inspect mr_game_ops_backend

# 查看容器日志大小
docker-compose exec backend du -sh /app/logs
```

## 🔐 安全注意事项

⚠️ **开发环境配置，不要用于生产！**

1. 使用的是开发密钥（见 `.env.development`）
2. DEBUG模式已开启
3. 数据库密码为默认值
4. CORS允许所有本地端口
5. Redis无密码保护（在docker-compose中设置）

## 📚 相关文档

- [生产环境部署](./DEPLOYMENT.md)
- [API文档](http://localhost:8000/docs)
- [项目README](./README.md)

## ❓ 获取帮助

遇到问题？

1. 查看日志: `docker-compose logs -f`
2. 检查容器状态: `docker-compose ps`
3. 查看本文档的故障排查章节
4. 提交Issue: [GitHub Issues](https://github.com/你的仓库/issues)
