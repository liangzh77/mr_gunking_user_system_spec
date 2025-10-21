# MR游戏运营管理系统 Node.js SDK

[![npm version](https://badge.fury.io/js/%40mr-gaming%2Fsdk-nodejs.svg)](https://badge.fury.io/js/%40mr-gaming%2Fsdk-nodejs)
[![TypeScript](https://img.shields.io/badge/TypeScript-4.9+-blue.svg)](https://www.typescriptlang.org/)
[![Node.js Version](https://img.shields.io/badge/node-%3E%3D16.0.0-brightgreen.svg)](https://nodejs.org/)

MR游戏运营管理系统的官方Node.js SDK，提供运营商认证、游戏授权、财务管理、余额查询等功能的完整API接口。

## 功能特性

- 🔐 **完整的认证系统** - 支持运营商注册、登录、权限管理
- 🎮 **游戏服务** - 游戏授权、会话管理、运营点管理
- 💰 **财务管理** - 余额查询、交易记录、充值退款
- 📊 **统计分析** - 消费统计、游戏数据、财务报表
- 🔄 **自动重试** - 网络错误自动重试机制
- 🚀 **TypeScript支持** - 完整的类型定义
- 📝 **详细日志** - 完整的请求/响应日志

## 安装

```bash
npm install @mr-gaming/sdk-nodejs
# 或
yarn add @mr-gaming/sdk-nodejs
# 或
pnpm add @mr-gaming/sdk-nodejs
```

## 快速开始

```typescript
import { MRSdk } from '@mr-gaming/sdk-nodejs';

// 初始化SDK
const sdk = new MRSdk({
  baseURL: 'https://api.example.com',
  timeout: 30000,
  retryCount: 3
});

// 快速登录
await sdk.quickLogin('your-username', 'your-password');

// 查询余额
const balance = await sdk.balance.getBalance();
console.log('当前余额:', balance.balance);

// 游戏授权
const authResult = await sdk.games.authorizeGame({
  app_id: 1,
  player_count: 4,
  session_id: 'unique-session-id'
});
console.log('游戏授权成功:', authResult.auth_token);
```

## 详细文档

### 初始化配置

```typescript
const sdk = new MRSdk({
  baseURL: 'https://api.example.com',  // API基础URL
  timeout: 30000,                       // 请求超时时间(毫秒)
  retryCount: 3,                        // 重试次数
  retryDelay: 1000                      // 重试延迟(毫秒)
});
```

### 运营商认证

```typescript
// 注册新运营商
const registerResult = await sdk.auth.register({
  username: 'new-operator',
  password: 'SecurePass123!',
  name: '张三',
  email: 'zhangsan@example.com',
  phone: '13800138000',
  company_name: '示例公司'
});

// 登录
const loginResult = await sdk.auth.login('username', 'password');

// 获取当前用户信息
const operator = await sdk.auth.getCurrentOperator();

// 修改密码
await sdk.auth.changePassword('old-password', 'new-password');

// 登出
await sdk.auth.logout();
```

### 游戏服务

```typescript
// 游戏授权
const gameAuth = await sdk.games.authorizeGame({
  app_id: 1,
  player_count: 4,
  session_id: 'session-123',
  site_id: 'site-456'  // 可选
});

// 结束游戏会话
const endResult = await sdk.games.endSession({
  app_id: 1,
  session_id: 'session-123',
  player_count: 4
});

// 创建运营点
const site = await sdk.games.createSite({
  site_name: '示例运营点',
  address: '北京市朝阳区示例街道123号',
  contact_person: '张三',
  contact_phone: '13800138000',
  operator_id: 'operator-789'
});

// 获取活跃会话
const activeSessions = await sdk.games.getActiveSessions();
```

### 余额服务

```typescript
// 获取余额信息
const balance = await sdk.balance.getBalance();

// 获取详细余额（包含冻结明细）
const detailedBalance = await sdk.balance.getDetailedBalance();

// 冻结余额
await sdk.balance.freezeBalance(1000, '临时冻结');

// 解冻余额
await sdk.balance.unfreezeBalance('freeze-id', 500);

// 获取余额变更记录
const history = await sdk.balance.getBalanceHistory({
  page: 1,
  page_size: 20,
  start_date: '2024-01-01',
  end_date: '2024-12-31'
});
```

### 交易服务

```typescript
// 获取交易记录
const transactions = await sdk.transactions.getTransactions({
  page: 1,
  page_size: 20,
  type: 'consumption',
  start_date: '2024-01-01'
});

// 获取交易详情
const transaction = await sdk.transactions.getTransaction('transaction-id');

// 导出交易记录
const exportResult = await sdk.transactions.exportTransactions({
  start_date: '2024-01-01',
  end_date: '2024-12-31',
  format: 'excel'
});

// 获取交易统计
const stats = await sdk.transactions.getTransactionStats({
  start_date: '2024-01-01',
  end_date: '2024-12-31',
  group_by: 'month'
});
```

### 充值服务

```typescript
// 创建充值订单
const order = await sdk.recharge.createRechargeOrder({
  amount: '100.00',
  payment_method: 'alipay',
  return_url: 'https://example.com/return',
  notify_url: 'https://example.com/notify'
});

// 获取订单详情
const orderDetail = await sdk.recharge.getRechargeOrder(order.order_id);

// 取消订单
await sdk.recharge.cancelRechargeOrder(order.order_id, '用户取消');

// 获取充值统计
const rechargeStats = await sdk.recharge.getRechargeStats({
  start_date: '2024-01-01',
  end_date: '2024-12-31'
});
```

### 退款服务

```typescript
// 申请退款
const refund = await sdk.refunds.requestRefund({
  reason: '服务不满意，申请退款',
  amount: '50.00',
  transaction_ids: ['tx-1', 'tx-2']
});

// 获取退款申请详情
const refundDetail = await sdk.refunds.getRefundRequest(refund.refund_request_id);

// 取消退款申请
await sdk.refunds.cancelRefundRequest(refund.refund_request_id);

// 获取可退款的交易
const refundableTransactions = await sdk.refunds.getRefundableTransactions({
  min_amount: 10
});
```

### 统计服务

```typescript
// 获取消费统计
const consumptionStats = await sdk.statistics.getConsumptionStats({
  start_date: '2024-01-01',
  end_date: '2024-12-31',
  group_by: 'month'
});

// 获取游戏统计
const gameStats = await sdk.statistics.getGameStats({
  start_date: '2024-01-01',
  sort_by: 'revenue',
  sort_order: 'desc',
  limit: 10
});

// 获取实时统计
const realTimeStats = await sdk.statistics.getRealTimeStats();

// 获取财务报表
const financialReports = await sdk.statistics.getFinancialReports({
  start_date: '2024-01-01',
  end_date: '2024-12-31',
  report_type: 'monthly'
});

// 导出统计数据
const exportResult = await sdk.statistics.exportStats({
  report_type: 'consumption',
  start_date: '2024-01-01',
  end_date: '2024-12-31',
  format: 'excel'
});
```

## 高级功能

### 错误处理

```typescript
import { AuthError, ValidationError, NetworkError } from '@mr-gaming/sdk-nodejs';

try {
  await sdk.auth.login('username', 'password');
} catch (error) {
  if (error instanceof AuthError) {
    console.error('认证失败:', error.message);
  } else if (error instanceof ValidationError) {
    console.error('数据验证失败:', error.message);
  } else if (error instanceof NetworkError) {
    console.error('网络错误:', error.message);
  }
}
```

### 批量操作

```typescript
const batch = sdk.createBatchOperation();

// 添加操作到批次
batch.add(() => sdk.games.authorizeGame({
  app_id: 1,
  player_count: 4,
  session_id: 'session-1'
}));

batch.add(() => sdk.games.authorizeGame({
  app_id: 2,
  player_count: 2,
  session_id: 'session-2'
}));

// 执行批量操作
const results = await batch.execute(3); // 并发数为3
```

### 事件监听

```typescript
const eventListener = sdk.createEventListener();

// 监听事件
eventListener.on('auth.success', (data) => {
  console.log('登录成功:', data);
});

eventListener.on('game.session.started', (data) => {
  console.log('游戏会话开始:', data.session_id);
});

// 发送事件
eventListener.emit('auth.success', { username: 'test-user' });
```

### 缓存管理

```typescript
const cache = sdk.createCacheManager();

// 设置缓存
cache.set('user-profile', userData, 300000); // 5分钟TTL

// 获取缓存
const cachedUser = cache.get('user-profile');

// 清理过期缓存
cache.cleanup();
```

### 自动重试

```typescript
// 使用内置的重试机制
await sdk.withRetry(
  async () => sdk.balance.getBalance(),
  3,      // 最大重试次数
  1000    // 重试延迟(毫秒)
);
```

## API参考

### 配置选项

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| baseURL | string | 是 | - | API基础URL |
| timeout | number | 否 | 30000 | 请求超时时间(毫秒) |
| retryCount | number | 否 | 3 | 自动重试次数 |
| retryDelay | number | 否 | 1000 | 重试延迟(毫秒) |

### 错误类型

- `MRSdkError` - 基础错误类
- `AuthError` - 认证相关错误
- `ApiError` - API请求错误
- `ValidationError` - 数据验证错误
- `NetworkError` - 网络连接错误
- `PermissionError` - 权限不足错误
- `BusinessError` - 业务逻辑错误
- `InsufficientBalanceError` - 余额不足错误
- `GameSessionError` - 游戏会话错误
- `DuplicateRequestError` - 重复请求错误

## 开发和测试

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/mr-gaming/nodejs-sdk.git
cd nodejs-sdk

# 安装依赖
npm install

# 构建
npm run build

# 运行测试
npm test

# 代码检查
npm run lint
```

### 运行示例

```bash
# 进入示例目录
cd examples

# 安装依赖
npm install

# 运行示例
npm start
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 支持

- 📖 [文档](https://docs.mr-gaming.com/sdk/nodejs)
- 🐛 [问题反馈](https://github.com/mr-gaming/nodejs-sdk/issues)
- 💬 [讨论区](https://github.com/mr-gaming/nodejs-sdk/discussions)
- 📧 [邮箱支持](mailto:support@mr-gaming.com)

## 更新日志

### v1.0.0 (2024-01-01)

- 🎉 首次发布
- ✨ 支持运营商认证、游戏授权、财务管理等功能
- 📝 完整的TypeScript类型定义
- 🔄 自动重试和错误处理机制
- 📊 统计分析功能
- 🚀 高性能批量操作支持