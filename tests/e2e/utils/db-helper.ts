import { Pool, QueryResult } from 'pg';
import { randomUUID } from 'crypto';
import { getEnvironment } from '../config/environments';

const env = getEnvironment();

/**
 * 数据库辅助类 - 用于测试数据的准备和清理
 */
export class DatabaseHelper {
  private pool: Pool | null = null;
  private testDataIds: { [key: string]: string[] } = {};

  constructor() {
    // 只在本地环境或有数据库配置时初始化
    if (env.database) {
      this.pool = new Pool({
        host: env.database.host,
        port: env.database.port,
        database: env.database.database,
        user: env.database.user,
        password: env.database.password,
      });

      console.log(`🗄️  Database helper initialized for ${env.name}`);
    } else {
      console.warn(`⚠️  Database helper disabled for ${env.name} environment`);
    }
  }

  /**
   * 执行SQL查询
   */
  async query<T = any>(sql: string, params?: any[]): Promise<QueryResult<T>> {
    if (!this.pool) {
      throw new Error('Database not configured for this environment');
    }
    return await this.pool.query<T>(sql, params);
  }

  /**
   * 创建测试运营商账户
   */
  async createTestOperator(username?: string): Promise<string> {
    if (!this.pool) {
      console.warn('Skipping createTestOperator - no database connection');
      return '';
    }

    // 生成唯一的用户名(始终添加时间戳确保唯一性)
    const timestamp = Date.now();
    const baseUsername = username || 'e2e_test_operator';
    const uniqueUsername = `${baseUsername}_${timestamp}`;

    console.log(`📝 Creating test operator: ${uniqueUsername}`);

    // 生成UUID、密码哈希和API密钥
    const operatorId = randomUUID();
    const passwordHash = '$2b$12$test_hash_placeholder_for_e2e_testing_only';
    const apiKey = `e2e_test_key_${timestamp}`;
    const apiKeyHash = '$2b$12$test_api_key_hash_placeholder_for_e2e';

    await this.query<{ id: string }>(`
      INSERT INTO operator_accounts (
        id, username, full_name, phone, email, password_hash,
        api_key, api_key_hash, balance, customer_tier, is_active, is_locked
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
      RETURNING id
    `, [
      operatorId,
      uniqueUsername,
      'E2E测试运营商',
      `138${timestamp.toString().slice(-8)}`, // 生成唯一手机号
      `e2e_test_${timestamp}@example.com`,    // 生成唯一邮箱
      passwordHash,
      apiKey,
      apiKeyHash,
      1000.00,
      'standard',
      true,
      false
    ]);

    this.trackTestData('operators', operatorId);

    console.log(`✅ Test operator created: ${operatorId}`);
    return operatorId;
  }

  /**
   * 创建测试交易记录
   */
  async createTestTransaction(
    operatorId: string,
    type: 'recharge' | 'consumption' | 'refund' | 'deduct',
    amount: number
  ): Promise<string> {
    if (!this.pool) {
      console.warn('Skipping createTestTransaction - no database connection');
      return '';
    }

    console.log(`📝 Creating test transaction: ${type} - ¥${amount}`);

    // 生成交易记录UUID
    const transactionId = randomUUID();

    // 获取当前余额
    const balanceResult = await this.query<{ balance: string }>(`
      SELECT balance FROM operator_accounts WHERE id = $1
    `, [operatorId]);

    const balanceBefore = parseFloat(balanceResult.rows[0].balance);
    let balanceAfter: number;

    if (type === 'recharge' || type === 'refund') {
      balanceAfter = balanceBefore + amount;
    } else {
      balanceAfter = balanceBefore - amount;
    }

    await this.query<{ id: string }>(`
      INSERT INTO transaction_records (
        id, operator_id, transaction_type, amount,
        balance_before, balance_after, description
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7)
      RETURNING id
    `, [
      transactionId,
      operatorId,
      type,
      amount,
      balanceBefore,
      balanceAfter,
      `E2E测试${type}`
    ]);

    // 更新运营商余额
    await this.query(`
      UPDATE operator_accounts
      SET balance = $1
      WHERE id = $2
    `, [balanceAfter, operatorId]);

    this.trackTestData('transactions', transactionId);

    console.log(`✅ Test transaction created: ${transactionId}`);
    return transactionId;
  }

  /**
   * 跟踪测试数据ID,便于清理
   */
  private trackTestData(type: string, id: string) {
    if (!this.testDataIds[type]) {
      this.testDataIds[type] = [];
    }
    this.testDataIds[type].push(id);
  }

  /**
   * 清理所有测试数据
   */
  async cleanupTestData() {
    if (!this.pool) {
      console.warn('Skipping cleanup - no database connection');
      return;
    }

    console.log('🧹 Cleaning up test data...');

    try {
      // 删除所有E2E测试相关的发票记录
      await this.query(`
        DELETE FROM invoice_records
        WHERE invoice_title LIKE '%E2E%' OR invoice_title LIKE '%自动化测试%'
      `);

      // 删除所有E2E测试相关的退款记录
      await this.query(`
        DELETE FROM refund_records
        WHERE refund_reason LIKE '%E2E%' OR refund_reason LIKE '%自动化测试%'
      `);

      // 删除所有E2E测试相关的应用授权申请
      await this.query(`
        DELETE FROM application_authorization_requests
        WHERE request_reason LIKE '%E2E%' OR request_reason LIKE '%自动化测试%'
      `);

      // 删除所有E2E测试相关的银行转账申请
      await this.query(`
        DELETE FROM bank_transfer_applications
        WHERE remark LIKE '%E2E%' OR remark LIKE '%自动化测试%'
      `);

      // 删除所有E2E测试相关的充值订单
      await this.query(`
        DELETE FROM recharge_orders
        WHERE order_id LIKE 'e2e_%'
      `);

      // 删除所有E2E测试相关的交易记录
      await this.query(`
        DELETE FROM transaction_records
        WHERE description LIKE '%E2E测试%' OR description LIKE '%E2E%'
      `);

      // 删除所有E2E测试站点
      await this.query(`
        DELETE FROM operation_sites
        WHERE name LIKE '%E2E测试%' OR name LIKE '%E2E%'
      `);

      // 删除所有E2E测试应用
      await this.query(`
        DELETE FROM applications
        WHERE app_name LIKE '%E2E测试%' OR app_code LIKE 'e2e_%'
      `);

      // 删除所有E2E测试运营商
      await this.query(`
        DELETE FROM operator_accounts
        WHERE username LIKE 'e2e_%'
          OR full_name LIKE '%E2E测试%'
          OR full_name LIKE 'E2E测试运营商%'
      `);

      this.testDataIds = {};
      console.log('✅ Test data cleaned up successfully');
    } catch (error) {
      console.error('❌ Error cleaning up test data:', error);
      throw error;
    }
  }

  /**
   * 获取运营商余额
   */
  async getOperatorBalance(operatorId: string): Promise<number> {
    if (!this.pool) {
      return 0;
    }

    const result = await this.query<{ balance: string }>(`
      SELECT balance FROM operator_accounts WHERE id = $1
    `, [operatorId]);

    return parseFloat(result.rows[0].balance);
  }

  /**
   * 获取运营商的交易记录数量
   */
  async getTransactionCount(operatorId: string, type?: string): Promise<number> {
    if (!this.pool) {
      return 0;
    }

    let sql = 'SELECT COUNT(*) as count FROM transaction_records WHERE operator_id = $1';
    const params: any[] = [operatorId];

    if (type) {
      sql += ' AND transaction_type = $2';
      params.push(type);
    }

    const result = await this.query<{ count: string }>(sql, params);
    return parseInt(result.rows[0].count);
  }

  /**
   * 关闭数据库连接
   */
  async close() {
    if (this.pool) {
      await this.pool.end();
      console.log('🔌 Database connection closed');
    }
  }
}
