# SpecKit 使用指南

> 完整的 SpecKit 工作流使用手册 - 从项目初始化到功能实现的完整开发流程

## 📋 目录

- [什么是 SpecKit](#什么是-speckit)
- [核心命令概览](#核心命令概览)
- [完整工作流](#完整工作流)
- [命令详解](#命令详解)
- [实际使用示例](#实际使用示例)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

---

## 什么是 SpecKit

SpecKit 是一套专为软件项目设计的**规范驱动开发工具链**，帮助团队：

- **定义项目宪章** (Constitution) - 确立不可违背的核心原则和约束
- **编写功能规格** (Specification) - 结构化描述功能需求和验收标准
- **制定实施计划** (Plan) - 设计技术方案和架构决策
- **生成任务列表** (Tasks) - 将计划分解为可执行的开发任务
- **执行实施** (Implementation) - 按照任务列表完成开发

SpecKit 确保从需求到实现的**全流程可追溯、可验证、可审计**。

---

## 核心命令概览

| 命令 | 用途 | 输出文件 | 使用时机 |
|------|------|----------|----------|
| `/speckit.constitution` | 创建/更新项目宪章 | `.specify/memory/constitution.md` | 项目初始化，或新增核心原则时 |
| `/speckit.specify` | 创建/更新功能规格 | `specs/{feature-id}/spec.md` | 开始新功能开发前 |
| `/speckit.plan` | 执行实施规划工作流 | `specs/{feature-id}/plan.md` | 规格确认后，开发前 |
| `/speckit.tasks` | 生成任务列表 | `specs/{feature-id}/tasks.md` | 计划完成后，开始编码前 |
| `/speckit.implement` | 执行实施任务 | 代码文件 | 任务列表生成后 |
| `/speckit.clarify` | 澄清规格中的模糊点 | 更新 `spec.md` | 发现需求不清晰时 |
| `/speckit.checklist` | 生成功能验收清单 | `specs/{feature-id}/checklists/{name}.md` | 需要定制化验收流程时 |
| `/speckit.analyze` | 跨文档一致性分析 | 控制台输出 | 任务生成后，实施前 |

---

## 完整工作流

### 阶段 0️⃣: 项目初始化（只做一次）

```bash
/speckit.constitution <项目核心原则描述>
```

**示例输入**:
```
/speckit.constitution 我们正在开发一个游戏运营管理系统，核心原则包括：
1. 测试驱动开发 - 所有代码必须先写测试
2. 零硬编码 - 业务配置必须外部化
3. API契约优先 - 先定义OpenAPI规范再实现
4. 完整的审计日志 - 所有财务操作可追溯
5. 端到端测试 - 使用Playwright覆盖核心用户流程
```

**输出**: 生成 `.specify/memory/constitution.md`，包含项目宪章和治理规则。

---

### 阶段 1️⃣: 功能规格定义

```bash
/speckit.specify <功能描述>
```

**示例输入**:
```
/speckit.specify 实现管理员管理运营商账户的功能，包括：
- 查看运营商列表（支持搜索、筛选、分页）
- 查看运营商详情（基本信息、余额、使用统计）
- 锁定/解锁运营商账户
- 查看运营商的操作审计日志
```

**输出**: 生成 `specs/001-xxx/spec.md`，包含：
- User Stories（用户故事）
- Acceptance Criteria（验收标准）
- API Contracts（API规范）
- Data Models（数据模型）
- Non-Functional Requirements（非功能性需求）

**可选：澄清模糊点**
```bash
/speckit.clarify
```
系统会自动识别规格中的不明确之处，提出最多5个针对性问题，将回答编码回规格文档。

---

### 阶段 2️⃣: 实施计划设计

```bash
/speckit.plan
```

**说明**:
- 无需额外参数，自动读取当前功能的 `spec.md`
- 使用规划模板生成详细的技术设计方案

**输出**: 生成 `specs/001-xxx/plan.md`，包含：
- Architecture Overview（架构概览）
- Technology Stack（技术栈选择）
- Implementation Steps（实施步骤）
- Database Schema（数据库设计）
- API Endpoints（接口设计）
- Test Strategy（测试策略）
- Complexity Tracking（复杂度追踪）

---

### 阶段 3️⃣: 任务分解

```bash
/speckit.tasks
```

**说明**:
- 基于 `plan.md` 和 `spec.md` 生成具体的开发任务
- 任务按依赖关系排序，标注优先级

**输出**: 生成 `specs/001-xxx/tasks.md`，包含：
- 后端任务（数据模型、API、业务逻辑、测试）
- 前端任务（页面、组件、状态管理、路由）
- 集成任务（E2E测试、部署配置）

**可选：一致性检查**
```bash
/speckit.analyze
```
非破坏性分析 spec.md、plan.md、tasks.md 之间的一致性，发现潜在问题。

---

### 阶段 4️⃣: 执行实施

```bash
/speckit.implement
```

**说明**:
- 按 `tasks.md` 中的任务顺序逐一实施
- 自动跟踪任务完成状态
- 遵循宪章中的原则（TDD、代码审查等）

**输出**:
- 生成/修改代码文件
- 更新任务状态
- 运行测试验证

---

### 阶段 5️⃣: 验收与交付（可选）

```bash
/speckit.checklist <验收场景描述>
```

**示例输入**:
```
/speckit.checklist 管理员运营商管理功能验收清单
```

**输出**: 生成 `specs/001-xxx/checklists/operator-management.md`，包含：
- 功能验收项
- 性能验收项
- 安全验收项
- 文档完整性检查

---

## 命令详解

### `/speckit.constitution`

**作用**: 创建或更新项目宪章（Constitution），定义项目的核心原则、架构约束、质量标准。

**使用场景**:
- 项目启动时，定义初始宪章
- 团队共识发生变化时，修订宪章
- 发现新的关键约束时，增补原则

**输入格式**:
```
/speckit.constitution <原则描述>

示例：
/speckit.constitution 新增原则：所有前端核心流程必须有Playwright E2E测试，覆盖率≥90%
```

**关键输出**:
- **Core Principles**: 不可违背的开发原则（如TDD、零硬编码）
- **Architecture Constraints**: 技术栈、安全、性能要求
- **Quality Assurance**: 代码审查、发布流程、技术债管理
- **Governance**: 宪章修订流程、合规性检查

**最佳实践**:
- 原则应具体、可执行、可验证（避免"代码要优雅"这种模糊表述）
- 每条原则必须说明**理由**，帮助团队理解背后的动机
- 重大修订需团队评审，记录在 `SYNC IMPACT REPORT` 中

---

### `/speckit.specify`

**作用**: 将自然语言功能需求转化为结构化的功能规格文档。

**使用场景**:
- 接到新功能需求时
- 现有功能需要重大改造时
- 需要补充缺失的规格文档时

**输入格式**:
```
/speckit.specify <详细功能描述>

示例：
/speckit.specify 实现运营商充值功能：
- 支持支付宝、微信、银行卡三种支付方式
- 充值金额限制：单笔100-10000元
- 充值成功后发送短信通知
- 所有充值记录必须可查询和导出
- 充值失败自动退款
```

**关键输出**:
- **User Stories**: 以用户视角描述功能（As a... I want... So that...）
- **Acceptance Criteria**: 可测试的验收条件
- **API Contracts**: RESTful API 规范（请求/响应/错误码）
- **Data Models**: 数据库表结构、字段约束
- **NFRs**: 性能指标、安全要求、可维护性标准

**最佳实践**:
- 输入时尽量详细，包含边界条件、异常场景
- 使用业务语言而非技术术语（让非技术人员也能理解）
- 规格应回答"做什么"而非"怎么做"（技术方案在 plan 阶段）

---

### `/speckit.clarify`

**作用**: 自动识别规格文档中的模糊、不明确之处，通过提问澄清。

**使用场景**:
- 规格初稿完成后，发现细节不清晰
- 团队对需求理解存在分歧
- 准备进入开发前的最终确认

**使用方式**:
```bash
/speckit.clarify
```

**工作流程**:
1. 系统分析当前 `spec.md`
2. 识别模糊点（如未定义的业务规则、缺失的边界条件）
3. 生成最多5个高针对性问题
4. 用户回答问题
5. 系统将答案编码回 `spec.md`

**示例问题**:
- "充值失败时，退款是立即到账还是T+1？"
- "支付超时时间是多久？超时后订单状态如何变化？"
- "同一用户并发充值时，如何保证余额一致性？"

---

### `/speckit.plan`

**作用**: 基于功能规格生成详细的技术实施计划。

**使用场景**:
- 规格确认后，开始技术设计时
- 需要评估技术可行性时
- 多人协作前，需要统一技术方案

**使用方式**:
```bash
/speckit.plan
```

**关键输出**:
- **Technology Stack**: 选择的技术栈及理由
- **Database Schema**: 数据库表设计、索引、约束
- **API Design**: 端点路由、请求/响应格式、认证方式
- **Component Architecture**: 前后端模块划分、依赖关系
- **Test Strategy**: 单元测试、集成测试、E2E测试策略
- **Complexity Tracking**: 偏离宪章的复杂度追踪（如引入新依赖）

**最佳实践**:
- 计划必须与宪章对齐（Complexity Tracking 表记录任何偏离）
- 数据库设计应包含迁移策略（Alembic/Flyway）
- API设计遵循 RESTful 规范或 GraphQL 最佳实践
- 前端架构考虑可维护性（组件复用、状态管理）

---

### `/speckit.tasks`

**作用**: 将实施计划分解为可执行的开发任务。

**使用场景**:
- 计划评审通过后，准备开始编码
- 需要分配任务给团队成员
- 需要估算开发时间

**使用方式**:
```bash
/speckit.tasks
```

**关键输出**:
- **Backend Tasks**:
  - 数据模型创建
  - API实现
  - 业务逻辑
  - 单元/集成测试
- **Frontend Tasks**:
  - 页面/组件开发
  - 状态管理
  - 路由配置
  - E2E测试
- **Integration Tasks**:
  - Docker配置
  - CI/CD流程
  - 部署脚本

**任务格式**:
```markdown
## Task 1: 创建 Recharge 数据模型
- **Priority**: High
- **Depends on**: None
- **Description**:
  - 创建 recharge 表（支付方式、金额、状态、时间戳）
  - 添加外键关联到 operator_account
  - 创建索引：operator_id, created_at, status
- **Acceptance**:
  - Alembic migration 成功执行
  - 单元测试覆盖所有字段约束
```

**最佳实践**:
- 任务应遵循 SMART 原则（Specific, Measurable, Achievable, Relevant, Time-bound）
- 明确任务间的依赖关系，避免阻塞
- 每个任务包含验收标准（如何验证完成）

---

### `/speckit.implement`

**作用**: 按照任务列表逐一执行开发工作。

**使用场景**:
- 任务列表生成后，开始编码
- 需要自动化执行标准化任务（如CRUD）

**使用方式**:
```bash
/speckit.implement
```

**工作流程**:
1. 读取 `tasks.md` 中的任务列表
2. 按优先级和依赖顺序执行
3. 每完成一个任务：
   - 生成/修改代码
   - 运行测试
   - 更新任务状态
4. 遇到错误时暂停，等待人工干预

**最佳实践**:
- 实施过程遵循 TDD（先写测试，再写实现）
- 每完成一个任务进行 git commit
- 复杂任务手动实现，简单任务可自动化

---

### `/speckit.analyze`

**作用**: 非破坏性分析 spec、plan、tasks 之间的一致性和质量。

**使用场景**:
- 任务生成后，实施前的最终检查
- 发现需求变更后，评估影响范围
- Code Review 时验证实现与规格一致

**使用方式**:
```bash
/speckit.analyze
```

**检查项**:
- **一致性检查**:
  - spec 中的 API 是否在 plan 中有设计？
  - plan 中的数据表是否在 tasks 中有创建任务？
  - tasks 中的测试是否覆盖 spec 中的验收标准？
- **质量检查**:
  - 是否遵循宪章原则（TDD、配置外部化）？
  - 是否存在未处理的边界情况？
  - 技术选型是否合理？

**输出示例**:
```
✅ Consistency Check PASSED
  - All APIs in spec.md are designed in plan.md
  - All database tables in plan.md have creation tasks

⚠️ Quality Warning
  - Task "Implement payment API" lacks unit test task
  - NFR "Response time < 200ms" not addressed in plan.md

🔴 Constitution Violation
  - Task "Hardcode payment timeout" violates Zero Hardcoding principle
```

---

### `/speckit.checklist`

**作用**: 为当前功能生成定制化的验收清单。

**使用场景**:
- 功能开发完成，准备测试时
- 需要系统化的验收流程
- 交付给QA或客户前

**使用方式**:
```bash
/speckit.checklist <验收场景描述>

示例：
/speckit.checklist 运营商充值功能上线前验收清单
```

**关键输出**:
- **功能完整性**: 所有 User Story 是否实现
- **性能达标**: NFR 中的性能指标是否满足
- **安全合规**: 支付安全、数据加密是否到位
- **文档完备**: API文档、用户手册是否更新

---

## 实际使用示例

### 示例1: 从零开始开发"管理员管理运营商"功能

```bash
# 步骤1: 项目初始化（首次使用）
/speckit.constitution 项目核心原则：测试驱动开发、零硬编码、API契约优先、完整审计日志、E2E测试覆盖核心流程

# 步骤2: 定义功能规格
/speckit.specify 实现管理员管理运营商的功能：
- 查看运营商列表（搜索用户名、筛选状态、分页显示）
- 查看运营商详情（基本信息、余额、授权应用、使用统计）
- 锁定/解锁运营商账户
- 导出运营商数据为Excel

# 步骤3: 澄清需求（可选）
/speckit.clarify
# 系统提问：锁定账户后，现有游戏会话是否立即终止？
# 回答：是的，锁定后立即断开所有会话

# 步骤4: 制定实施计划
/speckit.plan

# 步骤5: 生成任务列表
/speckit.tasks

# 步骤6: 一致性分析（可选）
/speckit.analyze

# 步骤7: 执行实施
/speckit.implement

# 步骤8: 生成验收清单
/speckit.checklist 管理员运营商管理功能上线验收
```

---

### 示例2: 为现有项目增加新原则

```bash
# 场景：发现现有项目缺少E2E测试，需要补充到宪章
/speckit.constitution 新增原则VI：端到端测试原则
- 所有前端核心流程必须有 Playwright E2E 测试
- 覆盖率≥90%的核心用户路径
- CI 环境自动运行，失败阻止部署
- 测试失败自动生成截图、视频、trace
- 测试套件执行时间 < 5分钟
```

---

### 示例3: 规格变更影响分析

```bash
# 场景：产品经理要求充值功能增加"虚拟货币充值"
/speckit.specify 更新运营商充值功能规格：
- 新增支持虚拟货币充值（游戏币、积分兑换）
- 虚拟货币兑换比例可配置
- 充值来源需记录（支付宝/微信/虚拟货币）

# 重新生成计划（会与旧计划对比差异）
/speckit.plan

# 分析影响范围
/speckit.analyze
# 输出：检测到 recharge 表结构变更，需要新增 migration 任务
```

---

## 最佳实践

### 1. 宪章优先
- 项目启动第一件事：定义宪章
- 所有技术决策必须符合宪章原则
- 发现宪章不合理时，修订宪章而非绕过

### 2. 规格即合同
- 规格文档是开发、测试、验收的唯一依据
- 需求变更必须更新规格，而非口头沟通
- 规格应包含"为什么"（业务价值），不只是"做什么"

### 3. 计划先行
- 编码前必须有完整的技术计划
- 计划包含数据库设计、API设计、测试策略
- 复杂功能需要技术负责人审查计划

### 4. 任务驱动
- 任务列表是进度跟踪的依据
- 每完成一个任务进行 git commit
- 任务卡住时及时更新状态，寻求帮助

### 5. 持续验证
- 使用 `/speckit.analyze` 检查一致性
- 代码审查时对照规格和计划
- 功能完成后用 `/speckit.checklist` 系统化验收

### 6. 文档同步
- 需求变更时，同步更新 spec → plan → tasks
- 使用版本控制跟踪文档演进
- 重大变更记录在宪章的 `SYNC REPORT` 中

---

## 常见问题

### Q1: 什么时候需要更新宪章？
**A**:
- 发现新的核心原则（如从"手动测试"升级到"自动化E2E测试"）
- 技术架构重大调整（如从单体迁移到微服务）
- 质量标准变化（如测试覆盖率从80%提升到90%）

宪章应保持稳定，频繁修改说明初始定义不够完善。

---

### Q2: 规格文档应该多详细？
**A**:
遵循"刚刚好"原则：
- **太简**: 缺少验收标准、边界条件 → 开发时需频繁追问
- **太详**: 包含技术实现细节 → 限制开发灵活性
- **合适**: 清晰的功能描述 + 可测试的验收条件 + 必要的约束

经验法则：非技术人员能读懂60%，技术人员能据此开发。

---

### Q3: plan 和 tasks 有什么区别？
**A**:
- **Plan**: "怎么做" - 技术方案、架构设计、技术选型（战略层面）
- **Tasks**: "做什么" - 具体的开发步骤、可分配给开发者（战术层面）

类比：plan是建筑设计图，tasks是施工工序表。

---

### Q4: /speckit.implement 能完全自动化开发吗？
**A**:
不能，也不应该。
- **能自动化**: 标准CRUD、配置文件、Boilerplate代码
- **需人工**: 复杂业务逻辑、性能优化、安全加固

SpecKit 的目标是减少重复劳动，而非替代开发者思考。

---

### Q5: 如何处理紧急需求？
**A**:
即使紧急，也要走最小化流程：
```bash
# 最小流程（10分钟）
/speckit.specify <紧急需求简述>
/speckit.tasks  # 生成任务，评估影响
/speckit.implement  # 快速实施

# 事后补全
/speckit.plan  # 补充技术设计
/speckit.analyze  # 检查遗留问题
```

跳过流程可能节省1小时，但可能带来1周的返工。

---

### Q6: 团队成员不遵守流程怎么办？
**A**:
1. **代码审查阶段拦截**: PR必须关联规格文档
2. **自动化检查**: CI中集成 `/speckit.analyze`，不通过则失败
3. **复盘改进**: 事故后分析是否因流程缺失导致

宪章的 `Governance` 章节应明确违规后果。

---

## 附录：SpecKit 文件组织结构

```
project-root/
├── .specify/
│   ├── memory/
│   │   └── constitution.md        # 项目宪章
│   ├── templates/
│   │   ├── spec-template.md       # 规格模板
│   │   ├── plan-template.md       # 计划模板
│   │   └── tasks-template.md      # 任务模板
│   └── scripts/                   # 自动化脚本
├── specs/
│   ├── 001-feature-name/
│   │   ├── spec.md                # 功能规格
│   │   ├── plan.md                # 实施计划
│   │   ├── tasks.md               # 任务列表
│   │   └── checklists/            # 验收清单
│   │       ├── qa-checklist.md
│   │       └── uat-checklist.md
│   └── 002-another-feature/
│       └── ...
└── src/                           # 源代码
```

---

## 总结

SpecKit 通过**宪章 → 规格 → 计划 → 任务 → 实施**的完整流程，确保：

✅ **可追溯性**: 每行代码都能追溯到需求
✅ **一致性**: 规格、设计、实现保持同步
✅ **质量保证**: 强制测试、代码审查、宪章合规
✅ **高效协作**: 清晰的文档减少沟通成本
✅ **风险控制**: 变更影响分析，降低返工概率

**记住**: SpecKit 是工具，不是教条。根据团队实际情况灵活调整流程，但核心原则不能妥协。

---

**最后更新**: 2025-10-17
**版本**: 1.0.0
