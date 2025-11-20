import { DatabaseHelper } from './utils/db-helper';

/**
 * 全局清理函数 - 在所有测试结束后自动执行
 *
 * Playwright会在所有测试完成后自动调用此函数
 */
async function globalTeardown() {
  console.log('\n🧹 ===== 开始清理E2E测试数据 =====\n');

  const db = new DatabaseHelper();

  try {
    await db.cleanupTestData();
    console.log('\n✅ ===== E2E测试数据清理完成 =====\n');
  } catch (error) {
    console.error('\n❌ ===== E2E测试数据清理失败 =====');
    console.error('错误信息:', error);
    // 不抛出错误,避免影响测试结果报告
  } finally {
    await db.close();
  }
}

export default globalTeardown;
