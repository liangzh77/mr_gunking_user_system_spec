import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright 端到端测试配置
 *
 * 用于自动化测试前端页面功能
 */
export default defineConfig({
  // 测试目录
  testDir: './tests/e2e',

  // 测试执行超时时间（30秒）
  timeout: 30000,

  // 失败时自动重试1次
  retries: 1,

  // 并行执行的worker数量
  workers: 1,

  // 测试报告配置
  reporter: [
    ['list'],  // 控制台列表输出
    ['html', { outputFolder: 'playwright-report', open: 'never' }],  // HTML报告
    ['json', { outputFile: 'test-results/results.json' }],  // JSON报告
  ],

  use: {
    // 基础 URL
    baseURL: 'http://localhost:5173',

    // 失败时截图
    screenshot: 'only-on-failure',

    // 失败时录制视频
    video: 'retain-on-failure',

    // 失败时保存trace
    trace: 'retain-on-failure',

    // 浏览器上下文配置
    viewport: { width: 1280, height: 720 },

    // 忽略HTTPS错误
    ignoreHTTPSErrors: true,
  },

  // 测试项目配置
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // 开发服务器配置
  // Playwright会自动启动和停止前端开发服务器
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
})
