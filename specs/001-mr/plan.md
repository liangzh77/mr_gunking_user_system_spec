# Implementation Plan: MR游戏运营管理系统

**Branch**: `001-mr` | **Date**: 2025-10-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-mr/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

构建MR游戏运营管理系统 - 游戏授权计费平台。核心功能包括：实时游戏授权与按玩家数计费、运营商账户与在线充值、运营点与应用授权管理、多维度统计分析、财务后台与审计。技术栈采用Python 3.11+ FastAPI + PostgreSQL，单实例部署支持20 req/s峰值吞吐量，遵循TDD、零硬编码、契约优先等核心原则。

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.104+, SQLAlchemy 2.0+ (ORM), Alembic (migration), Pydantic 2.0+ (validation)
**Storage**: PostgreSQL 14+ (主存储，支持事务和行级锁), 文件系统 (发票PDF存储)
**Testing**: pytest (单元测试 + 集成测试), pytest-cov (覆盖率), httpx (异步HTTP测试)
**Target Platform**: Linux Server (容器化部署，Docker)
**Project Type**: Web (Backend API + Frontend SPA)
**Performance Goals**: 授权API 20 req/s峰值吞吐量, P95响应时间 <2s (授权接口 <100ms)
**Constraints**: 单实例部署, PostgreSQL默认连接池, 数据库查询 <50ms, 无Redis依赖 (Phase 0)
**Scale/Scope**: 预计100+运营商, 1000+运营点, 10万+年游戏场次, 8个核心实体, 60+ API端点

**关键技术决策 (需Phase 0研究验证)**:
- 频率限制实现方案 (PostgreSQL表 vs 内存计数器)
- JWT Token刷新策略 (30天静态 vs 滑动窗口)
- 支付平台SDK选型 (官方SDK vs 自封装HTTP客户端)
- 定时任务调度框架 (APScheduler vs Celery Beat)
- 前端技术栈 (NEEDS CLARIFICATION: React/Vue.js + 状态管理方案)
- 并发扣费事务隔离级别 (READ COMMITTED vs SERIALIZABLE)
- 审计日志存储策略 (同PostgreSQL vs 独立时序数据库)
- 文件上传与存储 (本地磁盘 vs 对象存储OSS)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Phase 0 Gate Check (Pre-Research)

| 原则 | 状态 | 说明 |
|------|------|------|
| **I. 测试驱动开发** | ✅ PASS | Spec包含37个验收场景，支持Red-Green-Refactor；承诺单元测试80%覆盖率，核心业务逻辑100% |
| **II. 零硬编码** | ✅ PASS | 价格、玩家数范围、余额阈值等业务配置存储于数据库；API端点、数据库连接通过环境变量配置 |
| **III. 业务逻辑完整性** | ✅ PASS | 授权验证包含完整权限检查、余额验证、并发冲突处理；计费采用数据库事务+行级锁保证一致性；覆盖8个边界场景 |
| **IV. API契约优先** | ✅ PASS | 承诺Phase 1生成OpenAPI规范先于代码实现；契约测试覆盖所有端点；包含错误码和认证方式定义 |
| **V. 可观测性与审计** | ✅ PASS | FR-046/057明确审计日志需求（操作类型、资源ID、IP、时间）；FR-060要求健康检查端点；结构化日志支持追踪 |

**架构约束合规性:**
- ✅ 技术栈: Python 3.11+ FastAPI + PostgreSQL 14+ (符合要求)
- ✅ 安全: HTTPS TLS 1.3, API Key AES-256加密, 频率限制 (FR-053~056)
- ✅ 性能: P95 <2s (授权 <100ms), 20 req/s吞吐量 (符合≥1000 req/s要求需Phase 0验证单实例能力)
- ⚠️ **性能约束偏离**: 宪章要求≥1000 req/s，当前目标仅20 req/s (小规模部署假设，需记录理由)

**质量保证合规性:**
- ✅ PR审查、测试用例、文档更新流程 (需在tasks.md中体现)
- ✅ 数据库迁移使用Alembic支持回滚
- ✅ 禁止技术债务跳过测试 (已承诺)

---

### Phase 1 Gate Check (Post-Design)

**设计产物验证** (2025-10-11):
- ✅ **data-model.md**: 12个实体定义完整,包含字段/索引/约束/状态转换
- ✅ **contracts/** (代理生成): OpenAPI规范覆盖60+ API端点
- ✅ **quickstart.md** (代理生成): 开发环境搭建指南完整
- ✅ **research.md**: 8个技术决策均有代码示例和迁移路径

**原则复核** (设计后):
| 原则 | 状态 | Phase 1验证 |
|------|------|------------|
| **I. 测试驱动开发** | ✅ PASS | data-model.md包含验证规则,contracts/定义完整错误码,支持契约测试先行 |
| **II. 零硬编码** | ✅ PASS | 价格/玩家数存储于applications表,环境变量配置在quickstart.md明确 |
| **III. 业务逻辑完整性** | ✅ PASS | 并发扣费使用SELECT FOR UPDATE+会话ID幂等性,事务隔离级别明确(READ COMMITTED) |
| **IV. API契约优先** | ✅ PASS | contracts/ OpenAPI规范已生成,先于代码实现 |
| **V. 可观测性与审计** | ✅ PASS | api_key_usage_logs和finance_operation_logs表设计完整,分区策略明确 |

**技术债务检查**:
- ✅ 无跳过测试的占位符实现
- ✅ 所有"NEEDS CLARIFICATION"已在research.md解决
- ✅ Phase 1迁移路径清晰(Redis/Celery/TimescaleDB/OSS)

**最终判定**: ✅ **通过Phase 1宪章检查,可进入Phase 2任务分解**

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
backend/
├── src/
│   ├── models/              # SQLAlchemy ORM模型 (8个核心实体)
│   ├── schemas/             # Pydantic请求/响应模式 (契约定义)
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py      # 运营商认证 (JWT登录/刷新)
│   │   │   ├── operators.py # 运营商账户管理
│   │   │   ├── sites.py     # 运营点管理
│   │   │   ├── apps.py      # 应用与授权管理
│   │   │   ├── authorization.py  # 游戏授权API (核心)
│   │   │   ├── finance.py   # 充值/退款/发票
│   │   │   ├── usage.py     # 使用记录与统计
│   │   │   └── admin.py     # 管理员与财务后台
│   │   └── deps.py          # 依赖注入 (数据库会话、认证)
│   ├── services/
│   │   ├── authorization.py # 授权业务逻辑 (余额检查、扣费)
│   │   ├── payment.py       # 支付平台集成
│   │   ├── rate_limit.py    # 频率限制服务
│   │   └── audit.py         # 审计日志服务
│   ├── core/
│   │   ├── config.py        # 配置管理 (Pydantic Settings)
│   │   ├── security.py      # JWT、加密、HMAC
│   │   └── database.py      # 数据库连接池、会话管理
│   ├── tasks/               # 定时任务
│   │   ├── payment_sync.py  # 支付对账 (5分钟)
│   │   └── reports.py       # 财务报表生成
│   └── main.py              # FastAPI应用入口
├── tests/
│   ├── contract/            # 契约测试 (OpenAPI验证)
│   ├── integration/         # 集成测试 (数据库+支付平台)
│   │   ├── test_authorization_flow.py
│   │   └── test_payment_callback.py
│   └── unit/                # 单元测试 (80%覆盖率目标)
│       ├── test_services/
│       └── test_models/
├── alembic/                 # 数据库迁移脚本
├── docker-compose.yml       # 本地开发环境
├── Dockerfile
├── pyproject.toml           # Poetry依赖管理
└── pytest.ini

frontend/
├── src/
│   ├── components/          # 可复用组件
│   ├── pages/
│   │   ├── Dashboard.tsx    # 运营商首页
│   │   ├── Sites.tsx        # 运营点管理
│   │   ├── Finance.tsx      # 充值与交易记录
│   │   ├── Usage.tsx        # 使用记录与统计
│   │   └── Admin.tsx        # 管理员后台
│   ├── services/
│   │   └── api.ts           # API客户端 (基于OpenAPI生成)
│   ├── stores/              # 状态管理 (待Phase 0确定方案)
│   └── App.tsx
├── tests/
│   └── e2e/                 # 端到端测试
└── package.json

docs/
└── api/                     # OpenAPI规范导出 (Swagger UI)
```

**Structure Decision**: 采用Web应用结构 (Option 2)，前后端分离。后端使用FastAPI分层架构 (models-services-api)，前端使用现代SPA框架 (待Phase 0确认React/Vue.js选型)。测试按契约/集成/单元三层组织，确保TDD工作流。

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 性能目标偏离 (20 req/s vs 宪章1000 req/s) | 小规模运营场景，100运营商×10并发游戏=20峰值；单实例成本可控 | 1000 req/s需多实例部署+负载均衡，Phase 0不需要，过度设计增加复杂度和成本；可水平扩展预留 |
