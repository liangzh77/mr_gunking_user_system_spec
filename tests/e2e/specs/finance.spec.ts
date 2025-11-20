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

  test.skip('应该能够查看银行流水 @readonly', async ({ page }) => {
    await page.goto('/finance/bank-transfers');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 等待并验证主要内容
    await page.waitForSelector('.el-table, .el-card', { timeout: 10000 });

    console.log('✅ 银行流水页面加载成功');
  });

  test.skip('应该能够查看财务报表 @readonly', async ({ page }) => {
    await page.goto('/finance/reports');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 等待并验证主要内容
    await page.waitForSelector('.el-table, .el-card', { timeout: 10000 });

    console.log('✅ 财务报表页面加载成功');
  });

  test.skip('应该能够查看审计日志 @readonly', async ({ page }) => {
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

    // ========== 完整流程测试 ==========

    test('完整流程: 充值审核和扣费', async ({ page }) => {
      await page.goto('/finance/recharge-records');

      console.log('📝 开始测试充值审核和扣费流程');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 查找待审核的充值记录
      const pendingRow = page.locator('.el-table__row').filter({ hasText: /待审核|Pending/ }).first();

      if (await pendingRow.isVisible({ timeout: 2000 })) {
        // 查看充值详情
        const detailButton = pendingRow.getByRole('button', { name: /详情|查看/ }).first();
        if (await detailButton.isVisible({ timeout: 1000 })) {
          await detailButton.click();

          // 等待详情对话框
          const dialog = page.locator('.el-dialog').last();
          if (await dialog.isVisible({ timeout: 3000 })) {
            console.log('✅ 查看充值详情');

            // 验证详情内容
            const amount = dialog.locator('.el-descriptions-item').filter({ hasText: /金额/ });
            if (await amount.isVisible()) {
              console.log('✅ 确认充值金额');
            }

            // 验证凭证图片
            const voucher = dialog.locator('img, .voucher-image');
            if (await voucher.isVisible({ timeout: 1000 })) {
              console.log('✅ 查看转账凭证');
            }

            // 关闭详情
            await page.keyboard.press('Escape');
            await page.waitForTimeout(500);
          }
        }

        // 确认充值
        const confirmButton = pendingRow.getByRole('button', { name: /确认|审核/ }).first();
        if (await confirmButton.isVisible({ timeout: 1000 })) {
          console.log('✅ 找到确认按钮 (不实际审核以避免修改数据)');
        }

        // 测试驳回功能
        const rejectButton = pendingRow.getByRole('button', { name: /驳回|拒绝/ }).first();
        if (await rejectButton.isVisible({ timeout: 1000 })) {
          console.log('✅ 找到驳回按钮');
        }
      } else {
        console.log('⚠️  暂无待审核的充值记录');
      }

      // 测试已确认记录的扣费操作
      const confirmedRow = page.locator('.el-table__row').filter({ hasText: /已确认|已审核/ }).first();
      if (await confirmedRow.isVisible({ timeout: 2000 })) {
        const deductButton = confirmedRow.getByRole('button', { name: /扣费|确认扣费/ }).first();
        if (await deductButton.isVisible({ timeout: 1000 })) {
          console.log('✅ 找到扣费按钮 (不实际扣费)');
        }
      }
    });

    test('完整流程: 退款审批(通过和拒绝)', async ({ page }) => {
      await page.goto('/finance/refunds');

      console.log('📝 开始测试退款审批流程');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 查找待审核的退款申请
      const pendingRow = page.locator('.el-table__row').filter({ hasText: /待审核|Pending/ }).first();

      if (await pendingRow.isVisible({ timeout: 2000 })) {
        // 查看退款详情
        const detailButton = pendingRow.getByRole('button', { name: /详情|查看/ }).first();
        if (await detailButton.isVisible({ timeout: 1000 })) {
          await detailButton.click();

          const dialog = page.locator('.el-dialog').last();
          if (await dialog.isVisible({ timeout: 3000 })) {
            console.log('✅ 查看退款申请详情');

            // 验证退款信息
            const refundAmount = dialog.locator('.el-descriptions-item').filter({ hasText: /退款金额/ });
            if (await refundAmount.isVisible()) {
              console.log('✅ 确认退款金额');
            }

            const refundReason = dialog.locator('.el-descriptions-item').filter({ hasText: /退款原因/ });
            if (await refundReason.isVisible()) {
              console.log('✅ 查看退款原因');
            }

            await page.keyboard.press('Escape');
            await page.waitForTimeout(500);
          }
        }

        // 测试审批通过
        const approveButton = pendingRow.getByRole('button', { name: /通过|批准|同意/ }).first();
        if (await approveButton.isVisible({ timeout: 1000 })) {
          console.log('✅ 找到退款审批通过按钮 (不实际审批)');
        }

        // 测试审批拒绝
        const rejectButton = pendingRow.getByRole('button', { name: /拒绝|驳回/ }).first();
        if (await rejectButton.isVisible({ timeout: 1000 })) {
          console.log('✅ 找到退款审批拒绝按钮');
        }
      } else {
        console.log('⚠️  暂无待审核的退款申请');
      }
    });

    test('完整流程: 发票审核', async ({ page }) => {
      await page.goto('/finance/invoices');

      console.log('📝 开始测试发票审核流程');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 查找待审核的发票申请
      const pendingRow = page.locator('.el-table__row').filter({ hasText: /待审核|待开具/ }).first();

      if (await pendingRow.isVisible({ timeout: 2000 })) {
        // 查看发票详情
        const detailButton = pendingRow.getByRole('button', { name: /详情|查看/ }).first();
        if (await detailButton.isVisible({ timeout: 1000 })) {
          await detailButton.click();

          const dialog = page.locator('.el-dialog').last();
          if (await dialog.isVisible({ timeout: 3000 })) {
            console.log('✅ 查看发票申请详情');

            // 验证发票信息
            const invoiceType = dialog.locator('.el-descriptions-item').filter({ hasText: /发票类型/ });
            if (await invoiceType.isVisible()) {
              console.log('✅ 确认发票类型');
            }

            const companyName = dialog.locator('.el-descriptions-item').filter({ hasText: /公司名称/ });
            if (await companyName.isVisible()) {
              console.log('✅ 查看公司信息');
            }

            await page.keyboard.press('Escape');
            await page.waitForTimeout(500);
          }
        }

        // 测试开具发票
        const issueButton = pendingRow.getByRole('button', { name: /开具|审核/ }).first();
        if (await issueButton.isVisible({ timeout: 1000 })) {
          console.log('✅ 找到发票开具按钮 (不实际开具)');
        }
      } else {
        console.log('⚠️  暂无待审核的发票申请');
      }
    });

    test.skip('完整流程: 生成和导出财务报表', async ({ page }) => {
      await page.goto('/finance/reports');

      console.log('📝 开始测试财务报表生成和导出');

      // 等待页面加载
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      // 选择报表类型
      const reportTypeSelect = page.locator('.el-select').first();
      if (await reportTypeSelect.isVisible({ timeout: 2000 })) {
        await reportTypeSelect.click();
        await page.waitForTimeout(500);

        // 选择"收入报表"
        const incomeReport = page.getByRole('option', { name: /收入|营收/ }).first();
        if (await incomeReport.isVisible({ timeout: 1000 })) {
          await incomeReport.click();
          console.log('✅ 选择报表类型: 收入报表');
        } else {
          await page.keyboard.press('Escape');
        }
      }

      // 选择时间范围
      const dateRangePicker = page.locator('.el-date-editor');
      if (await dateRangePicker.isVisible({ timeout: 2000 })) {
        await dateRangePicker.click();
        await page.waitForTimeout(500);

        const thisMonthButton = page.getByRole('button', { name: /本月/ });
        if (await thisMonthButton.isVisible({ timeout: 1000 })) {
          await thisMonthButton.click();
          console.log('✅ 选择时间范围: 本月');
        } else {
          await page.keyboard.press('Escape');
        }
      }

      // 生成报表
      const generateButton = page.getByRole('button', { name: /生成|查询/ }).first();
      if (await generateButton.isVisible({ timeout: 1000 })) {
        await generateButton.click();
        await page.waitForTimeout(2000);
        console.log('✅ 生成报表');
      }

      // 验证报表内容
      const reportTable = page.locator('.el-table, .report-table');
      if (await reportTable.isVisible({ timeout: 3000 })) {
        console.log('✅ 报表数据已显示');
      }

      // 测试导出功能
      const exportButton = page.getByRole('button', { name: /导出|Export/ }).first();
      if (await exportButton.isVisible({ timeout: 2000 })) {
        console.log('✅ 找到导出按钮 (不实际导出)');
      }

      // 验证统计汇总
      const summary = page.locator('.summary, .total, .statistics');
      if (await summary.first().isVisible({ timeout: 2000 })) {
        console.log('✅ 显示统计汇总信息');
      }
    });

    test.skip('完整流程: 查看和核对银行流水', async ({ page }) => {
      await page.goto('/finance/bank-transfers');

      console.log('📝 开始测试银行流水查看和核对');

      // 等待页面加载
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      // 选择日期范围
      const dateRangePicker = page.locator('.el-date-editor').first();
      if (await dateRangePicker.isVisible({ timeout: 2000 })) {
        await dateRangePicker.click();
        await page.waitForTimeout(500);

        const recentDaysButton = page.getByRole('button', { name: /最近7天|近7天/ });
        if (await recentDaysButton.isVisible({ timeout: 1000 })) {
          await recentDaysButton.click();
          console.log('✅ 选择日期范围: 最近7天');
        } else {
          await page.keyboard.press('Escape');
        }
      }

      // 查询
      const queryButton = page.getByRole('button', { name: /查询|搜索/ }).first();
      if (await queryButton.isVisible({ timeout: 1000 })) {
        await queryButton.click();
        await page.waitForTimeout(1000);
        console.log('✅ 查询银行流水');
      }

      // 查看第一条流水详情
      const firstRow = page.locator('.el-table__row').first();
      if (await firstRow.isVisible({ timeout: 2000 })) {
        const detailButton = firstRow.getByRole('button', { name: /详情|查看/ }).first();
        if (await detailButton.isVisible({ timeout: 1000 })) {
          await detailButton.click();

          const dialog = page.locator('.el-dialog').last();
          if (await dialog.isVisible({ timeout: 3000 })) {
            console.log('✅ 查看流水详情');
            await page.keyboard.press('Escape');
          }
        }

        // 测试核对功能
        const verifyButton = firstRow.getByRole('button', { name: /核对|确认/ }).first();
        if (await verifyButton.isVisible({ timeout: 1000 })) {
          console.log('✅ 找到流水核对按钮 (不实际操作)');
        }
      }

      // 测试筛选功能
      const statusSelect = page.locator('.el-select').filter({ hasText: /状态/ }).first();
      if (await statusSelect.isVisible({ timeout: 1000 })) {
        await statusSelect.click();
        await page.waitForTimeout(300);

        const firstStatus = page.locator('.el-select-dropdown .el-option').first();
        if (await firstStatus.isVisible({ timeout: 1000 })) {
          await firstStatus.click();
          console.log('✅ 筛选流水状态');
        }
      }
    });

    test.skip('完整流程: 审计日志查询和分析', async ({ page }) => {
      await page.goto('/finance/audit-logs');

      console.log('📝 开始测试审计日志查询');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 选择操作类型
      const actionSelect = page.locator('.el-select').first();
      if (await actionSelect.isVisible({ timeout: 2000 })) {
        await actionSelect.click();
        await page.waitForTimeout(500);

        const rechargeAction = page.getByRole('option', { name: /充值|审核/ }).first();
        if (await rechargeAction.isVisible({ timeout: 1000 })) {
          await rechargeAction.click();
          console.log('✅ 筛选操作类型: 充值审核');
        } else {
          await page.keyboard.press('Escape');
        }
      }

      // 选择操作人
      const operatorSelect = page.locator('.el-select').nth(1);
      if (await operatorSelect.isVisible({ timeout: 1000 })) {
        await operatorSelect.click();
        await page.waitForTimeout(500);

        const firstOperator = page.locator('.el-select-dropdown .el-option').first();
        if (await firstOperator.isVisible({ timeout: 1000 })) {
          await firstOperator.click();
          console.log('✅ 筛选操作人');
        }
      }

      // 选择日期范围
      const dateRangePicker = page.locator('.el-date-editor');
      if (await dateRangePicker.isVisible({ timeout: 2000 })) {
        await dateRangePicker.click();
        await page.waitForTimeout(500);

        const todayButton = page.getByRole('button', { name: /今天|Today/ });
        if (await todayButton.isVisible({ timeout: 1000 })) {
          await todayButton.click();
          console.log('✅ 选择日期: 今天');
        } else {
          await page.keyboard.press('Escape');
        }
      }

      // 查询
      const queryButton = page.getByRole('button', { name: /查询|搜索/ }).first();
      if (await queryButton.isVisible({ timeout: 1000 })) {
        await queryButton.click();
        await page.waitForTimeout(1000);
        console.log('✅ 查询审计日志');
      }

      // 查看日志详情
      const firstRow = page.locator('.el-table__row').first();
      if (await firstRow.isVisible({ timeout: 2000 })) {
        const detailButton = firstRow.getByRole('button', { name: /详情|查看/ }).first();
        if (await detailButton.isVisible({ timeout: 1000 })) {
          await detailButton.click();

          const dialog = page.locator('.el-dialog').last();
          if (await dialog.isVisible({ timeout: 3000 })) {
            console.log('✅ 查看审计日志详情');
            await page.keyboard.press('Escape');
          }
        }
      }

      // 测试导出日志
      const exportButton = page.getByRole('button', { name: /导出/ }).first();
      if (await exportButton.isVisible({ timeout: 2000 })) {
        console.log('✅ 找到导出日志按钮 (不实际导出)');
      }
    });
  }
});
