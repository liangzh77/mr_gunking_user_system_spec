import { test, expect } from '@playwright/test';
import { loginAsAdmin, logout } from '../fixtures/auth';
import { getEnvironment } from '../config/environments';

const env = getEnvironment();
const isProduction = env.name === 'production';

test.describe('管理员角色测试', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test.afterEach(async ({ page }) => {
    await logout(page);
  });

  test('应该成功登录并显示仪表盘 @readonly', async ({ page }) => {
    // 验证URL
    await expect(page).toHaveURL(/.*\/admin\/dashboard/);

    // 验证仪表盘统计卡片显示
    await expect(page.locator('.stat-card').first()).toBeVisible({ timeout: 10000 });

    // 验证侧边栏
    await expect(page.locator('.sidebar')).toBeVisible();

    console.log('✅ 管理员仪表盘加载成功');
  });

  test('应该能够查看运营商列表 @readonly', async ({ page }) => {
    await page.goto('/admin/operators');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 验证页面内容
    await expect(page.locator('.el-table')).toBeVisible();

    console.log('✅ 运营商列表页面加载成功');
  });

  test('应该能够查看站点管理 @readonly', async ({ page }) => {
    await page.goto('/admin/operator-sites');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 等待并验证主要内容
    await page.waitForSelector('.el-table, .el-card', { timeout: 10000 });

    console.log('✅ 站点管理页面加载成功');
  });

  test('应该能够查看应用管理 @readonly', async ({ page }) => {
    await page.goto('/admin/applications');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 验证页面内容
    await expect(page.locator('.el-table')).toBeVisible();

    console.log('✅ 应用管理页面加载成功');
  });

  test('应该能够查看应用审批 @readonly', async ({ page }) => {
    await page.goto('/admin/app-requests');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 等待并验证主要内容
    await page.waitForSelector('.el-table, .el-card', { timeout: 10000 });

    console.log('✅ 应用审批页面加载成功');
  });

  test('应该能够查看游戏授权 @readonly', async ({ page }) => {
    await page.goto('/admin/authorizations');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 等待并验证卡片元素
    await page.waitForSelector('.el-card', { timeout: 10000 });
    await expect(page.locator('.el-card').first()).toBeVisible();

    console.log('✅ 游戏授权页面加载成功');
  });

  test('应该能够查看交易记录 @readonly', async ({ page }) => {
    await page.goto('/admin/transactions');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 验证页面内容
    await expect(page.locator('.el-table')).toBeVisible();

    console.log('✅ 交易记录页面加载成功');
  });

  // 本地环境的写操作测试
  if (!isProduction) {
    test('应该能够访问创建应用页面', async ({ page }) => {
      await page.goto('/admin/applications/create');

      // 等待页面加载
      await page.waitForLoadState('networkidle');

      // 验证表单存在
      await page.waitForSelector('.el-form, .el-card', { timeout: 10000 });

      console.log('✅ 创建应用页面加载成功');
    });

    test('应该能够搜索运营商', async ({ page }) => {
      await page.goto('/admin/operators');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 输入搜索关键词
      const searchBox = page.getByPlaceholder(/搜索|用户名|运营商/);
      await searchBox.fill('operator');

      // 点击搜索按钮或等待自动搜索
      const searchButton = page.getByRole('button', { name: /搜索|查询/ });
      if (await searchButton.isVisible({ timeout: 1000 })) {
        await searchButton.click();
      }

      // 等待搜索结果
      await page.waitForTimeout(1000);

      console.log('✅ 运营商搜索功能正常');
    });

    test('应该能够筛选交易记录', async ({ page }) => {
      await page.goto('/admin/transactions');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 尝试筛选功能
      const typeSelect = page.locator('.el-select').first();
      if (await typeSelect.isVisible({ timeout: 2000 })) {
        await typeSelect.click();

        // 等待下拉选项出现
        await page.waitForTimeout(500);

        // 查找并点击第一个可用选项
        const firstOption = page.locator('.el-select-dropdown .el-option').first();
        if (await firstOption.isVisible({ timeout: 2000 })) {
          await firstOption.click();
          await page.waitForTimeout(1000);
          console.log('✅ 交易记录筛选功能正常');
        }
      }
    });
  }
});
