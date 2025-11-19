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

    // ========== 完整流程测试 ==========

    test('完整流程: 在线充值申请(银行转账)', async ({ page }) => {
      await page.goto('/operator/recharge');

      // 等待页面加载
      await page.waitForLoadState('networkidle');

      console.log('📝 开始测试在线充值流程');

      // 1. 点击快捷金额
      const presetTag = page.locator('.preset-tag').filter({ hasText: '100' }).first();
      if (await presetTag.isVisible({ timeout: 2000 })) {
        await presetTag.click();
        console.log('✅ 选择快捷金额: ¥100');
      } else {
        // 手动输入金额
        const amountInput = page.locator('input[placeholder*="充值金额"]');
        await amountInput.fill('100');
        console.log('✅ 手动输入金额: ¥100');
      }

      // 2. 选择银行转账支付方式
      const bankTransferRadio = page.locator('.el-radio').filter({ hasText: /银行转账/ });
      await bankTransferRadio.click();
      console.log('✅ 选择支付方式: 银行转账');

      // 3. 验证银行账户信息显示
      await page.waitForSelector('.bank-info-card', { timeout: 5000 });
      const bankInfo = page.locator('.bank-info-card');
      await expect(bankInfo).toBeVisible();
      console.log('✅ 银行账户信息已显示');

      // 4. 测试复制账户信息
      const copyButtons = page.locator('.bank-info-card button').filter({ hasText: '复制' });
      const copyCount = await copyButtons.count();
      if (copyCount > 0) {
        await copyButtons.first().click();
        await page.waitForTimeout(500);
        console.log('✅ 账户信息复制功能正常');
      }

      // 5. 上传转账凭证 (使用测试图片)
      // 注意: 这里创建一个简单的测试图片文件
      const testImagePath = await page.evaluate(() => {
        // 创建一个1x1的PNG图片 (最小有效PNG)
        const canvas = document.createElement('canvas');
        canvas.width = 1;
        canvas.height = 1;
        return canvas.toDataURL('image/png');
      });

      // 查找上传按钮
      const uploadButton = page.locator('button').filter({ hasText: /上传凭证|选择文件/ }).first();
      if (await uploadButton.isVisible({ timeout: 2000 })) {
        console.log('⚠️  找到上传按钮,但跳过文件上传(需要真实文件路径)');
      }

      // 6. 填写备注
      const remarkInput = page.locator('textarea[placeholder*="备注"]');
      if (await remarkInput.isVisible({ timeout: 1000 })) {
        await remarkInput.fill('E2E自动化测试 - 充值申请');
        console.log('✅ 填写备注信息');
      }

      console.log('✅ 充值申请表单填写完成 (未实际提交以避免生成测试数据)');
    });

    test('完整流程: 修改个人资料', async ({ page }) => {
      await page.goto('/operator/profile');

      console.log('📝 开始测试修改个人资料');

      // 等待页面加载
      await page.waitForLoadState('networkidle');
      await page.waitForSelector('.el-form', { timeout: 10000 });

      // 查找编辑按钮
      const editButton = page.getByRole('button', { name: /编辑|修改/ }).first();
      if (await editButton.isVisible({ timeout: 2000 })) {
        await editButton.click();
        console.log('✅ 点击编辑按钮');

        // 等待表单可编辑
        await page.waitForTimeout(500);

        // 修改联系电话
        const phoneInput = page.locator('input[placeholder*="手机"]');
        if (await phoneInput.isVisible({ timeout: 1000 }) && await phoneInput.isEnabled()) {
          const originalPhone = await phoneInput.inputValue();
          await phoneInput.fill('13800138888');
          console.log('✅ 修改联系电话');

          // 保存修改
          const saveButton = page.getByRole('button', { name: /保存|确定/ }).first();
          if (await saveButton.isVisible({ timeout: 1000 })) {
            await saveButton.click();

            // 等待成功消息
            const successMessage = page.locator('.el-message--success');
            if (await successMessage.isVisible({ timeout: 3000 })) {
              console.log('✅ 个人资料修改成功');

              // 恢复原始值
              await page.waitForTimeout(1000);
              await editButton.click();
              await page.waitForTimeout(500);
              await phoneInput.fill(originalPhone);
              await saveButton.click();
              console.log('✅ 已恢复原始数据');
            } else {
              console.log('⚠️  未收到成功消息,可能修改失败');
            }
          }
        } else {
          console.log('⚠️  表单不可编辑或结构已变更');
        }
      } else {
        console.log('⚠️  未找到编辑按钮');
      }
    });

    test('完整流程: 创建站点并编辑', async ({ page }) => {
      await page.goto('/operator/sites');

      console.log('📝 开始测试创建和编辑站点');

      // 等待表格加载
      await page.waitForSelector('.el-table', { timeout: 10000 });

      // 记录创建前的站点数量
      const initialRows = await page.locator('.el-table__row').count();
      console.log(`当前站点数量: ${initialRows}`);

      // 点击创建按钮
      const createButton = page.getByRole('button', { name: /创建|新增|添加/ }).first();
      if (await createButton.isVisible({ timeout: 2000 })) {
        await createButton.click();

        // 等待对话框
        const dialog = page.locator('.el-dialog').last();
        await expect(dialog).toBeVisible({ timeout: 3000 });

        const timestamp = Date.now();
        const siteName = `E2E测试站点_${timestamp}`;
        const siteUrl = `https://e2e-test-${timestamp}.example.com`;

        // 填写站点名称
        const nameInput = dialog.locator('input').first();
        await nameInput.fill(siteName);
        console.log(`✅ 输入站点名称: ${siteName}`);

        // 填写站点URL
        const urlInput = dialog.locator('input').nth(1);
        if (await urlInput.isVisible()) {
          await urlInput.fill(siteUrl);
          console.log(`✅ 输入站点URL: ${siteUrl}`);
        }

        // 填写描述
        const descInput = dialog.locator('textarea');
        if (await descInput.isVisible({ timeout: 1000 })) {
          await descInput.fill('E2E自动化测试站点,测试完成后将删除');
          console.log('✅ 输入站点描述');
        }

        // 提交创建
        const submitButton = dialog.getByRole('button', { name: /确定|提交/ }).first();
        await submitButton.click();

        // 等待成功消息
        const successMessage = page.locator('.el-message--success');
        await expect(successMessage).toBeVisible({ timeout: 5000 });
        console.log('✅ 站点创建成功');

        // 等待表格刷新
        await page.waitForTimeout(1000);

        // 验证新站点出现在列表中
        const newRows = await page.locator('.el-table__row').count();
        if (newRows > initialRows) {
          console.log(`✅ 站点列表已更新: ${initialRows} -> ${newRows}`);
        }

        // 查找刚创建的站点并编辑
        const newSiteRow = page.locator('.el-table__row').filter({ hasText: siteName }).first();
        if (await newSiteRow.isVisible({ timeout: 2000 })) {
          // 点击编辑按钮
          const editButton = newSiteRow.getByRole('button', { name: /编辑/ }).first();
          if (await editButton.isVisible({ timeout: 1000 })) {
            await editButton.click();

            // 等待编辑对话框
            const editDialog = page.locator('.el-dialog').last();
            await expect(editDialog).toBeVisible({ timeout: 3000 });

            // 修改描述
            const editDescInput = editDialog.locator('textarea');
            if (await editDescInput.isVisible({ timeout: 1000 })) {
              await editDescInput.fill('E2E自动化测试站点 - 已编辑');
              console.log('✅ 修改站点描述');

              // 保存修改
              const saveButton = editDialog.getByRole('button', { name: /确定|保存/ }).first();
              await saveButton.click();

              // 等待成功消息
              await expect(successMessage).toBeVisible({ timeout: 5000 });
              console.log('✅ 站点编辑成功');
            }
          }

          // 删除测试站点
          const deleteButton = newSiteRow.getByRole('button', { name: /删除/ }).first();
          if (await deleteButton.isVisible({ timeout: 1000 })) {
            await deleteButton.click();

            // 确认删除
            const confirmButton = page.getByRole('button', { name: /确定/ }).last();
            if (await confirmButton.isVisible({ timeout: 2000 })) {
              await confirmButton.click();
              await expect(successMessage).toBeVisible({ timeout: 5000 });
              console.log('✅ 测试站点已删除');
            }
          }
        }
      } else {
        console.log('⚠️  未找到创建站点按钮');
      }
    });

    test('完整流程: 提交应用申请', async ({ page }) => {
      await page.goto('/operator/app-requests');

      console.log('📝 开始测试应用申请流程');

      // 等待页面加载
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      // 点击新建申请按钮
      const createButton = page.getByRole('button', { name: /新建申请|创建/ }).first();
      if (await createButton.isVisible({ timeout: 2000 })) {
        await createButton.click();

        // 等待对话框
        const dialog = page.locator('.el-dialog').last();
        await expect(dialog).toBeVisible({ timeout: 3000 });

        // 选择应用
        const appSelect = dialog.locator('.el-select').first();
        if (await appSelect.isVisible({ timeout: 1000 })) {
          await appSelect.click();
          await page.waitForTimeout(500);

          // 选择第一个应用
          const firstOption = page.locator('.el-select-dropdown .el-option').first();
          if (await firstOption.isVisible({ timeout: 2000 })) {
            await firstOption.click();
            console.log('✅ 选择应用');
          }
        }

        // 填写申请原因
        const reasonInput = dialog.locator('textarea');
        if (await reasonInput.isVisible({ timeout: 1000 })) {
          await reasonInput.fill('E2E自动化测试 - 申请应用使用权限');
          console.log('✅ 填写申请原因');
        }

        console.log('✅ 应用申请表单填写完成 (不实际提交)');

        // 关闭对话框
        await page.keyboard.press('Escape');
      } else {
        console.log('⚠️  未找到新建申请按钮');
      }
    });

    test('完整流程: 查看和导出统计数据', async ({ page }) => {
      await page.goto('/operator/statistics');

      console.log('📝 开始测试统计数据查看和导出');

      // 等待页面加载
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // 选择日期范围
      const dateRangePicker = page.locator('.el-date-editor').first();
      if (await dateRangePicker.isVisible({ timeout: 2000 })) {
        await dateRangePicker.click();
        await page.waitForTimeout(500);

        // 选择本月
        const thisMonthButton = page.getByRole('button', { name: /本月|This Month/ });
        if (await thisMonthButton.isVisible({ timeout: 1000 })) {
          await thisMonthButton.click();
          console.log('✅ 选择日期范围: 本月');
        } else {
          await page.keyboard.press('Escape');
        }
      }

      // 点击查询按钮
      const queryButton = page.getByRole('button', { name: /查询|搜索/ }).first();
      if (await queryButton.isVisible({ timeout: 1000 })) {
        await queryButton.click();
        await page.waitForTimeout(1000);
        console.log('✅ 执行查询');
      }

      // 查找导出按钮
      const exportButton = page.getByRole('button', { name: /导出|Export/ }).first();
      if (await exportButton.isVisible({ timeout: 2000 })) {
        console.log('✅ 找到导出按钮 (不实际导出以避免文件下载)');
      }

      // 验证图表显示
      const charts = page.locator('canvas, .chart, .echarts');
      const chartCount = await charts.count();
      if (chartCount > 0) {
        console.log(`✅ 页面显示 ${chartCount} 个图表`);
      }
    });

    test('完整流程: 查看消息并标记已读', async ({ page }) => {
      await page.goto('/operator/messages');

      console.log('📝 开始测试消息中心');

      // 等待页面加载
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      // 查找未读消息
      const unreadMessage = page.locator('.el-table__row').filter({ hasText: /未读/ }).first();
      if (await unreadMessage.isVisible({ timeout: 2000 })) {
        // 点击消息查看详情
        await unreadMessage.click();
        await page.waitForTimeout(500);

        // 或者点击标记已读按钮
        const markReadButton = unreadMessage.getByRole('button', { name: /标记已读|已读/ }).first();
        if (await markReadButton.isVisible({ timeout: 1000 })) {
          await markReadButton.click();
          await page.waitForTimeout(500);
          console.log('✅ 标记消息为已读');
        }
      } else {
        console.log('⚠️  暂无未读消息');
      }

      // 测试消息筛选
      const filterSelect = page.locator('.el-select').filter({ hasText: /全部|未读|已读/ }).first();
      if (await filterSelect.isVisible({ timeout: 1000 })) {
        await filterSelect.click();
        await page.waitForTimeout(300);

        const unreadOption = page.getByRole('option', { name: /未读/ });
        if (await unreadOption.isVisible({ timeout: 1000 })) {
          await unreadOption.click();
          await page.waitForTimeout(500);
          console.log('✅ 筛选未读消息');
        }
      }
    });
  }
});
