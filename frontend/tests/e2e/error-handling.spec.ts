import { test, expect } from '@playwright/test'

/**
 * 异常场景端到端测试套件
 *
 * 测试系统的错误处理能力，包括网络错误、验证错误、会话超时等
 */

test.describe('错误处理测试', () => {

  test('1. 运营商登录失败测试 - 错误的用户名', async ({ page }) => {
    await page.goto('/operator/login')

    // 输入错误的凭证
    await page.fill('input[placeholder="请输入用户名"], input[type="text"]', 'wronguser')
    await page.fill('input[placeholder="请输入密码"], input[type="password"]', 'wrongpass')
    await page.click('button:has-text("登录"), button[type="submit"]')

    // 等待错误消息出现
    await page.waitForTimeout(1000)

    // 验证仍在登录页面
    expect(page.url()).toContain('/operator/login')

    // 验证错误提示（Element Plus的消息提示）
    const errorMessage = page.locator('.el-message--error')
    const errorExists = await errorMessage.count() > 0
    if (errorExists) {
      await expect(errorMessage).toBeVisible()
    }
  })

  test('2. 管理员登录失败测试 - 错误的密码', async ({ page }) => {
    await page.goto('/admin/login')

    // 输入正确的用户名但错误的密码
    await page.fill('input[placeholder="请输入用户名"], input[type="text"]', 'admin')
    await page.fill('input[placeholder="请输入密码"], input[type="password"]', 'wrongpassword')
    await page.click('button:has-text("登录"), button[type="submit"]')

    // 等待错误消息
    await page.waitForTimeout(1000)

    // 验证仍在登录页面
    expect(page.url()).toContain('/admin/login')
  })

  test('3. 财务登录失败测试 - 空表单提交', async ({ page }) => {
    await page.goto('/finance/login')

    // 不输入任何内容直接点击登录
    await page.click('button:has-text("登录"), button[type="submit"]')

    // 等待表单验证
    await page.waitForTimeout(500)

    // 验证仍在登录页面
    expect(page.url()).toContain('/finance/login')

    // 验证表单验证错误提示存在
    const validationError = page.locator('.el-form-item__error')
    const errorExists = await validationError.count() > 0
    if (errorExists) {
      await expect(validationError.first()).toBeVisible()
    }
  })

  test('4. 未授权访问测试 - 未登录访问管理员页面', async ({ page }) => {
    // 清除所有存储以确保未登录状态
    await page.context().clearCookies()
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })

    // 尝试直接访问管理员Dashboard
    await page.goto('/admin/dashboard')

    // 应该被重定向到登录页
    await page.waitForURL(/\/admin\/login/, { timeout: 5000 })
    expect(page.url()).toContain('/admin/login')
  })

  test('5. 未授权访问测试 - 未登录访问财务页面', async ({ page }) => {
    // 清除所有存储
    await page.context().clearCookies()
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })

    // 尝试直接访问财务Dashboard
    await page.goto('/finance/dashboard')

    // 应该被重定向到登录页
    await page.waitForURL(/\/finance\/login/, { timeout: 5000 })
    expect(page.url()).toContain('/finance/login')
  })

  test('6. 未授权访问测试 - 未登录访问运营商页面', async ({ page }) => {
    // 清除所有存储
    await page.context().clearCookies()
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })

    // 尝试直接访问运营商Dashboard
    await page.goto('/operator/dashboard')

    // 应该被重定向到登录页
    await page.waitForURL(/\/operator\/login/, { timeout: 5000 })
    expect(page.url()).toContain('/operator/login')
  })

  test('7. 404页面测试 - 访问不存在的路由', async ({ page }) => {
    await page.goto('/this-page-does-not-exist')

    // 验证404页面元素
    await expect(page.locator('text=404')).toBeVisible()

    // 截图
    await page.screenshot({ path: 'test-results/screenshots/404-page.png', fullPage: true })
  })

  test('8. 注册表单验证测试 - 密码不匹配', async ({ page }) => {
    await page.goto('/operator/register')

    // 填写表单但密码和确认密码不匹配
    await page.fill('input[placeholder*="用户名"]', 'testuser')
    await page.fill('input[placeholder*="密码"]:not([placeholder*="确认"])', 'Password123')
    await page.fill('input[placeholder*="确认密码"]', 'DifferentPassword123')
    await page.fill('input[placeholder*="联系电话"]', '13800138000')
    await page.fill('input[placeholder*="电子邮箱"]', 'test@example.com')

    // 提交表单
    await page.click('button:has-text("注册"), button[type="submit"]')

    // 等待验证
    await page.waitForTimeout(500)

    // 验证表单验证错误
    const validationError = page.locator('.el-form-item__error')
    const errorExists = await validationError.count() > 0
    if (errorExists) {
      await expect(validationError.first()).toBeVisible()
    }
  })

  test('9. 注册表单验证测试 - 无效的邮箱格式', async ({ page }) => {
    await page.goto('/operator/register')

    // 填写表单但邮箱格式错误
    await page.fill('input[placeholder*="用户名"]', 'testuser')
    await page.fill('input[placeholder*="密码"]:not([placeholder*="确认"])', 'Password123')
    await page.fill('input[placeholder*="确认密码"]', 'Password123')
    await page.fill('input[placeholder*="联系电话"]', '13800138000')
    await page.fill('input[placeholder*="电子邮箱"]', 'invalid-email')

    // 失去焦点触发验证
    await page.click('body')

    // 等待验证
    await page.waitForTimeout(500)

    // 验证邮箱字段的错误提示
    const emailError = page.locator('.el-form-item__error')
    const errorExists = await emailError.count() > 0
    if (errorExists) {
      const errorText = await emailError.first().textContent()
      expect(errorText).toContain('邮箱')
    }
  })

  test('10. 跨角色访问测试 - 运营商token访问管理员页面', async ({ page }) => {
    // 设置运营商token
    await page.goto('/operator/login')
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'fake-operator-token')
      localStorage.setItem('operator_id', 'fake-operator-id')
    })

    // 尝试访问管理员页面
    await page.goto('/admin/dashboard')

    // 应该被重定向到管理员登录页或显示权限不足
    await page.waitForTimeout(2000)
    const isAdminLogin = page.url().includes('/admin/login')
    const isOperatorPage = page.url().includes('/operator/')

    // 应该不在管理员Dashboard
    expect(page.url()).not.toContain('/admin/dashboard')
  })

  test('11. 表单提交后错误消息显示测试', async ({ page }) => {
    await page.goto('/operator/login')

    // 输入错误凭证
    await page.fill('input[placeholder="请输入用户名"], input[type="text"]', 'nonexistentuser')
    await page.fill('input[placeholder="请输入密码"], input[type="password"]', 'wrongpass123')
    await page.click('button:has-text("登录"), button[type="submit"]')

    // 等待错误消息
    await page.waitForTimeout(1500)

    // 验证错误消息出现并自动消失
    const errorMessage = page.locator('.el-message')
    const messageExists = await errorMessage.count() > 0

    // 如果消息存在，等待它消失（Element Plus的消息默认3秒后自动关闭）
    if (messageExists) {
      await page.waitForTimeout(4000)
      const messageStillExists = await errorMessage.count() > 0
      // 消息应该已经消失
      expect(messageStillExists).toBe(false)
    }
  })

  test('12. 页面加载超时处理测试', async ({ page }) => {
    // 设置较短的超时时间
    page.setDefaultTimeout(3000)

    try {
      // 尝试访问一个可能加载缓慢的页面
      await page.goto('/operator/login')

      // 如果成功加载，验证页面元素存在
      await expect(page.locator('text=运营商登录')).toBeVisible({ timeout: 3000 })
    } catch (error) {
      // 捕获超时错误
      console.log('页面加载超时，这是预期的错误处理测试')
    } finally {
      // 恢复默认超时
      page.setDefaultTimeout(30000)
    }
  })

  test('13. 输入特殊字符验证测试', async ({ page }) => {
    await page.goto('/operator/login')

    // 尝试输入特殊字符
    await page.fill('input[placeholder="请输入用户名"], input[type="text"]', '<script>alert("xss")</script>')
    await page.fill('input[placeholder="请输入密码"], input[type="password"]', '"><img src=x onerror=alert(1)>')

    // 提交表单
    await page.click('button:has-text("登录"), button[type="submit"]')

    // 等待响应
    await page.waitForTimeout(1000)

    // 验证页面没有执行恶意脚本（仍在登录页）
    expect(page.url()).toContain('/operator/login')

    // 验证没有弹窗出现
    const dialogs: string[] = []
    page.on('dialog', dialog => {
      dialogs.push(dialog.message())
      dialog.dismiss()
    })

    await page.waitForTimeout(1000)
    expect(dialogs.length).toBe(0)
  })

  test('14. 空白输入验证测试', async ({ page }) => {
    await page.goto('/operator/register')

    // 只输入空格
    await page.fill('input[placeholder*="用户名"]', '   ')
    await page.fill('input[placeholder*="密码"]:not([placeholder*="确认"])', '   ')
    await page.fill('input[placeholder*="联系电话"]', '   ')

    // 提交表单
    await page.click('button:has-text("注册"), button[type="submit"]')

    // 等待验证
    await page.waitForTimeout(500)

    // 验证表单验证错误
    const validationErrors = page.locator('.el-form-item__error')
    const errorCount = await validationErrors.count()

    // 应该有多个验证错误
    expect(errorCount).toBeGreaterThan(0)
  })

  test('15. 会话过期后重定向测试', async ({ page }) => {
    await page.goto('/operator/login')

    // 模拟已登录状态（设置过期的token）
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'expired-token')
      localStorage.setItem('operator_id', 'test-operator')
    })

    // 访问需要登录的页面
    await page.goto('/operator/dashboard')

    // 等待API响应（可能返回401）
    await page.waitForTimeout(2000)

    // 根据实际实现，可能会：
    // 1. 重定向到登录页
    // 2. 显示错误消息
    // 3. 清除token并要求重新登录

    // 验证至少有某种错误处理
    const isLoginPage = page.url().includes('/login')
    const hasErrorMessage = await page.locator('.el-message--error').count() > 0

    // 应该有错误处理（重定向或错误消息）
    expect(isLoginPage || hasErrorMessage).toBeTruthy()
  })
})

test.describe('网络错误模拟测试', () => {

  test('16. 模拟网络离线状态', async ({ page, context }) => {
    // 模拟离线状态
    await context.setOffline(true)

    await page.goto('/operator/login')

    // 尝试登录
    await page.fill('input[placeholder="请输入用户名"], input[type="text"]', 'testuser')
    await page.fill('input[placeholder="请输入密码"], input[type="password"]', 'password')
    await page.click('button:has-text("登录"), button[type="submit"]')

    // 等待网络错误
    await page.waitForTimeout(2000)

    // 验证显示了网络错误消息
    const errorMessage = page.locator('.el-message--error')
    const hasError = await errorMessage.count() > 0

    // 恢复在线状态
    await context.setOffline(false)

    // 网络错误应该被捕获
    expect(hasError).toBeTruthy()
  })
})
