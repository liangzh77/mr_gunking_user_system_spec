# E2E 测试框架更新日志

## [1.0.0] - 2025-11-19

### ✨ 初始发布

完整的 E2E 自动化测试框架,支持三个角色的全面测试。

#### 新增功能

**测试框架**
- ✅ Playwright E2E 测试框架
- ✅ TypeScript 类型安全
- ✅ 多环境支持 (localhost/production)
- ✅ 智能测试分类 (@readonly 标签)
- ✅ 数据库集成与自动清理

**测试覆盖**
- ✅ 管理员角色: 11 个测试用例
- ✅ 财务角色: 14 个测试用例
- ✅ 运营商角色: 19 个测试用例
- ✅ 总计: 44 个测试用例

**核心测试**
- ✅ 登录/登出功能
- ✅ 页面访问验证
- ✅ 数据筛选功能
- ✅ CRUD 操作测试
- ✅ **财务扣费功能验证**
- ✅ **运营商扣费类型显示验证**

**文档**
- ✅ README.md - 完整使用文档
- ✅ QUICKSTART.md - 快速开始指南
- ✅ ARCHITECTURE.md - 架构说明
- ✅ CHANGELOG.md - 更新日志

#### 修复

**登录选择器问题**
- 🐛 修复管理员登录占位符不匹配问题
  - 管理员登录使用 "请输入管理员用户名"
  - 财务/运营商登录使用 "请输入用户名"

**验证码处理**
- 🐛 修复登录时验证码未填写导致超时问题
  - 本地环境自动填写验证码 `0000`
  - 生产环境等待验证码加载(需手动处理)
  - 所有三个角色登录均已修复

**数据库 UUID 生成问题**
- 🐛 修复数据库插入时 UUID 字段为 null 的问题
  - PostgreSQL 表的 `id` 字段为 UUID 类型,需要显式提供
  - 在 TypeScript 中使用 `randomUUID()` 生成 UUID
  - 修复了 `createTestOperator` 和 `createTestTransaction` 方法
- 🐛 修复 ON CONFLICT 约束错误
  - 移除了 `ON CONFLICT (username)` 子句(username 没有唯一约束)
  - 通过时间戳生成唯一 API key 避免冲突

**页面验证选择器优化**
- 🐛 修复页面元素验证失败问题
  - 大部分页面没有 h1/h2 标题元素
  - 改为验证实际页面内容元素:
    - 仪表盘: 验证 `.stat-card` 统计卡片
    - 列表页面: 验证 `.el-table` 表格
    - 表单页面: 验证 `.el-card` 或 `.el-form`
    - 灵活验证: 某些页面支持多种内容形式
  - 44个测试用例全部更新优化

#### 文件结构

```
tests/
├── e2e/
│   ├── config/
│   │   └── environments.ts       # 环境配置
│   ├── fixtures/
│   │   └── auth.ts               # 认证 fixtures
│   ├── specs/
│   │   ├── admin.spec.ts         # 管理员测试
│   │   ├── finance.spec.ts       # 财务测试
│   │   └── operator.spec.ts      # 运营商测试
│   └── utils/
│       └── db-helper.ts          # 数据库工具
├── playwright.config.ts          # Playwright 配置
├── package.json                  # NPM 配置
├── tsconfig.json                 # TypeScript 配置
├── .env                          # 环境变量
├── .env.example                  # 环境变量模板
├── .gitignore                    # Git 忽略规则
├── README.md                     # 使用文档
├── QUICKSTART.md                 # 快速开始
├── ARCHITECTURE.md               # 架构说明
└── CHANGELOG.md                  # 本文件
```

#### 依赖

- @playwright/test: ^1.40.0
- @types/node: ^20.0.0
- @types/pg: ^8.10.0
- cross-env: ^7.0.3
- dotenv: ^16.3.1
- pg: ^8.11.0
- typescript: ^5.0.0

#### 使用方法

```bash
# 安装
npm install
npx playwright install

# 本地测试
npm run test:localhost:ui

# 生产测试
npm run test:production
```

#### 贡献者

- Claude Code - 初始框架开发

---

## 未来计划

### v1.1.0 (计划中)
- [ ] 添加 API 层面测试
- [ ] 集成到 CI/CD 管道
- [ ] 添加测试覆盖率报告
- [ ] 添加性能测试

### v1.2.0 (计划中)
- [ ] 添加可访问性测试
- [ ] 添加移动端适配测试
- [ ] 添加视觉回归测试
- [ ] 支持更多环境配置

---

## 版本说明

遵循 [语义化版本 2.0.0](https://semver.org/)

- **主版本号**: 不兼容的 API 修改
- **次版本号**: 向下兼容的功能性新增
- **修订号**: 向下兼容的问题修正
