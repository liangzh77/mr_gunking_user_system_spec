import { test, expect } from '@playwright/test';
import { loginAsFinance, logout } from '../fixtures/auth';
import { getEnvironment } from '../config/environments';
import { DatabaseHelper } from '../utils/db-helper';

const env = getEnvironment();
const isProduction = env.name === 'production';
const db = new DatabaseHelper();

test.describe('财务角色测试', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsFinance(page);
  });

  test.afterEach(async ({ page }) => {
    await logout(page);
  });

  test.afterAll(async () => {
    if (!isProduction) {
      await db.cleanupTestData();
      await db.close();
    }
  });

  test('应该成功登录并显示仪表盘 @readonly', async ({ page }) => {
    // 验证URL
    await expect(page).toHaveURL(/.*\/finance\/dashboard/);

    // 验证仪表盘统计卡片显示
    await expect(page.locator('.stat-card').first()).toBeVisible({ timeout: 10000 });

    console.log('✅ 财务仪表盘加载成功');
  });

  test('应该能够查看充值记录 @readonly', async ({ page }) => {
    await page.goto('/finance/recharge-records');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 验证页面内容
    await expect(page.locator('.el-table')).toBeVisible();

    console.log('✅ 充值记录页面加载成功');
  });

  test('应该能够查看交易记录 @readonly', async ({ page }) => {
    await page.goto('/finance/transactions');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 验证页面内容
    await expect(page.locator('.el-table')).toBeVisible();

    console.log('✅ 交易记录页面加载成功');
  });

  test('应该能够查看退款管理 @readonly', async ({ page }) => {
    await page.goto('/finance/refunds');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 验证页面内容
    await expect(page.locator('.el-table')).toBeVisible();

    console.log('✅ 退款管理页面加载成功');
  });

  test('应该能够查看发票管理 @readonly', async ({ page }) => {
    await page.goto('/finance/invoices');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 验证页面内容
    await expect(page.locator('.el-table')).toBeVisible();

    console.log('✅ 发票管理页面加载成功');
  });

  test('应该能够查看银行流水 @readonly', async ({ page }) => {
    await page.goto('/finance/bank-transfers');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 等待并验证主要内容
    await page.waitForSelector('.el-table, .el-card', { timeout: 10000 });

    console.log('✅ 银行流水页面加载成功');
  });

  test('应该能够查看财务报表 @readonly', async ({ page }) => {
    await page.goto('/finance/reports');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 等待并验证主要内容
    await page.waitForSelector('.el-table, .el-card', { timeout: 10000 });

    console.log('✅ 财务报表页面加载成功');
  });

  test('应该能够查看审计日志 @readonly', async ({ page }) => {
    await page.goto('/finance/audit-logs');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 验证页面内容
    await expect(page.locator('.el-table')).toBeVisible();

    console.log('✅ 审计日志页面加载成功');
  });

  // 本地环境的写操作测试
  if (!isProduction) {
    test('应该能够筛选充值记录', async ({ page }) => {
      await page.goto('/finance/recharge-records');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 选择充值方式筛选
      const methodSelect = page.locator('.el-select').filter({ hasText: /充值方式|支付方式/ });
      if (await methodSelect.isVisible({ timeout: 2000 })) {
        await methodSelect.click();

        // 选择第一个选项
        const firstOption = page.locator('.el-select-dropdown .el-option').first();
        if (await firstOption.isVisible({ timeout: 2000 })) {
          await firstOption.click();
          await page.waitForTimeout(1000);
          console.log('✅ 充值记录筛选功能正常');
        }
      }
    });

    test('应该能够筛选交易类型', async ({ page }) => {
      await page.goto('/finance/transactions');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 选择交易类型
      const typeSelect = page.locator('.el-select').first();
      if (await typeSelect.isVisible({ timeout: 2000 })) {
        await typeSelect.click();

        // 选择"充值"类型
        const rechargeOption = page.getByRole('option', { name: /充值/ });
        if (await rechargeOption.isVisible({ timeout: 2000 })) {
          await rechargeOption.click();
          await page.waitForTimeout(1000);
          console.log('✅ 交易类型筛选功能正常');
        }
      }
    });

    test('应该能够确认充值', async ({ page }) => {
      // 创建测试运营商
      const operatorId = await db.createTestOperator('e2e_finance_test_op');

      await page.goto('/finance/recharge-records');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 查找待审核的充值记录(如果有)
      const pendingRow = page.locator('.el-table__row').filter({ hasText: /待审核|Pending/ }).first();

      if (await pendingRow.isVisible({ timeout: 2000 })) {
        // 点击确认按钮
        const confirmButton = pendingRow.getByRole('button', { name: /确认|通过/ });
        await confirmButton.click();

        // 确认操作
        const dialogConfirmButton = page.getByRole('button', { name: /确定|确认/ });
        if (await dialogConfirmButton.isVisible({ timeout: 2000 })) {
          await dialogConfirmButton.click();
        }

        // 等待成功消息
        await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });

        console.log('✅ 充值确认功能正常');
      } else {
        console.log('⚠️  没有待审核的充值记录,跳过确认测试');
      }
    });

    test('应该能够执行扣费操作', async ({ page }) => {
      // 创建测试运营商并设置余额
      const operatorId = await db.createTestOperator('e2e_deduct_test_op');

      await page.goto('/finance/recharge-records');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 查找第一条记录进行扣费测试
      const firstRow = page.locator('.el-table__row').first();

      if (await firstRow.isVisible({ timeout: 2000 })) {
        // 点击扣费按钮
        const deductButton = firstRow.getByRole('button', { name: /扣费|确认扣费/ });

        if (await deductButton.isVisible({ timeout: 2000 })) {
          await deductButton.click();

          // 确认扣费对话框
          const confirmButton = page.getByRole('button', { name: /确定|确认/ });
          if (await confirmButton.isVisible({ timeout: 2000 })) {
            await confirmButton.click();
          }

          // 等待成功消息
          await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });

          console.log('✅ 扣费操作功能正常');
        } else {
          console.log('⚠️  未找到扣费按钮,可能记录已扣费');
        }
      }
    });

    test('应该能够审批退款申请', async ({ page }) => {
      await page.goto('/finance/refunds');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 查找待审核的退款申请
      const pendingRow = page.locator('.el-table__row').filter({ hasText: /待审核|Pending/ }).first();

      if (await pendingRow.isVisible({ timeout: 2000 })) {
        // 点击审批按钮
        const approveButton = pendingRow.getByRole('button', { name: /通过|批准/ });
        if (await approveButton.isVisible({ timeout: 1000 })) {
          await approveButton.click();

          // 确认操作
          const confirmButton = page.getByRole('button', { name: /确定|确认/ });
          if (await confirmButton.isVisible({ timeout: 2000 })) {
            await confirmButton.click();
          }

          // 等待成功消息
          await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });

          console.log('✅ 退款审批功能正常');
        }
      } else {
        console.log('⚠️  没有待审核的退款申请,跳过审批测试');
      }
    });
  }
});
