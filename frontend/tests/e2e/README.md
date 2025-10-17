# 端到端测试 (E2E Testing) 使用指南

本项目使用 **Playwright** 进行前端端到端自动化测试。

## 📋 目录

- [安装依赖](#安装依赖)
- [运行测试](#运行测试)
- [调试测试](#调试测试)
- [编写测试](#编写测试)
- [最佳实践](#最佳实践)

---

## 安装依赖

如果是首次运行测试，需要安装 Playwright 浏览器：

```bash
cd frontend
npm install
npx playwright install chromium
```

---

## 运行测试

### 1. 无头模式运行（默认）

在后台运行所有测试，不显示浏览器窗口：

```bash
cd frontend
npm run test:e2e
```

### 2. 可视化模式运行

打开浏览器窗口，可以看到测试执行过程：

```bash
npm run test:e2e:headed
```

### 3. UI 模式（推荐用于开发）

使用 Playwright UI 界面运行测试，支持暂停、回放、查看 DOM 等：

```bash
npm run test:e2e:ui
```

### 4. 查看测试报告

运行测试后，查看HTML格式的详细报告：

```bash
npm run test:e2e:report
```

---

## 调试测试

### 1. 调试模式

逐步执行测试，支持断点调试：

```bash
npm run test:e2e:debug
```

在调试模式下，你可以：
- 使用 Playwright Inspector 查看每一步操作
- 在代码中设置断点
- 查看DOM元素、网络请求、控制台输出

### 2. 运行特定测试

只运行某个测试文件：

```bash
npx playwright test admin.spec.ts
```

只运行包含特定关键词的测试：

```bash
npx playwright test -g "登录"
```

### 3. 查看 Trace

如果测试失败，Playwright 会自动记录 trace。查看 trace：

```bash
npx playwright show-trace test-results/<trace-file>.zip
```

---

## 编写测试

### 测试文件结构

测试文件应放在 `frontend/tests/e2e/` 目录下，文件名以 `.spec.ts` 结尾。

```typescript
import { test, expect } from '@playwright/test'

test.describe('功能名称', () => {
  test.beforeEach(async ({ page }) => {
    // 每个测试前的准备工作
    await page.goto('/admin/login')
  })

  test('测试用例名称', async ({ page }) => {
    // 执行操作
    await page.fill('input[type="text"]', 'admin')
    await page.click('button:has-text("登录")')

    // 断言验证
    await expect(page).toHaveURL(/dashboard/)
    await expect(page.locator('text=欢迎')).toBeVisible()
  })
})
```

### 常用操作

```typescript
// 导航
await page.goto('/path')

// 点击
await page.click('button:has-text("提交")')

// 填写表单
await page.fill('input[name="username"]', 'admin')

// 选择下拉选项
await page.selectOption('select#status', 'active')

// 等待元素
await page.waitForSelector('.loading', { state: 'hidden' })

// 截图
await page.screenshot({ path: 'screenshot.png' })

// 断言
await expect(page).toHaveURL(/dashboard/)
await expect(page.locator('h1')).toHaveText('标题')
await expect(page.locator('.error')).not.toBeVisible()
```

---

## 最佳实践

### 1. 测试隔离

每个测试应该独立运行，不依赖其他测试的状态：

```typescript
test.beforeEach(async ({ page }) => {
  // 每个测试前重新登录
  await adminLogin(page)
})
```

### 2. 使用有意义的选择器

优先使用语义化的选择器：

```typescript
// ✅ 好
await page.click('button:has-text("登录")')
await page.locator('[data-testid="submit-btn"]').click()

// ❌ 避免
await page.click('.el-button.el-button--primary:nth-child(3)')
```

### 3. 等待机制

使用 Playwright 的自动等待，避免硬编码延迟：

```typescript
// ✅ 好
await page.waitForURL(/dashboard/)
await expect(page.locator('.data')).toBeVisible()

// ❌ 避免
await page.waitForTimeout(3000)
```

### 4. 错误处理

测试失败时自动截图和录制：

```typescript
// playwright.config.ts 已配置
screenshot: 'only-on-failure',
video: 'retain-on-failure',
trace: 'retain-on-failure',
```

### 5. 环境准备

确保测试前环境准备好：
- 前端服务已启动（`npm run dev`）
- 后端服务已启动（Docker Compose）
- 数据库包含必要的测试数据

---

## 测试覆盖范围

当前测试套件涵盖：

- ✅ 管理员登录
- ✅ Dashboard 页面
- ✅ 运营商列表（搜索、筛选、分页）
- ✅ 应用列表（搜索、详情）
- ✅ 授权申请（查看、审核）
- ✅ 侧边栏导航
- ✅ 退出登录

---

## 故障排查

### 测试超时

如果测试经常超时，可以增加超时时间：

```typescript
// 在 playwright.config.ts 中
timeout: 60000, // 60秒
```

### 元素找不到

使用 Playwright Inspector 检查元素选择器：

```bash
npm run test:e2e:debug
```

### 网络请求失败

检查后端服务是否正常运行：

```bash
docker-compose ps
docker logs mr_game_ops_backend
```

---

## 相关资源

- [Playwright 官方文档](https://playwright.dev/)
- [Playwright API 参考](https://playwright.dev/docs/api/class-playwright)
- [Best Practices](https://playwright.dev/docs/best-practices)

---

## 持续集成 (CI)

在 CI 环境中运行测试：

```yaml
# .github/workflows/e2e.yml 示例
- name: Run E2E tests
  run: |
    cd frontend
    npm ci
    npx playwright install --with-deps chromium
    npm run test:e2e
```
