# 手动测试指南

本文档说明如何手动测试 MR 游戏运营管理系统的 API。

## 前置条件

1. PostgreSQL 数据库容器正在运行（`mr_game_ops_db`）
2. 种子数据已创建（3个管理员账户）

## 测试方法

### 方法 1: 使用 Python 测试脚本（推荐）

这是最简单的方法，自动测试所有端点：

```bash
# 在项目根目录执行
cd backend

# 启动 FastAPI 应用（后台运行）
docker run -d --name mr_api --network host \
  -v "C:\data\liang\code\github_projects\mr_gunking_user_system_spec\backend:/app" \
  -w /app python:3.11-slim \
  bash -c "pip install -q -r requirements.txt && python -m uvicorn src.main:app --host 0.0.0.0 --port 8000"

# 等待应用启动（约10秒）
sleep 10

# 运行测试脚本
docker run --rm --network host \
  -v "C:\data\liang\code\github_projects\mr_gunking_user_system_spec\backend:/app" \
  -w /app python:3.11-slim \
  bash -c "pip install -q requests && python scripts/test_admin_api.py"

# 查看应用日志（可选）
docker logs mr_api

# 清理
docker stop mr_api && docker rm mr_api
```

### 方法 2: 使用 curl 命令

如果你想手动测试单个端点：

#### 1. 健康检查

```bash
docker run --rm --network host curlimages/curl:latest \
  curl -X GET http://localhost:8000/health
```

#### 2. 管理员登录

```bash
docker run --rm --network host curlimages/curl:latest \
  curl -X POST http://localhost:8000/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"superadmin","password":"admin123456"}'
```

成功响应示例：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 2592000,
  "user": {
    "id": "uuid-here",
    "username": "superadmin",
    "full_name": "系统管理员",
    "email": "admin@example.com",
    "role": "super_admin",
    "permissions": ["*"],
    "is_active": true
  }
}
```

#### 3. 获取当前用户信息

先保存 token（从上一步获取），然后：

```bash
# 替换 YOUR_TOKEN_HERE 为实际的 access_token
docker run --rm --network host curlimages/curl:latest \
  curl -X GET http://localhost:8000/api/v1/admin/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### 4. 刷新 Token

```bash
docker run --rm --network host curlimages/curl:latest \
  curl -X POST http://localhost:8000/api/v1/admin/refresh \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### 5. 修改密码

```bash
docker run --rm --network host curlimages/curl:latest \
  curl -X POST http://localhost:8000/api/v1/admin/change-password \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"old_password":"admin123456","new_password":"new_password_123"}'
```

#### 6. 登出

```bash
docker run --rm --network host curlimages/curl:latest \
  curl -X POST http://localhost:8000/api/v1/admin/logout \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 方法 3: 使用 Postman 或类似工具

如果你有 Windows 上的 API 测试工具（Postman、Insomnia 等）：

1. 启动 FastAPI 应用并映射端口：
   ```bash
   docker run -d --name mr_api -p 8000:8000 \
     -v "C:\data\liang\code\github_projects\mr_gunking_user_system_spec\backend:/app" \
     -w /app python:3.11-slim \
     bash -c "pip install -q -r requirements.txt && python -m uvicorn src.main:app --host 0.0.0.0 --port 8000"
   ```

2. 在 Postman 中访问 `http://localhost:8000/api/docs` 查看 Swagger UI

3. 使用 Swagger UI 进行交互式测试

## 测试账户

种子数据中包含以下测试账户：

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| superadmin | admin123456 | super_admin | 所有权限 (*) |
| admin_zhang | admin123456 | admin | operator:read, operator:write, operator:audit |
| admin_li | admin123456 | admin | config:read, config:write, operator:read |

## API 端点列表

| 方法 | 路径 | 说明 | 需要认证 |
|------|------|------|----------|
| GET | /health | 健康检查 | ❌ |
| GET | / | API 根信息 | ❌ |
| POST | /api/v1/admin/login | 管理员登录 | ❌ |
| POST | /api/v1/admin/logout | 管理员登出 | ✅ |
| GET | /api/v1/admin/me | 获取当前用户信息 | ✅ |
| POST | /api/v1/admin/refresh | 刷新访问令牌 | ✅ |
| POST | /api/v1/admin/change-password | 修改密码 | ✅ |

## 常见问题

### Q: 端口 8000 被占用？

检查并停止占用端口的进程：
```bash
docker ps | grep 8000
docker stop <container_id>
```

### Q: 数据库连接失败？

确保 PostgreSQL 容器正在运行：
```bash
docker ps | grep mr_game_ops_db
```

### Q: 登录失败（401 Unauthorized）？

检查：
1. 数据库中是否有管理员账户
2. 密码是否正确（admin123456）
3. 账户是否激活（is_active = true）

查询数据库验证：
```bash
docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops \
  -c "SELECT username, is_active FROM admin_accounts;"
```

## 下一步

完成手动测试后，建议编写自动化测试用例（pytest）以确保功能稳定性。
