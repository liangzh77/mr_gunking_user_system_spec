# E2E 自动化测试框架

这是一个基于 Playwright 的端到端(E2E)自动化测试框架,用于测试 MR Gunking 用户系统的所有功能。

## 功能特点

- ✅ **多角色支持**: 管理员、财务、运营商三个角色的全面测试
- ✅ **多环境支持**: 支持 localhost 和生产环境 (mrgun.chu-jiao.com)
- ✅ **智能测试分类**: 生产环境仅运行只读测试,本地环境运行全部测试
- ✅ **数据库集成**: 自动创建和清理测试数据
- ✅ **完整的页面覆盖**: 测试所有页面的加载和核心功能
- ✅ **自动化验证**: 自动验证页面加载、元素显示、操作结果

## 目录结构

```
tests/
├── e2e/
│   ├── config/
│   │   └── environments.ts       # 环境配置(localhost/production)
│   ├── fixtures/
│   │   └── auth.ts               # 认证相关fixture(登录/登出)
│   ├── specs/
│   │   ├── admin.spec.ts         # 管理员角色测试
│   │   ├── finance.spec.ts       # 财务角色测试
│   │   └── operator.spec.ts      # 运营商角色测试
│   └── utils/
│       └── db-helper.ts          # 数据库辅助工具
├── playwright.config.ts          # Playwright配置
├── tsconfig.json                 # TypeScript配置
├── package.json                  # NPM依赖和脚本
├── .env.example                  # 环境变量模板
└── README.md                     # 本文档
```

## 安装

1. 进入测试目录:
```bash
cd tests
```

2. 安装依赖:
```bash
npm install
```

3. 安装 Playwright 浏览器:
```bash
npx playwright install
```

4. 配置环境变量:
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件,填入生产环境凭证(如需测试生产环境)
# TEST_ENV=localhost
# PROD_ADMIN_PASSWORD=your_password
# PROD_FINANCE_PASSWORD=your_password
# PROD_OPERATOR_PASSWORD=your_password
```

## 使用方法

### 快速开始 (推荐)

使用便捷脚本运行测试:

```bash
# Windows 环境
.\run-e2e-tests.bat localhost ui      # 本地环境,UI模式
.\run-e2e-tests.bat localhost headless # 本地环境,无头模式
.\run-e2e-tests.bat production headless # 生产环境,无头模式

# 如果不指定参数,默认使用 localhost + ui
.\run-e2e-tests.bat
```

### 运行所有测试

```bash
# 在本地环境运行所有测试 (UI 模式,可见浏览器)
npm run test:localhost:ui

# 在本地环境运行所有测试 (无头模式)
npm run test:localhost

# 在生产环境运行只读测试
npm run test:production
```

### 运行特定角色的测试

```bash
# 测试管理员功能
npx playwright test admin.spec.ts

# 测试财务功能
npx playwright test finance.spec.ts

# 测试运营商功能
npx playwright test operator.spec.ts
```

### UI 模式运行(推荐用于开发调试)

```bash
# 本地环境 - 带可视化界面
npm run test:localhost:ui

# 生产环境 - 带可视化界面
npm run test:production:ui
```

### 调试模式

```bash
# 步进调试模式
npm run test:localhost:debug

# 显示浏览器窗口运行
npm run test:localhost:headed
```

### 代码生成器(录制测试)

```bash
# 在本地环境录制测试
npm run test:codegen:localhost

# 在生产环境录制测试
npm run test:codegen:production
```

### 查看测试报告

```bash
# 打开 HTML 测试报告
npm run test:report

# 查看测试结果 JSON
cat test-results/results.json

# 查看 JUnit XML 报告 (用于 CI)
cat test-results/junit.xml
```

### 测试结果说明

测试运行后会生成以下内容:

- `playwright-report/` - HTML 可视化报告
- `test-results/` - 测试结果、截图、视频、traces
  - `results.json` - JSON 格式的测试结果
  - `junit.xml` - JUnit 格式的报告 (CI 集成)
  - `videos/` - 失败测试的视频录像
  - 失败测试的截图和 trace 文件

## 测试标签说明

- `@readonly`: 只读测试,可以在生产环境运行
- 无标签: 写操作测试,仅在本地环境运行

生产环境只会运行带 `@readonly` 标签的测试用例,确保不会修改生产数据。

## 环境配置

### Localhost 环境

- URL: `https://localhost`
- 凭证: 在代码中硬编码(admin/admin123, finance1/finance123, operator1/operator123)
- 数据库: 支持直接操作数据库进行数据准备和清理
- 测试类型: 全部测试(只读 + 写操作)

### Production 环境

- URL: `https://mrgun.chu-jiao.com`
- 凭证: 从 `.env` 文件读取
- 数据库: 不直接操作生产数据库
- 测试类型: 仅只读测试

## 测试覆盖范围

### 管理员角色 (admin.spec.ts)

**只读测试** (生产环境可运行):
- ✅ 登录功能
- ✅ 仪表盘显示
- ✅ 运营商列表查看
- ✅ 站点管理查看
- ✅ 应用管理查看
- ✅ 应用审批查看
- ✅ 游戏授权查看
- ✅ 交易记录查看

**写操作测试** (仅本地环境):
- ✅ 创建新应用
- ✅ 搜索运营商
- ✅ 筛选交易记录

**完整流程测试** (仅本地环境):
- ✅ 完整流程: 创建应用
- ✅ 完整流程: 审批应用申请
- ✅ 完整流程: 管理游戏授权
- ✅ 完整流程: 运营商账户管理(查看详情/锁定/解锁/编辑)
- ✅ 完整流程: 查看和导出交易报表
- ✅ 完整流程: 管理运营商站点

### 财务角色 (finance.spec.ts)

**只读测试** (生产环境可运行):
- ✅ 登录功能
- ✅ 仪表盘显示
- ✅ 充值记录查看
- ✅ 交易记录查看
- ✅ 退款管理查看
- ✅ 发票管理查看
- ✅ 银行流水查看
- ✅ 财务报表查看
- ✅ 审计日志查看

**写操作测试** (仅本地环境):
- ✅ 筛选充值记录
- ✅ 筛选交易类型
- ✅ 确认充值
- ✅ 执行扣费操作
- ✅ 审批退款申请

**完整流程测试** (仅本地环境):
- ✅ 完整流程: 充值审核和扣费
- ✅ 完整流程: 退款审批(通过和拒绝)
- ✅ 完整流程: 发票审核
- ✅ 完整流程: 生成和导出财务报表
- ✅ 完整流程: 查看和核对银行流水
- ✅ 完整流程: 审计日志查询和分析

### 运营商角色 (operator.spec.ts)

**只读测试** (生产环境可运行):
- ✅ 登录功能
- ✅ 仪表盘显示
- ✅ 个人资料查看
- ✅ 充值页面访问
- ✅ 交易记录查看
- ✅ **财务扣费类型正确显示** (关键测试)
- ✅ 站点管理查看
- ✅ 应用管理查看
- ✅ 应用申请查看
- ✅ 使用记录查看
- ✅ 统计分析查看
- ✅ 退款管理查看
- ✅ 发票管理查看
- ✅ 消息中心查看

**写操作测试** (仅本地环境):
- ✅ 筛选交易记录
- ✅ 筛选扣费记录
- ✅ 提交充值申请
- ✅ 创建站点
- ✅ 申请退款
- ✅ 申请发票
- ✅ 查看使用记录详情

**完整流程测试** (仅本地环境):
- ✅ 完整流程: 在线充值申请(银行转账)
- ✅ 完整流程: 在线充值申请(微信支付)
- ✅ 完整流程: 修改个人资料
- ✅ 完整流程: 提交应用申请
- ✅ 完整流程: 创建站点并编辑
- ✅ 完整流程: 查看和导出统计数据
- ✅ 完整流程: 查看消息并标记已读

## 数据库辅助工具

`DatabaseHelper` 类提供以下功能:

```typescript
// 创建测试运营商
const operatorId = await db.createTestOperator('e2e_test_operator');

// 创建测试交易
const transactionId = await db.createTestTransaction(
  operatorId,
  'recharge', // 或 'consumption', 'refund', 'deduct'
  100.00
);

// 查询运营商余额
const balance = await db.getOperatorBalance(operatorId);

// 查询交易记录数
const count = await db.getTransactionCount(operatorId, 'recharge');

// 清理所有测试数据
await db.cleanupTestData();

// 关闭数据库连接
await db.close();
```

## 最佳实践

1. **本地开发**: 使用 UI 模式进行开发和调试
   ```bash
   npm run test:localhost:ui
   ```

2. **CI/CD**: 使用无头模式运行测试
   ```bash
   npm run test:localhost
   ```

3. **生产验证**: 定期运行只读测试验证生产环境
   ```bash
   npm run test:production
   ```

4. **添加新测试**:
   - 只读测试添加 `@readonly` 标签
   - 写操作测试放在 `if (!isProduction)` 块中

5. **数据清理**: 测试结束后自动清理,但建议定期检查

## 故障排查

### 测试失败

1. 检查服务是否运行:
   ```bash
   docker-compose ps
   ```

2. 查看服务日志:
   ```bash
   docker-compose logs -f backend
   docker-compose logs -f frontend
   ```

3. 检查数据库连接:
   ```bash
   docker-compose exec postgres psql -U mr_admin -d mr_game_ops
   ```

### 元素定位失败

1. 使用 UI 模式查看页面实际状态
2. 使用 Playwright Inspector:
   ```bash
   npm run test:localhost:debug
   ```
3. 使用代码生成器录制正确的操作:
   ```bash
   npm run test:codegen:localhost
   ```

### 环境配置问题

1. 确认 `.env` 文件存在并正确配置
2. 确认 `TEST_ENV` 环境变量设置正确
3. 生产环境确认凭证已正确配置

## 持续集成(CI/CD)

### GitHub Actions

项目已包含 GitHub Actions 配置文件 `.github/workflows/e2e-tests.yml`,提供以下功能:

**特性:**
- ✅ 自动在 push 和 PR 时运行测试
- ✅ 支持手动触发工作流
- ✅ 并行执行测试 (3个分片)
- ✅ 自动启动 PostgreSQL 和 Redis 服务
- ✅ 自动运行数据库迁移
- ✅ 自动启动后端和前端服务
- ✅ 生成 HTML、JSON、JUnit 测试报告
- ✅ 失败时保留截图和视频
- ✅ 自动合并多个分片的测试报告

**配置 GitHub Secrets:**

在 GitHub 仓库设置中添加以下 secrets:

```
DB_PASSWORD                  # 数据库密码
LOCALHOST_ADMIN_USERNAME     # 管理员用户名 (可选,默认 admin)
LOCALHOST_ADMIN_PASSWORD     # 管理员密码 (可选,默认 admin123)
LOCALHOST_FINANCE_USERNAME   # 财务用户名 (可选,默认 finance)
LOCALHOST_FINANCE_PASSWORD   # 财务密码 (可选,默认 finance123)
LOCALHOST_OPERATOR_USERNAME  # 运营商用户名 (可选,默认 operator)
LOCALHOST_OPERATOR_PASSWORD  # 运营商密码 (可选,默认 operator123)
```

**手动触发:**

在 GitHub Actions 页面选择 "E2E Tests" workflow,点击 "Run workflow",选择环境(localhost 或 production)。

### 其他 CI 平台示例

```yaml
# GitLab CI 示例
e2e-tests:
  image: mcr.microsoft.com/playwright:v1.40.0-jammy
  services:
    - postgres:14
    - redis:7-alpine
  script:
    - cd tests
    - npm ci
    - npx playwright install --with-deps chromium
    - TEST_ENV=localhost npm run test:localhost
```

## 注意事项

1. **生产环境测试**: 始终使用 `test:production` 命令,确保只运行只读测试
2. **数据隔离**: 本地测试会创建 `e2e_` 前缀的测试数据,测试结束后自动清理
3. **并发控制**: 配置为串行执行(workers: 1),避免数据竞争
4. **超时设置**: 默认 60 秒测试超时,30 秒导航超时,可根据需要调整
5. **认证缓存**: 测试间会清理 cookies 和 localStorage,确保隔离

## 维护指南

### 添加新的测试用例

1. 在对应的 `spec.ts` 文件中添加测试
2. 决定是只读测试还是写操作测试
3. 只读测试添加 `@readonly` 标签
4. 写操作测试用 `if (!isProduction)` 包裹

示例:
```typescript
test('应该能够查看新页面 @readonly', async ({ page }) => {
  await page.goto('/new-page');
  await expect(page.locator('h1')).toBeVisible();
});

if (!isProduction) {
  test('应该能够创建新记录', async ({ page }) => {
    // 写操作测试
  });
}
```

### 更新环境配置

编辑 `e2e/config/environments.ts` 文件:
- 添加新环境
- 修改现有环境配置
- 更新凭证

### 扩展数据库工具

编辑 `e2e/utils/db-helper.ts` 文件:
- 添加新的数据创建方法
- 添加新的查询方法
- 扩展清理逻辑

## 技术栈

- **Playwright**: ^1.40.0 - 浏览器自动化框架
- **TypeScript**: ^5.0.0 - 类型安全的测试代码
- **pg**: ^8.11.0 - PostgreSQL 数据库客户端
- **dotenv**: ^16.3.1 - 环境变量管理
- **cross-env**: ^7.0.3 - 跨平台环境变量设置

## 许可证

与主项目保持一致

## 支持

如有问题,请联系开发团队或提交 Issue。
