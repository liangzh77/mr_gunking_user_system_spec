import { Page } from '@playwright/test';
import { getEnvironment } from '../config/environments';

const env = getEnvironment();

/**
 * 管理员登录
 */
export async function loginAsAdmin(page: Page) {
  console.log(`🔐 Logging in as Admin on ${env.name}`);

  await page.goto('/admin/login');

  // 填写登录表单
  await page.getByPlaceholder('请输入管理员用户名').fill(env.credentials.admin.username);
  await page.getByPlaceholder('请输入密码').fill(env.credentials.admin.password);

  // 填写验证码
  if (env.name === 'localhost') {
    // 本地环境验证码固定为 0000
    await page.getByPlaceholder('请输入验证码').fill('0000');
  } else {
    // 生产环境需要等待验证码加载并手动处理
    await page.waitForTimeout(2000);
  }

  // 点击登录按钮
  await page.getByRole('button', { name: '登录' }).click();

  // 等待跳转到仪表盘
  await page.waitForURL('**/admin/dashboard', {
    timeout: 15000,
    waitUntil: 'networkidle'
  });

  console.log('✅ Admin logged in successfully');
}

/**
 * 财务人员登录
 */
export async function loginAsFinance(page: Page) {
  console.log(`🔐 Logging in as Finance on ${env.name}`);

  await page.goto('/finance/login');

  await page.getByPlaceholder('请输入用户名').fill(env.credentials.finance.username);
  await page.getByPlaceholder('请输入密码').fill(env.credentials.finance.password);

  // 填写验证码
  if (env.name === 'localhost') {
    // 本地环境验证码固定为 0000
    await page.getByPlaceholder('请输入验证码').fill('0000');
  } else {
    // 生产环境需要等待验证码加载并手动处理
    await page.waitForTimeout(2000);
  }

  await page.getByRole('button', { name: '登录' }).click();

  await page.waitForURL('**/finance/dashboard', {
    timeout: 15000,
    waitUntil: 'networkidle'
  });

  console.log('✅ Finance logged in successfully');
}

/**
 * 运营商登录
 */
export async function loginAsOperator(page: Page) {
  console.log(`🔐 Logging in as Operator on ${env.name}`);

  await page.goto('/operator/login');

  await page.getByPlaceholder('请输入用户名').fill(env.credentials.operator.username);
  await page.getByPlaceholder('请输入密码').fill(env.credentials.operator.password);

  // 填写验证码
  if (env.name === 'localhost') {
    // 本地环境验证码固定为 0000
    await page.getByPlaceholder('请输入验证码').fill('0000');
  } else {
    // 生产环境需要等待验证码加载并手动处理
    await page.waitForTimeout(2000);
  }

  await page.getByRole('button', { name: '登录' }).click();

  await page.waitForURL('**/operator/dashboard', {
    timeout: 15000,
    waitUntil: 'networkidle'
  });

  console.log('✅ Operator logged in successfully');
}

/**
 * 登出
 */
export async function logout(page: Page) {
  console.log('🚪 Logging out...');

  // 点击用户头像或登出按钮
  try {
    // 尝试查找登出按钮
    const logoutButton = page.getByRole('button', { name: /登出|退出/ });
    if (await logoutButton.isVisible({ timeout: 2000 })) {
      await logoutButton.click();
    }
  } catch (error) {
    console.log('⚠️  Logout button not found, clearing cookies instead');
  }

  // 清除所有cookie和localStorage
  await page.context().clearCookies();
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  console.log('✅ Logged out successfully');
}
