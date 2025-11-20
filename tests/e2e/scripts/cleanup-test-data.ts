import { DatabaseHelper } from '../utils/db-helper';

/**
 * 清理所有E2E测试数据的独立脚本
 *
 * 使用方法:
 *   npx tsx tests/e2e/scripts/cleanup-test-data.ts
 */
async function main() {
  console.log('🧹 开始清理E2E测试数据...\n');

  const db = new DatabaseHelper();

  try {
    // 执行清理
    await db.cleanupTestData();

    console.log('\n✅ 清理完成!');
    console.log('\n清理的数据包括:');
    console.log('  - 所有 e2e_ 开头的运营商账户');
    console.log('  - 所有名称包含 "E2E测试" 的运营商');
    console.log('  - 所有相关的交易记录、退款记录、发票记录');
    console.log('  - 所有相关的站点、应用、充值订单');

  } catch (error) {
    console.error('❌ 清理失败:', error);
    process.exit(1);
  } finally {
    await db.close();
  }
}

main();
