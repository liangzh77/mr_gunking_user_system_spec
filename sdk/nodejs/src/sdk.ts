/**
 * MR游戏运营管理系统主SDK类
 */

import { HttpClient, HttpClientConfig } from './http-client';
import { MRConfig } from './types';
import { AuthError } from './errors';
import {
  OperatorAuth,
  GameService,
  BalanceService,
  TransactionService,
  RechargeService,
  RefundService,
  StatisticsService
} from './services';

export class MRSdk {
  private http: HttpClient;
  private isInitialized: boolean = false;

  // 服务实例
  public auth: OperatorAuth;
  public games: GameService;
  public balance: BalanceService;
  public transactions: TransactionService;
  public recharge: RechargeService;
  public refunds: RefundService;
  public statistics: StatisticsService;

  constructor(config: MRConfig) {
    this.validateConfig(config);

    // 创建HTTP客户端
    const httpConfig: HttpClientConfig = {
      baseURL: config.baseURL,
      timeout: config.timeout || 30000,
      retryCount: config.retryCount || 3,
      retryDelay: config.retryDelay || 1000,
      headers: {
        'X-SDK-Version': '1.0.0',
        'X-SDK-Platform': 'Node.js'
      }
    };

    this.http = new HttpClient(httpConfig);

    // 初始化服务
    this.auth = new OperatorAuth(this.http);
    this.games = new GameService(this.http);
    this.balance = new BalanceService(this.http);
    this.transactions = new TransactionService(this.http);
    this.recharge = new RechargeService(this.http);
    this.refunds = new RefundService(this.http);
    this.statistics = new StatisticsService(this.http);

    this.isInitialized = true;
  }

  /**
   * 初始化SDK
   */
  async initialize(): Promise<void> {
    if (!this.isInitialized) {
      throw new Error('SDK未正确初始化');
    }

    // 可以在这里添加初始化逻辑，比如检查API连接等
    console.log('MR SDK initialized successfully');
  }

  /**
   * 设置认证令牌
   */
  setAuthToken(token: string): void {
    if (!token || token.trim().length === 0) {
      throw new Error('认证令牌不能为空');
    }

    this.http.setAuthToken(token.trim());
  }

  /**
   * 清除认证令牌
   */
  clearAuthToken(): void {
    this.http.clearAuthToken();
  }

  /**
   * 获取当前认证令牌
   */
  getAuthToken(): string | undefined {
    return this.http['axios'].defaults.headers.common['Authorization'];
  }

  /**
   * 验证配置
   */
  private validateConfig(config: MRConfig): void {
    if (!config) {
      throw new Error('配置不能为空');
    }

    if (!config.baseURL || config.baseURL.trim().length === 0) {
      throw new Error('baseURL不能为空');
    }

    // 验证URL格式
    try {
      new URL(config.baseURL);
    } catch {
      throw new Error('baseURL格式无效');
    }

    if (config.timeout && (config.timeout < 1000 || config.timeout > 300000)) {
      throw new Error('timeout应在1000-300000毫秒之间');
    }

    if (config.retryCount && (config.retryCount < 0 || config.retryCount > 10)) {
      throw new Error('retryCount应在0-10之间');
    }

    if (config.retryDelay && (config.retryDelay < 100 || config.retryDelay > 10000)) {
      throw new Error('retryDelay应在100-10000毫秒之间');
    }
  }

  /**
   * 获取SDK版本
   */
  getVersion(): string {
    return '1.0.0';
  }

  /**
   * 获取SDK信息
   */
  getSdkInfo(): {
    version: string;
    platform: string;
    baseURL: string;
    isAuthenticated: boolean;
  } {
    return {
      version: this.getVersion(),
      platform: 'Node.js',
      baseURL: this.http['axios'].defaults.baseURL,
      isAuthenticated: !!this.getAuthToken()
    };
  }

  /**
   * 测试API连接
   */
  async testConnection(): Promise<boolean> {
    try {
      // 尝试访问一个简单的API端点
      await this.http.get('/v1/health');
      return true;
    } catch (error) {
      console.error('API连接测试失败:', error);
      return false;
    }
  }

  /**
   * 快速登录（使用用户名和密码）
   */
  async quickLogin(username: string, password: string): Promise<void> {
    try {
      const authResponse = await this.auth.login(username, password);
      this.setAuthToken(authResponse.access_token);
      console.log('登录成功，用户:', username);
    } catch (error) {
      console.error('登录失败:', error);
      throw error;
    }
  }

  /**
   * 快速登出
   */
  async quickLogout(): Promise<void> {
    try {
      await this.auth.logout();
      this.clearAuthToken();
      console.log('登出成功');
    } catch (error) {
      // 即使登出失败，也清除本地token
      this.clearAuthToken();
      console.error('登出失败:', error);
    }
  }

  /**
   * 检查认证状态
   */
  async checkAuthStatus(): Promise<boolean> {
    try {
      return await this.auth.validateToken();
    } catch (error) {
      return false;
    }
  }

  /**
   * 批量操作助手
   */
  createBatchOperation<T>() {
    return new BatchOperationHelper<T>(this.http);
  }

  /**
   * 事件监听器
   */
  createEventListener() {
    return new EventListener();
  }

  /**
   * 缓存管理器
   */
  createCacheManager() {
    return new CacheManager();
  }

  /**
   * 错误重试机制
   */
  async withRetry<T>(
    operation: () => Promise<T>,
    maxAttempts: number = 3,
    delay: number = 1000
  ): Promise<T> {
    let lastError: Error;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;

        if (attempt === maxAttempts) {
          throw lastError;
        }

        // 对于认证错误，不进行重试
        if (error instanceof AuthError) {
          throw error;
        }

        console.warn(`操作失败，${delay}ms后进行第${attempt + 1}次重试:`, error.message);
        await new Promise(resolve => setTimeout(resolve, delay * attempt));
      }
    }

    throw lastError!;
  }

  /**
   * 优雅关闭SDK
   */
  async shutdown(): Promise<void> {
    console.log('正在关闭MR SDK...');

    // 清理会话缓存
    this.games.clearSessionCache();

    // 清除认证令牌
    this.clearAuthToken();

    // 其他清理工作...
    this.isInitialized = false;

    console.log('MR SDK已关闭');
  }
}

// 批量操作助手类
class BatchOperationHelper<T> {
  private operations: Array<() => Promise<T>> = [];

  constructor(private http: HttpClient) {}

  add(operation: () => Promise<T>): this {
    this.operations.push(operation);
    return this;
  }

  async execute(concurrency: number = 5): Promise<T[]> {
    const results: T[] = [];
    const errors: Error[] = [];

    // 分批执行
    for (let i = 0; i < this.operations.length; i += concurrency) {
      const batch = this.operations.slice(i, i + concurrency);
      const batchPromises = batch.map(async (operation, index) => {
        try {
          const result = await operation();
          return { index: i + index, result, error: null };
        } catch (error) {
          return { index: i + index, result: null, error: error as Error };
        }
      });

      const batchResults = await Promise.all(batchPromises);

      // 处理批次结果
      batchResults.forEach(({ index, result, error }) => {
        if (error) {
          errors.push(error);
        } else {
          results[index] = result;
        }
      });
    }

    if (errors.length > 0) {
      console.error(`批量操作完成，${errors.length}个失败:`, errors);
    }

    return results;
  }
}

// 事件监听器类
class EventListener {
  private listeners: Map<string, Array<(data: any) => void>> = new Map();

  on(event: string, callback: (data: any) => void): this {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)!.push(callback);
    return this;
  }

  off(event: string, callback?: (data: any) => void): this {
    if (!this.listeners.has(event)) {
      return this;
    }

    if (!callback) {
      this.listeners.delete(event);
    } else {
      const callbacks = this.listeners.get(event)!;
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }

    return this;
  }

  emit(event: string, data?: any): void {
    if (!this.listeners.has(event)) {
      return;
    }

    this.listeners.get(event)!.forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error(`事件处理器执行失败 (${event}):`, error);
      }
    });
  }
}

// 缓存管理器类
class CacheManager {
  private cache: Map<string, { data: any; expires: number }> = new Map();

  set(key: string, data: any, ttl: number = 300000): void { // 默认5分钟
    const expires = Date.now() + ttl;
    this.cache.set(key, { data, expires });
  }

  get<T = any>(key: string): T | null {
    const item = this.cache.get(key);
    if (!item) {
      return null;
    }

    if (Date.now() > item.expires) {
      this.cache.delete(key);
      return null;
    }

    return item.data as T;
  }

  delete(key: string): boolean {
    return this.cache.delete(key);
  }

  clear(): void {
    this.cache.clear();
  }

  // 清理过期缓存
  cleanup(): void {
    const now = Date.now();
    for (const [key, item] of this.cache.entries()) {
      if (now > item.expires) {
        this.cache.delete(key);
      }
    }
  }

  size(): number {
    return this.cache.size;
  }
}