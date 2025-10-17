import { test, expect, Page } from '@playwright/test'

/**
 * 管理员端到端测试套件
 *
 * 测试管理员登录、运营商列表、应用列表、授权申请等核心功能
 */

// 测试使用的管理员凭证（根据实际情况修改）
const ADMIN_CREDENTIALS = {
  username: 'admin',
  password: 'Admin123',
}

/**
 * 辅助函数：管理员登录
 */
async function adminLogin(page: Page) {
  await page.goto('/admin/login')
  await page.fill('input[placeholder="请输入用户名"], input[type="text"]', ADMIN_CREDENTIALS.username)
  await page.fill('input[placeholder="请输入密码"], input[type="password"]', ADMIN_CREDENTIALS.password)
  await page.click('button:has-text("登录"), button[type="submit"]')

  // 等待登录成功，跳转到Dashboard
  await page.waitForURL(/\/admin\/dashboard/, { timeout: 5000 })
}

test.describe('管理员功能测试', () => {

  test.beforeEach(async ({ page }) => {
    // 每个测试前都执行登录
    await adminLogin(page)
  })

  test('1. 管理员登录测试', async ({ page }) => {
    // 验证已经成功登录并跳转到Dashboard
    expect(page.url()).toContain('/admin/dashboard')

    // 验证页面包含"管理面板"标题
    await expect(page.locator('text=管理面板')).toBeVisible()
  })

  test('2. Dashboard 页面加载测试', async ({ page }) => {
    // 验证 Dashboard 页面元素
    await expect(page.locator('text=管理面板')).toBeVisible()

    // 验证侧边栏菜单存在
    await expect(page.locator('text=运营商管理')).toBeVisible()
    await expect(page.locator('text=应用管理')).toBeVisible()
  })

  test('3. 运营商列表页面测试', async ({ page }) => {
    // 点击侧边栏的"运营商管理"展开菜单
    await page.click('text=运营商管理')

    // 等待菜单展开后点击"运营商列表"
    await page.click('text=运营商列表')

    // 等待导航到运营商列表页面
    await page.waitForURL(/\/admin\/operators/, { timeout: 5000 })

    // 验证页面标题
    await expect(page.locator('text=运营商管理').first()).toBeVisible()

    // 验证搜索框存在
    await expect(page.locator('input[placeholder*="用户名"]')).toBeVisible()

    // 验证状态筛选下拉框存在
    await expect(page.locator('text=状态').first()).toBeVisible()

    // 验证表格存在（可能没有数据，所以只检查表格结构）
    const table = page.locator('.el-table')
    await expect(table).toBeVisible()

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/operators-list.png', fullPage: true })
  })

  test('4. 应用列表页面测试', async ({ page }) => {
    // 点击侧边栏的"应用管理"展开菜单
    await page.click('text=应用管理')

    // 等待菜单展开后点击"应用列表"
    await page.click('text=应用列表')

    // 等待导航到应用列表页面
    await page.waitForURL(/\/admin\/applications/, { timeout: 5000 })

    // 验证页面标题
    await expect(page.locator('text=应用管理').first()).toBeVisible()

    // 验证搜索框存在
    await expect(page.locator('input[placeholder*="应用"]')).toBeVisible()

    // 验证表格存在
    const table = page.locator('.el-table')
    await expect(table).toBeVisible()

    // 如果有数据，验证表格列
    const hasData = await page.locator('.el-table__row').count() > 0
    if (hasData) {
      // 验证表格包含关键列（应用代码、应用名称、单价等）
      await expect(page.locator('text=应用代码')).toBeVisible()
      await expect(page.locator('text=应用名称')).toBeVisible()
      await expect(page.locator('text=单价')).toBeVisible()
    }

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/applications-list.png', fullPage: true })
  })

  test('5. 授权申请页面测试', async ({ page }) => {
    // 点击侧边栏的"应用管理"展开菜单
    await page.click('text=应用管理')

    // 等待菜单展开后点击"授权申请"
    await page.click('text=授权申请')

    // 等待导航到授权申请页面
    await page.waitForURL(/\/admin\/app-requests/, { timeout: 5000 })

    // 验证页面标题
    await expect(page.locator('text=授权申请审核').first()).toBeVisible()

    // 验证状态筛选下拉框存在
    await expect(page.locator('text=状态').first()).toBeVisible()

    // 验证表格存在
    const table = page.locator('.el-table')
    await expect(table).toBeVisible()

    // 如果有数据，验证表格列
    const hasData = await page.locator('.el-table__row').count() > 0
    if (hasData) {
      await expect(page.locator('text=应用名称')).toBeVisible()
      await expect(page.locator('text=申请理由')).toBeVisible()
    }

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/app-requests.png', fullPage: true })
  })

  test('6. 侧边栏导航测试', async ({ page }) => {
    // 测试所有主要菜单项都可以点击
    const menuItems = [
      { parent: '运营商管理', child: '运营商列表', url: '/admin/operators' },
      { parent: '应用管理', child: '应用列表', url: '/admin/applications' },
      { parent: '应用管理', child: '授权申请', url: '/admin/app-requests' },
    ]

    for (const item of menuItems) {
      // 展开父菜单
      await page.click(`text=${item.parent}`)

      // 点击子菜单
      await page.click(`text=${item.child}`)

      // 验证URL变化
      await page.waitForURL(new RegExp(item.url), { timeout: 3000 })
      expect(page.url()).toContain(item.url)

      // 等待一下再测试下一个
      await page.waitForTimeout(500)
    }
  })

  test('7. 搜索功能测试（运营商列表）', async ({ page }) => {
    // 导航到运营商列表
    await page.click('text=运营商管理')
    await page.click('text=运营商列表')
    await page.waitForURL(/\/admin\/operators/)

    // 在搜索框输入测试关键词
    const searchInput = page.locator('input[placeholder*="用户名"]')
    await searchInput.fill('test')

    // 点击搜索（或按回车）
    await searchInput.press('Enter')

    // 等待API请求完成（通过等待loading消失）
    await page.waitForTimeout(1000)

    // 验证搜索框的值
    await expect(searchInput).toHaveValue('test')
  })

  test('8. 分页功能测试', async ({ page }) => {
    // 导航到运营商列表
    await page.click('text=运营商管理')
    await page.click('text=运营商列表')
    await page.waitForURL(/\/admin\/operators/)

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

  test('9. 退出登录测试', async ({ page }) => {
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
    await page.waitForURL(/\/admin\/login/, { timeout: 5000 })
    expect(page.url()).toContain('/admin/login')
  })
})
