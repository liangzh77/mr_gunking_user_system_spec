import { test, expect, Page } from '@playwright/test'

/**
 * 运营商端到端测试套件
 *
 * 测试运营商登录、注册、充值、运营点管理、应用授权、使用记录等核心功能
 */

// 测试使用的运营商凭证（根据实际情况修改）
const OPERATOR_CREDENTIALS = {
  username: 'testoperator',
  password: 'Operator123',
}

/**
 * 辅助函数：运营商登录
 */
async function operatorLogin(page: Page) {
  await page.goto('/operator/login')
  await page.fill('input[placeholder="请输入用户名"], input[type="text"]', OPERATOR_CREDENTIALS.username)
  await page.fill('input[placeholder="请输入密码"], input[type="password"]', OPERATOR_CREDENTIALS.password)
  await page.click('button:has-text("登录"), button[type="submit"]')

  // 等待登录成功，跳转到Dashboard
  await page.waitForURL(/\/operator\/dashboard/, { timeout: 5000 })
}

test.describe('运营商功能测试', () => {

  test.beforeEach(async ({ page }) => {
    // 每个测试前都执行登录
    await operatorLogin(page)
  })

  test('1. 运营商登录测试', async ({ page }) => {
    // 验证已经成功登录并跳转到Dashboard
    expect(page.url()).toContain('/operator/dashboard')

    // 验证页面包含运营商相关内容
    await expect(page.locator('text=账户余额')).toBeVisible()
  })

  test('2. Dashboard 页面加载测试', async ({ page }) => {
    // 验证 Dashboard 页面关键元素
    await expect(page.locator('text=账户余额')).toBeVisible()
    await expect(page.locator('text=今日消费')).toBeVisible()
    await expect(page.locator('text=本月消费')).toBeVisible()

    // 验证侧边栏菜单存在
    await expect(page.locator('text=个人信息')).toBeVisible()
    await expect(page.locator('text=充值')).toBeVisible()
    await expect(page.locator('text=交易记录')).toBeVisible()
    await expect(page.locator('text=运营点管理')).toBeVisible()

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/operator-dashboard.png', fullPage: true })
  })

  test('3. 个人信息页面测试', async ({ page }) => {
    // 点击侧边栏的"个人信息"
    await page.click('text=个人信息')

    // 等待导航到个人信息页面
    await page.waitForURL(/\/operator\/profile/, { timeout: 5000 })

    // 验证页面包含个人信息表单
    await expect(page.locator('text=用户名')).toBeVisible()
    await expect(page.locator('text=联系电话')).toBeVisible()
    await expect(page.locator('text=电子邮箱')).toBeVisible()

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/operator-profile.png', fullPage: true })
  })

  test('4. 充值页面测试', async ({ page }) => {
    // 点击侧边栏的"充值"
    await page.click('text=充值')

    // 等待导航到充值页面
    await page.waitForURL(/\/operator\/recharge/, { timeout: 5000 })

    // 验证页面包含充值相关元素
    await expect(page.locator('text=充值金额')).toBeVisible()
    await expect(page.locator('text=支付方式')).toBeVisible()

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/operator-recharge.png', fullPage: true })
  })

  test('5. 交易记录页面测试', async ({ page }) => {
    // 点击侧边栏的"交易记录"
    await page.click('text=交易记录')

    // 等待导航到交易记录页面
    await page.waitForURL(/\/operator\/transactions/, { timeout: 5000 })

    // 验证页面标题
    await expect(page.locator('text=交易记录').first()).toBeVisible()

    // 验证表格存在
    const table = page.locator('.el-table')
    await expect(table).toBeVisible()

    // 如果有数据，验证表格列
    const hasData = await page.locator('.el-table__row').count() > 0
    if (hasData) {
      await expect(page.locator('text=交易类型')).toBeVisible()
      await expect(page.locator('text=金额')).toBeVisible()
      await expect(page.locator('text=交易时间')).toBeVisible()
    }

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/operator-transactions.png', fullPage: true })
  })

  test('6. 退款页面测试', async ({ page }) => {
    // 点击侧边栏的"退款"
    await page.click('text=退款')

    // 等待导航到退款页面
    await page.waitForURL(/\/operator\/refunds/, { timeout: 5000 })

    // 验证页面标题
    await expect(page.locator('text=退款管理').first()).toBeVisible()

    // 验证表格存在
    const table = page.locator('.el-table')
    await expect(table).toBeVisible()

    // 验证"申请退款"按钮存在
    await expect(page.locator('button:has-text("申请退款")')).toBeVisible()

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/operator-refunds.png', fullPage: true })
  })

  test('7. 发票页面测试', async ({ page }) => {
    // 点击侧边栏的"发票"
    await page.click('text=发票')

    // 等待导航到发票页面
    await page.waitForURL(/\/operator\/invoices/, { timeout: 5000 })

    // 验证页面标题
    await expect(page.locator('text=发票管理').first()).toBeVisible()

    // 验证表格存在
    const table = page.locator('.el-table')
    await expect(table).toBeVisible()

    // 验证"申请开票"按钮存在
    await expect(page.locator('button:has-text("申请开票")')).toBeVisible()

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/operator-invoices.png', fullPage: true })
  })

  test('8. 运营点管理页面测试', async ({ page }) => {
    // 点击侧边栏的"运营点管理"
    await page.click('text=运营点管理')

    // 等待导航到运营点管理页面
    await page.waitForURL(/\/operator\/sites/, { timeout: 5000 })

    // 验证页面标题
    await expect(page.locator('text=运营点管理').first()).toBeVisible()

    // 验证表格存在
    const table = page.locator('.el-table')
    await expect(table).toBeVisible()

    // 验证"创建运营点"按钮存在
    await expect(page.locator('button:has-text("创建运营点")')).toBeVisible()

    // 如果有数据，验证表格列
    const hasData = await page.locator('.el-table__row').count() > 0
    if (hasData) {
      await expect(page.locator('text=运营点代码')).toBeVisible()
      await expect(page.locator('text=运营点名称')).toBeVisible()
      await expect(page.locator('text=状态')).toBeVisible()
    }

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/operator-sites.png', fullPage: true })
  })

  test('9. 应用授权页面测试', async ({ page }) => {
    // 点击侧边栏的"应用授权"
    await page.click('text=应用授权')

    // 等待导航到应用授权页面
    await page.waitForURL(/\/operator\/applications/, { timeout: 5000 })

    // 验证页面标题
    await expect(page.locator('text=应用授权管理').first()).toBeVisible()

    // 验证表格存在
    const table = page.locator('.el-table')
    await expect(table).toBeVisible()

    // 验证"申请授权"按钮存在
    await expect(page.locator('button:has-text("申请授权")')).toBeVisible()

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/operator-applications.png', fullPage: true })
  })

  test('10. 使用记录页面测试', async ({ page }) => {
    // 点击侧边栏的"使用记录"
    await page.click('text=使用记录')

    // 等待导航到使用记录页面
    await page.waitForURL(/\/operator\/usage-records/, { timeout: 5000 })

    // 验证页面标题
    await expect(page.locator('text=使用记录').first()).toBeVisible()

    // 验证表格存在
    const table = page.locator('.el-table')
    await expect(table).toBeVisible()

    // 如果有数据，验证表格列
    const hasData = await page.locator('.el-table__row').count() > 0
    if (hasData) {
      await expect(page.locator('text=应用代码')).toBeVisible()
      await expect(page.locator('text=运营点')).toBeVisible()
      await expect(page.locator('text=调用次数')).toBeVisible()
    }

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/operator-usage-records.png', fullPage: true })
  })

  test('11. 统计分析页面测试', async ({ page }) => {
    // 点击侧边栏的"统计分析"
    await page.click('text=统计分析')

    // 等待导航到统计分析页面
    await page.waitForURL(/\/operator\/statistics/, { timeout: 5000 })

    // 验证页面标题
    await expect(page.locator('text=统计分析').first()).toBeVisible()

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/operator-statistics.png', fullPage: true })
  })

  test('12. 侧边栏导航测试', async ({ page }) => {
    // 测试所有主要菜单项都可以点击
    const menuItems = [
      { name: '账户概览', url: '/operator/dashboard' },
      { name: '个人信息', url: '/operator/profile' },
      { name: '充值', url: '/operator/recharge' },
      { name: '交易记录', url: '/operator/transactions' },
      { name: '退款', url: '/operator/refunds' },
      { name: '发票', url: '/operator/invoices' },
      { name: '运营点管理', url: '/operator/sites' },
      { name: '应用授权', url: '/operator/applications' },
      { name: '使用记录', url: '/operator/usage-records' },
      { name: '统计分析', url: '/operator/statistics' },
    ]

    for (const item of menuItems) {
      // 点击菜单项
      await page.click(`text=${item.name}`)

      // 验证URL变化
      await page.waitForURL(new RegExp(item.url), { timeout: 3000 })
      expect(page.url()).toContain(item.url)

      // 等待一下再测试下一个
      await page.waitForTimeout(300)
    }
  })

  test('13. 交易记录筛选测试', async ({ page }) => {
    // 导航到交易记录页面
    await page.click('text=交易记录')
    await page.waitForURL(/\/operator\/transactions/)

    // 等待页面加载
    await page.waitForTimeout(1000)

    // 检查类型筛选下拉框
    const typeSelect = page.locator('.el-select').first()
    const selectExists = await typeSelect.count() > 0

    if (selectExists) {
      await typeSelect.click()
      await page.waitForTimeout(500)

      // 验证下拉选项存在
      await expect(page.locator('.el-select-dropdown text=充值')).toBeVisible()
      await expect(page.locator('.el-select-dropdown text=消费')).toBeVisible()
    }
  })

  test('14. 退出登录测试', async ({ page }) => {
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
    await page.waitForURL(/\/operator\/login/, { timeout: 5000 })
    expect(page.url()).toContain('/operator/login')
  })
})

test.describe('运营商注册测试', () => {

  test('15. 注册页面加载测试', async ({ page }) => {
    await page.goto('/operator/register')

    // 验证注册页面元素
    await expect(page.locator('text=运营商注册')).toBeVisible()
    await expect(page.locator('input[placeholder*="用户名"]')).toBeVisible()
    await expect(page.locator('input[placeholder*="密码"]')).toBeVisible()
    await expect(page.locator('input[placeholder*="确认密码"]')).toBeVisible()
    await expect(page.locator('input[placeholder*="联系电话"]')).toBeVisible()
    await expect(page.locator('input[placeholder*="电子邮箱"]')).toBeVisible()

    // 验证有"去登录"链接
    await expect(page.locator('text=去登录')).toBeVisible()

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/operator-register.png', fullPage: true })
  })
})
