# Implementation Plan: MR游戏运营管理系统

**Branch**: `001-mr` | **Date**: 2025-10-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-mr/spec.md`

## Summary

MR游戏运营管理系统是一个云端后台服务，为游戏运营商提供实时游戏授权和计费服务。系统核心功能包括：头显Server通过API Key认证请求游戏授权，系统验证运营商授权状态和余额，按玩家数量计费并扣款，返回授权Token后游戏启动。运营商可在Web前台管理账户、充值、查看交易记录、管理运营点、申请应用授权。管理员负责为运营商授权应用、配置价格和玩家数量范围。财务人员审核退款和发票申请，查看收入统计和大客户分析。

**技术方案**：采用FastAPI（Python）构建RESTful API，PostgreSQL存储关系数据，Redis实现分布式锁和缓存。认证采用API Key + HMAC签名，支付集成微信/支付宝SDK。前端使用现代框架（React/Vue）构建Web管理界面。系统遵循TDD原则，先定义OpenAPI契约，配置外部化，关键操作记录审计日志。

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.104+, SQLAlchemy 2.0+ (ORM), Alembic (migration), Pydantic 2.0+ (validation), Redis-py 5.0+
**Storage**: PostgreSQL 14+ (主数据库), Redis 7.0+ (缓存和分布式锁)
**Testing**: pytest 7.4+, pytest-asyncio (异步测试), httpx (API测试), faker (测试数据生成)
**Target Platform**: Linux server (Docker容器化部署，Kubernetes/Docker Compose编排)
**Project Type**: Web application (backend + frontend分离)
**Performance Goals**:
  - 授权API响应时间 P95 < 100ms
  - 系统吞吐量 ≥ 1000 req/s
  - 支持单运营商10并发授权请求
  - 数据库查询 < 50ms
**Constraints**:
  - 授权请求必须幂等（相同sessionId重复请求返回已授权信息）
  - 扣费操作必须原子性（数据库事务保证）
  - 并发扣费必须无冲突（行级锁 + 乐观锁）
  - 支付回调5分钟内未到达需主动查询
  - API Key泄露检测响应时间 < 1分钟
**Scale/Scope**:
  - 预计支持100+运营商
  - 每日授权请求量 ~10万次
  - 数据库表记录量：使用记录百万级，交易记录十万级
  - 前端页面 ~30个（运营商端15个，管理员端10个，财务端5个）

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. 测试驱动开发 (TDD)

✅ **通过** - 计划遵循TDD原则：
- Phase 0完成后优先编写契约测试（Contract Tests）
- 每个用户故事实现前先编写集成测试（验证失败）
- 核心业务逻辑（授权、计费、余额扣减）要求100%覆盖率
- 单元测试覆盖率目标≥80%

### II. 零硬编码原则

✅ **通过** - 配置外部化策略：
- 价格、玩家数范围存储在数据库Application表
- 余额阈值、会话超时、频率限制等存储在配置表或环境变量
- 支付平台密钥通过环境变量注入
- API端点、数据库连接通过.env文件配置

### III. 业务逻辑完整性

✅ **通过** - 完整业务逻辑实现：
- 授权流程包含完整验证链（API Key → 授权状态 → 玩家数范围 → 余额充足性）
- 计费逻辑处理边界情况（并发、重复请求、审核期间消费）
- 使用数据库事务保证数据一致性
- 所有异常路径返回明确错误码和消息

### IV. API契约优先

✅ **通过** - 契约优先开发流程：
- Phase 1首先生成OpenAPI 3.0规范（/contracts/openapi.yaml）
- 使用Pydantic模型定义请求/响应schema
- 契约测试验证实现与规范一致性
- 提供完整API文档和SDK示例代码

### V. 可观测性与审计

✅ **通过** - 完善的可观测性设计：
- 使用structlog记录结构化JSON日志（trace_id, user_id, operation）
- 授权和扣费操作写入审计日志表（不可变）
- 集成Prometheus暴露业务指标（授权成功率、响应时间、计费金额）
- 使用OpenTelemetry实现分布式追踪

### 架构约束检查

✅ **通过** - 符合技术栈要求：
- 后端：Python 3.11 + FastAPI（支持OpenAPI自动生成）
- 数据库：PostgreSQL 14 + Redis 7
- 认证：API Key + HMAC签名
- 部署：Docker容器化

✅ **通过** - 符合性能约束：
- 设计支持授权API P95 < 100ms（Redis缓存热点数据）
- 吞吐量≥1000 req/s（异步处理 + 连接池优化）
- 数据库查询优化（索引设计、N+1问题避免）

✅ **通过** - 符合安全要求：
- HTTPS (TLS 1.3) 加密传输
- 敏感数据AES-256加密存储
- 频率限制（Redis滑动窗口算法）
- 审计日志记录所有管理员操作

### 质量保证检查

✅ **通过** - 质量流程合规：
- 所有代码通过PR审查
- PR包含测试用例和文档更新
- 数据库迁移使用Alembic，支持回滚
- 核心模块变更需技术负责人批准

---

## Project Structure

### Documentation (this feature)

```
specs/001-mr/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - 技术选型和最佳实践调研
├── data-model.md        # Phase 1 output - 数据模型设计
├── quickstart.md        # Phase 1 output - 快速入门指南
├── contracts/           # Phase 1 output - API契约定义
│   ├── openapi.yaml     # OpenAPI 3.0规范
│   ├── auth.yaml        # 授权相关接口
│   ├── operator.yaml    # 运营商接口
│   ├── admin.yaml       # 管理员接口
│   └── finance.yaml     # 财务接口
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
backend/
├── src/
│   ├── models/          # SQLAlchemy模型（Operator, Application, UsageRecord等）
│   ├── schemas/         # Pydantic schemas（请求/响应验证）
│   ├── services/        # 业务逻辑层（AuthService, BillingService等）
│   ├── api/             # FastAPI路由（/v1/auth, /v1/operators等）
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── operators.py
│   │   │   ├── admin.py
│   │   │   └── finance.py
│   │   └── deps.py      # 依赖注入（数据库会话、认证等）
│   ├── core/            # 核心配置（settings, security, logging）
│   ├── db/              # 数据库配置（连接、会话管理）
│   └── utils/           # 工具函数（加密、日志、metrics）
├── tests/
│   ├── contract/        # 契约测试（OpenAPI契约验证）
│   ├── integration/     # 集成测试（完整业务流程）
│   └── unit/            # 单元测试（服务和模型）
├── alembic/             # 数据库迁移脚本
├── .env.example         # 环境变量示例
├── Dockerfile           # Docker镜像构建
├── docker-compose.yml   # 本地开发环境
├── pyproject.toml       # 项目依赖和配置
└── README.md

frontend/
├── src/
│   ├── components/      # 可复用组件（表单、图表、表格）
│   ├── pages/           # 页面组件
│   │   ├── operator/    # 运营商端页面（账户、充值、统计）
│   │   ├── admin/       # 管理员端页面（应用管理、授权）
│   │   └── finance/     # 财务端页面（退款审核、报表）
│   ├── services/        # API调用封装
│   ├── stores/          # 状态管理（Pinia/Vuex或Redux）
│   ├── router/          # 路由配置
│   └── utils/           # 工具函数（格式化、验证）
├── tests/               # 前端测试（Vitest/Jest）
├── Dockerfile
├── package.json
└── README.md

sdk/                     # 头显Server集成SDK
├── python/              # Python SDK
│   ├── mr_auth_sdk/
│   │   ├── client.py
│   │   ├── models.py
│   │   └── exceptions.py
│   ├── examples/        # 示例代码
│   └── tests/
├── nodejs/              # Node.js SDK
│   ├── src/
│   ├── examples/
│   └── tests/
└── csharp/              # C# SDK
    ├── MRAuthSDK/
    ├── Examples/
    └── Tests/
```

**Structure Decision**: 选择Web application结构（后端+前端分离）因为系统包含：
1. RESTful API后端（供头显Server和Web前端调用）
2. Web管理前台（运营商、管理员、财务三端）
3. 独立SDK（供头显Server集成）

后端使用Python FastAPI构建高性能API，前端使用现代框架（React/Vue）构建响应式界面，SDK多语言支持方便现场集成。

---

## Complexity Tracking

*无违规项*

所有设计符合宪章要求：
- 采用标准RESTful架构，无额外复杂度
- 使用成熟技术栈（FastAPI, PostgreSQL, Redis），行业标准实践
- 配置外部化、TDD流程、API契约优先均已纳入设计

---

## Phase 0: Research (待生成 research.md)

Phase 0将调研以下技术选型和最佳实践：

1. **FastAPI最佳实践**：异步处理、依赖注入、中间件设计
2. **PostgreSQL事务管理**：行级锁实现、隔离级别选择、并发控制
3. **Redis分布式锁**：Redlock算法、锁超时处理、防重复扣费
4. **支付平台集成**：微信支付/支付宝SDK、回调验证、异常处理
5. **API Key认证**：HMAC签名算法、密钥轮换策略、频率限制
6. **结构化日志**：structlog配置、trace_id生成、日志聚合方案
7. **监控指标**：Prometheus metrics设计、Grafana仪表盘、告警规则
8. **数据库迁移**：Alembic最佳实践、零停机迁移、回滚策略
9. **前端架构**：React/Vue选型、状态管理方案、图表库选择
10. **SDK设计**：多语言SDK结构、错误处理、重试机制

## Phase 1: Design (待生成 data-model.md, contracts/, quickstart.md)

Phase 1将生成：
- **data-model.md**：12个核心实体的表结构、关系、索引设计
- **contracts/**：OpenAPI 3.0规范，包含所有API端点定义
- **quickstart.md**：本地开发环境搭建、首次授权测试流程

## Phase 2: Tasks (由 /speckit.tasks 命令生成)

Phase 2将根据用户故事生成可执行任务列表（tasks.md）
