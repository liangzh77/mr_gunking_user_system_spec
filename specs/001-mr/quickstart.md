# Quick Start Guide: MR游戏运营管理系统

**Version**: 1.0.0
**Date**: 2025-10-10
**Time to Complete**: ~30分钟

---

## 概述

本指南帮助您快速搭建MR游戏运营管理系统的本地开发环境，并完成第一次游戏授权测试。

系统核心功能：
- 头显Server通过API Key + HMAC签名请求游戏授权
- 系统验证运营商授权、余额，按玩家数量计费
- 返回授权Token，游戏启动
- 运营商Web端管理账户、充值、查看统计

**技术栈**: FastAPI + PostgreSQL + Redis + Docker

---

## 前置要求

### 必需软件

| 软件 | 最低版本 | 用途 | 下载地址 |
|------|---------|------|---------|
| **Docker Desktop** | 20.10+ | 容器运行环境 | https://www.docker.com/products/docker-desktop |
| **Docker Compose** | 2.0+ | 容器编排工具 | 随Docker Desktop安装 |
| **Python** | 3.11+ | 后端运行环境 | https://www.python.org/downloads/ |
| **Git** | 2.30+ | 版本控制 | https://git-scm.com/downloads |

### 推荐工具

- **VS Code** + Python扩展 (代码编辑)
- **Postman** 或 **Insomnia** (API测试)
- **pgAdmin 4** (数据库管理，可选)

### 系统要求

- **内存**: 8GB+ (Docker需要至少4GB)
- **磁盘**: 20GB可用空间
- **操作系统**: Windows 10+, macOS 12+, Ubuntu 20.04+

### 验证安装

```bash
# 验证Docker版本
docker --version
# 输出示例: Docker version 24.0.6, build ed223bc

# 验证Docker Compose版本
docker compose version
# 输出示例: Docker Compose version v2.21.0

# 验证Python版本
python --version
# 输出示例: Python 3.11.5

# 验证Git版本
git --version
# 输出示例: git version 2.42.0
```

---

## 第一步：克隆项目并安装依赖 (5分钟)

### 1.1 克隆代码仓库

```bash
# 克隆项目 (假设仓库已初始化)
git clone https://github.com/your-org/mr-game-system.git
cd mr-game-system
```

**当前阶段说明**: 如果项目尚未初始化后端代码，请先创建项目结构：

```bash
# 创建后端项目目录
mkdir -p backend/src/{models,schemas,services,api/v1,core,db,utils}
mkdir -p backend/tests/{contract,integration,unit}
mkdir -p backend/alembic/versions
```

### 1.2 安装Python依赖

在项目根目录创建虚拟环境并安装依赖：

```bash
# Windows
cd backend
python -m venv venv
venv\Scripts\activate

# macOS/Linux
cd backend
python3 -m venv venv
source venv/bin/activate
```

创建 `backend/requirements.txt` 文件：

```txt
# Web框架
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# 数据库
sqlalchemy==2.0.23
alembic==1.12.1
asyncpg==0.29.0
psycopg2-binary==2.9.9

# 数据验证
pydantic==2.5.0
pydantic-settings==2.1.0

# 认证和安全
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Redis
redis==5.0.1
hiredis==2.2.3

# HTTP客户端 (支付接口)
httpx==0.25.2

# 日志
structlog==23.2.0

# 测试
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
faker==20.1.0

# 代码质量
ruff==0.1.6
black==23.11.0
mypy==1.7.1
```

安装依赖：

```bash
pip install -r requirements.txt
```

### 1.3 配置环境变量

在 `backend/` 目录创建 `.env` 文件：

```env
# ================================
# 应用配置
# ================================
APP_NAME="MR游戏运营管理系统"
APP_VERSION="1.0.0"
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production-min-32-chars
CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]

# ================================
# 数据库配置 (PostgreSQL)
# ================================
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=mr_game_system
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres123
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# DATABASE_URL格式 (SQLAlchemy使用)
DATABASE_URL=postgresql+asyncpg://postgres:postgres123@localhost:5432/mr_game_system

# ================================
# Redis配置
# ================================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis123
REDIS_DB=0
REDIS_URL=redis://:redis123@localhost:6379/0

# ================================
# JWT认证配置
# ================================
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=43200  # 30天

# ================================
# API Key配置
# ================================
API_KEY_LENGTH=64
API_KEY_EXPIRE_DAYS=0  # 0表示永不过期

# ================================
# 支付平台配置 (测试环境)
# ================================
# 微信支付
WECHAT_PAY_APP_ID=wx1234567890abcdef
WECHAT_PAY_MCH_ID=1234567890
WECHAT_PAY_API_KEY=your_wechat_api_key_32_chars_here
WECHAT_PAY_NOTIFY_URL=http://your-domain.com/api/v1/payment/wechat/callback

# 支付宝
ALIPAY_APP_ID=2021001234567890
ALIPAY_PRIVATE_KEY_PATH=./keys/alipay_private_key.pem
ALIPAY_PUBLIC_KEY_PATH=./keys/alipay_public_key.pem
ALIPAY_NOTIFY_URL=http://your-domain.com/api/v1/payment/alipay/callback

# ================================
# 业务配置
# ================================
# 余额不足阈值 (元)
LOW_BALANCE_THRESHOLD=100.00

# 授权请求频率限制 (次/分钟)
RATE_LIMIT_PER_MINUTE=10

# HMAC签名有效期 (秒)
HMAC_SIGNATURE_EXPIRE_SECONDS=300

# 支付回调超时时间 (秒)
PAYMENT_CALLBACK_TIMEOUT=300

# ================================
# 日志配置
# ================================
LOG_LEVEL=INFO
LOG_FORMAT=json  # json 或 console

# ================================
# 监控配置 (可选)
# ================================
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
```

**安全提示**:
- 生产环境必须修改 `SECRET_KEY` 和 `JWT_SECRET_KEY`
- 可使用以下命令生成随机密钥：
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

---

## 第二步：启动基础设施 (5分钟)

### 2.1 启动Docker容器

在项目根目录创建 `docker-compose.yml` 文件（见附录A）。

启动PostgreSQL和Redis：

```bash
# 在项目根目录执行
docker compose up -d postgres redis

# 查看容器日志
docker compose logs -f postgres redis
```

**预期输出**:
```
✔ Container mr-game-postgres  Started
✔ Container mr-game-redis     Started
```

### 2.2 验证容器状态

```bash
# 检查容器运行状态
docker compose ps

# 预期输出:
# NAME                IMAGE               STATUS
# mr-game-postgres    postgres:14         Up 30 seconds
# mr-game-redis       redis:7-alpine      Up 30 seconds
```

### 2.3 测试数据库连接

```bash
# 连接PostgreSQL (密码: postgres123)
docker exec -it mr-game-postgres psql -U postgres -d mr_game_system

# 在psql中执行 (验证数据库已创建)
\l
# 查看是否有 mr_game_system 数据库

# 退出psql
\q
```

### 2.4 测试Redis连接

```bash
# 连接Redis
docker exec -it mr-game-redis redis-cli -a redis123

# 测试命令
PING
# 预期输出: PONG

# 退出Redis
exit
```

**常见问题排查**: 见本文档"常见问题排查"章节

---

## 第三步：初始化数据库 (5分钟)

### 3.1 创建数据库迁移脚本

在 `backend/` 目录初始化Alembic：

```bash
# 确保虚拟环境已激活
cd backend

# 初始化Alembic (如果尚未初始化)
alembic init alembic

# 配置alembic.ini中的数据库连接
# 修改 sqlalchemy.url 为:
# sqlalchemy.url = postgresql+asyncpg://postgres:postgres123@localhost:5432/mr_game_system
```

创建初始迁移脚本（基于data-model.md中的表结构）：

```bash
# 创建迁移脚本
alembic revision -m "initial_schema"
```

编辑生成的迁移文件 `alembic/versions/xxxx_initial_schema.py`，参考附录C中的建表SQL。

### 3.2 运行数据库迁移

```bash
# 应用迁移 (创建所有表)
alembic upgrade head

# 预期输出:
# INFO  [alembic.runtime.migration] Running upgrade  -> xxxx, initial_schema
```

### 3.3 插入种子数据

创建 `backend/scripts/seed_data.py` 文件：

```python
"""种子数据脚本 - 创建测试用超级管理员和示例应用"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
import secrets

DATABASE_URL = "postgresql+asyncpg://postgres:postgres123@localhost:5432/mr_game_system"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_data():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 创建超级管理员
        admin_sql = """
        INSERT INTO admin_accounts (username, full_name, email, password_hash, role, is_active)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (username) DO NOTHING
        RETURNING id;
        """
        admin_password = pwd_context.hash("admin123")
        result = await session.execute(
            admin_sql,
            ("admin", "系统管理员", "admin@example.com", admin_password, "super_admin", True)
        )
        await session.commit()
        print("✅ 创建超级管理员: admin / admin123")

        # 创建示例应用
        app_sql = """
        INSERT INTO applications (app_code, app_name, description, price_per_player, min_players, max_players, is_active)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (app_code) DO NOTHING;
        """
        await session.execute(
            app_sql,
            ("space_adventure", "太空探险", "沉浸式太空探索VR游戏", 10.00, 2, 8, True)
        )
        await session.execute(
            app_sql,
            ("galaxy_war", "星际战争", "多人协作射击游戏", 15.00, 4, 10, True)
        )
        await session.commit()
        print("✅ 创建示例应用: 太空探险、星际战争")

        # 创建测试运营商
        operator_sql = """
        INSERT INTO operator_accounts
        (username, full_name, phone, email, password_hash, api_key, api_key_hash, balance, customer_tier)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (username) DO NOTHING
        RETURNING id;
        """
        api_key = secrets.token_urlsafe(48)
        api_key_hash = pwd_context.hash(api_key)
        operator_password = pwd_context.hash("operator123")

        result = await session.execute(
            operator_sql,
            (
                "test_operator",
                "测试运营商",
                "13800138000",
                "test@example.com",
                operator_password,
                api_key,
                api_key_hash,
                1000.00,  # 初始余额1000元
                "standard"
            )
        )
        await session.commit()

        print(f"✅ 创建测试运营商: test_operator / operator123")
        print(f"   API Key: {api_key}")
        print(f"   初始余额: 1000.00元")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_data())
```

运行种子数据脚本：

```bash
python scripts/seed_data.py
```

### 3.4 验证数据库

```bash
# 连接数据库
docker exec -it mr-game-postgres psql -U postgres -d mr_game_system

# 查看所有表
\dt

# 查看管理员账户
SELECT username, full_name, role FROM admin_accounts;

# 查看应用列表
SELECT app_code, app_name, price_per_player FROM applications;

# 查看运营商账户
SELECT username, full_name, balance, customer_tier FROM operator_accounts;

# 退出
\q
```

**预期输出**:
- 14个表已创建
- 1个管理员账户 (admin)
- 2个示例应用 (太空探险, 星际战争)
- 1个测试运营商 (test_operator, 余额1000元)

---

## 第四步：启动API服务 (5分钟)

### 4.1 创建FastAPI应用入口

创建 `backend/src/main.py` 文件：

```python
"""FastAPI应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from src.core.config import settings
from src.db.session import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库连接池
    await init_db()
    yield
    # 关闭时清理资源

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查端点
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

# 根路径
@app.get("/")
async def root():
    return {
        "message": "MR游戏运营管理系统API",
        "version": settings.APP_VERSION,
        "docs_url": "/docs"
    }

# TODO: 引入路由模块
# from src.api.v1 import auth, operators, admin, finance
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
# app.include_router(operators.router, prefix="/api/v1/operators", tags=["运营商"])
# app.include_router(admin.router, prefix="/api/v1/admin", tags=["管理员"])
# app.include_router(finance.router, prefix="/api/v1/finance", tags=["财务"])

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
```

创建配置文件 `backend/src/core/config.py`：

```python
"""应用配置"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "MR游戏运营管理系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # 数据库配置
    DATABASE_URL: str

    # Redis配置
    REDIS_URL: str

    # JWT配置
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200

    # API Key配置
    API_KEY_LENGTH: int = 64

    # 业务配置
    LOW_BALANCE_THRESHOLD: float = 100.00
    RATE_LIMIT_PER_MINUTE: int = 10
    HMAC_SIGNATURE_EXPIRE_SECONDS: int = 300

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

创建数据库会话管理 `backend/src/db/session.py`：

```python
"""数据库会话管理"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """初始化数据库连接池"""
    pass

async def get_db():
    """获取数据库会话 (依赖注入)"""
    async with async_session() as session:
        yield session
```

### 4.2 启动FastAPI开发服务器

```bash
# 确保在backend目录且虚拟环境已激活
cd backend

# 启动服务 (自动重载模式)
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**预期输出**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 4.3 验证API服务

在浏览器或使用curl测试：

```bash
# 测试健康检查
curl http://localhost:8000/health

# 预期输出:
# {"status":"ok","service":"MR游戏运营管理系统","version":"1.0.0"}
```

### 4.4 查看API文档

在浏览器访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**预期看到**:
- API文档交互界面
- 健康检查端点
- 根路径端点

---

## 第五步：测试游戏授权流程 (10分钟)

### 5.1 准备测试工具

使用Postman或创建测试脚本 `backend/tests/test_authorization.py`：

```python
"""游戏授权流程测试脚本"""
import httpx
import hmac
import hashlib
import base64
import time
import json
from uuid import uuid4

# ============================================
# 配置信息 (从种子数据获取)
# ============================================
API_BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key-from-seed-data"  # 替换为实际API Key
OPERATOR_ID = "your-operator-id"  # 替换为实际运营商ID
SITE_ID = "your-site-id"  # 需要先创建运营点

# ============================================
# HMAC签名生成函数
# ============================================
def generate_hmac_signature(api_key: str, method: str, path: str, body: dict, timestamp: int) -> str:
    """
    生成HMAC-SHA256签名

    签名消息格式:
    {timestamp}\\n{method}\\n{path}\\n{body_json}
    """
    body_json = json.dumps(body, separators=(',', ':')) if body else ""
    message = f"{timestamp}\n{method}\n{path}\n{body_json}"

    signature = hmac.new(
        api_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()

    return base64.b64encode(signature).decode('utf-8')

# ============================================
# 1. 创建运营点 (需要先实现运营商登录和运营点创建接口)
# ============================================
async def create_operation_site():
    """创建测试运营点"""
    # TODO: 实现运营商登录获取JWT token
    # TODO: 调用创建运营点接口
    print("⏭️  跳过 - 需要先实现运营点创建接口")
    return "mock-site-id"

# ============================================
# 2. 管理员授权应用给运营商 (需要先实现管理员接口)
# ============================================
async def admin_authorize_app():
    """管理员授权应用"""
    # TODO: 实现管理员授权接口
    print("⏭️  跳过 - 需要先实现管理员授权接口")

# ============================================
# 3. 发起游戏授权请求 (核心测试)
# ============================================
async def test_game_authorization():
    """测试游戏授权流程"""
    print("\n========================================")
    print("测试游戏授权流程")
    print("========================================\n")

    # 生成会话ID (格式: {operatorId}_{timestamp}_{random})
    session_id = f"{OPERATOR_ID}_{int(time.time())}_{uuid4().hex[:16]}"

    # 请求参数
    method = "POST"
    path = "/api/v1/auth/authorize"
    timestamp = int(time.time())

    body = {
        "app_code": "space_adventure",
        "player_count": 5,
        "session_id": session_id,
        "site_id": SITE_ID
    }

    # 生成HMAC签名
    signature = generate_hmac_signature(API_KEY, method, path, body, timestamp)

    # 发送请求
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": API_KEY,
        "X-Signature": signature,
        "X-Timestamp": str(timestamp),
        "X-Session-ID": session_id
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}{path}",
                json=body,
                headers=headers
            )

            print(f"状态码: {response.status_code}")
            print(f"响应体: {response.json()}\n")

            if response.status_code == 200:
                data = response.json()
                print("✅ 授权成功!")
                print(f"   授权Token: {data['authorization_token']}")
                print(f"   扣费金额: {data['total_cost']}元")
                print(f"   剩余余额: {data['remaining_balance']}元")
            else:
                print(f"❌ 授权失败: {response.json()}")

        except httpx.RequestError as e:
            print(f"❌ 请求失败: {e}")

# ============================================
# 4. 验证余额扣减和使用记录
# ============================================
async def verify_billing():
    """验证计费结果"""
    # TODO: 查询运营商余额和使用记录
    print("⏭️  跳过 - 需要先实现查询接口")

if __name__ == "__main__":
    import asyncio

    print("=" * 50)
    print("MR游戏授权流程完整测试")
    print("=" * 50)

    # 执行测试
    asyncio.run(test_game_authorization())
```

### 5.2 HMAC签名生成示例

**当前状态**: API授权接口尚未实现，以下为接口实现后的测试步骤。

完整的HMAC签名生成示例见附录D。

### 5.3 预期授权流程 (待接口实现后测试)

1. **头显Server发起授权请求**:
   - 携带API Key、HMAC签名、时间戳、会话ID
   - 请求体包含应用代码、玩家数量、运营点ID

2. **系统验证流程**:
   - ✅ 验证API Key有效性
   - ✅ 验证HMAC签名正确性
   - ✅ 验证时间戳在5分钟内
   - ✅ 验证运营商对应用的授权状态
   - ✅ 验证玩家数量在应用允许范围内
   - ✅ 验证账户余额充足

3. **扣费和授权**:
   - 计算费用: 5人 × 10元/人 = 50元
   - 扣减余额: 1000元 - 50元 = 950元
   - 创建使用记录
   - 创建消费交易记录
   - 返回授权Token

4. **验证结果**:
   - 查询运营商余额: 950元
   - 查询使用记录: 1条新记录
   - 查询交易记录: 1条消费记录

### 5.4 幂等性测试

使用相同的 `session_id` 重复请求：

```bash
# 预期行为: 返回已存在的授权信息，不重复扣费
```

### 5.5 余额不足测试

修改请求玩家数量为 100 人（需要1000元，超过余额）：

```bash
# 预期响应:
# {
#   "error_code": "INSUFFICIENT_BALANCE",
#   "message": "账户余额不足，需要1000.00元，当前余额950.00元"
# }
```

---

## 常见问题排查

### 数据库连接失败

**症状**: `psycopg2.OperationalError: could not connect to server`

**解决方案**:
```bash
# 1. 检查容器是否运行
docker compose ps

# 2. 检查PostgreSQL日志
docker compose logs postgres

# 3. 验证端口映射
docker compose port postgres 5432

# 4. 测试连接
docker exec -it mr-game-postgres psql -U postgres -d mr_game_system

# 5. 如果端口冲突，修改docker-compose.yml中的端口映射
ports:
  - "5433:5432"  # 使用5433端口避免冲突
```

### Redis连接失败

**症状**: `redis.exceptions.ConnectionError: Error connecting to Redis`

**解决方案**:
```bash
# 1. 检查容器运行状态
docker compose ps redis

# 2. 验证Redis密码
docker exec -it mr-game-redis redis-cli -a redis123 PING

# 3. 检查.env中的REDIS_URL配置
REDIS_URL=redis://:redis123@localhost:6379/0
```

### 端口冲突

**症状**: `Error starting userland proxy: listen tcp4 0.0.0.0:5432: bind: address already in use`

**解决方案**:
```bash
# Windows - 查找占用端口的进程
netstat -ano | findstr :5432
taskkill /PID <进程ID> /F

# macOS/Linux - 查找并杀死进程
lsof -i :5432
kill -9 <进程ID>

# 或修改docker-compose.yml使用其他端口
ports:
  - "5433:5432"  # PostgreSQL
  - "6380:6379"  # Redis
```

### HMAC签名验证失败

**症状**: `{"error_code": "INVALID_SIGNATURE", "message": "签名验证失败"}`

**常见原因**:
1. **时间戳过期**: 确保客户端和服务器时间同步（误差<5分钟）
2. **签名消息格式错误**: 严格按照 `{timestamp}\n{method}\n{path}\n{body}` 格式
3. **API Key错误**: 使用正确的64位API Key
4. **JSON序列化差异**: 确保请求体JSON格式一致（无空格、字段顺序）

**调试步骤**:
```python
# 在服务端和客户端分别打印签名消息
print(f"签名消息:\n{message}")
print(f"生成签名: {signature}")

# 对比两端输出是否完全一致
```

### Docker内存不足

**症状**: 容器频繁重启或OOM错误

**解决方案**:
```bash
# 1. 检查Docker资源限制
docker stats

# 2. 在Docker Desktop中调整内存限制
# Settings → Resources → Memory (建议≥4GB)

# 3. 清理未使用的容器和镜像
docker system prune -a
```

### Alembic迁移失败

**症状**: `alembic.util.exc.CommandError: Target database is not up to date`

**解决方案**:
```bash
# 1. 查看当前迁移版本
alembic current

# 2. 查看迁移历史
alembic history

# 3. 回滚到特定版本
alembic downgrade <version>

# 4. 重新迁移
alembic upgrade head

# 5. 如果数据库损坏，重建数据库
docker compose down -v
docker compose up -d postgres
alembic upgrade head
```

---

## 下一步

恭喜完成本地环境搭建！接下来您可以：

### 1. 深入学习系统架构

- 📖 阅读 [数据模型文档](./data-model.md) - 了解14个核心实体和关系
- 📖 查看 [API契约文档](./contracts/CONTRACT_SUMMARY.md) - 查看60个接口定义
- 📖 研究 [实施计划](./plan.md) - 了解技术选型和开发规划

### 2. 开发和测试

- ✍️ 实现核心业务接口 (参考 `tasks.md` - 需先运行 `/speckit.tasks` 生成)
- 🧪 编写单元测试和集成测试
- 📝 完善API文档和代码注释

### 3. 运行测试套件

```bash
# 运行所有测试
cd backend
pytest

# 运行契约测试
pytest tests/contract/

# 运行集成测试
pytest tests/integration/

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 4. 搭建前端开发环境

```bash
# 创建前端项目 (使用Vue 3 + Vite示例)
npm create vite@latest frontend -- --template vue-ts
cd frontend
npm install

# 安装UI框架 (Element Plus示例)
npm install element-plus
npm install @element-plus/icons-vue

# 安装HTTP客户端和状态管理
npm install axios pinia
npm install vue-router@4

# 启动开发服务器
npm run dev
```

### 5. 集成支付平台 (测试环境)

- 申请微信支付和支付宝测试账号
- 配置支付回调URL (使用ngrok或本地测试工具)
- 实现支付回调处理逻辑

### 6. 部署到生产环境

- 配置生产环境变量 (修改SECRET_KEY、数据库密码等)
- 使用Gunicorn + Nginx部署FastAPI
- 配置SSL证书 (Let's Encrypt)
- 设置监控和告警 (Prometheus + Grafana)

---

## 附录

### 附录A：完整的docker-compose.yml示例

```yaml
version: '3.8'

services:
  # PostgreSQL数据库
  postgres:
    image: postgres:14-alpine
    container_name: mr-game-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres123
      POSTGRES_DB: mr_game_system
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --lc-collate=C --lc-ctype=C"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      # 初始化脚本 (可选)
      - ./backend/scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - mr-game-network

  # Redis缓存
  redis:
    image: redis:7-alpine
    container_name: mr-game-redis
    command: redis-server --requirepass redis123 --appendonly yes
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "redis123", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - mr-game-network

  # pgAdmin (可选 - 数据库管理界面)
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: mr-game-pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin123
      PGADMIN_CONFIG_SERVER_MODE: 'False'
    ports:
      - "5050:80"
    volumes:
      - pgadmin_data:/var/lib/pgadmin
    depends_on:
      - postgres
    restart: unless-stopped
    networks:
      - mr-game-network

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  pgadmin_data:
    driver: local

networks:
  mr-game-network:
    driver: bridge
```

**使用pgAdmin**: 访问 http://localhost:5050，登录后添加服务器：
- Host: postgres
- Port: 5432
- Username: postgres
- Password: postgres123

### 附录B：.env文件完整配置参考

见"第一步 → 1.3 配置环境变量"章节。

### 附录C：测试数据SQL脚本

```sql
-- ============================================
-- 测试数据SQL脚本
-- 执行前确保已运行Alembic迁移创建表结构
-- ============================================

-- 1. 创建超级管理员
INSERT INTO admin_accounts (id, username, full_name, email, password_hash, role, is_active)
VALUES (
  gen_random_uuid(),
  'admin',
  '系统管理员',
  'admin@example.com',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqP.fODZRm',  -- 密码: admin123
  'super_admin',
  true
)
ON CONFLICT (username) DO NOTHING;

-- 2. 创建示例应用
INSERT INTO applications (id, app_code, app_name, description, price_per_player, min_players, max_players, is_active)
VALUES
(
  gen_random_uuid(),
  'space_adventure',
  '太空探险',
  '沉浸式太空探索VR游戏，支持2-8人联机协作',
  10.00,
  2,
  8,
  true
),
(
  gen_random_uuid(),
  'galaxy_war',
  '星际战争',
  '多人协作射击游戏，支持4-10人团队对抗',
  15.00,
  4,
  10,
  true
)
ON CONFLICT (app_code) DO NOTHING;

-- 3. 创建测试运营商
-- 注意: API Key和密码哈希需要实际生成
INSERT INTO operator_accounts (
  id, username, full_name, phone, email,
  password_hash, api_key, api_key_hash,
  balance, customer_tier, is_active
)
VALUES (
  gen_random_uuid(),
  'test_operator',
  '测试运营商',
  '13800138000',
  'test@example.com',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqP.fODZRm',  -- 密码: operator123
  'your-generated-api-key-64-chars',  -- 替换为实际生成的API Key
  '$2b$12$...',  -- 替换为API Key的bcrypt哈希
  1000.00,
  'standard',
  true
)
ON CONFLICT (username) DO NOTHING;

-- 4. 为测试运营商创建运营点
INSERT INTO operation_sites (id, operator_id, name, address, contact_person, contact_phone, is_active)
VALUES (
  gen_random_uuid(),
  (SELECT id FROM operator_accounts WHERE username = 'test_operator'),
  '测试运营点',
  '北京市朝阳区测试大街123号',
  '张三',
  '13900139000',
  true
);

-- 5. 管理员授权应用给运营商
INSERT INTO operator_app_authorizations (
  id, operator_id, application_id, authorized_by, is_active
)
VALUES (
  gen_random_uuid(),
  (SELECT id FROM operator_accounts WHERE username = 'test_operator'),
  (SELECT id FROM applications WHERE app_code = 'space_adventure'),
  (SELECT id FROM admin_accounts WHERE username = 'admin'),
  true
);

-- 验证数据
SELECT 'Admin accounts:' as table_name, COUNT(*) as count FROM admin_accounts
UNION ALL
SELECT 'Applications:', COUNT(*) FROM applications
UNION ALL
SELECT 'Operator accounts:', COUNT(*) FROM operator_accounts
UNION ALL
SELECT 'Operation sites:', COUNT(*) FROM operation_sites
UNION ALL
SELECT 'App authorizations:', COUNT(*) FROM operator_app_authorizations;
```

### 附录D：HMAC签名生成示例

#### Python示例

```python
import hmac
import hashlib
import base64
import json
import time

def generate_hmac_signature(
    api_key: str,
    method: str,
    path: str,
    body: dict | None,
    timestamp: int
) -> str:
    """
    生成HMAC-SHA256签名

    Args:
        api_key: 运营商API Key (64位)
        method: HTTP方法 (如 "POST")
        path: API路径 (如 "/api/v1/auth/authorize")
        body: 请求体字典 (如 {"app_code": "space_adventure", ...})
        timestamp: Unix时间戳 (秒)

    Returns:
        Base64编码的HMAC签名
    """
    # 构建签名消息
    body_json = json.dumps(body, separators=(',', ':')) if body else ""
    message = f"{timestamp}\n{method}\n{path}\n{body_json}"

    # 计算HMAC-SHA256签名
    signature = hmac.new(
        api_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()

    # Base64编码
    return base64.b64encode(signature).decode('utf-8')

# 使用示例
if __name__ == "__main__":
    api_key = "your-64-char-api-key-here"
    method = "POST"
    path = "/api/v1/auth/authorize"
    timestamp = int(time.time())

    body = {
        "app_code": "space_adventure",
        "player_count": 5,
        "session_id": "550e8400_1728540000_a1b2c3d4",
        "site_id": "660e8400-e29b-41d4-a716-446655440001"
    }

    signature = generate_hmac_signature(api_key, method, path, body, timestamp)

    print("请求头:")
    print(f"  X-Api-Key: {api_key}")
    print(f"  X-Signature: {signature}")
    print(f"  X-Timestamp: {timestamp}")
    print(f"  X-Session-ID: {body['session_id']}")
```

#### Node.js示例

```javascript
const crypto = require('crypto');

function generateHmacSignature(apiKey, method, path, body, timestamp) {
  /**
   * 生成HMAC-SHA256签名
   *
   * @param {string} apiKey - 运营商API Key (64位)
   * @param {string} method - HTTP方法 (如 "POST")
   * @param {string} path - API路径
   * @param {object|null} body - 请求体对象
   * @param {number} timestamp - Unix时间戳 (秒)
   * @returns {string} Base64编码的HMAC签名
   */

  // 构建签名消息
  const bodyJson = body ? JSON.stringify(body) : "";
  const message = `${timestamp}\n${method}\n${path}\n${bodyJson}`;

  // 计算HMAC-SHA256签名
  const hmac = crypto.createHmac('sha256', apiKey);
  hmac.update(message);

  // Base64编码
  return hmac.digest('base64');
}

// 使用示例
const apiKey = "your-64-char-api-key-here";
const method = "POST";
const path = "/api/v1/auth/authorize";
const timestamp = Math.floor(Date.now() / 1000);

const body = {
  app_code: "space_adventure",
  player_count: 5,
  session_id: "550e8400_1728540000_a1b2c3d4",
  site_id: "660e8400-e29b-41d4-a716-446655440001"
};

const signature = generateHmacSignature(apiKey, method, path, body, timestamp);

console.log("请求头:");
console.log(`  X-Api-Key: ${apiKey}`);
console.log(`  X-Signature: ${signature}`);
console.log(`  X-Timestamp: ${timestamp}`);
console.log(`  X-Session-ID: ${body.session_id}`);
```

#### C#示例

```csharp
using System;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

public class HmacHelper
{
    /// <summary>
    /// 生成HMAC-SHA256签名
    /// </summary>
    /// <param name="apiKey">运营商API Key (64位)</param>
    /// <param name="method">HTTP方法 (如 "POST")</param>
    /// <param name="path">API路径</param>
    /// <param name="body">请求体对象</param>
    /// <param name="timestamp">Unix时间戳 (秒)</param>
    /// <returns>Base64编码的HMAC签名</returns>
    public static string GenerateHmacSignature(
        string apiKey,
        string method,
        string path,
        object body,
        long timestamp)
    {
        // 构建签名消息
        string bodyJson = body != null
            ? JsonSerializer.Serialize(body, new JsonSerializerOptions
            {
                WriteIndented = false
            })
            : "";

        string message = $"{timestamp}\n{method}\n{path}\n{bodyJson}";

        // 计算HMAC-SHA256签名
        using (var hmac = new HMACSHA256(Encoding.UTF8.GetBytes(apiKey)))
        {
            byte[] hash = hmac.ComputeHash(Encoding.UTF8.GetBytes(message));
            return Convert.ToBase64String(hash);
        }
    }
}

// 使用示例
class Program
{
    static void Main()
    {
        string apiKey = "your-64-char-api-key-here";
        string method = "POST";
        string path = "/api/v1/auth/authorize";
        long timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds();

        var body = new
        {
            app_code = "space_adventure",
            player_count = 5,
            session_id = "550e8400_1728540000_a1b2c3d4",
            site_id = "660e8400-e29b-41d4-a716-446655440001"
        };

        string signature = HmacHelper.GenerateHmacSignature(
            apiKey, method, path, body, timestamp
        );

        Console.WriteLine("请求头:");
        Console.WriteLine($"  X-Api-Key: {apiKey}");
        Console.WriteLine($"  X-Signature: {signature}");
        Console.WriteLine($"  X-Timestamp: {timestamp}");
        Console.WriteLine($"  X-Session-ID: {body.session_id}");
    }
}
```

### 附录E：常用命令速查表

```bash
# ============================================
# Docker命令
# ============================================
# 启动所有容器
docker compose up -d

# 查看容器状态
docker compose ps

# 查看容器日志
docker compose logs -f [service_name]

# 停止所有容器
docker compose down

# 停止并删除数据卷 (⚠️ 会删除数据库数据)
docker compose down -v

# 重启单个服务
docker compose restart postgres

# 进入容器shell
docker exec -it mr-game-postgres bash

# ============================================
# 数据库命令
# ============================================
# 连接PostgreSQL
docker exec -it mr-game-postgres psql -U postgres -d mr_game_system

# 导出数据库
docker exec -it mr-game-postgres pg_dump -U postgres mr_game_system > backup.sql

# 导入数据库
docker exec -i mr-game-postgres psql -U postgres -d mr_game_system < backup.sql

# ============================================
# Alembic命令
# ============================================
# 创建迁移脚本
alembic revision -m "description"

# 应用迁移
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 查看当前版本
alembic current

# 查看迁移历史
alembic history

# ============================================
# Python/FastAPI命令
# ============================================
# 启动开发服务器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 运行测试
pytest

# 运行测试并生成覆盖率
pytest --cov=src --cov-report=html

# 代码格式化
black src/
ruff check src/ --fix

# 类型检查
mypy src/

# ============================================
# Redis命令
# ============================================
# 连接Redis
docker exec -it mr-game-redis redis-cli -a redis123

# 查看所有键
KEYS *

# 获取键值
GET key_name

# 删除键
DEL key_name

# 清空当前数据库
FLUSHDB

# ============================================
# 其他工具命令
# ============================================
# 生成随机密钥 (用于SECRET_KEY)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 生成API Key (64位)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 生成密码哈希
python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your_password'))"
```

---

## 文档维护

**版本**: 1.0.0
**最后更新**: 2025-10-10
**维护者**: 开发团队

**变更日志**:
- 2025-10-10: 初始版本，覆盖本地环境搭建和基础测试流程

**反馈渠道**:
- 问题反馈: https://github.com/your-org/mr-game-system/issues
- 技术支持: dev-support@example.com
- 文档改进建议: docs@example.com

---

**祝您开发顺利！** 如有任何问题，请参考本文档"常见问题排查"章节或联系技术支持团队。
