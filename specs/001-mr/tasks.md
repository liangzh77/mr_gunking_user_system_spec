# Tasks: MR游戏运营管理系统

**Feature Branch**: `001-mr`
**Input**: Design documents from `/specs/001-mr/`
**Prerequisites**: spec.md, plan.md, data-model.md, research.md, contracts/, quickstart.md

**Organization**: Tasks are grouped by user story (按用户故事组织) to enable independent implementation and testing of each story.

**项目遵循TDD原则**: 测试优先于实现 (Red-Green-Refactor)

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Web app**: `backend/src/`, `frontend/src/`, `sdk/`
- Backend: Python 3.11+ + FastAPI 0.104+
- Frontend: Vue 3 + TypeScript + Pinia + Element Plus
- Database: PostgreSQL 14+ (Phase 0暂无Redis，频率限制使用slowapi内存实现)

---

## Phase 1: Setup (项目初始化)

**Purpose**: 项目结构初始化和基础配置

- [X] T001 创建项目目录结构 in project root (backend/, frontend/, sdk/, docs/)
- [X] T002 初始化后端Python项目 in backend/pyproject.toml and backend/requirements.txt
- [X] T003 配置Docker Compose in docker-compose.yml (PostgreSQL 14)
- [X] T004 配置环境变量模板 in backend/.env.example
- [X] T005 [P] 配置代码质量工具 in backend/ (black, ruff, mypy, pytest配置)
- [ ] T006 [P] 初始化前端Vue项目 in frontend/ (package.json, tsconfig.json, vite.config.ts)
- [ ] T007 [P] 初始化Python SDK项目 in sdk/python/
- [X] T008 [P] 创建项目README in README.md
- [ ] T005a 生成OpenAPI契约规范 in specs/001-mr/contracts/openapi.yaml (基于data-model.md和spec.md的API需求，定义60+端点的请求/响应Schema、错误码、认证方式，使用datamodel-code-generator或手动编写，必须在Phase 3测试编写前完成)

**Checkpoint**: ✅ 项目结构就绪，Docker容器可以启动 (MVP核心完成，前端和SDK可延后)

---

## Phase 2: Foundational (基础设施 - 所有用户故事的阻塞前置条件)

**Purpose**: 核心基础设施，必须完成后才能开始任何用户故事

**⚠️ CRITICAL**: 没有Phase 2完成，任何用户故事都无法开始

### 数据库基础

- [X] T009 配置Alembic数据库迁移框架 in backend/alembic/ ✅ 2025-10-11 (commit: 7601824)
- [X] T010 创建数据库初始迁移脚本 in backend/alembic/versions/20251011_001_initial_schema.py (包含16个实体表) ✅ 2025-10-11 (commit: 7601824)
- [X] T011 运行数据库迁移并验证表结构 (执行 alembic upgrade head) ✅ 2025-10-11 (commit: baa5134)
- [ ] T010a 验证迁移脚本与data-model.md一致性 in backend/tests/integration/test_schema_consistency.py (使用SQLAlchemy反射读取数据库Schema，对比data-model.md定义的表名/字段/类型/索引/约束，不匹配时测试失败并输出差异报告)
- [X] T012 创建种子数据脚本 in backend/scripts/seed_data.sql (至少包含: 1个超级管理员账号admin/Admin@123、1个财务账号finance/Finance@123、2个测试运营商账号operator1/operator2含初始余额1000元) ✅ 2025-10-12 (commit: 060638a)

### 核心中间件和服务 (可并行)

- [X] T013 [P] 实现API Key认证中间件 in backend/src/core/security/api_key.py ✅ 2025-10-13
- [X] T014 [P] 实现HMAC签名验证中间件 in backend/src/core/security/hmac.py ✅ 2025-10-13
- [X] T015 [P] 实现JWT Token生成和验证服务 in backend/src/core/security/jwt.py ✅ 2025-10-11 (commit: e07c671)
- [X] T016 [P] 实现结构化日志配置 in backend/src/core/logging.py (structlog + JSON格式) ✅ 2025-10-11 (commit: e07c671)
- [X] T017 [P] 实现Prometheus metrics中间件 in backend/src/core/metrics/prometheus.py (实现NFR-017a定义的8个核心指标：mr_auth_requests_total、mr_auth_latency_seconds、mr_operator_balance_yuan、mr_payment_callback_total、mr_revenue_total_yuan、mr_db_connection_pool_active、mr_api_errors_total、mr_rate_limit_blocked_total，使用prometheus_client库，暴露/metrics端点) ✅ 2025-10-13
- [X] T017a [P] 契约测试：Prometheus指标格式 in backend/tests/contract/test_prometheus_metrics.py (验证/metrics端点返回有效Prometheus格式、包含所有NFR-017a定义的指标) ✅ 2025-10-13 (骨架)
- [X] T017b [P] 集成测试：指标准确性 in backend/tests/integration/test_metrics_accuracy.py (触发授权请求，验证mr_auth_requests_total递增、mr_auth_latency_seconds正确记录) ✅ 2025-10-13 (骨架)
- [X] T018 [P] 实现频率限制中间件 in backend/src/core/middleware/rate_limit.py (使用slowapi库，实现FR-055双重限制：单运营商10次/分钟、单IP 100次/分钟，超限返回HTTP 429及Retry-After响应头) ✅ 2025-10-13
- [X] T018a [P] 集成测试：频率限制功能 in backend/tests/integration/test_rate_limit.py (验证单运营商10次/分钟限制、单IP 100次/分钟限制、超限返回HTTP 429及Retry-After头) ✅ 2025-10-13 (骨架)
- [X] T018b [P] 单元测试：频率限制计数器 in backend/tests/unit/middleware/test_rate_limit.py (验证计数器递增、重置、并发安全) ✅ 2025-10-13 (骨架)
- [X] T019 [P] 实现并发控制工具 in backend/src/core/utils/db_lock.py (使用SELECT FOR UPDATE行级锁用于并发扣费控制) ✅ 2025-10-13

### FastAPI应用框架

- [X] T020 配置FastAPI应用核心 in backend/src/main.py (CORS、异常处理、中间件注册、lifespan) ✅ 2025-10-11 (commit: ccca883)
- [X] T021 实现数据库会话管理 in backend/src/db/session.py (SQLAlchemy async session) ✅ 2025-10-11 (commit: 26e9414)
- [X] T022 实现依赖注入工厂 in backend/src/api/dependencies.py (get_db, CurrentUserToken等) ✅ 2025-10-11 (commit: ccca883)
- [X] T023 [P] 实现全局异常处理器 in backend/src/middleware/exception_handler.py ✅ 2025-10-11 (commit: ccca883)
- [X] T024 [P] 实现Pydantic配置模型 in backend/src/core/config.py (Settings类) ✅ 2025-10-11 (commit: e07c671)
- [X] T024a [P] 实现健康检查端点 in backend/src/main.py::health_check_endpoint (GET /health，返回JSON格式{"status":"healthy|degraded|unhealthy","checks":{...}}，检查项：database执行SELECT 1验证PostgreSQL连接、payment_api调用支付平台健康检查端点超时5秒标记不可用、disk_space检查发票存储路径可用空间>1GB，状态判定：所有通过→200 healthy、支付API不可用但数据库正常→200 degraded、数据库不可用→503 unhealthy) ✅ 2025-10-11 (commit: ccca883)

### 公共Schema和工具

- [X] T025 [P] 创建公共Pydantic schemas in backend/src/schemas/common.py (ErrorResponse, TokenResponse等) ✅ 2025-10-11 (commit: 26e9414)
- [X] T026 [P] 实现密码哈希工具 in backend/src/core/utils/password.py (bcrypt) ✅ 2025-10-11 (commit: e07c671)
- [X] T026a [P] 实现加密工具类 in backend/src/core/security/encryption.py (AES-256-GCM加密/解密、密钥派生函数PBKDF2、支持多版本密钥解密以兼容密钥轮换场景，主密钥从环境变量MASTER_ENCRYPTION_KEY读取) ✅ 2025-10-13
- [X] T026b [P] 单元测试：加密工具 in backend/tests/unit/security/test_encryption.py (验证加密可逆性、密钥轮换兼容性、错误密钥解密失败) ✅ 2025-10-13
- [X] T027 [P] 实现金额计算工具 in backend/src/core/utils/money.py (精确decimal计算) ✅ 2025-10-11 (commit: e07c671)
- [X] T028 [P] 实现时间戳验证工具 in backend/src/core/utils/timestamp.py ✅ 2025-10-11 (commit: e07c671)

**Checkpoint**: ✅✅ **Phase 2 基础设施完成** - 用户故事可以并行开始 (27/28 tasks完成，96% - 仅T010a Schema一致性测试待完善)

---

## Phase 3: User Story 1 - 游戏授权与实时计费 (Priority: P1) 🎯 MVP

**依赖**: Phase 2 (基础设施) + T005a (contracts/已生成)

**Goal**: 头显Server请求游戏授权，系统验证、扣费、返回Token

**Independent Test**: 头显Server配置凭证 → 请求授权 → 扣费成功 → 游戏启动

### 测试任务 (TDD - 基于contracts/编写测试)

- [ ] T029 [P] [US1] 契约测试：游戏授权接口 in backend/tests/contract/test_game_authorize.py (验证POST /v1/auth/game/authorize契约)
- [ ] T030 [P] [US1] 集成测试：完整授权流程 in backend/tests/integration/test_authorization_flow.py (API Key验证 → 余额扣费 → 返回Token)
- [ ] T031 [P] [US1] 集成测试：余额不足场景 in backend/tests/integration/test_insufficient_balance.py
- [ ] T032 [P] [US1] 集成测试：会话ID幂等性 in backend/tests/integration/test_session_idempotency.py (防重复扣费)
- [ ] T033 [P] [US1] 集成测试：玩家数量范围验证 in backend/tests/integration/test_player_count_validation.py
- [ ] T033a [P] [US1] 集成测试：会话ID格式验证 in backend/tests/integration/test_session_id_validation.py (测试FR-061：格式错误、operatorId不匹配、时间戳过期超过5分钟、随机数不足16位等场景，验证返回HTTP 400及详细错误信息)
- [ ] T034 [P] [US1] 集成测试：并发扣费冲突处理 in backend/tests/integration/test_concurrent_billing.py

### 数据模型 (可并行)

- [ ] T035 [P] [US1] 创建OperatorAccount模型 in backend/src/models/operator.py (运营商账户表)
- [ ] T036 [P] [US1] 创建Application模型 in backend/src/models/application.py (应用表)
- [ ] T037 [P] [US1] 创建OperationSite模型 in backend/src/models/site.py (运营点表)
- [ ] T038 [P] [US1] 创建UsageRecord模型 in backend/src/models/usage_record.py (使用记录表)
- [ ] T039 [P] [US1] 创建TransactionRecord模型 in backend/src/models/transaction.py (交易记录表)
- [ ] T040 [P] [US1] 创建OperatorAppAuthorization模型 in backend/src/models/authorization.py (应用授权关系表)

### Pydantic Schemas (可并行)

- [ ] T041 [P] [US1] 创建授权请求Schema in backend/src/schemas/auth.py (GameAuthorizeRequest, GameAuthorizeResponse)
- [ ] T042 [P] [US1] 创建使用记录Schema in backend/src/schemas/usage.py (UsageRecordSchema)
- [ ] T043 [P] [US1] 创建交易记录Schema in backend/src/schemas/transaction.py (TransactionSchema)

### 业务服务

- [ ] T044 [US1] 实现AuthService in backend/src/services/auth.py (API Key验证、HMAC签名验证、应用授权检查、玩家数量验证)
- [ ] T045 [US1] 实现BillingService in backend/src/services/billing.py (余额检查、扣费事务[行级锁+原子性]、使用记录创建、交易记录创建、会话ID幂等性检查)

### API接口

- [ ] T046 [US1] 实现游戏授权API in backend/src/api/v1/auth.py::authorize_game (POST /v1/auth/game/authorize)
- [ ] T047 [US1] 注册授权路由 in backend/src/main.py (app.include_router(auth.router))

### 单元测试 (补充)

- [ ] T048 [P] [US1] AuthService单元测试 in backend/tests/unit/services/test_auth_service.py
- [ ] T049 [P] [US1] BillingService单元测试 in backend/tests/unit/services/test_billing_service.py

**Checkpoint**: User Story 1完成 - 核心授权计费功能可独立测试和演示

---

## Phase 4: User Story 2 - 运营商账户与财务管理 (Priority: P1)

**Goal**: 运营商注册、充值、退款、发票管理

**Independent Test**: 注册账户 → 充值100元 → 消费50元 → 申请退款 → 余额归零

### 测试任务 (TDD)

- [ ] T050 [P] [US2] 契约测试：运营商注册接口 in backend/tests/contract/test_operator_register.py (POST /v1/auth/operators/register)
- [ ] T051 [P] [US2] 契约测试：运营商登录接口 in backend/tests/contract/test_operator_login.py (POST /v1/auth/operators/login)
- [ ] T052 [P] [US2] 契约测试：充值接口 in backend/tests/contract/test_recharge.py (POST /v1/operators/me/recharge)
- [ ] T053 [P] [US2] 集成测试：完整财务流程 in backend/tests/integration/test_finance_flow.py (充值 → 查看余额 → 申请退款)
- [ ] T054 [P] [US2] 集成测试：支付回调失败回滚 in backend/tests/integration/test_payment_callback_failure.py

### 数据模型 (可并行)

- [ ] T055 [P] [US2] 创建RefundRecord模型 in backend/src/models/refund.py (退款记录表)
- [ ] T056 [P] [US2] 创建InvoiceRecord模型 in backend/src/models/invoice.py (发票记录表)

### Pydantic Schemas (可并行)

- [ ] T057 [P] [US2] 创建运营商注册Schema in backend/src/schemas/operator.py (OperatorRegisterRequest, OperatorProfile)
- [ ] T058 [P] [US2] 创建登录Schema in backend/src/schemas/auth.py (LoginRequest, LoginResponse)
- [ ] T059 [P] [US2] 创建充值Schema in backend/src/schemas/payment.py (RechargeRequest, RechargeResponse)
- [ ] T060 [P] [US2] 创建退款Schema in backend/src/schemas/refund.py (RefundRequest, RefundResponse)
- [ ] T061 [P] [US2] 创建发票Schema in backend/src/schemas/invoice.py (InvoiceRequest, InvoiceResponse)

### 业务服务

- [ ] T062 [US2] 实现OperatorService in backend/src/services/operator.py (注册、登录、个人信息管理)
- [ ] T063 [US2] 实现PaymentService in backend/src/services/payment.py (微信支付集成、支付宝集成、支付回调验证、充值事务处理)
- [ ] T064 [US2] 实现RefundService in backend/src/services/refund.py (退款申请创建、可退余额计算、退款事务处理)
- [ ] T065 [US2] 实现InvoiceService in backend/src/services/invoice.py (发票申请创建、电子发票生成)

### API接口 (可并行)

- [ ] T066 [P] [US2] 实现运营商注册API in backend/src/api/v1/auth.py::register_operator (POST /v1/auth/operators/register)
- [ ] T067 [P] [US2] 实现运营商登录API in backend/src/api/v1/auth.py::operator_login (POST /v1/auth/operators/login)
- [ ] T068 [P] [US2] 实现运营商登出API in backend/src/api/v1/auth.py::operator_logout (POST /v1/auth/operators/logout)
- [ ] T069 [P] [US2] 实现查询个人信息API in backend/src/api/v1/operators.py::get_profile (GET /v1/operators/me)
- [ ] T070 [P] [US2] 实现更新个人信息API in backend/src/api/v1/operators.py::update_profile (PUT /v1/operators/me)
- [ ] T071 [P] [US2] 实现充值API in backend/src/api/v1/operators.py::recharge (POST /v1/operators/me/recharge)
- [ ] T072 [P] [US2] 实现查询余额API in backend/src/api/v1/operators.py::get_balance (GET /v1/operators/me/balance)
- [ ] T073 [P] [US2] 实现交易记录查询API in backend/src/api/v1/operators.py::get_transactions (GET /v1/operators/me/transactions)
- [ ] T074 [P] [US2] 实现退款申请API in backend/src/api/v1/operators.py::apply_refund (POST /v1/operators/me/refunds)
- [ ] T075 [P] [US2] 实现退款记录查询API in backend/src/api/v1/operators.py::get_refunds (GET /v1/operators/me/refunds)
- [ ] T076 [P] [US2] 实现发票申请API in backend/src/api/v1/operators.py::apply_invoice (POST /v1/operators/me/invoices)
- [ ] T077 [P] [US2] 实现发票记录查询API in backend/src/api/v1/operators.py::get_invoices (GET /v1/operators/me/invoices)
- [ ] T078 [US2] 实现支付回调处理接口 in backend/src/api/v1/webhooks.py (POST /v1/webhooks/payment/wechat, POST /v1/webhooks/payment/alipay)
- [ ] T079 [US2] 注册运营商路由 in backend/src/main.py

### 单元测试 (补充)

- [ ] T080 [P] [US2] OperatorService单元测试 in backend/tests/unit/services/test_operator_service.py
- [ ] T081 [P] [US2] PaymentService单元测试 in backend/tests/unit/services/test_payment_service.py
- [ ] T082 [P] [US2] RefundService单元测试 in backend/tests/unit/services/test_refund_service.py

**Checkpoint**: User Story 1 + 2完成 - 运营商可自助管理财务

---

## Phase 5: User Story 3 - 运营点与应用授权管理 (Priority: P2)

**Goal**: 运营商创建运营点、配置头显Server、查看已授权应用、申请新应用授权

**Independent Test**: 创建两个运营点"北京门店"和"上海门店"，为北京门店配置头显Server凭证，查看已授权应用列表，申请新应用并等待审核

### 测试任务 (TDD)

- [ ] T083 [P] [US3] 契约测试：创建运营点接口 in backend/tests/contract/test_create_site.py (POST /v1/operators/me/sites)
- [ ] T084 [P] [US3] 契约测试：查询已授权应用接口 in backend/tests/contract/test_authorized_apps.py (GET /v1/operators/me/applications)
- [ ] T085 [P] [US3] 集成测试：运营点管理流程 in backend/tests/integration/test_site_management.py (创建 → 编辑 → 删除)
- [ ] T086 [P] [US3] 集成测试：应用授权申请流程 in backend/tests/integration/test_app_request.py (申请 → 待审核状态)

### 数据模型 (已在US1创建，本阶段无需新增)

### Pydantic Schemas (可并行)

- [ ] T087 [P] [US3] 创建运营点Schema in backend/src/schemas/site.py (SiteCreateRequest, SiteUpdateRequest, SiteResponse)
- [ ] T088 [P] [US3] 创建应用授权申请Schema in backend/src/schemas/app_request.py (AppRequestCreate, AppRequestResponse)
- [ ] T089 [P] [US3] 创建已授权应用Schema in backend/src/schemas/application.py (AuthorizedApplicationResponse)

### 业务服务

- [ ] T090 [US3] 实现SiteService in backend/src/services/site.py (创建运营点、编辑运营点、删除运营点、查询运营点)
- [ ] T091 [US3] 实现ApplicationService in backend/src/services/application.py (查询已授权应用、申请新应用授权)

### API接口 (可并行)

- [ ] T092 [P] [US3] 实现创建运营点API in backend/src/api/v1/operators.py::create_site (POST /v1/operators/me/sites)
- [ ] T093 [P] [US3] 实现运营点列表API in backend/src/api/v1/operators.py::get_sites (GET /v1/operators/me/sites)
- [ ] T094 [P] [US3] 实现运营点详情API in backend/src/api/v1/operators.py::get_site (GET /v1/operators/me/sites/{site_id})
- [ ] T095 [P] [US3] 实现更新运营点API in backend/src/api/v1/operators.py::update_site (PUT /v1/operators/me/sites/{site_id})
- [ ] T096 [P] [US3] 实现删除运营点API in backend/src/api/v1/operators.py::delete_site (DELETE /v1/operators/me/sites/{site_id})
- [ ] T097 [P] [US3] 实现查询已授权应用API in backend/src/api/v1/operators.py::get_authorized_applications (GET /v1/operators/me/applications)
- [ ] T098 [P] [US3] 实现申请应用授权API in backend/src/api/v1/operators.py::request_application (POST /v1/operators/me/applications/requests)
- [ ] T099 [P] [US3] 实现查询授权申请列表API in backend/src/api/v1/operators.py::get_app_requests (GET /v1/operators/me/applications/requests)

### 单元测试 (补充)

- [ ] T100 [P] [US3] SiteService单元测试 in backend/tests/unit/services/test_site_service.py
- [ ] T101 [P] [US3] ApplicationService单元测试 in backend/tests/unit/services/test_application_service.py

**Checkpoint**: User Story 1 + 2 + 3完成 - 运营商可管理运营点和应用授权

---

## Phase 6: User Story 4 - 使用记录与多维度统计 (Priority: P2)

**Goal**: 运营商查看每次游戏详细记录、可视化消费趋势、支持数据导出

**Independent Test**: 在两个运营点分别启动不同游戏，查看使用记录显示两条明细，查看按运营点统计图表，导出Excel报表

### 测试任务 (TDD)

- [ ] T102 [P] [US4] 契约测试：使用记录查询接口 in backend/tests/contract/test_usage_records.py (GET /v1/operators/me/usage-records)
- [ ] T103 [P] [US4] 契约测试：统计数据接口 in backend/tests/contract/test_statistics.py (GET /v1/operators/me/statistics)
- [ ] T104 [P] [US4] 集成测试：多维度统计查询 in backend/tests/integration/test_statistics.py (按运营点、按应用、按时间)
- [ ] T105 [P] [US4] 集成测试：数据导出功能 in backend/tests/integration/test_export.py

### 业务服务

- [ ] T106 [US4] 实现UsageService in backend/src/services/usage.py (查询使用记录、多维度统计、数据聚合)
- [ ] T107 [US4] 实现ExportService in backend/src/services/export.py (导出Excel、导出CSV)

### Pydantic Schemas (可并行)

- [ ] T108 [P] [US4] 创建统计Schema in backend/src/schemas/statistics.py (StatisticsRequest, StatisticsResponse, TrendData)
- [ ] T109 [P] [US4] 创建导出Schema in backend/src/schemas/export.py (ExportRequest, ExportResponse)

### API接口 (可并行)

- [ ] T110 [P] [US4] 实现使用记录查询API in backend/src/api/v1/operators.py::get_usage_records (GET /v1/operators/me/usage-records)
- [ ] T111 [P] [US4] 实现使用记录详情API in backend/src/api/v1/operators.py::get_usage_record (GET /v1/operators/me/usage-records/{record_id})
- [ ] T112 [P] [US4] 实现按运营点统计API in backend/src/api/v1/operators.py::get_statistics_by_site (GET /v1/operators/me/statistics/by-site)
- [ ] T113 [P] [US4] 实现按应用统计API in backend/src/api/v1/operators.py::get_statistics_by_application (GET /v1/operators/me/statistics/by-application)
- [ ] T114 [P] [US4] 实现按时间统计API in backend/src/api/v1/operators.py::get_statistics_by_time (GET /v1/operators/me/statistics/by-time)
- [ ] T115 [P] [US4] 实现玩家数量分布统计API in backend/src/api/v1/operators.py::get_player_distribution (GET /v1/operators/me/statistics/player-distribution)
- [ ] T116 [P] [US4] 实现导出使用记录API in backend/src/api/v1/operators.py::export_usage_records (GET /v1/operators/me/usage-records/export)
- [ ] T117 [P] [US4] 实现导出统计报表API in backend/src/api/v1/operators.py::export_statistics (GET /v1/operators/me/statistics/export)

### 单元测试 (补充)

- [ ] T118 [P] [US4] UsageService单元测试 in backend/tests/unit/services/test_usage_service.py
- [ ] T119 [P] [US4] ExportService单元测试 in backend/tests/unit/services/test_export_service.py

**Checkpoint**: User Story 1-4完成 - 运营商可查看数据和统计

---

## Phase 7: User Story 5 - 管理员权限与应用配置 (Priority: P2)

**Goal**: 管理员创建运营商账户、授权应用、配置价格、管理API Key

**Independent Test**: 管理员登录后台，创建运营商账户，为其授权"太空探险"并设置单价10元、玩家范围2-8人，查看API Key，强制重置后旧Key失效

### 测试任务 (TDD)

- [ ] T120 [P] [US5] 契约测试：管理员登录接口 in backend/tests/contract/test_admin_login.py (POST /v1/auth/admin/login)
- [ ] T121 [P] [US5] 契约测试：创建运营商接口 in backend/tests/contract/test_admin_create_operator.py (POST /v1/admin/operators)
- [ ] T122 [P] [US5] 契约测试：授权应用接口 in backend/tests/contract/test_admin_authorize_app.py (POST /v1/admin/operators/{operator_id}/applications)
- [ ] T123 [P] [US5] 集成测试：完整管理员流程 in backend/tests/integration/test_admin_workflow.py (创建运营商 → 授权应用 → 调价)
- [ ] T124 [P] [US5] 集成测试：API Key重置 in backend/tests/integration/test_api_key_reset.py

### 数据模型

- [X] T125 [P] [US5] 创建AdminAccount模型 in backend/src/models/admin.py (管理员账户表) ✅ 2025-10-12
- [ ] T126 [P] [US5] 创建ApplicationRequest模型 in backend/src/models/app_request.py (应用授权申请表)

### Pydantic Schemas (可并行)

- [X] T127 [P] [US5] 创建管理员登录Schema in backend/src/schemas/admin.py (AdminLoginRequest, AdminLoginResponse等9个schemas) ✅ 2025-10-12
- [ ] T128 [P] [US5] 创建运营商管理Schema in backend/src/schemas/admin/operator.py (CreateOperatorRequest, OperatorDetailResponse)
- [ ] T129 [P] [US5] 创建应用管理Schema in backend/src/schemas/admin/application.py (CreateApplicationRequest, UpdateApplicationRequest, ApplicationResponse)
- [ ] T130 [P] [US5] 创建授权管理Schema in backend/src/schemas/admin/authorization.py (AuthorizeApplicationRequest, AuthorizationResponse)

### 业务服务

- [X] T131 [US5] 实现AdminAuthService in backend/src/services/admin_auth.py (管理员登录、token刷新、密码修改) ✅ 2025-10-12
- [ ] T132 [US5] 实现AdminApplicationService in backend/src/services/admin_application.py (应用创建、价格调整、玩家范围配置)
- [ ] T133 [US5] 实现AdminAuthorizationService in backend/src/services/admin_authorization.py (授权审批、授权撤销)

### API接口 (可并行)

- [X] T134 [P] [US5] 实现管理员认证API in backend/src/api/v1/admin_auth.py (5个端点: login/logout/me/refresh/change-password) ✅ 2025-10-12
- [ ] T135 [P] [US5] 实现创建运营商API in backend/src/api/v1/admin/operators.py::create_operator (POST /v1/admin/operators)
- [ ] T136 [P] [US5] 实现运营商列表API in backend/src/api/v1/admin/operators.py::get_operators (GET /v1/admin/operators)
- [ ] T137 [P] [US5] 实现运营商详情API in backend/src/api/v1/admin/operators.py::get_operator (GET /v1/admin/operators/{operator_id})
- [ ] T138 [P] [US5] 实现更新运营商分类API in backend/src/api/v1/admin/operators.py::update_operator_tier (PUT /v1/admin/operators/{operator_id}/tier)
- [ ] T139 [P] [US5] 实现查看API Key API in backend/src/api/v1/admin/operators.py::get_api_key (GET /v1/admin/operators/{operator_id}/api-key)
- [ ] T140 [P] [US5] 实现重置API Key API in backend/src/api/v1/admin/operators.py::reset_api_key (POST /v1/admin/operators/{operator_id}/api-key/reset)
- [ ] T141 [P] [US5] 实现创建应用API in backend/src/api/v1/admin/applications.py::create_application (POST /v1/admin/applications)
- [ ] T142 [P] [US5] 实现应用列表API in backend/src/api/v1/admin/applications.py::get_applications (GET /v1/admin/applications)
- [ ] T143 [P] [US5] 实现更新应用价格API in backend/src/api/v1/admin/applications.py::update_application_price (PUT /v1/admin/applications/{app_id}/price)
- [ ] T144 [P] [US5] 实现更新玩家范围API in backend/src/api/v1/admin/applications.py::update_player_range (PUT /v1/admin/applications/{app_id}/player-range)
- [ ] T145 [P] [US5] 实现授权应用API in backend/src/api/v1/admin/operators.py::authorize_application (POST /v1/admin/operators/{operator_id}/applications)
- [ ] T146 [P] [US5] 实现撤销授权API in backend/src/api/v1/admin/operators.py::revoke_authorization (DELETE /v1/admin/operators/{operator_id}/applications/{app_id})
- [ ] T147 [P] [US5] 实现查询授权申请列表API in backend/src/api/v1/admin/app-requests.py::get_app_requests (GET /v1/admin/app-requests)
- [ ] T148 [P] [US5] 实现审批授权申请API in backend/src/api/v1/admin/app-requests.py::approve_app_request (POST /v1/admin/app-requests/{request_id}/approve)
- [ ] T149 [P] [US5] 实现拒绝授权申请API in backend/src/api/v1/admin/app-requests.py::reject_app_request (POST /v1/admin/app-requests/{request_id}/reject)
- [ ] T150 [P] [US5] 实现发布系统公告API in backend/src/api/v1/admin/announcements.py::create_announcement (POST /v1/admin/announcements)
- [ ] T151 [US5] 注册管理员路由 in backend/src/main.py

### 单元测试 (补充)

- [ ] T152 [P] [US5] AdminService单元测试 in backend/tests/unit/services/test_admin_service.py
- [ ] T153 [P] [US5] AdminApplicationService单元测试 in backend/tests/unit/services/test_admin_application_service.py
- [ ] T154 [P] [US5] AdminAuthorizationService单元测试 in backend/tests/unit/services/test_admin_authorization_service.py

**Checkpoint**: User Story 1-5完成 - 管理员可管理整个系统

---

## Phase 8: User Story 6 - 财务后台与审计 (Priority: P3)

**Goal**: 财务人员查看收入概览、审核退款、生成报表、查看审计日志

**Independent Test**: 财务人员登录，查看今日收入仪表盘，审核一笔退款申请并通过，导出本月财务报表，查看审计日志

### 测试任务 (TDD)

- [ ] T155 [P] [US6] 契约测试：财务人员登录接口 in backend/tests/contract/test_finance_login.py (POST /v1/auth/finance/login)
- [ ] T156 [P] [US6] 契约测试：财务仪表盘接口 in backend/tests/contract/test_finance_dashboard.py (GET /v1/finance/dashboard)
- [ ] T157 [P] [US6] 契约测试：退款审核接口 in backend/tests/contract/test_refund_review.py (POST /v1/finance/refunds/{refund_id}/approve)
- [ ] T158 [P] [US6] 集成测试：退款审核流程 in backend/tests/integration/test_refund_review.py (查看详情 → 审核通过 → 记录日志)
- [ ] T159 [P] [US6] 集成测试：财务报表生成 in backend/tests/integration/test_finance_report.py

### 数据模型

- [ ] T160 [P] [US6] 创建FinanceAccount模型 in backend/src/models/finance.py (财务账户表)
- [ ] T161 [P] [US6] 创建FinanceOperationLog模型 in backend/src/models/finance_log.py (财务操作日志表)

### Pydantic Schemas (可并行)

- [ ] T162 [P] [US6] 创建财务登录Schema in backend/src/schemas/auth.py (FinanceLoginRequest, FinanceLoginResponse)
- [ ] T163 [P] [US6] 创建财务仪表盘Schema in backend/src/schemas/finance/dashboard.py (DashboardResponse, RevenueOverview)
- [ ] T164 [P] [US6] 创建退款审核Schema in backend/src/schemas/finance/refund.py (RefundDetailResponse, RefundReviewRequest)
- [ ] T165 [P] [US6] 创建发票审核Schema in backend/src/schemas/finance/invoice.py (InvoiceDetailResponse, InvoiceReviewRequest)
- [ ] T166 [P] [US6] 创建财务报表Schema in backend/src/schemas/finance/report.py (ReportRequest, ReportResponse)
- [ ] T167 [P] [US6] 创建审计日志Schema in backend/src/schemas/finance/audit.py (AuditLogResponse)

### 业务服务

- [ ] T168 [US6] 实现FinanceService in backend/src/services/finance.py (财务人员登录、权限验证)
- [ ] T169 [US6] 实现FinanceDashboardService in backend/src/services/finance_dashboard.py (仪表盘数据聚合、大客户分析)
- [ ] T170 [US6] 实现FinanceRefundService in backend/src/services/finance_refund.py (退款审核、余额重算)
- [ ] T171 [US6] 实现FinanceInvoiceService in backend/src/services/finance_invoice.py (发票审核、开票)
- [ ] T172 [US6] 实现FinanceReportService in backend/src/services/finance_report.py (日/周/月报表生成、PDF导出)
- [ ] T173 [US6] 实现AuditLogService in backend/src/services/audit_log.py (操作日志记录、查询)

### API接口 (可并行)

- [ ] T174 [P] [US6] 实现财务人员登录API in backend/src/api/v1/auth.py::finance_login (POST /v1/auth/finance/login)
- [ ] T175 [P] [US6] 实现财务仪表盘API in backend/src/api/v1/finance/dashboard.py::get_dashboard (GET /v1/finance/dashboard)
- [ ] T176 [P] [US6] 实现今日收入概览API in backend/src/api/v1/finance/dashboard.py::get_today_overview (GET /v1/finance/dashboard/today)
- [ ] T177 [P] [US6] 实现本月趋势API in backend/src/api/v1/finance/dashboard.py::get_month_trend (GET /v1/finance/dashboard/month-trend)
- [ ] T178 [P] [US6] 实现大客户分析API in backend/src/api/v1/finance/customers.py::get_top_customers (GET /v1/finance/customers/top)
- [ ] T179 [P] [US6] 实现客户财务详情API in backend/src/api/v1/finance/customers.py::get_customer_finance (GET /v1/finance/customers/{operator_id}/finance)
- [ ] T180 [P] [US6] 实现退款申请列表API in backend/src/api/v1/finance/refunds.py::get_refunds (GET /v1/finance/refunds)
- [ ] T181 [P] [US6] 实现退款详情API in backend/src/api/v1/finance/refunds.py::get_refund (GET /v1/finance/refunds/{refund_id})
- [ ] T182 [P] [US6] 实现审核通过退款API in backend/src/api/v1/finance/refunds.py::approve_refund (POST /v1/finance/refunds/{refund_id}/approve)
- [ ] T183 [P] [US6] 实现拒绝退款API in backend/src/api/v1/finance/refunds.py::reject_refund (POST /v1/finance/refunds/{refund_id}/reject)
- [ ] T184 [P] [US6] 实现发票申请列表API in backend/src/api/v1/finance/invoices.py::get_invoices (GET /v1/finance/invoices)
- [ ] T185 [P] [US6] 实现审核发票API in backend/src/api/v1/finance/invoices.py::review_invoice (POST /v1/finance/invoices/{invoice_id}/review)
- [ ] T186 [P] [US6] 实现生成财务报表API in backend/src/api/v1/finance/reports.py::generate_report (POST /v1/finance/reports/generate)
- [ ] T187 [P] [US6] 实现导出报表API in backend/src/api/v1/finance/reports.py::export_report (GET /v1/finance/reports/{report_id}/export)
- [ ] T188 [P] [US6] 实现查询审计日志API in backend/src/api/v1/finance/audit-logs.py::get_audit_logs (GET /v1/finance/audit-logs)
- [ ] T189 [US6] 注册财务路由 in backend/src/main.py

### 后台任务 (定时报表生成)

- [ ] T189a [US6] 实现定时财务报表生成任务 in backend/src/tasks/scheduled_reports.py (使用APScheduler，每日凌晨1点生成日报、每周一凌晨生成周报、每月1日凌晨生成月报，报表包含收入统计/大客户数据/使用统计三部分，自动保存到文件系统backend/reports/并记录数据库finance_reports表)
- [ ] T189b [P] [US6] 单元测试：报表生成调度 in backend/tests/unit/tasks/test_scheduled_reports.py (验证调度配置正确、报表生成逻辑、文件保存路径)

### 单元测试 (补充)

- [ ] T190 [P] [US6] FinanceDashboardService单元测试 in backend/tests/unit/services/test_finance_dashboard_service.py
- [ ] T191 [P] [US6] FinanceRefundService单元测试 in backend/tests/unit/services/test_finance_refund_service.py
- [ ] T192 [P] [US6] FinanceReportService单元测试 in backend/tests/unit/services/test_finance_report_service.py

**Checkpoint**: User Story 1-6完成 - 财务人员可审核和生成报表

---

## Phase 9: User Story 7 - 数据统计人员全局报表 (Priority: P3)

**Goal**: 数据统计人员查看全局运营数据、多维度交叉分析、生成统计报表

**Independent Test**: 数据统计人员登录，查看按应用统计报表，筛选"北京区域运营点"显示消费趋势，导出CSV报表

### 测试任务 (TDD)

- [ ] T193 [P] [US7] 契约测试：全局统计仪表盘接口 in backend/tests/contract/test_global_dashboard.py (GET /v1/statistics/dashboard)
- [ ] T194 [P] [US7] 契约测试：多维度分析接口 in backend/tests/contract/test_cross_analysis.py (GET /v1/statistics/cross-analysis)
- [ ] T195 [P] [US7] 集成测试：全局统计查询 in backend/tests/integration/test_global_statistics.py

### Pydantic Schemas (可并行)

- [ ] T196 [P] [US7] 创建全局统计Schema in backend/src/schemas/statistics/global.py (GlobalDashboardResponse, CrossAnalysisRequest)
- [ ] T197 [P] [US7] 创建玩家分布统计Schema in backend/src/schemas/statistics/player_distribution.py (PlayerDistributionResponse)

### 业务服务

- [ ] T198 [US7] 实现GlobalStatisticsService in backend/src/services/global_statistics.py (全局数据聚合、多维度交叉分析)

### API接口 (可并行)

- [ ] T199 [P] [US7] 实现全局统计仪表盘API in backend/src/api/v1/statistics/dashboard.py::get_global_dashboard (GET /v1/statistics/dashboard)
- [ ] T200 [P] [US7] 实现按应用统计API in backend/src/api/v1/statistics/applications.py::get_app_statistics (GET /v1/statistics/by-application)
- [ ] T201 [P] [US7] 实现按运营点统计API in backend/src/api/v1/statistics/sites.py::get_site_statistics (GET /v1/statistics/by-site)
- [ ] T202 [P] [US7] 实现玩家数量分布API in backend/src/api/v1/statistics/players.py::get_player_distribution (GET /v1/statistics/player-distribution)
- [ ] T203 [P] [US7] 实现多维度交叉分析API in backend/src/api/v1/statistics/cross-analysis.py::cross_analysis (POST /v1/statistics/cross-analysis)
- [ ] T204 [P] [US7] 实现导出全局报表API in backend/src/api/v1/statistics/export.py::export_global_report (GET /v1/statistics/export)
- [ ] T205 [US7] 注册统计路由 in backend/src/main.py

### 单元测试 (补充)

- [ ] T206 [P] [US7] GlobalStatisticsService单元测试 in backend/tests/unit/services/test_global_statistics_service.py

**Checkpoint**: User Story 1-7完成 - 数据统计人员可查看全局数据

---

## Phase 10: User Story 8 - 消息通知与系统公告 (Priority: P3)

**Goal**: 运营商接收系统通知、查看消息列表、查看历史公告

**Independent Test**: 管理员发布"太空探险"价格上调公告，运营商登录后看到未读消息提醒，点击查看详情后标记为已读

### 测试任务 (TDD)

- [ ] T207 [P] [US8] 契约测试：消息列表接口 in backend/tests/contract/test_messages.py (GET /v1/operators/me/messages)
- [ ] T208 [P] [US8] 集成测试：消息通知流程 in backend/tests/integration/test_message_notification.py (发布公告 → 接收消息 → 标记已读)

### 数据模型

- [ ] T209 [P] [US8] 创建MessageNotification模型 in backend/src/models/message.py (消息通知表)
- [ ] T210 [P] [US8] 创建MessageReceipt模型 in backend/src/models/message_receipt.py (消息接收表，记录已读状态)

### Pydantic Schemas (可并行)

- [ ] T211 [P] [US8] 创建消息Schema in backend/src/schemas/message.py (MessageResponse, MessageListResponse)
- [ ] T212 [P] [US8] 创建公告Schema in backend/src/schemas/announcement.py (AnnouncementResponse)

### 业务服务

- [ ] T213 [US8] 实现MessageService in backend/src/services/message.py (消息发送、余额不足提醒、价格调整通知)
- [ ] T214 [US8] 实现NotificationService in backend/src/services/notification.py (消息推送、已读状态管理)

### API接口 (可并行)

- [ ] T215 [P] [US8] 实现消息列表API in backend/src/api/v1/operators.py::get_messages (GET /v1/operators/me/messages)
- [ ] T216 [P] [US8] 实现消息详情API in backend/src/api/v1/operators.py::get_message (GET /v1/operators/me/messages/{message_id})
- [ ] T217 [P] [US8] 实现标记已读API in backend/src/api/v1/operators.py::mark_message_read (POST /v1/operators/me/messages/{message_id}/read)
- [ ] T218 [P] [US8] 实现未读数量API in backend/src/api/v1/operators.py::get_unread_count (GET /v1/operators/me/messages/unread-count)
- [ ] T219 [P] [US8] 实现批量标记已读API in backend/src/api/v1/operators.py::mark_all_read (POST /v1/operators/me/messages/mark-all-read)

### 后台任务 (异步通知)

- [ ] T220 [US8] 实现余额不足定时检查任务 in backend/src/tasks/balance_check.py (每小时检查余额<100元的运营商并发送提醒)
- [ ] T221 [US8] 实现价格调整自动通知任务 in backend/src/tasks/price_change_notify.py (应用价格调整时自动通知所有授权运营商)

### 单元测试 (补充)

- [ ] T222 [P] [US8] MessageService单元测试 in backend/tests/unit/services/test_message_service.py
- [ ] T223 [P] [US8] NotificationService单元测试 in backend/tests/unit/services/test_notification_service.py

**Checkpoint**: 所有8个用户故事完成 - 系统功能完整

---

## Phase 11: Frontend (前端开发)

**Purpose**: 构建运营商、管理员、财务三端Web界面

### 前端基础设施

- [ ] T224 配置Vue Router in frontend/src/router/index.ts (三端路由: /operator, /admin, /finance)
- [ ] T225 配置Pinia状态管理 in frontend/src/stores/ (auth, user, config)
- [ ] T226 配置Axios HTTP客户端 in frontend/src/utils/http.ts (拦截器、错误处理)
- [ ] T227 [P] 实现通用组件 in frontend/src/components/ (LoadingSpinner, Pagination, DataTable, Chart)
- [ ] T228 [P] 实现认证Guard in frontend/src/router/guards.ts (JWT验证、权限检查)

### 运营商端前端 (15个页面)

- [ ] T229 [P] 实现运营商登录页 in frontend/src/pages/operator/Login.vue
- [ ] T230 [P] 实现运营商注册页 in frontend/src/pages/operator/Register.vue
- [ ] T231 [P] 实现仪表盘页面 in frontend/src/pages/operator/Dashboard.vue (余额、消费概览)
- [ ] T232 [P] 实现账户管理页 in frontend/src/pages/operator/Profile.vue
- [ ] T233 [P] 实现充值页面 in frontend/src/pages/operator/Recharge.vue
- [ ] T234 [P] 实现交易记录页 in frontend/src/pages/operator/Transactions.vue
- [ ] T235 [P] 实现退款申请页 in frontend/src/pages/operator/Refunds.vue
- [ ] T236 [P] 实现发票申请页 in frontend/src/pages/operator/Invoices.vue
- [ ] T237 [P] 实现运营点管理页 in frontend/src/pages/operator/Sites.vue
- [ ] T238 [P] 实现已授权应用页 in frontend/src/pages/operator/Applications.vue
- [ ] T239 [P] 实现应用授权申请页 in frontend/src/pages/operator/AppRequests.vue
- [ ] T240 [P] 实现使用记录页 in frontend/src/pages/operator/UsageRecords.vue
- [ ] T241 [P] 实现消费统计页 in frontend/src/pages/operator/Statistics.vue (ECharts图表)
- [ ] T242 [P] 实现消息中心页 in frontend/src/pages/operator/Messages.vue
- [ ] T243 [P] 实现数据导出页 in frontend/src/pages/operator/Export.vue
- [ ] T243a [P] 实现前端Vue组件单元测试 in frontend/tests/unit/ (使用Vitest，至少覆盖核心业务组件：Dashboard.vue、Recharge.vue、Statistics.vue，验证数据渲染、用户交互、API调用)

### 管理员端前端 (10个页面)

- [ ] T244 [P] 实现管理员登录页 in frontend/src/pages/admin/Login.vue
- [ ] T245 [P] 实现管理员仪表盘 in frontend/src/pages/admin/Dashboard.vue
- [ ] T246 [P] 实现运营商列表页 in frontend/src/pages/admin/Operators.vue
- [ ] T247 [P] 实现运营商详情页 in frontend/src/pages/admin/OperatorDetail.vue
- [ ] T248 [P] 实现创建运营商页 in frontend/src/pages/admin/CreateOperator.vue
- [ ] T249 [P] 实现应用管理页 in frontend/src/pages/admin/Applications.vue
- [ ] T250 [P] 实现创建应用页 in frontend/src/pages/admin/CreateApplication.vue
- [ ] T251 [P] 实现授权申请审批页 in frontend/src/pages/admin/AppRequests.vue
- [ ] T252 [P] 实现授权管理页 in frontend/src/pages/admin/Authorizations.vue
- [ ] T253 [P] 实现系统公告页 in frontend/src/pages/admin/Announcements.vue

### 财务端前端 (5个页面)

- [ ] T254 [P] 实现财务登录页 in frontend/src/pages/finance/Login.vue
- [ ] T255 [P] 实现财务仪表盘 in frontend/src/pages/finance/Dashboard.vue (收入概览、大客户分析)
- [ ] T256 [P] 实现退款审核页 in frontend/src/pages/finance/Refunds.vue
- [ ] T257 [P] 实现发票审核页 in frontend/src/pages/finance/Invoices.vue
- [ ] T258 [P] 实现财务报表页 in frontend/src/pages/finance/Reports.vue (生成和导出)
- [ ] T259 [P] 实现审计日志页 in frontend/src/pages/finance/AuditLogs.vue

**Checkpoint**: 前端三端功能完整

---

## Phase 12: SDK (头显Server集成SDK)

**Purpose**: 提供Python/Node.js/C# SDK方便头显Server集成

### Python SDK

- [ ] T260 实现Python SDK客户端 in sdk/python/mr_auth_sdk/client.py (API Key认证、HMAC签名、授权请求)
- [ ] T261 [P] 实现Python SDK模型 in sdk/python/mr_auth_sdk/models.py
- [ ] T262 [P] 实现Python SDK异常 in sdk/python/mr_auth_sdk/exceptions.py
- [ ] T263 [P] 创建Python SDK示例 in sdk/python/examples/authorize_game.py
- [ ] T264 [P] 实现Python SDK测试 in sdk/python/tests/test_client.py

### Node.js SDK

- [ ] T265 [P] 实现Node.js SDK客户端 in sdk/nodejs/src/client.ts
- [ ] T266 [P] 实现Node.js SDK类型定义 in sdk/nodejs/src/types.ts
- [ ] T267 [P] 创建Node.js SDK示例 in sdk/nodejs/examples/authorize_game.js
- [ ] T268 [P] 实现Node.js SDK测试 in sdk/nodejs/tests/client.test.ts

### C# SDK

- [ ] T269 [P] 实现C# SDK客户端 in sdk/csharp/MRAuthSDK/MRAuthClient.cs
- [ ] T270 [P] 实现C# SDK模型 in sdk/csharp/MRAuthSDK/Models/
- [ ] T271 [P] 创建C# SDK示例 in sdk/csharp/Examples/AuthorizeGame.cs
- [ ] T272 [P] 实现C# SDK测试 in sdk/csharp/Tests/MRAuthClientTests.cs

**Checkpoint**: SDK完成，头显Server可以集成

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: 改进代码质量、性能优化、文档完善

### 性能优化

- [ ] T273 [P] 优化数据库查询性能 (添加缺失索引、N+1问题修复)
- [ ] T274 [P] 实现Redis缓存热点数据 (应用信息、运营商余额)
- [ ] T275 [P] 优化API响应时间 (数据库连接池、异步处理)

### 安全加固

- [ ] T276 [P] 实现HTTPS强制重定向 in backend/src/main.py (包含TLS 1.3配置验证，拒绝TLS 1.2及以下版本连接)
- [ ] T277 [P] 实现敏感数据加密存储 (使用T026a的encryption.py工具类，对运营商API Key、支付平台密钥、JWT Secret进行AES-256-GCM加密后存储数据库)
- [ ] T278 [P] 实现异常IP检测服务 in backend/src/services/security/ip_monitor.py (实现FR-056检测规则：单IP 5分钟内失败>20次、1分钟内使用不同API Key>5个，检测触发后自动锁定关联账户operator_accounts.is_locked=true并发送告警邮件给管理员，响应时间<1分钟)
- [ ] T278a [P] 集成测试：异常IP检测与锁定 in backend/tests/integration/test_ip_detection.py (模拟暴力攻击场景：连续失败25次、切换6个API Key，验证账户锁定operator_accounts.is_locked=true、验证告警邮件发送、验证锁定后授权请求返回HTTP 403)
- [ ] T278b [P] 单元测试：IP检测规则引擎 in backend/tests/unit/services/test_ip_monitor.py (验证失败计数器、API Key追踪、锁定触发逻辑)

### 文档和部署

- [ ] T279 [P] 更新API文档 in docs/api/ (Swagger UI)
- [ ] T280 [P] 更新README in README.md (项目介绍、快速开始、部署指南)
- [ ] T281 [P] 创建部署配置 in deploy/ (Dockerfile, docker-compose.prod.yml, Nginx配置)
- [ ] T282 [P] 配置CI/CD流程 in .github/workflows/ci.yml (自动测试、构建、部署)

### 测试覆盖率

- [ ] T283 [P] 补充单元测试达到80%覆盖率 in backend/tests/unit/
- [ ] T284 [P] 实现性能测试 in backend/tests/performance/ (Locust压力测试)
- [ ] T285 [P] 实现端到端测试 in frontend/tests/e2e/ (Playwright)

### 最终验证

- [ ] T286 运行quickstart.md验证完整流程 (从环境搭建到首次授权)
- [ ] T287 运行所有测试套件并生成报告
- [ ] T288 代码审查和重构
- [ ] T289 性能基准测试 in backend/tests/performance/test_benchmark.py (授权API P95 < 100ms满足NFR-001, 峰值吞吐量 ≥ 20 req/s满足NFR-002, 10万条记录导出<30秒满足SC-009/NFR-004, 系统可用性≥99.5%验证SC-011/NFR-005)
- [ ] T289a [P] 编写性能基线测试 in backend/tests/performance/test_baseline.py (在优化前建立性能基线：当前授权API响应时间P50/P95/P99、数据库查询耗时、内存占用，优化后对比验证改进效果，遵循TDD原则不跳过测试)
- [ ] T290 [P] 实现客户分类自动更新任务 in backend/src/tasks/tier_recalculation.py (使用APScheduler，每月1日凌晨2点根据上月消费额自动重新计算所有运营商客户分类：≥10000元→VIP、1000-10000元→普通、<1000元→试用，记录变更日志)

**Checkpoint**: 项目完成，可以投入生产

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 - 可立即开始
- **Foundational (Phase 2)**: 依赖Phase 1完成 - **阻塞所有用户故事**
- **User Stories (Phase 3-10)**: 全部依赖Phase 2完成
  - 用户故事可以并行实现 (如果有多个开发人员)
  - 或按优先级顺序实现 (P1 → P2 → P3)
- **Frontend (Phase 11)**: 依赖对应用户故事的后端API完成
- **SDK (Phase 12)**: 依赖US1(游戏授权API)完成
- **Polish (Phase 13)**: 依赖所有期望的用户故事完成

### User Story Dependencies

- **User Story 1 (P1)**: 可在Phase 2后开始 - 无其他故事依赖
- **User Story 2 (P1)**: 可在Phase 2后开始 - 无其他故事依赖
- **User Story 3 (P2)**: 可在Phase 2后开始 - 无其他故事依赖
- **User Story 4 (P2)**: 依赖US1(使用记录已生成) - 但可独立测试
- **User Story 5 (P2)**: 可在Phase 2后开始 - 无其他故事依赖
- **User Story 6 (P3)**: 依赖US2(退款、发票功能) - 但可独立测试
- **User Story 7 (P3)**: 依赖US1(使用记录已生成) - 但可独立测试
- **User Story 8 (P3)**: 可在Phase 2后开始 - 无其他故事依赖

### Within Each User Story

- 测试 **MUST** 先写并失败 (TDD原则)
- 模型 → 服务 → 接口
- 核心实现 → 集成
- 故事完成后验证独立性再进入下一个优先级

### Parallel Opportunities

- Phase 1内所有[P]任务可并行
- Phase 2内所有[P]任务可并行 (T013-T029)
- Phase 2完成后，所有用户故事可并行开始 (如果团队容量允许)
- 每个故事内的[P]任务可并行:
  - 所有测试可并行
  - 所有模型可并行
  - 所有Schemas可并行
  - 所有API接口可并行
- 不同用户故事可由不同团队成员并行工作

---

## Parallel Example: User Story 1

```bash
# 同时启动User Story 1的所有测试 (TDD - 先写测试):
Task: "契约测试：游戏授权接口 in backend/tests/contract/test_game_authorize.py"
Task: "集成测试：完整授权流程 in backend/tests/integration/test_authorization_flow.py"
Task: "集成测试：余额不足场景 in backend/tests/integration/test_insufficient_balance.py"
Task: "集成测试:会话ID幂等性 in backend/tests/integration/test_session_idempotency.py"
Task: "集成测试:玩家数量范围验证 in backend/tests/integration/test_player_count_validation.py"
Task: "集成测试:并发扣费冲突处理 in backend/tests/integration/test_concurrent_billing.py"

# 同时创建User Story 1的所有模型:
Task: "创建OperatorAccount模型 in backend/src/models/operator.py"
Task: "创建Application模型 in backend/src/models/application.py"
Task: "创建OperationSite模型 in backend/src/models/site.py"
Task: "创建UsageRecord模型 in backend/src/models/usage_record.py"
Task: "创建TransactionRecord模型 in backend/src/models/transaction.py"
Task: "创建OperatorAppAuthorization模型 in backend/src/models/authorization.py"

# 同时创建User Story 1的所有Schemas:
Task: "创建授权请求Schema in backend/src/schemas/auth.py"
Task: "创建使用记录Schema in backend/src/schemas/usage.py"
Task: "创建交易记录Schema in backend/src/schemas/transaction.py"
```

---

## Implementation Strategy

### MVP First (仅User Story 1)

1. 完成Phase 1: Setup
2. 完成Phase 2: Foundational (CRITICAL - 阻塞所有故事)
3. 完成Phase 3: User Story 1 (游戏授权与计费)
4. **STOP并验证**: 独立测试User Story 1
5. 准备演示/部署 (如果需要)

### Incremental Delivery (增量交付)

1. Setup + Foundational → 基础就绪
2. 添加User Story 1 → 独立测试 → 部署/演示 (MVP!)
3. 添加User Story 2 → 独立测试 → 部署/演示
4. 添加User Story 3 → 独立测试 → 部署/演示
5. 每个故事都增加价值且不破坏之前的故事

### Parallel Team Strategy (并行团队策略)

多个开发人员时:

1. 团队一起完成Setup + Foundational
2. Foundational完成后:
   - 开发者A: User Story 1
   - 开发者B: User Story 2
   - 开发者C: User Story 5 (管理员功能)
3. 故事独立完成并集成

### 优先级指导

- **P1优先**: US1(授权计费) + US2(财务管理) - 核心业务价值
- **P2次要**: US3(运营点管理) + US4(统计分析) + US5(管理员功能) - 完善功能
- **P3可选**: US6(财务后台) + US7(全局统计) + US8(消息通知) - 增值功能

---

## Notes

- **[P] tasks**: 不同文件，无依赖，可并行
- **[Story] label**: 将任务映射到具体用户故事，便于追溯
- **每个用户故事应独立可完成和测试**
- **验证测试失败后再实现** (TDD)
- **在每个任务或逻辑组后提交**
- **在任何Checkpoint处停下来独立验证故事**
- **避免**: 模糊任务、相同文件冲突、破坏独立性的跨故事依赖

---

## 实施要点总结

1. **TDD原则**: 所有用户故事都先写契约测试和集成测试，确保失败后再实现
2. **幂等性保证**: 游戏授权使用会话ID防重复扣费，支付回调验证避免重复充值
3. **并发安全**: 余额扣费使用数据库行级锁(SELECT FOR UPDATE)保证原子性
4. **财务精确性**: 所有金额使用DECIMAL(10,2)类型，避免浮点精度问题
5. **审计合规**: 所有敏感操作记录审计日志(操作人、时间、IP、详情)
6. **性能目标**: 授权API P95 < 100ms, 系统吞吐量 ≥ 20 req/s峰值 (小规模部署)
7. **独立测试**: 每个用户故事完成后应能独立测试，不依赖其他故事
8. **配置外部化**: 价格、阈值、超时等配置存储在数据库或环境变量，零硬编码

**总任务数**: 303个任务 (原289 + 新增14个安全/监控/测试任务)

**新增任务摘要**:
- Phase 1: T005a (OpenAPI契约生成)
- Phase 2: T010a, T017a/b, T018a/b, T026a/b (基础设施测试和加密工具)
- Phase 3: T033a (会话ID格式验证测试)
- Phase 8: T189a/b (定时财务报表生成)
- Phase 11: T243a (前端单元测试)
- Phase 13: T278a/b, T289a, T290 (安全加固、性能基线、客户分类任务)

**预计工作量**:
- 1个全栈开发人员: 约3-4个月 (按优先级顺序)
- 3个开发人员并行: 约1.5-2个月 (Foundational → 并行实现用户故事)

祝开发顺利！🚀
