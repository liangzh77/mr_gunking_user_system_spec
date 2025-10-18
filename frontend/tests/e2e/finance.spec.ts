import { test, expect, Page } from '@playwright/test'

/**
 * 财务端到端测试套件
 *
 * 测试财务人员登录、退款审核、发票审核、报表生成等核心功能
 */

// 测试使用的财务凭证（根据实际情况修改）
const FINANCE_CREDENTIALS = {
  username: 'finance',
  password: 'Finance123',
}

/**
 * 辅助函数：财务登录
 */
async function financeLogin(page: Page) {
  await page.goto('/finance/login')
  await page.fill('input[placeholder="请输入用户名"], input[type="text"]', FINANCE_CREDENTIALS.username)
  await page.fill('input[placeholder="请输入密码"], input[type="password"]', FINANCE_CREDENTIALS.password)
  await page.click('button:has-text("登录"), button[type="submit"]')

  // 等待登录成功，跳转到Dashboard
  await page.waitForURL(/\/finance\/dashboard/, { timeout: 5000 })
}

test.describe('财务功能测试', () => {

  test.beforeEach(async ({ page }) => {
    // 每个测试前都执行登录
    await financeLogin(page)
  })

  test('1. 财务登录测试', async ({ page }) => {
    // 验证已经成功登录并跳转到Dashboard
    expect(page.url()).toContain('/finance/dashboard')

    // 验证页面包含财务相关标题
    await expect(page.locator('text=财务管理')).toBeVisible()
  })

  test('2. Dashboard 页面加载测试', async ({ page }) => {
    // 验证 Dashboard 页面关键元素
    await expect(page.locator('text=今日充值')).toBeVisible()
    await expect(page.locator('text=今日消费')).toBeVisible()
    await expect(page.locator('text=今日退款')).toBeVisible()
    await expect(page.locator('text=今日净收入')).toBeVisible()

    // 验证运营商统计
    await expect(page.locator('text=运营商总数')).toBeVisible()
    await expect(page.locator('text=今日活跃运营商')).toBeVisible()

    // 验证Top客户表格
    await expect(page.locator('text=消费Top客户')).toBeVisible()
    const table = page.locator('.el-table')
    await expect(table.first()).toBeVisible()

    // 验证待处理事项
    await expect(page.locator('text=待处理事项')).toBeVisible()
    await expect(page.locator('text=待审核退款')).toBeVisible()
    await expect(page.locator('text=待审核发票')).toBeVisible()

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/finance-dashboard.png', fullPage: true })
  })

  test('3. 退款审核页面测试', async ({ page }) => {
    // 点击侧边栏的"退款审核"
    await page.click('text=退款审核')

    // 等待导航到退款审核页面
    await page.waitForURL(/\/finance\/refunds/, { timeout: 5000 })

    // 验证页面标题
    await expect(page.locator('text=退款审核').first()).toBeVisible()

    // 验证搜索框存在
    await expect(page.locator('input[placeholder*="退款"]')).toBeVisible()

    // 验证状态筛选下拉框存在
    await expect(page.locator('text=状态').first()).toBeVisible()

    // 验证表格存在
    const table = page.locator('.el-table')
    await expect(table).toBeVisible()

    // 如果有数据，验证表格列
    const hasData = await page.locator('.el-table__row').count() > 0
    if (hasData) {
      await expect(page.locator('text=退款ID')).toBeVisible()
      await expect(page.locator('text=运营商')).toBeVisible()
      await expect(page.locator('text=退款金额')).toBeVisible()
      await expect(page.locator('text=退款原因')).toBeVisible()
    }

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/finance-refunds.png', fullPage: true })
  })

  test('4. 发票审核页面测试', async ({ page }) => {
    // 点击侧边栏的"发票审核"
    await page.click('text=发票审核')

    // 等待导航到发票审核页面
    await page.waitForURL(/\/finance\/invoices/, { timeout: 5000 })

    // 验证页面标题
    await expect(page.locator('text=发票审核').first()).toBeVisible()

    // 验证搜索框存在
    await expect(page.locator('input[placeholder*="发票"]')).toBeVisible()

    // 验证状态筛选下拉框存在
    await expect(page.locator('text=状态').first()).toBeVisible()

    // 验证表格存在
    const table = page.locator('.el-table')
    await expect(table).toBeVisible()

    // 如果有数据，验证表格列
    const hasData = await page.locator('.el-table__row').count() > 0
    if (hasData) {
      await expect(page.locator('text=发票ID')).toBeVisible()
      await expect(page.locator('text=运营商')).toBeVisible()
      await expect(page.locator('text=发票类型')).toBeVisible()
      await expect(page.locator('text=开票金额')).toBeVisible()
    }

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/finance-invoices.png', fullPage: true })
  })

  test('5. 报表生成页面测试', async ({ page }) => {
    // 点击侧边栏的"财务报表"
    await page.click('text=财务报表')

    // 等待导航到财务报表页面
    await page.waitForURL(/\/finance\/reports/, { timeout: 5000 })

    // 验证报表生成表单存在
    await expect(page.locator('text=生成财务报表')).toBeVisible()
    await expect(page.locator('text=报表类型')).toBeVisible()
    await expect(page.locator('text=导出格式')).toBeVisible()

    // 验证快速报表按钮
    await expect(page.locator('text=今日财务报表')).toBeVisible()
    await expect(page.locator('text=本周财务报表')).toBeVisible()
    await expect(page.locator('text=本月财务报表')).toBeVisible()
    await expect(page.locator('text=上月财务报表')).toBeVisible()

    // 验证历史报表表格
    await expect(page.locator('text=历史报表')).toBeVisible()
    const table = page.locator('.el-table')
    await expect(table).toBeVisible()

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/finance-reports.png', fullPage: true })
  })

  test('6. 侧边栏导航测试', async ({ page }) => {
    // 测试所有主要菜单项都可以点击
    const menuItems = [
      { name: '财务概览', url: '/finance/dashboard' },
      { name: '退款审核', url: '/finance/refunds' },
      { name: '发票审核', url: '/finance/invoices' },
      { name: '财务报表', url: '/finance/reports' },
    ]

    for (const item of menuItems) {
      // 点击菜单项
      await page.click(`text=${item.name}`)

      // 验证URL变化
      await page.waitForURL(new RegExp(item.url), { timeout: 3000 })
      expect(page.url()).toContain(item.url)

      // 等待一下再测试下一个
      await page.waitForTimeout(500)
    }
  })

  test('7. 退款搜索功能测试', async ({ page }) => {
    // 导航到退款审核页面
    await page.click('text=退款审核')
    await page.waitForURL(/\/finance\/refunds/)

    // 在搜索框输入测试关键词
    const searchInput = page.locator('input[placeholder*="退款"]')
    await searchInput.fill('test')

    // 点击搜索（或按回车）
    await searchInput.press('Enter')

    // 等待API请求完成
    await page.waitForTimeout(1000)

    // 验证搜索框的值
    await expect(searchInput).toHaveValue('test')
  })

  test('8. 发票状态筛选测试', async ({ page }) => {
    // 导航到发票审核页面
    await page.click('text=发票审核')
    await page.waitForURL(/\/finance\/invoices/)

    // 等待页面加载
    await page.waitForTimeout(1000)

    // 点击状态筛选下拉框
    const statusSelect = page.locator('.el-select').first()
    await statusSelect.click()

    // 等待下拉选项出现
    await page.waitForTimeout(500)

    // 验证下拉选项存在
    await expect(page.locator('.el-select-dropdown text=待审核')).toBeVisible()
    await expect(page.locator('.el-select-dropdown text=已批准')).toBeVisible()
    await expect(page.locator('.el-select-dropdown text=已拒绝')).toBeVisible()
  })

  test('9. 分页功能测试', async ({ page }) => {
    // 导航到退款审核页面
    await page.click('text=退款审核')
    await page.waitForURL(/\/finance\/refunds/)

    // 等待页面加载
    await page.waitForTimeout(1000)

    // 检查分页组件是否存在
    const pagination = page.locator('.el-pagination')
    const paginationExists = await pagination.count() > 0

    if (paginationExists) {
      await expect(pagination).toBeVisible()

      // 如果有多页，测试翻页
      const nextButton = page.locator('.el-pagination button.btn-next')
      const isDisabled = await nextButton.getAttribute('disabled')

      if (!isDisabled) {
        // 点击下一页
        await nextButton.click()
        await page.waitForTimeout(1000)
      }
    }
  })

  test('10. 退出登录测试', async ({ page }) => {
    // 点击右上角用户头像或下拉菜单
    await page.click('.user-dropdown, .el-dropdown')

    // 等待下拉菜单展开
    await page.waitForTimeout(500)

    // 点击退出登录
    await page.click('text=退出登录')

    // 等待确认对话框
    await page.waitForTimeout(500)

    // 点击确认按钮
    await page.click('.el-message-box button:has-text("确定")')

    // 验证已跳转回登录页
    await page.waitForURL(/\/finance\/login/, { timeout: 5000 })
    expect(page.url()).toContain('/finance/login')
  })
})
