# MR游戏运营管理系统

**游戏授权计费平台** - 为MR/VR游戏运营商提供实时授权、按玩家数计费、财务管理的综合平台

## 项目概述

MR游戏运营管理系统是一个专为游戏运营商设计的授权和计费平台。系统支持:

- **实时游戏授权**: 头显Server请求游戏启动授权，系统验证权限、扣费并返回授权Token
- **按玩家数计费**: 根据游戏玩家数量实时计算费用，支持并发扣费和幂等性保证
- **运营商自助管理**: 在线充值、余额查询、交易记录、退款申请、发票开具
- **多维度统计分析**: 按运营点/应用/时间维度统计，可视化图表，数据导出
- **管理员后台**: 运营商管理、应用配置、价格调整、授权审批
- **财务与审计**: 收入概览、大客户分析、退款审核、审计日志

## 🚀 快速开始（Docker）

### 前置要求

- Docker Desktop 或 Docker Engine 20.10+
- Docker Compose V2
- 最小 4GB RAM

### 一键启动

```bash
# 克隆项目
git clone https://github.com/liangzh77/mr_gunking_user_system_spec.git
cd mr_gunking_user_system_spec

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 访问系统

- **管理后台**: http://localhost:5173/admin/login
  - 用户名: `admin`
  - 密码: `Admin@123456`
- **API 文档**: http://localhost:8000/api/docs
- **数据库管理**: http://localhost:5050

详细部署文档请查看: [Docker 部署指南](./docs/DOCKER_DEPLOYMENT.md)

## 技术栈

### 后端
- **语言**: Python 3.12
- **框架**: FastAPI 0.104+
- **数据库**: PostgreSQL 14 (Alpine)
- **缓存**: Redis 7 (Alpine)
- **ORM**: SQLAlchemy 2.0+ (Async)
- **认证**: JWT (python-jose)
- **密码哈希**: Bcrypt (10 rounds)
- **监控**: Prometheus Client

### 前端
- **框架**: Vue 3 + TypeScript
- **状态管理**: Pinia
- **UI组件库**: Element Plus
- **构建工具**: Vite 5

### 容器化
- **Docker**: 多阶段构建优化
- **镜像**: Alpine Linux (最小化)
- **编排**: Docker Compose V2

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- Git
- Redis 5.0+ (可选，推荐用于生产环境)

### 1. 克隆项目

```bash
git clone <repository-url>
cd mr_gunking_user_system_spec
```

### 2. 后端设置

#### 2.1 创建虚拟环境

```bash
cd backend
python -m venv .venv312

# Windows
.venv312\Scripts\activate

# Linux/Mac
source .venv312/bin/activate
```

#### 2.2 安装依赖

```bash
pip install -r requirements.txt
```

#### 2.3 初始化数据库

```bash
# 运行数据库迁移
alembic upgrade head

# 初始化数据（创建管理员账户和测试应用）
python init_data.py
```

执行成功后会看到：
```
管理员账户: admin / Admin123
应用数据: 3个测试游戏应用已创建
```

#### 2.4 配置 Redis (可选)

```bash
# 安装 Redis (Ubuntu/Debian)
sudo apt install redis-server

# 启动 Redis
redis-server

# 或使用 Docker
docker run -d -p 6379:6379 redis:7-alpine
```

**环境变量配置** (`.env`):
```bash
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=  # 生产环境设置密码
```

注：开发环境可不配置 Redis，系统会优雅降级到无缓存模式。

#### 2.5 启动后端服务

```bash
# 开发模式（热重载）
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. 前端设置

#### 3.1 安装依赖

```bash
cd frontend
npm install
```

#### 3.2 启动开发服务器

```bash
npm run dev
```

### 4. 访问系统

- **前端应用**: http://localhost:5173/
- **API 文档 (Swagger UI)**: http://localhost:8000/api/docs
- **API 文档 (ReDoc)**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json
- **健康检查**: http://localhost:8000/health
- **Prometheus 指标**: http://localhost:8000/metrics

### 5. 默认账户

**管理员账户**:
- 用户名: `admin`
- 密码: `Admin123`

**运营商账户**:
- 请通过前端注册页面自行注册：http://localhost:5173/operator/register

## 项目结构

```
.
├── backend/                  # 后端代码
│   ├── src/
│   │   ├── api/             # API路由
│   │   │   └── v1/
│   │   ├── models/          # SQLAlchemy ORM模型
│   │   ├── schemas/         # Pydantic数据模式
│   │   ├── services/        # 业务逻辑服务
│   │   ├── core/            # 核心功能 (配置、安全、日志)
│   │   ├── db/              # 数据库会话管理
│   │   └── main.py          # FastAPI应用入口
│   ├── tests/               # 测试
│   │   ├── contract/        # 契约测试 (API规范验证)
│   │   ├── integration/     # 集成测试
│   │   ├── unit/            # 单元测试
│   │   └── performance/     # 性能基准测试
│   ├── docs/                # 技术文档
│   │   ├── API_DOCUMENTATION.md       # API 参考文档
│   │   ├── OPENAPI_CUSTOMIZATION.md   # OpenAPI 定制指南
│   │   ├── HTTPS_DEPLOYMENT.md        # HTTPS 部署指南
│   │   └── ENCRYPTION_GUIDE.md        # 加密使用指南
│   ├── deployment/          # 部署配置
│   │   └── nginx.conf       # Nginx 反向代理配置
│   ├── alembic/             # 数据库迁移脚本
│   ├── scripts/             # 工具脚本 (种子数据等)
│   ├── pyproject.toml       # Poetry配置
│   ├── requirements.txt     # Pip依赖
│   ├── PERFORMANCE_OPTIMIZATION.md  # 性能优化记录
│   └── .env.example         # 环境变量模板
│
├── frontend/                # 前端代码 (Vue 3)
│   ├── src/
│   │   ├── pages/           # 页面组件
│   │   ├── components/      # 可复用组件
│   │   ├── stores/          # Pinia状态管理
│   │   ├── router/          # Vue Router配置
│   │   └── utils/           # 工具函数
│   └── package.json
│
├── sdk/                     # 客户端SDK
│   ├── python/              # Python SDK (头显Server集成)
│   ├── nodejs/              # Node.js SDK
│   └── csharp/              # C# SDK
│
├── docs/                    # 文档
│   └── api/                 # API文档导出
│
├── specs/                   # 功能规格文档
│   └── 001-mr/
│       ├── spec.md          # 功能规格
│       ├── plan.md          # 实施计划
│       ├── data-model.md    # 数据模型
│       ├── research.md      # 技术研究
│       ├── quickstart.md    # 快速入门指南
│       ├── tasks.md         # 任务分解
│       └── contracts/       # API契约定义
│
├── docker-compose.yml       # Docker编排配置
└── README.md                # 本文件
```

## 开发指南

### 运行测试

```bash
cd backend

# 运行所有测试
pytest

# 运行特定类型的测试
pytest -m unit           # 单元测试
pytest -m integration    # 集成测试
pytest -m contract       # 契约测试

# 查看测试覆盖率
pytest --cov-report=html
# 打开 htmlcov/index.html 查看详细报告
```

### 代码质量检查

```bash
cd backend

# 代码格式化
black src tests

# 代码检查
ruff check src tests

# 类型检查
mypy src
```

### 数据库迁移

```bash
cd backend

# 创建新迁移
alembic revision --autogenerate -m "描述变更"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看迁移历史
alembic history
```

## 核心功能

### 已完成功能 (95%)

**后端API** ✅
- [x] 运营商认证（注册、登录、个人信息管理）
- [x] 游戏授权API（实时计费、会话管理）
- [x] 在线充值（支付订单创建、回调处理）
- [x] 退款管理（申请、审批、退款）
- [x] 发票管理（申请、审核、开具）
- [x] 运营点管理（CRUD）
- [x] 应用授权申请（申请、审批）
- [x] 交易记录查询（筛选、分页）
- [x] 使用记录查询（筛选、分页、导出）
- [x] 统计分析（多维度、数据导出）
- [x] 管理员后台（登录、审批管理）

**前端页面** ✅
- [x] Dashboard（账户概览、余额、快捷操作）
- [x] 运营点管理（列表、创建、编辑、删除）
- [x] 已授权应用（列表、申请记录）
- [x] 在线充值（金额选择、支付展示）
- [x] 使用记录查询（筛选、分页、导出、统计）
- [x] 交易记录查询（筛选、分页、分类统计）
- [x] 统计分析（4个维度、可视化、导出）
- [x] 退款管理（申请列表、新建申请）
- [x] 发票管理（申请列表、新建申请、下载）
- [x] 个人信息管理（查看、编辑）

### 完整功能路线图

详见 [specs/001-mr/tasks.md](specs/001-mr/tasks.md)

## 性能目标与实际表现

### 性能优化成果 (Phase 13)

| 指标 | 目标 | 优化前 | 优化后 | 优化幅度 |
|------|------|--------|--------|---------|
| 管理员登录 P95 | < 100ms | 281.62ms | ~127ms | **-55%** |
| 数据库查询 | < 50ms | N+1 问题 | 批量加载 | **-95%** |
| 缓存命中率 | N/A | 0% | 70-80% | **新增** |

### 性能目标

- **授权API响应时间**: P95 < 100ms, P99 < 2s (NFR-001) ⚠️ 接近目标
- **系统吞吐量**: ≥ 20 req/s 峰值 (小规模部署) (NFR-002) ✅ 已达标
- **数据库查询**: 单次查询 < 50ms (NFR-003) ✅ 已达标
- **数据导出**: 10万条记录 < 30秒 (NFR-004) ✅ 已达标
- **系统可用性**: ≥ 99.5% (NFR-005) 📊 监控中

### 优化措施

1. **密码哈希优化**: Bcrypt rounds 从 12 降到 10 (-60% 验证时间)
2. **数据库索引**: 在 username 字段创建索引
3. **N+1 查询修复**: 使用 `selectinload()` 和批量查询
4. **Redis 缓存**: 管理员信息缓存 10 分钟 TTL
5. **连接池优化**: 数据库连接池配置

详见: [backend/PERFORMANCE_OPTIMIZATION.md](backend/PERFORMANCE_OPTIMIZATION.md)

## 安全特性

### 传输安全
- **HTTPS/TLS 1.3**: 反向代理强制重定向，现代密码套件
- **安全响应头**: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- **OCSP Stapling**: 减少客户端证书验证开销

### 数据安全
- **AES-256-GCM 加密**: 敏感数据加密存储（API Key、支付信息）
  - AEAD 认证加密
  - 随机 96位 Nonce
  - PBKDF2 密钥派生（100,000 迭代）
  - 密钥轮换支持（版本前缀）
- **密码哈希**: Bcrypt (10 rounds，符合 OWASP 标准)

### 认证授权
- **JWT Token**: HS256 签名，24小时有效期
- **API Key**: 64字符随机生成，安全存储
- **双重认证**: 管理员 (JWT) + 运营商 (API Key)

### 访问控制
- **IP 监控系统**:
  - 登录失败检测（5次/15分钟触发封禁）
  - 自动封禁机制（1小时临时封禁）
  - IP 信誉评分（5级评分系统）
  - 暴力破解防护
- **频率限制**:
  - 运营商: 10次/分钟
  - IP: 100次/分钟
  - 响应头: X-RateLimit-*

### 审计合规
- **审计日志**: 结构化 JSON 日志，所有敏感操作记录
- **合规性**: GDPR, PCI DSS, SOC 2 ready

详见:
- [backend/docs/HTTPS_DEPLOYMENT.md](backend/docs/HTTPS_DEPLOYMENT.md)
- [backend/docs/ENCRYPTION_GUIDE.md](backend/docs/ENCRYPTION_GUIDE.md)

## 贡献指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交变更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 开发流程

- 遵循TDD原则 (测试驱动开发)
- 测试覆盖率不低于80% (核心业务逻辑100%)
- 代码必须通过Black格式化和Ruff检查
- 所有PR必须通过CI/CD流程
- 功能需求参考 [specs/001-mr/spec.md](specs/001-mr/spec.md)

## 许可证

待定

## 联系方式

- 项目文档: [specs/001-mr/](specs/001-mr/)
- Issue追踪: GitHub Issues
- 邮箱: (待补充)

---

## 技术文档

### 架构与设计
- [功能规格](specs/001-mr/spec.md) - 完整功能需求
- [数据模型](specs/001-mr/data-model.md) - 数据库设计
- [实施计划](specs/001-mr/plan.md) - 开发路线图

### API 文档
- [API 参考](backend/docs/API_DOCUMENTATION.md) - 完整 API 文档
- [OpenAPI 定制](backend/docs/OPENAPI_CUSTOMIZATION.md) - 文档定制指南
- [Swagger UI](http://localhost:8000/api/docs) - 交互式 API 文档（需启动服务）

### 安全与部署
- [HTTPS 部署](backend/docs/HTTPS_DEPLOYMENT.md) - TLS 1.3 配置指南
- [加密指南](backend/docs/ENCRYPTION_GUIDE.md) - AES-256-GCM 使用
- [Nginx 配置](backend/deployment/nginx.conf) - 反向代理配置

### 性能与测试
- [性能优化](backend/PERFORMANCE_OPTIMIZATION.md) - 优化记录与基准测试
- [快速入门](specs/001-mr/quickstart.md) - 开发指南

---

**当前版本**: 0.1.0 (Phase 13 完成 - 安全增强)
**最后更新**: 2025-10-18
