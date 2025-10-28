<!--
SYNC IMPACT REPORT
==================
Version: 1.0.3 (AI Agent Autonomous Execution Principle Addition)
Ratification Date: 2025-10-10
Last Amended: 2025-10-17

Amendment Summary:
- 新增原则VII: AI Agent自主执行原则 (AI Agent Autonomous Execution Principle)
- 理由: AI Agent 应在既定框架内自主决策和执行，避免频繁打断用户，提高开发效率
- 影响范围: AI Agent 工作流程，决策机制，用户交互模式

Previous Amendments:
- v1.0.2 (2025-10-17): 新增原则VI - 端到端测试原则，要求使用 Playwright 进行 E2E 测试
- v1.0.1 (2025-10-13): 性能约束调整，系统吞吐量从≥1000 req/s调整为≥20 req/s (小规模部署场景)

Principles Defined:
- I. 测试驱动开发 (Test-Driven Development)
- II. 零硬编码原则 (Zero Hardcoding)
- III. 业务逻辑完整性 (Business Logic Integrity)
- IV. API契约优先 (API Contract First)
- V. 可观测性与审计 (Observability & Audit)
- VI. 端到端测试原则 (End-to-End Testing)
- VII. AI Agent自主执行原则 (AI Agent Autonomous Execution) - NEW

Sections Added:
- 架构约束 (Architecture Constraints)
- 质量保证 (Quality Assurance)
- 治理规则 (Governance)

Templates Status:
✅ plan-template.md - Aligned with constitution principles
✅ spec-template.md - User story structure supports TDD
✅ tasks-template.md - Task organization supports testing-first approach

Follow-up TODOs:
- [ ] 更新 plan.md 删除 Complexity Tracking 表中的性能偏离记录
- [ ] 在 CI/CD 流程中集成 Playwright E2E 测试
-->

# MR游戏运营管理系统 Constitution

## Core Principles

### I. 测试驱动开发 (Test-Driven Development)

**规则 (NON-NEGOTIABLE)**:
- 所有功能实现必须遵循 Red-Green-Refactor 周期
- 测试必须先于实现编写，并在实现前验证失败
- 每个用户故事必须包含独立的验收测试场景
- 单元测试覆盖率不得低于80%，核心业务逻辑必须达到100%
- 集成测试必须覆盖所有API端点和外部系统交互

**理由**: MR游戏授权系统涉及实时计费和扣款，任何错误都可能导致财务损失或服务中断。TDD确保每个功能在部署前都经过严格验证，降低生产环境风险。

### II. 零硬编码原则 (Zero Hardcoding)

**规则 (MANDATORY)**:
- 禁止在代码中硬编码任何业务配置（价格、时长、玩家数限制等）
- 所有配置必须外部化（环境变量、配置文件、数据库配置表）
- 业务规则必须通过规则引擎或可配置策略实现
- 魔法数字必须定义为有意义的常量或配置项
- API端点、数据库连接等基础设施信息必须环境化

**理由**: 游戏运营需求变化频繁（价格调整、促销活动、规则变更）。硬编码会导致每次调整都需要重新部署，增加风险和运维成本。可配置化设计使运营人员能够快速响应市场变化。

### III. 业务逻辑完整性 (Business Logic Integrity)

**规则 (STRICT)**:
- 所有业务逻辑必须实现真实的计算和验证，禁止占位符或模拟实现
- 授权验证必须包含完整的权限检查、配额验证、状态机转换
- 计费逻辑必须处理所有边界情况（并发游戏、异常终止、退款场景）
- 数据一致性必须通过事务保证，关键操作必须支持幂等性
- 错误处理必须覆盖所有异常路径，不得使用通用catch-all

**理由**: 游戏授权和计费是核心业务流程，不完整的逻辑会导致收入损失或用户纠纷。所有逻辑必须在第一次实现时就达到生产级质量标准。

### IV. API契约优先 (API Contract First)

**规则 (REQUIRED)**:
- 所有API必须先定义OpenAPI/Swagger规范，后实现代码
- 契约必须包含完整的请求/响应模式、错误码、认证方式
- 契约变更必须遵循语义化版本控制（破坏性变更 = MAJOR版本）
- 所有API必须包含契约测试（Contract Tests），验证实现与规范一致性
- 现场服务器集成前必须提供详细的API文档和示例代码

**理由**: 现场服务器依赖API进行游戏授权，契约变更可能导致服务中断。契约优先方法确保API设计经过充分考虑，减少后期返工。

### V. 可观测性与审计 (Observability & Audit)

**规则 (MANDATORY)**:
- 所有关键操作必须记录结构化日志（JSON格式，包含trace_id、user_id、operation）
- 游戏授权和计费事件必须写入审计日志（不可变、可追溯）
- 系统必须暴露监控指标（授权成功率、响应时间、计费金额等）
- 错误必须包含上下文信息（用户、操作、输入参数），便于问题排查
- 关键业务流程必须支持分布式追踪（end-to-end visibility）

**理由**: 运营系统需要实时监控业务健康度，审计日志是财务对账和纠纷解决的依据。完善的可观测性能够快速定位和解决生产问题。

### VI. 端到端测试原则 (End-to-End Testing)

**规则 (MANDATORY)**:
- 所有前端核心用户流程必须实施自动化 E2E 测试，使用 Playwright 框架
- 每个用户角色（管理员、运营商）的关键业务路径必须有对应的 E2E 测试用例
- E2E 测试覆盖率必须达到≥90%的核心用户流程（登录、核心业务操作、数据查询、异常处理）
- 所有 E2E 测试必须在 CI 环境中自动运行，测试失败阻止部署
- 测试失败时必须自动生成调试资源（截图、视频录制、Playwright trace）
- E2E 测试套件总执行时间必须 < 5分钟，保证快速反馈
- 测试用例必须独立运行，不依赖其他测试的状态或执行顺序

**理由**: 前端用户界面是系统的关键交互层，涉及复杂的用户操作流程（充值、授权申请、统计查询等）。手动测试无法保证每次变更后所有流程的完整性。自动化 E2E 测试能够在代码变更时快速验证完整的用户体验，防止 UI 破坏性变更进入生产环境，同时为重构和优化提供安全网。

**测试范围要求**:
- **管理员端**: 登录、Dashboard加载、运营商列表（搜索/筛选/分页）、应用列表（搜索/详情）、授权申请审核（通过/拒绝）、侧边栏导航、退出登录
- **运营商端**: 登录、注册、充值流程、应用授权申请、运营点管理、使用记录查询、统计图表显示
- **异常场景**: 网络错误处理、表单验证错误、权限不足提示、会话过期处理

### VII. AI Agent自主执行原则 (AI Agent Autonomous Execution)

**规则 (MANDATORY)**:
- AI Agent 必须按照任务列表（tasks.md）、优先级和依赖关系自主决策并推进实施
- AI Agent 应持续执行任务直至完成或遇到阻塞，无需在每个小决策点请求用户批准
- **仅在以下情况才询问用户**：
  - 遇到技术障碍无法自行解决（如关键依赖缺失、环境错误）
  - 需求规格存在歧义或矛盾，需要业务决策
  - 发现重大架构问题，可能需要偏离原计划
  - 需要用户提供外部信息（如API密钥、账号凭证）
  - 操作可能产生破坏性影响（如删除数据、修改核心配置）
- **不应询问的情况**：
  - 选择下一个要执行的任务（应自动按优先级选择）
  - 常规代码实现细节（如选择哪个库、如何组织代码）
  - 是否继续执行后续任务（应自动继续）
  - 提供多个选项让用户选择（应自己评估并决策）
  - 本次会话消耗了大量token和时间，总结当前进展并汇报
- AI Agent 应定期汇报关键进度节点（Phase完成、User Story完成），但无需等待批准即可继续
- 遇到测试失败时，AI Agent 应自动分析原因并修复，除非多次尝试仍失败

**理由**: 频繁打断用户会降低开发效率，AI Agent 应像一个经验丰富的开发者一样自主工作。用户已通过 constitution.md、spec.md、tasks.md 提供了完整的决策框架，AI Agent 应在此框架内自主执行。只有真正需要人类判断的重大决策才应询问用户。

## 架构约束

### 技术栈要求
- **后端语言**: Python 3.11+ 或 Node.js 18+ (基于团队技术栈选择)
- **API框架**: FastAPI (Python) 或 Express.js (Node.js)，必须支持OpenAPI自动生成
- **数据库**: PostgreSQL 14+ (事务支持) + Redis (缓存和分布式锁)
- **认证**: OAuth 2.0 或 API Key + HMAC签名（现场服务器认证）
- **部署**: 容器化（Docker），支持水平扩展和零停机部署

### 安全要求
- 所有外部API必须使用HTTPS（TLS 1.3+）
- 敏感数据（API密钥、支付信息）必须加密存储
- 授权令牌必须设置合理的过期时间（建议≤24小时）
- 必须实现请求频率限制（Rate Limiting），防止滥用
- 生产环境必须启用审计日志，记录所有管理员操作

### 性能约束
- API响应时间：P95 < 200ms（授权接口 < 100ms）
- 系统吞吐量：支持至少20次/秒的授权请求（小规模部署场景，可水平扩展至更高吞吐量）
- 数据库查询：单次查询 < 50ms，避免N+1问题
- 缓存策略：热点数据（价格配置、用户额度）必须缓存，TTL根据业务特性设定

## 质量保证

### 代码审查要求
- 所有代码变更必须通过Pull Request，禁止直接提交到主分支
- PR必须包含：测试用例、文档更新、宪章合规性自查
- 至少一名团队成员审查通过后方可合并
- 核心模块（授权、计费）变更需要技术负责人批准

### 发布流程
- 必须在预发布环境验证所有变更
- 数据库迁移必须支持回滚（使用migration工具）
- 重大变更必须制定降级方案（feature flag、蓝绿部署）
- 发布后必须监控关键指标至少1小时

### 技术债务管理
- 禁止以"技术债务"为由跳过测试或简化实现
- 复杂度违规（如引入额外依赖、偏离架构模式）必须在代码审查中说明理由
- 发现的bug必须在修复时补充回归测试

## Governance

### 宪章修订流程
- 本宪章优先级高于所有其他开发实践
- 修订需经团队讨论，记录修订理由和影响范围
- 重大变更（原则删除或重新定义）需全员同意
- 修订后必须更新所有依赖文档（模板、流程指南）

### 合规性检查
- 每个功能的Implementation Plan必须包含Constitution Check章节
- 代码审查必须验证宪章合规性（测试覆盖率、配置外部化、日志完整性）
- 违规情况必须在Complexity Tracking表中说明理由和替代方案

### 版本控制
- 宪章版本遵循语义化版本控制：MAJOR.MINOR.PATCH
- MAJOR: 破坏性变更（原则删除、强制要求变更）
- MINOR: 新增原则或章节、扩展现有指导
- PATCH: 措辞优化、错误修正、澄清说明

**Version**: 1.0.3 | **Ratified**: 2025-10-10 | **Last Amended**: 2025-10-17
