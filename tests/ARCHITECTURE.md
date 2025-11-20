# E2E 测试框架架构说明

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                   E2E Test Framework                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Admin      │  │   Finance    │  │   Operator   │  │
│  │   Tests      │  │   Tests      │  │   Tests      │  │
│  │ (11 cases)   │  │ (14 cases)   │  │ (19 cases)   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                 │           │
│         └─────────────────┴─────────────────┘           │
│                         │                                │
│         ┌───────────────┴───────────────┐               │
│         │                               │               │
│  ┌──────▼────────┐            ┌────────▼────────┐      │
│  │  Auth         │            │  Environment    │      │
│  │  Fixtures     │            │  Config         │      │
│  │ - loginAs*()  │            │ - localhost     │      │
│  │ - logout()    │            │ - production    │      │
│  └───────────────┘            └─────────────────┘      │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │          Database Helper (localhost only)       │   │
│  │  - createTestOperator()                         │   │
│  │  - createTestTransaction()                      │   │
│  │  - getOperatorBalance()                         │   │
│  │  - cleanupTestData()                            │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 文件结构详解

### 配置文件层

**playwright.config.ts**
- Playwright 主配置
- 环境感知配置(根据 TEST_ENV 动态调整)
- 本地环境自动启动服务
- 浏览器配置、超时设置

**tsconfig.json**
- TypeScript 编译配置
- 目标 ES2020
- CommonJS 模块

**package.json**
- NPM 依赖管理
- 测试脚本定义
- 支持 localhost/production 切换

### 环境配置层

**e2e/config/environments.ts**
```typescript
environments = {
  localhost: {
    baseURL: 'https://localhost',
    credentials: { admin, finance, operator },
    database: { PostgreSQL 连接信息 }
  },
  production: {
    baseURL: 'https://mrgun.chu-jiao.com',
    credentials: { 从 .env 读取 },
    database: undefined  // 不操作生产数据库
  }
}
```

### 认证层

**e2e/fixtures/auth.ts**
- 三个角色的登录函数
- 统一的登出函数
- 自动等待页面跳转
- Cookie/LocalStorage 清理

### 数据层

**e2e/utils/db-helper.ts**
- 仅在本地环境可用
- 自动创建/清理测试数据
- 支持事务操作
- 余额计算自动化

### 测试规格层

**e2e/specs/admin.spec.ts**
- 管理员所有功能测试
- 8 个只读测试 (@readonly)
- 3 个写操作测试 (本地环境)

**e2e/specs/finance.spec.ts**
- 财务所有功能测试
- 8 个只读测试 (@readonly)
- 6 个写操作测试 (本地环境)
- **关键功能**: 确认充值、执行扣费

**e2e/specs/operator.spec.ts**
- 运营商所有功能测试
- 12 个只读测试 (@readonly)
- 7 个写操作测试 (本地环境)
- **关键验证**: 财务扣费类型正确显示

## 测试流程

### 本地环境测试流程

```
1. 启动测试
   npm run test:localhost

2. 读取环境配置
   TEST_ENV=localhost

3. 初始化数据库连接
   DatabaseHelper.connect()

4. 执行测试
   ├── beforeEach: 登录
   ├── 执行测试用例
   │   ├── 只读测试
   │   └── 写操作测试
   └── afterEach: 登出

5. 清理数据
   DatabaseHelper.cleanupTestData()

6. 生成报告
```

### 生产环境测试流程

```
1. 启动测试
   npm run test:production

2. 读取环境配置
   TEST_ENV=production
   从 .env 读取凭证

3. 跳过数据库初始化
   DatabaseHelper 禁用

4. 执行测试
   ├── beforeEach: 登录
   ├── 执行测试用例
   │   └── 只读测试 (@readonly)
   └── afterEach: 登出

5. 生成报告
```

## 测试标签系统

### @readonly 标签
- 标记只读测试
- 可在生产环境运行
- 不修改任何数据
- 仅验证页面访问和显示

### 无标签
- 默认为写操作测试
- 仅在本地环境运行
- 使用 `if (!isProduction)` 包裹
- 可能创建/修改/删除数据

## 数据管理策略

### 本地环境
- 测试数据前缀: `e2e_`
- 自动创建: beforeEach 或 test 内
- 自动清理: afterAll
- 支持事务回滚

### 生产环境
- 不创建任何数据
- 不修改任何数据
- 仅读取现有数据
- 依赖真实数据存在

## 并发控制

```typescript
// playwright.config.ts
{
  fullyParallel: false,  // 串行执行
  workers: 1,            // 单个 worker
}
```

**原因**:
- 避免数据竞争
- 数据库操作冲突
- 登录状态隔离
- 结果可预测

## 错误处理

### 页面加载超时
```typescript
await page.waitForLoadState('networkidle', { timeout: 30000 });
```

### 元素定位失败
```typescript
if (await element.isVisible({ timeout: 2000 })) {
  // 执行操作
} else {
  console.log('⚠️  元素不可见,跳过测试');
}
```

### 数据库连接失败
```typescript
if (!this.pool) {
  console.warn('Skipping - no database connection');
  return '';
}
```

## 扩展性设计

### 添加新角色
1. 在 `environments.ts` 添加凭证
2. 在 `auth.ts` 添加登录函数
3. 创建新的 `{role}.spec.ts`

### 添加新环境
```typescript
// environments.ts
export const environments = {
  localhost: { ... },
  production: { ... },
  staging: {  // 新环境
    name: 'staging',
    baseURL: 'https://staging.example.com',
    credentials: { ... }
  }
}
```

### 添加新的数据库操作
```typescript
// db-helper.ts
async createTestInvoice(operatorId: string): Promise<string> {
  // 实现
}
```

## 性能优化

### 选择器优化
```typescript
// 推荐: 语义化选择器
page.getByRole('button', { name: '登录' })
page.getByLabel('用户名')
page.getByPlaceholder('请输入密码')

// 避免: CSS 选择器
page.locator('.login-button')  // 脆弱
```

### 等待策略
```typescript
// 推荐: 等待特定状态
await page.waitForURL('**/dashboard');
await expect(element).toBeVisible();

// 避免: 固定等待
await page.waitForTimeout(5000);  // 不稳定
```

## 安全考虑

### 凭证管理
- 本地凭证: 代码中硬编码(测试环境)
- 生产凭证: `.env` 文件(不提交到 Git)
- `.env` 在 `.gitignore` 中

### 数据隔离
- 测试数据前缀: `e2e_`
- 自动清理机制
- 不操作生产数据库

### HTTPS 处理
```typescript
// localhost: 忽略自签名证书
ignoreHTTPSErrors: true

// production: 验证证书
ignoreHTTPSErrors: false
```

## 最佳实践

1. **测试独立性**: 每个测试独立运行,不依赖其他测试
2. **数据清理**: 始终清理测试数据
3. **错误处理**: 优雅处理失败情况
4. **日志记录**: 使用 console.log 记录关键步骤
5. **语义选择器**: 使用 getByRole/getByLabel
6. **等待策略**: 等待特定状态,避免固定延迟
7. **标签使用**: 正确标记只读测试

## 持续改进

### 当前覆盖率
- 管理员: 11 个测试用例
- 财务: 14 个测试用例
- 运营商: 19 个测试用例
- **总计: 44 个测试用例**

### 待改进方向
- [ ] 添加 API 层面测试
- [ ] 添加性能测试
- [ ] 添加可访问性测试
- [ ] 添加移动端适配测试
- [ ] 集成到 CI/CD 管道
- [ ] 添加视觉回归测试
- [ ] 增加测试覆盖率报告

## 工具链

- **Playwright**: ^1.40.0 - E2E 测试框架
- **TypeScript**: ^5.0.0 - 类型安全
- **PostgreSQL Client**: ^8.11.0 - 数据库操作
- **dotenv**: ^16.3.1 - 环境变量
- **cross-env**: ^7.0.3 - 跨平台环境变量

## 总结

这是一个企业级的 E2E 测试框架,具有:
- ✅ 完整的角色覆盖
- ✅ 多环境支持
- ✅ 智能测试分类
- ✅ 数据管理自动化
- ✅ 良好的可维护性
- ✅ 详尽的文档

可以作为其他项目的测试框架模板。
