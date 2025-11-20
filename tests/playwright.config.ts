import { defineConfig, devices } from '@playwright/test';
import { getEnvironment } from './e2e/config/environments';

const env = getEnvironment();

export default defineConfig({
  testDir: './e2e/specs',
  fullyParallel: false, // 串行执行避免数据竞争
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // 单线程执行

  // 全局清理 - 所有测试结束后自动清理测试数据
  globalTeardown: './e2e/global-teardown.ts',

  timeout: 60 * 1000, // 60秒超时
  expect: {
    timeout: 10 * 1000, // 10秒断言超时
  },

  reporter: [
    ['html', {
      outputFolder: `playwright-report`,
      open: 'never'
    }],
    ['json', { outputFile: `test-results/results.json` }],
    ['junit', { outputFile: `test-results/junit.xml` }],
    ['list'],
    // CI 环境添加 GitHub Actions reporter
    ...(process.env.CI ? [['github']] : [])
  ],

  use: {
    baseURL: env.baseURL,
    trace: 'retain-on-failure', // 失败时保留完整trace
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ignoreHTTPSErrors: env.ignoreHTTPSErrors,

    // 设置默认导航超时
    navigationTimeout: 30 * 1000,
    actionTimeout: 15 * 1000,

    // 添加更详细的上下文信息
    contextOptions: {
      recordVideo: {
        dir: 'test-results/videos',
        size: { width: 1920, height: 1080 }
      }
    }
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
      },
    },
  ],

  // 本地环境启动服务
  webServer: env.name === 'localhost' ? {
    command: 'cd .. && docker-compose up',
    url: env.baseURL,
    reuseExistingServer: true,
    ignoreHTTPSErrors: true,
    timeout: 120 * 1000, // 2分钟启动时间
  } : undefined,
});
