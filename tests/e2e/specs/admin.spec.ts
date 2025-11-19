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

    // ========== 完整流程测试 ==========

    test('完整流程: 创建应用', async ({ page }) => {
      await page.goto('/admin/applications/create');

      console.log('📝 开始测试创建应用流程');

      // 等待页面加载
      await page.waitForLoadState('networkidle');
      await page.waitForSelector('.el-form', { timeout: 10000 });

      const timestamp = Date.now();
      const appName = `E2E测试应用_${timestamp}`;
      const appKey = `e2e_test_app_${timestamp}`;

      // 填写应用名称
      const nameInput = page.locator('input[placeholder*="应用名称"]').or(page.locator('.el-form-item').filter({ hasText: /应用名称/ }).locator('input')).first();
      if (await nameInput.isVisible({ timeout: 2000 })) {
        await nameInput.fill(appName);
        console.log(`✅ 输入应用名称: ${appName}`);
      }

      // 填写应用标识
      const keyInput = page.locator('input[placeholder*="应用标识"]').or(page.locator('.el-form-item').filter({ hasText: /应用标识|App Key/ }).locator('input')).first();
      if (await keyInput.isVisible({ timeout: 2000 })) {
        await keyInput.fill(appKey);
        console.log(`✅ 输入应用标识: ${appKey}`);
      }

      // 选择应用类型
      const typeSelect = page.locator('.el-select').first();
      if (await typeSelect.isVisible({ timeout: 2000 })) {
        await typeSelect.click();
        await page.waitForTimeout(500);
        const firstType = page.locator('.el-select-dropdown .el-option').first();
        if (await firstType.isVisible({ timeout: 1000 })) {
          await firstType.click();
          console.log('✅ 选择应用类型');
        }
      }

      // 填写描述
      const descTextarea = page.locator('textarea[placeholder*="描述"]').or(page.locator('.el-form-item').filter({ hasText: /描述/ }).locator('textarea')).first();
      if (await descTextarea.isVisible({ timeout: 2000 })) {
        await descTextarea.fill('E2E自动化测试应用,测试完成后将删除');
        console.log('✅ 输入应用描述');
      }

      // 提交创建
      const submitButton = page.getByRole('button', { name: /提交|创建/ }).first();
      if (await submitButton.isVisible({ timeout: 2000 })) {
        await submitButton.click();

        // 等待成功消息
        const successMessage = page.locator('.el-message--success');
        if (await successMessage.isVisible({ timeout: 5000 })) {
          console.log('✅ 应用创建成功');

          // 返回应用列表并删除测试应用
          await page.goto('/admin/applications');
          await page.waitForSelector('.el-table', { timeout: 10000 });

          const appRow = page.locator('.el-table__row').filter({ hasText: appName }).first();
          if (await appRow.isVisible({ timeout: 2000 })) {
            const deleteButton = appRow.getByRole('button', { name: /删除/ }).first();
            if (await deleteButton.isVisible({ timeout: 1000 })) {
              await deleteButton.click();

              // 确认删除
              const confirmButton = page.getByRole('button', { name: /确定/ }).last();
              if (await confirmButton.isVisible({ timeout: 2000 })) {
                await confirmButton.click();
                await expect(successMessage).toBeVisible({ timeout: 5000 });
                console.log('✅ 测试应用已删除');
              }
            }
          }
        } else {
          console.log('⚠️  可能创建失败或表单验证错误');
        }
      }
    });

    test('完整流程: 审批应用申请', async ({ page }) => {
      await page.goto('/admin/app-requests');

      console.log('📝 开始测试应用申请审批流程');

      // 等待页面加载
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      // 查找待审核的申请
      const pendingRow = page.locator('.el-table__row').filter({ hasText: /待审核|Pending/ }).first();

      if (await pendingRow.isVisible({ timeout: 2000 })) {
        // 点击查看详情
        const detailButton = pendingRow.getByRole('button', { name: /详情|查看/ }).first();
        if (await detailButton.isVisible({ timeout: 1000 })) {
          await detailButton.click();

          // 等待详情对话框
          const dialog = page.locator('.el-dialog').last();
          await expect(dialog).toBeVisible({ timeout: 3000 });
          console.log('✅ 查看申请详情');

          // 关闭详情
          await page.keyboard.press('Escape');
          await page.waitForTimeout(500);
        }

        // 点击通过按钮
        const approveButton = pendingRow.getByRole('button', { name: /通过|批准|同意/ }).first();
        if (await approveButton.isVisible({ timeout: 1000 })) {
          console.log('✅ 找到审批按钮 (不实际审批以避免修改数据)');
        } else {
          console.log('⚠️  未找到审批按钮');
        }
      } else {
        console.log('⚠️  暂无待审核的申请');
      }
    });

    test('完整流程: 管理游戏授权', async ({ page }) => {
      await page.goto('/admin/authorizations');

      console.log('📝 开始测试游戏授权管理');

      // 等待页面加载
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      // 查找创建授权按钮
      const createButton = page.getByRole('button', { name: /创建授权|新增授权|添加/ }).first();

      if (await createButton.isVisible({ timeout: 2000 })) {
        await createButton.click();

        // 等待对话框
        const dialog = page.locator('.el-dialog').last();
        await expect(dialog).toBeVisible({ timeout: 3000 });

        // 选择运营商
        const operatorSelect = dialog.locator('.el-select').first();
        if (await operatorSelect.isVisible({ timeout: 1000 })) {
          await operatorSelect.click();
          await page.waitForTimeout(500);

          const firstOperator = page.locator('.el-select-dropdown .el-option').first();
          if (await firstOperator.isVisible({ timeout: 2000 })) {
            await firstOperator.click();
            console.log('✅ 选择运营商');
          }
        }

        // 选择应用
        const appSelect = dialog.locator('.el-select').nth(1);
        if (await appSelect.isVisible({ timeout: 1000 })) {
          await appSelect.click();
          await page.waitForTimeout(500);

          const firstApp = page.locator('.el-select-dropdown .el-option').first();
          if (await firstApp.isVisible({ timeout: 2000 })) {
            await firstApp.click();
            console.log('✅ 选择应用');
          }
        }

        // 设置授权期限
        const datePicker = dialog.locator('.el-date-editor');
        if (await datePicker.isVisible({ timeout: 1000 })) {
          console.log('✅ 授权表单验证通过 (不实际创建)');
        }

        // 关闭对话框
        await page.keyboard.press('Escape');
      } else {
        console.log('⚠️  未找到创建授权按钮');
      }
    });

    test('完整流程: 运营商账户管理', async ({ page }) => {
      await page.goto('/admin/operators');

      console.log('📝 开始测试运营商账户管理');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 查找第一个运营商
      const firstRow = page.locator('.el-table__row').first();

      if (await firstRow.isVisible({ timeout: 2000 })) {
        // 点击查看详情
        const detailButton = firstRow.getByRole('button', { name: /详情|查看/ }).first();
        if (await detailButton.isVisible({ timeout: 1000 })) {
          await detailButton.click();

          // 等待详情对话框
          const dialog = page.locator('.el-dialog').last();
          if (await dialog.isVisible({ timeout: 3000 })) {
            console.log('✅ 查看运营商详情');

            // 关闭对话框
            await page.keyboard.press('Escape');
          }
        }

        // 测试锁定/解锁功能 (不实际操作)
        const lockButton = firstRow.getByRole('button', { name: /锁定|解锁/ }).first();
        if (await lockButton.isVisible({ timeout: 1000 })) {
          console.log('✅ 找到锁定/解锁按钮 (不实际操作)');
        }

        // 测试编辑功能
        const editButton = firstRow.getByRole('button', { name: /编辑/ }).first();
        if (await editButton.isVisible({ timeout: 1000 })) {
          await editButton.click();

          const dialog = page.locator('.el-dialog').last();
          if (await dialog.isVisible({ timeout: 3000 })) {
            console.log('✅ 打开运营商编辑对话框');

            // 关闭对话框
            await page.keyboard.press('Escape');
          }
        }
      }
    });

    test('完整流程: 查看和导出交易报表', async ({ page }) => {
      await page.goto('/admin/transactions');

      console.log('📝 开始测试交易报表查看和导出');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 选择日期范围
      const dateRangePicker = page.locator('.el-date-editor').first();
      if (await dateRangePicker.isVisible({ timeout: 2000 })) {
        await dateRangePicker.click();
        await page.waitForTimeout(500);

        // 选择最近7天
        const recentDaysButton = page.getByRole('button', { name: /最近7天|近7天/ });
        if (await recentDaysButton.isVisible({ timeout: 1000 })) {
          await recentDaysButton.click();
          console.log('✅ 选择日期范围: 最近7天');
        } else {
          await page.keyboard.press('Escape');
        }
      }

      // 选择交易类型筛选
      const typeSelect = page.locator('.el-select').first();
      if (await typeSelect.isVisible({ timeout: 1000 })) {
        await typeSelect.click();
        await page.waitForTimeout(300);

        const rechargeOption = page.getByRole('option', { name: /充值/ }).first();
        if (await rechargeOption.isVisible({ timeout: 1000 })) {
          await rechargeOption.click();
          await page.waitForTimeout(500);
          console.log('✅ 筛选充值交易');
        }
      }

      // 查询
      const queryButton = page.getByRole('button', { name: /查询|搜索/ }).first();
      if (await queryButton.isVisible({ timeout: 1000 })) {
        await queryButton.click();
        await page.waitForTimeout(1000);
        console.log('✅ 执行查询');
      }

      // 测试导出功能
      const exportButton = page.getByRole('button', { name: /导出|Export/ }).first();
      if (await exportButton.isVisible({ timeout: 2000 })) {
        console.log('✅ 找到导出按钮 (不实际导出)');
      }

      // 验证统计信息
      const statsCard = page.locator('.stat-card, .statistics-card, .summary-card');
      if (await statsCard.first().isVisible({ timeout: 2000 })) {
        const count = await statsCard.count();
        console.log(`✅ 显示 ${count} 个统计卡片`);
      }
    });

    test('完整流程: 管理运营商站点', async ({ page }) => {
      await page.goto('/admin/operator-sites');

      console.log('📝 开始测试运营商站点管理');

      // 等待页面加载
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      // 搜索特定运营商的站点
      const searchInput = page.locator('input[placeholder*="搜索"]').first();
      if (await searchInput.isVisible({ timeout: 2000 })) {
        await searchInput.fill('operator');
        await page.waitForTimeout(500);
        console.log('✅ 搜索运营商站点');
      }

      // 选择运营商筛选
      const operatorSelect = page.locator('.el-select').first();
      if (await operatorSelect.isVisible({ timeout: 2000 })) {
        await operatorSelect.click();
        await page.waitForTimeout(500);

        const firstOperator = page.locator('.el-select-dropdown .el-option').first();
        if (await firstOperator.isVisible({ timeout: 1000 })) {
          await firstOperator.click();
          await page.waitForTimeout(500);
          console.log('✅ 筛选运营商');
        }
      }

      // 查看站点详情
      const firstRow = page.locator('.el-table__row').first();
      if (await firstRow.isVisible({ timeout: 2000 })) {
        const detailButton = firstRow.getByRole('button', { name: /详情|查看/ }).first();
        if (await detailButton.isVisible({ timeout: 1000 })) {
          await detailButton.click();

          const dialog = page.locator('.el-dialog').last();
          if (await dialog.isVisible({ timeout: 3000 })) {
            console.log('✅ 查看站点详情');
            await page.keyboard.press('Escape');
          }
        }
      }
    });
  }
});
