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

## 技术栈

### 后端
- **语言**: Python 3.11+
- **框架**: FastAPI 0.104+
- **数据库**: SQLite (开发) / PostgreSQL 14+ (生产)
- **ORM**: SQLAlchemy 2.0+ (Async)
- **迁移工具**: Alembic
- **数据验证**: Pydantic 2.0+
- **认证**: JWT (python-jose)
- **密码哈希**: Passlib + Bcrypt
- **频率限制**: Slowapi (内存实现)
- **日志**: Structlog (结构化JSON日志)
- **监控**: Prometheus Client

### 前端
- **框架**: Vue 3 + TypeScript
- **状态管理**: Pinia
- **UI组件库**: Element Plus
- **HTTP客户端**: Axios
- **路由**: Vue Router
- **日期处理**: Day.js
- **构建工具**: Vite

### 开发工具
- **容器化**: Docker + Docker Compose
- **代码格式化**: Black
- **代码检查**: Ruff
- **类型检查**: MyPy
- **测试框架**: Pytest + pytest-asyncio
- **测试覆盖率**: pytest-cov (目标: 80%+)

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- Git

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

#### 2.4 启动后端服务

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
- **API文档**: http://localhost:8000/api/docs
- **健康检查**: http://localhost:8000/health

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
│   │   └── unit/            # 单元测试
│   ├── alembic/             # 数据库迁移脚本
│   ├── scripts/             # 工具脚本 (种子数据等)
│   ├── pyproject.toml       # Poetry配置
│   ├── requirements.txt     # Pip依赖
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

## 性能目标

- **授权API响应时间**: P95 < 100ms, P99 < 2s (NFR-001)
- **系统吞吐量**: ≥ 20 req/s 峰值 (小规模部署) (NFR-002)
- **数据库查询**: 单次查询 < 50ms (NFR-003)
- **数据导出**: 10万条记录 < 30秒 (NFR-004)
- **系统可用性**: ≥ 99.5% (NFR-005)

## 安全特性

- **HTTPS**: TLS 1.3加密所有外部通信 (FR-053)
- **数据加密**: API Key和敏感数据AES-256加密存储 (FR-054, NFR-010)
- **JWT认证**: HS256签名,30天有效期 (NFR-011)
- **频率限制**: 10次/分钟(单运营商), 100次/分钟(单IP) (FR-055, NFR-012)
- **审计日志**: 所有敏感操作记录,不可篡改 (FR-057, NFR-013)

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

**当前版本**: 0.1.0 (MVP开发中)
**最后更新**: 2025-10-11
