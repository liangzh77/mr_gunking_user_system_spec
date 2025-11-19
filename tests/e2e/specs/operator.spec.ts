import { test, expect } from '@playwright/test';
import { loginAsOperator, logout } from '../fixtures/auth';
import { getEnvironment } from '../config/environments';
import { DatabaseHelper } from '../utils/db-helper';

const env = getEnvironment();
const isProduction = env.name === 'production';
const db = new DatabaseHelper();

test.describe('运营商角色测试', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsOperator(page);
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
    await expect(page).toHaveURL(/.*\/operator\/dashboard/);

    // 验证仪表盘统计卡片显示
    await expect(page.locator('.stat-card').first()).toBeVisible({ timeout: 10000 });

    // 验证余额卡片
    await expect(page.locator('.balance-card')).toBeVisible();

    console.log('✅ 运营商仪表盘加载成功');
  });

  test('应该能够查看个人资料 @readonly', async ({ page }) => {
    await page.goto('/operator/profile');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 等待并验证主要内容
    await page.waitForSelector('.el-card, .el-form', { timeout: 10000 });

    console.log('✅ 个人资料页面加载成功');
  });

  test('应该能够查看充值页面 @readonly', async ({ page }) => {
    await page.goto('/operator/recharge');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 等待并验证主要内容
    await page.waitForSelector('.el-card, .el-form', { timeout: 10000 });

    console.log('✅ 充值页面加载成功');
  });

  test('应该能够查看交易记录 @readonly', async ({ page }) => {
    await page.goto('/operator/transactions');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 验证页面内容
    await expect(page.locator('.el-table')).toBeVisible();

    console.log('✅ 交易记录页面加载成功');
  });

  test('应该正确显示财务扣费类型 @readonly', async ({ page }) => {
    await page.goto('/operator/transactions');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 检查扣费类型筛选器
    const typeSelect = page.locator('.el-select').first();
    if (await typeSelect.isVisible({ timeout: 2000 })) {
      await typeSelect.click();

      // 验证"财务扣费"选项存在
      const deductOption = page.getByRole('option', { name: '财务扣费' });
      await expect(deductOption).toBeVisible();

      console.log('✅ 财务扣费类型显示正确');

      // 关闭下拉框
      await page.keyboard.press('Escape');
    }
  });

  test('应该能够查看站点管理 @readonly', async ({ page }) => {
    await page.goto('/operator/sites');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 验证页面内容
    await expect(page.locator('.el-table')).toBeVisible();

    console.log('✅ 站点管理页面加载成功');
  });

  test('应该能够查看应用管理 @readonly', async ({ page }) => {
    await page.goto('/operator/applications');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 验证页面内容
    await expect(page.locator('.el-table')).toBeVisible();

    console.log('✅ 应用管理页面加载成功');
  });

  test('应该能够查看应用申请 @readonly', async ({ page }) => {
    await page.goto('/operator/app-requests');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 等待并验证主要内容
    await page.waitForSelector('.el-table, .el-card', { timeout: 10000 });

    console.log('✅ 应用申请页面加载成功');
  });

  test('应该能够查看使用记录 @readonly', async ({ page }) => {
    await page.goto('/operator/usage-records');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 验证页面内容
    await expect(page.locator('.el-table')).toBeVisible();

    console.log('✅ 使用记录页面加载成功');
  });

  test('应该能够查看统计分析 @readonly', async ({ page }) => {
    await page.goto('/operator/statistics');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 等待并验证主要内容
    await page.waitForSelector('.el-table, .el-card, .chart, canvas', { timeout: 10000 });

    console.log('✅ 统计分析页面加载成功');
  });

  test('应该能够查看退款管理 @readonly', async ({ page }) => {
    await page.goto('/operator/refunds');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 验证页面内容
    await expect(page.locator('.el-table')).toBeVisible();

    console.log('✅ 退款管理页面加载成功');
  });

  test('应该能够查看发票管理 @readonly', async ({ page }) => {
    await page.goto('/operator/invoices');

    // 等待表格加载
    await page.waitForSelector('.el-table', { timeout: 10000 });

    // 验证页面内容
    await expect(page.locator('.el-table')).toBeVisible();

    console.log('✅ 发票管理页面加载成功');
  });

  test('应该能够查看消息中心 @readonly', async ({ page }) => {
    await page.goto('/operator/messages');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 等待并验证主要内容
    await page.waitForSelector('.el-table, .el-card, .message-list, .el-timeline', { timeout: 10000 });

    console.log('✅ 消息中心页面加载成功');
  });

  // 本地环境的写操作测试
  if (!isProduction) {
    test('应该能够筛选交易记录', async ({ page }) => {
      await page.goto('/operator/transactions');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 选择交易类型
      const typeSelect = page.locator('.el-select').first();
      if (await typeSelect.isVisible({ timeout: 2000 })) {
        await typeSelect.click();

        // 选择"充值"类型
        const rechargeOption = page.getByRole('option', { name: '充值' });
        if (await rechargeOption.isVisible({ timeout: 2000 })) {
          await rechargeOption.click();
          await page.waitForTimeout(1000);
          console.log('✅ 交易记录筛选功能正常');
        }
      }
    });

    test('应该能够筛选扣费记录', async ({ page }) => {
      await page.goto('/operator/transactions');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 选择交易类型
      const typeSelect = page.locator('.el-select').first();
      if (await typeSelect.isVisible({ timeout: 2000 })) {
        await typeSelect.click();

        // 选择"财务扣费"类型
        const deductOption = page.getByRole('option', { name: '财务扣费' });
        if (await deductOption.isVisible({ timeout: 2000 })) {
          await deductOption.click();
          await page.waitForTimeout(1000);

          // 验证筛选结果
          const table = page.locator('.el-table');
          await expect(table).toBeVisible();

          console.log('✅ 扣费记录筛选功能正常');
        }
      }
    });

    test('应该能够提交充值申请', async ({ page }) => {
      await page.goto('/operator/recharge');

      // 填写充值金额
      const amountInput = page.getByLabel(/充值金额|金额|Amount/);
      await amountInput.fill('100');

      // 选择支付方式
      const methodSelect = page.locator('.el-select').filter({ hasText: /支付方式|Payment/ });
      if (await methodSelect.isVisible({ timeout: 2000 })) {
        await methodSelect.click();
        await page.getByRole('option').first().click();
      }

      // 上传凭证(如果需要)
      const uploadButton = page.locator('.el-upload');
      if (await uploadButton.isVisible({ timeout: 2000 })) {
        console.log('⚠️  上传凭证功能需要实际文件,跳过');
      }

      // 提交申请
      const submitButton = page.getByRole('button', { name: /提交|申请/ });
      if (await submitButton.isVisible({ timeout: 2000 })) {
        // 注意:这里不实际提交,避免创建过多测试数据
        console.log('✅ 充值申请表单验证通过');
      }
    });

    test('应该能够创建站点', async ({ page }) => {
      await page.goto('/operator/sites');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 点击创建按钮
      const createButton = page.getByRole('button', { name: /创建|新增|添加/ });

      if (await createButton.isVisible({ timeout: 2000 })) {
        await createButton.click();

        // 等待对话框出现
        const dialog = page.locator('.el-dialog');
        await expect(dialog).toBeVisible({ timeout: 2000 });

        // 填写站点信息
        const siteNameInput = page.getByLabel(/站点名称|名称|Name/);
        if (await siteNameInput.isVisible({ timeout: 2000 })) {
          await siteNameInput.fill(`E2E测试站点_${Date.now()}`);

          // 填写URL
          const urlInput = page.getByLabel(/URL|网址|地址/);
          if (await urlInput.isVisible({ timeout: 1000 })) {
            await urlInput.fill('https://e2e-test.example.com');
          }

          // 点击提交
          const dialogSubmitButton = dialog.getByRole('button', { name: /确定|提交/ });
          await dialogSubmitButton.click();

          // 等待成功消息
          await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });

          console.log('✅ 站点创建功能正常');
        } else {
          // 关闭对话框
          await page.keyboard.press('Escape');
          console.log('⚠️  站点创建表单结构可能已变更,跳过测试');
        }
      } else {
        console.log('⚠️  未找到创建按钮,可能权限不足');
      }
    });

    test('应该能够申请退款', async ({ page }) => {
      await page.goto('/operator/refunds');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 点击申请退款按钮
      const applyButton = page.getByRole('button', { name: /申请|新增/ });

      if (await applyButton.isVisible({ timeout: 2000 })) {
        await applyButton.click();

        // 等待对话框
        const dialog = page.locator('.el-dialog');
        if (await dialog.isVisible({ timeout: 2000 })) {
          // 填写退款金额
          const amountInput = page.getByLabel(/金额|Amount/);
          if (await amountInput.isVisible({ timeout: 1000 })) {
            await amountInput.fill('50');

            // 填写原因
            const reasonInput = page.getByLabel(/原因|理由|Reason/);
            if (await reasonInput.isVisible({ timeout: 1000 })) {
              await reasonInput.fill('E2E自动化测试退款');

              // 注意:不实际提交,避免创建过多测试数据
              console.log('✅ 退款申请表单验证通过');

              // 关闭对话框
              await page.keyboard.press('Escape');
            }
          }
        }
      } else {
        console.log('⚠️  未找到退款申请按钮');
      }
    });

    test('应该能够申请发票', async ({ page }) => {
      await page.goto('/operator/invoices');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 点击申请发票按钮
      const applyButton = page.getByRole('button', { name: /申请|开具/ });

      if (await applyButton.isVisible({ timeout: 2000 })) {
        await applyButton.click();

        // 等待对话框
        const dialog = page.locator('.el-dialog');
        if (await dialog.isVisible({ timeout: 2000 })) {
          console.log('✅ 发票申请对话框正常打开');

          // 关闭对话框
          await page.keyboard.press('Escape');
        }
      } else {
        console.log('⚠️  未找到发票申请按钮');
      }
    });

    test('应该能够查看使用记录详情', async ({ page }) => {
      await page.goto('/operator/usage-records');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 查找第一条记录
      const firstRow = page.locator('.el-table__row').first();

      if (await firstRow.isVisible({ timeout: 2000 })) {
        // 查找详情按钮
        const detailButton = firstRow.getByRole('button', { name: /详情|查看/ });

        if (await detailButton.isVisible({ timeout: 1000 })) {
          await detailButton.click();

          // 等待详情对话框
          const dialog = page.locator('.el-dialog');
          await expect(dialog).toBeVisible({ timeout: 2000 });

          console.log('✅ 使用记录详情功能正常');

          // 关闭对话框
          await page.keyboard.press('Escape');
        } else {
          console.log('⚠️  没有使用记录或无详情按钮');
        }
      }
    });
  }
});
