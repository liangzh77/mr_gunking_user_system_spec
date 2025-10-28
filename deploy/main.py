from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import uvicorn
import asyncpg
import redis
import json
from datetime import datetime, timedelta
import secrets
import os
from enum import Enum

app = FastAPI(
    title="MR游戏运营管理系统",
    version="1.0.0",
    description="MR游戏运营管理系统 - 生产环境"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://121.41.231.69", "http://localhost", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
db_pool = None
redis_client = None
security = HTTPBearer()

# 枚举定义
class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    FINANCE = "finance"
    OPERATOR = "operator"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"

# 数据模型
class AdminLogin(BaseModel):
    username: str
    password: str

class AdminResponse(BaseModel):
    id: str
    username: str
    role: UserRole
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None

class OperatorCreate(BaseModel):
    username: str
    password: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str = "operator"

class UserProfile(BaseModel):
    id: str
    username: str
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    balance: float
    created_at: datetime

class RechargeRequest(BaseModel):
    user_id: str
    amount: float
    payment_method: str
    remark: Optional[str] = None

class SiteInfo(BaseModel):
    id: str
    name: str
    identifier: str
    server_ip: str
    player_count: int
    revenue_today: float
    status: str

# 数据库连接
async def get_db():
    global db_pool
    if db_pool is None:
        try:
            db_pool = await asyncpg.create_pool(
                "postgresql://mr_admin_prod:ProdSecure2024!@localhost/mr_game_ops_prod",
                min_size=5,
                max_size=20
            )
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return None
    return db_pool

# Redis连接
def get_redis():
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        except Exception as e:
            print(f"Redis连接失败: {e}")
            return None
    return redis_client

# 健康检查
@app.get("/")
async def root():
    return {
        "message": "MR游戏运营管理系统 - 生产环境",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "server": "121.41.231.69"
    }

@app.get("/health")
async def health_check():
    db_status = "disconnected"
    redis_status = "disconnected"

    try:
        # 测试数据库连接
        pool = await get_db()
        if pool:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                db_status = "connected"
    except Exception as e:
        print(f"数据库健康检查失败: {e}")

    try:
        # 测试Redis连接
        redis_conn = get_redis()
        if redis_conn:
            redis_conn.ping()
            redis_status = "connected"
    except Exception as e:
        print(f"Redis健康检查失败: {e}")

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "redis": redis_status,
        "timestamp": datetime.now().isoformat(),
        "uptime": "运行中"
    }

# 管理员认证
@app.post("/api/v1/admin/login")
async def admin_login(login_data: AdminLogin):
    # 模拟管理员验证（生产环境应连接数据库）
    if login_data.username == "admin" and login_data.password == "AdminSecure123!2024":
        return {
            "access_token": "mock_jwt_token_" + secrets.token_urlsafe(32),
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": "admin-001",
                "username": "admin",
                "role": "super_admin",
                "full_name": "系统管理员",
                "email": "admin@mr-game.com",
                "permissions": ["*"]
            }
        }
    elif login_data.username == "finance" and login_data.password == "Finance123!2024":
        return {
            "access_token": "mock_jwt_token_" + secrets.token_urlsafe(32),
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": "finance-001",
                "username": "finance",
                "role": "finance",
                "full_name": "财务管理员",
                "email": "finance@mr-game.com",
                "permissions": ["finance", "reports"]
            }
        }

    raise HTTPException(status_code=401, detail="用户名或密码错误")

@app.get("/api/v1/admin/profile")
async def admin_profile(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return {
        "id": "admin-001",
        "username": "admin",
        "role": "super_admin",
        "full_name": "系统管理员",
        "email": "admin@mr-game.com",
        "phone": "13800138000",
        "permissions": ["*"],
        "last_login": datetime.now().isoformat()
    }

# 仪表板数据
@app.get("/api/v1/admin/dashboard")
async def admin_dashboard():
    return {
        "overview": {
            "total_users": 1245,
            "active_users": 892,
            "total_revenue": 125680.50,
            "today_revenue": 3456.80,
            "total_sites": 8,
            "active_sites": 6
        },
        "charts": {
            "daily_revenue": [1200, 1450, 1800, 2200, 2800, 3456],
            "user_growth": [100, 150, 200, 280, 350, 420],
            "site_performance": [
                {"name": "站点1", "revenue": 1250, "users": 45},
                {"name": "站点2", "revenue": 980, "users": 38},
                {"name": "站点3", "revenue": 756, "users": 28}
            ]
        },
        "recent_activities": [
            {"id": 1, "type": "user_register", "user": "player001", "time": "2024-01-20 10:30:00", "amount": None},
            {"id": 2, "type": "recharge", "user": "player002", "amount": 100.0, "time": "2024-01-20 10:25:00"},
            {"id": 3, "type": "withdraw", "user": "player003", "amount": 50.0, "time": "2024-01-20 10:20:00"},
            {"id": 4, "type": "user_login", "user": "player004", "time": "2024-01-20 10:15:00", "amount": None}
        ],
        "alerts": [
            {"type": "warning", "message": "站点3响应时间过长", "time": "10分钟前"},
            {"type": "info", "message": "今日充值目标已完成80%", "time": "30分钟前"}
        ]
    }

# 用户管理
@app.get("/api/v1/admin/users")
async def get_users(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    mock_users = [
        {
            "id": f"user_{i:03d}",
            "username": f"player{i:03d}",
            "full_name": f"玩家{i:03d}",
            "email": f"player{i:03d}@example.com",
            "phone": f"138{10000000 + i}",
            "balance": round(1000.0 + (i * 123.45), 2),
            "status": "active" if i % 10 != 0 else "banned",
            "created_at": "2024-01-15 10:30:00",
            "last_login": "2024-01-20 09:45:00"
        }
        for i in range(1, 51)
    ]

    if search:
        mock_users = [u for u in mock_users if search.lower() in u["username"].lower()]

    start = (page - 1) * limit
    end = start + limit

    return {
        "data": mock_users[start:end],
        "total": len(mock_users),
        "page": page,
        "limit": limit,
        "pages": (len(mock_users) + limit - 1) // limit
    }

@app.post("/api/v1/admin/users")
async def create_user(user_data: dict, credentials: HTTPAuthorizationCredentials = Depends(security)):
    new_user = {
        "id": f"user_{secrets.randbelow(9999):04d}",
        "username": user_data.get("username"),
        "full_name": user_data.get("full_name"),
        "email": user_data.get("email"),
        "phone": user_data.get("phone"),
        "balance": 0.0,
        "status": "active",
        "created_at": datetime.now().isoformat()
    }
    return {"message": "用户创建成功", "user": new_user}

# 运营站点管理
@app.get("/api/v1/admin/sites")
async def get_sites(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return {
        "data": [
            {
                "id": "site_001",
                "name": "MR游戏主站",
                "identifier": "mr-main-server",
                "server_ip": "192.168.1.10",
                "player_count": 245,
                "revenue_today": 3456.80,
                "status": "online",
                "cpu_usage": 45.2,
                "memory_usage": 68.5,
                "last_update": datetime.now().isoformat()
            },
            {
                "id": "site_002",
                "name": "MR游戏备用站",
                "identifier": "mr-backup-server",
                "server_ip": "192.168.1.11",
                "player_count": 156,
                "revenue_today": 2234.50,
                "status": "online",
                "cpu_usage": 32.8,
                "memory_usage": 54.3,
                "last_update": datetime.now().isoformat()
            },
            {
                "id": "site_003",
                "name": "MR游戏测试站",
                "identifier": "mr-test-server",
                "server_ip": "192.168.1.12",
                "player_count": 23,
                "revenue_today": 123.00,
                "status": "maintenance",
                "cpu_usage": 15.6,
                "memory_usage": 28.9,
                "last_update": datetime.now().isoformat()
            }
        ],
        "total": 3,
        "online": 2,
        "maintenance": 1
    }

@app.post("/api/v1/admin/sites")
async def create_site(site_data: dict, credentials: HTTPAuthorizationCredentials = Depends(security)):
    new_site = {
        "id": f"site_{secrets.randbelow(9999):03d}",
        "name": site_data.get("name"),
        "identifier": site_data.get("identifier"),
        "server_ip": site_data.get("server_ip"),
        "player_count": 0,
        "revenue_today": 0.0,
        "status": "offline",
        "created_at": datetime.now().isoformat()
    }
    return {"message": "站点创建成功", "site": new_site}

# 财务管理
@app.get("/api/v1/admin/finance/overview")
async def get_finance_overview(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return {
        "summary": {
            "total_balance": 456789.12,
            "today_revenue": 3456.80,
            "today_expenses": 1234.50,
            "pending_refunds": 2345.00,
            "monthly_revenue": 85670.45,
            "monthly_expenses": 34210.30
        },
        "transactions": [
            {
                "id": "txn_001",
                "type": "recharge",
                "user": "player001",
                "amount": 100.00,
                "status": "success",
                "method": "alipay",
                "time": "2024-01-20 10:30:00"
            },
            {
                "id": "txn_002",
                "type": "withdraw",
                "user": "player002",
                "amount": 50.00,
                "status": "pending",
                "method": "bank_card",
                "time": "2024-01-20 10:25:00"
            }
        ]
    }

@app.get("/api/v1/admin/finance/reports")
async def get_finance_reports(
    start_date: str = None,
    end_date: str = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    return {
        "revenue_chart": [
            {"date": "2024-01-15", "amount": 2456.30},
            {"date": "2024-01-16", "amount": 2890.45},
            {"date": "2024-01-17", "amount": 3124.80},
            {"date": "2024-01-18", "amount": 2987.60},
            {"date": "2024-01-19", "amount": 3567.90},
            {"date": "2024-01-20", "amount": 3456.80}
        ],
        "payment_methods": [
            {"method": "alipay", "amount": 15678.90, "count": 245},
            {"method": "wechat", "amount": 12345.60, "count": 189},
            {"method": "bank_card", "amount": 8765.40, "count": 67}
        ],
        "top_users": [
            {"username": "player001", "total_amount": 2345.60, "transaction_count": 15},
            {"username": "player002", "total_amount": 1987.30, "transaction_count": 12},
            {"username": "player003", "total_amount": 1654.80, "transaction_count": 8}
        ]
    }

# 统计分析
@app.get("/api/v1/admin/statistics")
async def get_statistics(
    period: str = "today",
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    return {
        "user_stats": {
            "total_users": 1245,
            "new_users": 23,
            "active_users": 892,
            "online_users": 456
        },
        "revenue_stats": {
            "total_revenue": 125680.50,
            "today_revenue": 3456.80,
            "avg_revenue_per_user": 100.93,
            "conversion_rate": 23.5
        },
        "game_stats": {
            "total_games": 15,
            "active_games": 12,
            "popular_games": [
                {"name": "德州扑克", "players": 156},
                {"name": "百家乐", "players": 134},
                {"name": "轮盘", "players": 89}
            ]
        }
    }

# 系统设置
@app.get("/api/v1/admin/settings")
async def get_settings(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return {
        "system": {
            "site_name": "MR游戏运营管理系统",
            "version": "1.0.0",
            "timezone": "Asia/Shanghai",
            "maintenance_mode": False
        },
        "security": {
            "password_policy": "strong",
            "session_timeout": 3600,
            "max_login_attempts": 5,
            "two_factor_auth": False
        },
        "notifications": {
            "email_enabled": True,
            "sms_enabled": True,
            "admin_alerts": True
        }
    }

@app.post("/api/v1/admin/settings")
async def update_settings(settings_data: dict, credentials: HTTPAuthorizationCredentials = Depends(security)):
    return {"message": "设置更新成功"}

# API文档和测试页面
@app.get("/docs", response_class=HTMLResponse)
async def custom_docs():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MR游戏管理系统 - API文档</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; text-align: center; }
            .api-list { margin: 20px 0; }
            .api-item { padding: 15px; margin: 10px 0; background: #ecf0f1; border-radius: 5px; border-left: 4px solid #3498db; }
            .method { font-weight: bold; color: #27ae60; }
            .endpoint { font-family: monospace; background: #2c3e50; color: white; padding: 2px 6px; border-radius: 3px; }
            a { color: #3498db; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎮 MR游戏运营管理系统</h1>
            <p><strong>版本:</strong> 1.0.0 | <strong>状态:</strong> 🟢 运行中</p>
            <p><strong>服务器:</strong> 121.41.231.69 | <strong>时间:</strong> """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>

            <h2>🚀 主要API端点</h2>
            <div class="api-list">
                <div class="api-item">
                    <span class="method">GET</span> <span class="endpoint">/</span> - 系统状态
                </div>
                <div class="api-item">
                    <span class="method">GET</span> <span class="endpoint">/health</span> - 健康检查
                </div>
                <div class="api-item">
                    <span class="method">POST</span> <span class="endpoint">/api/v1/admin/login</span> - 管理员登录
                </div>
                <div class="api-item">
                    <span class="method">GET</span> <span class="endpoint">/api/v1/admin/dashboard</span> - 仪表板数据
                </div>
                <div class="api-item">
                    <span class="method">GET</span> <span class="endpoint">/api/v1/admin/users</span> - 用户管理
                </div>
                <div class="api-item">
                    <span class="method">GET</span> <span class="endpoint">/api/v1/admin/sites</span> - 站点管理
                </div>
                <div class="api-item">
                    <span class="method">GET</span> <span class="endpoint">/api/v1/admin/finance/overview</span> - 财务概览
                </div>
                <div class="api-item">
                    <span class="method">GET</span> <span class="endpoint">/api/v1/admin/statistics</span> - 统计分析
                </div>
            </div>

            <h2>🔑 测试账号</h2>
            <div class="api-item">
                <strong>超级管理员:</strong> admin / AdminSecure123!2024
            </div>
            <div class="api-item">
                <strong>财务管理员:</strong> finance / Finance123!2024
            </div>

            <h2>📱 前端访问</h2>
            <div class="api-item">
                <a href="http://121.41.231.69" target="_blank">🌐 访问前端界面</a>
            </div>
        </div>
    </body>
    </html>
    """

# 启动事件
@app.on_event("startup")
async def startup_event():
    print("🎮 MR游戏运营管理系统启动成功！")
    print("🌐 访问地址: http://121.41.231.69")
    print("📚 API文档: http://121.41.231.69/docs")
    print("🔍 健康检查: http://121.41.231.69/health")
    print("👤 管理员账号: admin / AdminSecure123!2024")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )