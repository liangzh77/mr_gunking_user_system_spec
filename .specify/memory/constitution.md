<!--
SYNC IMPACT REPORT
==================
Version: 1.0.0 (Initial Constitution)
Ratification Date: 2025-10-10
Last Amended: 2025-10-10

Principles Defined:
- I. 测试驱动开发 (Test-Driven Development)
- II. 零硬编码原则 (Zero Hardcoding)
- III. 业务逻辑完整性 (Business Logic Integrity)
- IV. API契约优先 (API Contract First)
- V. 可观测性与审计 (Observability & Audit)

Sections Added:
- 架构约束 (Architecture Constraints)
- 质量保证 (Quality Assurance)
- 治理规则 (Governance)

Templates Status:
✅ plan-template.md - Aligned with constitution principles
✅ spec-template.md - User story structure supports TDD
✅ tasks-template.md - Task organization supports testing-first approach

Follow-up TODOs: None
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
- 系统吞吐量：支持至少1000次/秒的授权请求
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

**Version**: 1.0.0 | **Ratified**: 2025-10-10 | **Last Amended**: 2025-10-10
