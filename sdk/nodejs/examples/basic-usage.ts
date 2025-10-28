/**
 * MR游戏运营管理系统 Node.js SDK 基础使用示例
 */

import { MRSdk, AuthError, ValidationError } from '../src';

async function basicUsageExample() {
  console.log('=== MR SDK 基础使用示例 ===\n');

  // 1. 初始化SDK
  console.log('1. 初始化SDK...');
  const sdk = new MRSdk({
    baseURL: 'https://api.example.com', // 替换为实际的API地址
    timeout: 30000,
    retryCount: 3,
    retryDelay: 1000
  });

  try {
    await sdk.initialize();
    console.log('✅ SDK初始化成功\n');
  } catch (error) {
    console.error('❌ SDK初始化失败:', error);
    return;
  }

  // 2. 测试API连接
  console.log('2. 测试API连接...');
  try {
    const isConnected = await sdk.testConnection();
    if (isConnected) {
      console.log('✅ API连接正常\n');
    } else {
      console.log('⚠️ API连接失败，但继续执行示例\n');
    }
  } catch (error) {
    console.log('⚠️ API连接测试失败:', error.message, '\n');
  }

  // 3. 运营商登录
  console.log('3. 运营商登录...');
  try {
    await sdk.quickLogin('demo-operator', 'DemoPassword123!');
    console.log('✅ 登录成功\n');
  } catch (error) {
    if (error instanceof AuthError) {
      console.error('❌ 登录失败:', error.message);
      console.log('💡 提示：请检查用户名和密码是否正确\n');
    } else {
      console.error('❌ 登录异常:', error.message, '\n');
    }
    return;
  }

  // 4. 获取当前运营商信息
  console.log('4. 获取当前运营商信息...');
  try {
    const operator = await sdk.auth.getCurrentOperator();
    if (operator) {
      console.log('✅ 运营商信息:');
      console.log('   用户名:', operator.username);
      console.log('   姓名:', operator.full_name);
      console.log('   邮箱:', operator.email);
      console.log('   公司:', operator.company_name || '无');
      console.log('   状态:', operator.is_active ? '活跃' : '禁用');
      console.log('   创建时间:', operator.created_at);
      console.log('');
    }
  } catch (error) {
    console.error('❌ 获取运营商信息失败:', error.message, '\n');
  }

  // 5. 查询余额
  console.log('5. 查询余额信息...');
  try {
    const balance = await sdk.balance.getBalance();
    console.log('✅ 余额信息:');
    console.log('   当前余额:', balance.balance);
    console.log('   可用余额:', balance.available_balance);
    console.log('   冻结余额:', balance.frozen_balance);
    console.log('   货币:', balance.currency);
    console.log('   更新时间:', balance.updated_at);
    console.log('');
  } catch (error) {
    console.error('❌ 查询余额失败:', error.message, '\n');
  }

  // 6. 获取交易记录
  console.log('6. 获取交易记录...');
  try {
    const transactions = await sdk.transactions.getTransactions({
      page: 1,
      page_size: 5
    });

    console.log('✅ 交易记录:');
    console.log(`   总记录数: ${transactions.total}`);
    console.log(`   当前页: ${transactions.page}/${transactions.total_pages}`);

    if (transactions.items.length > 0) {
      console.log('   最近交易:');
      transactions.items.forEach((tx, index) => {
        console.log(`     ${index + 1}. ${tx.type} - ${tx.amount} - ${tx.description} (${tx.created_at})`);
      });
    } else {
      console.log('   暂无交易记录');
    }
    console.log('');
  } catch (error) {
    console.error('❌ 获取交易记录失败:', error.message, '\n');
  }

  // 7. 创建运营点
  console.log('7. 创建运营点...');
  try {
    const newSite = await sdk.games.createSite({
      site_name: '示例运营点',
      address: '北京市朝阳区示例街道123号',
      contact_person: '张三',
      contact_phone: '13800138000',
      operator_id: 'demo-operator-id' // 这应该是实际的运营商ID
    });
    console.log('✅ 运营点创建成功:');
    console.log('   运营点ID:', newSite.site_id);
    console.log('   名称:', newSite.site_name);
    console.log('   地址:', newSite.address);
    console.log('');
  } catch (error) {
    console.error('❌ 创建运营点失败:', error.message, '\n');
  }

  // 8. 获取运营点列表
  console.log('8. 获取运营点列表...');
  try {
    const sites = await sdk.games.getSites();
    console.log('✅ 运营点列表:');
    if (sites.length > 0) {
      sites.forEach((site, index) => {
        console.log(`   ${index + 1}. ${site.site_name} - ${site.address} - ${site.contact_person}`);
      });
    } else {
      console.log('   暂无运营点');
    }
    console.log('');
  } catch (error) {
    console.error('❌ 获取运营点列表失败:', error.message, '\n');
  }

  // 9. 游戏授权示例
  console.log('9. 游戏授权示例...');
  try {
    const gameAuth = await sdk.games.authorizeGame({
      app_id: 1,
      player_count: 4,
      session_id: `demo-session-${Date.now()}`,
      site_id: 'demo-site-id' // 可选，使用实际的运营点ID
    });
    console.log('✅ 游戏授权成功:');
    console.log('   会话ID:', gameAuth.session_id);
    console.log('   授权令牌:', gameAuth.auth_token);
    console.log('   玩家数量:', gameAuth.player_count);
    console.log('   每玩家费用:', gameAuth.cost_per_player);
    console.log('   过期时间:', gameAuth.expires_at);
    console.log('');

    // 等待几秒模拟游戏进行
    console.log('⏳ 模拟游戏进行中...');
    await new Promise(resolve => setTimeout(resolve, 3000));

    // 结束游戏会话
    console.log('10. 结束游戏会话...');
    const endResult = await sdk.games.endSession({
      app_id: 1,
      session_id: gameAuth.session_id,
      player_count: 4
    });
    console.log('✅ 游戏会话结束:');
    console.log('   会话ID:', endResult.session_id);
    console.log('   总费用:', endResult.total_cost);
    console.log('   游戏时长(分钟):', endResult.duration_minutes);
    console.log('');
  } catch (error) {
    console.error('❌ 游戏授权失败:', error.message, '\n');
  }

  // 11. 获取统计数据
  console.log('11. 获取消费统计...');
  try {
    const stats = await sdk.statistics.getConsumptionStats({
      start_date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 最近7天
      end_date: new Date().toISOString().split('T')[0],
      group_by: 'day'
    });

    console.log('✅ 消费统计:');
    console.log('   总玩家数:', stats.total_stats.total_players);
    console.log('   总游戏时长:', stats.total_stats.total_duration, '分钟');
    console.log('   总消费:', stats.total_stats.total_cost);
    console.log('   会话数:', stats.total_stats.session_count);
    console.log('   平均会话时长:', stats.total_stats.avg_session_duration, '分钟');
    console.log('   每小时费用:', stats.total_stats.cost_per_hour);
    console.log('');
  } catch (error) {
    console.error('❌ 获取统计数据失败:', error.message, '\n');
  }

  // 12. 创建充值订单示例
  console.log('12. 创建充值订单示例...');
  try {
    const rechargeOrder = await sdk.recharge.createRechargeOrder({
      amount: '100.00',
      payment_method: 'alipay',
      return_url: 'https://example.com/return',
      notify_url: 'https://example.com/notify'
    });
    console.log('✅ 充值订单创建成功:');
    console.log('   订单ID:', rechargeOrder.order_id);
    console.log('   充值金额:', rechargeOrder.amount);
    console.log('   状态:', rechargeOrder.status);
    console.log('   支付方式:', rechargeOrder.payment_method);
    if (rechargeOrder.payment_url) {
      console.log('   支付链接:', rechargeOrder.payment_url);
    }
    if (rechargeOrder.qr_code) {
      console.log('   二维码:', rechargeOrder.qr_code);
    }
    console.log('   过期时间:', rechargeOrder.expires_at);
    console.log('');
  } catch (error) {
    console.error('❌ 创建充值订单失败:', error.message, '\n');
  }

  // 13. 错误处理示例
  console.log('13. 错误处理示例...');
  try {
    // 尝试使用无效的数据
    await sdk.auth.register({
      username: 'a', // 太短
      password: '123', // 太简单
      name: '',
      email: 'invalid-email',
      phone: '123'
    });
  } catch (error) {
    if (error instanceof ValidationError) {
      console.log('✅ 成功捕获验证错误:');
      console.log('   错误信息:', error.message);
      console.log('   错误代码:', error.code);
    } else {
      console.log('❌ 未能正确捕获验证错误');
    }
  }

  // 14. SDK信息
  console.log('14. SDK信息...');
  const sdkInfo = sdk.getSdkInfo();
  console.log('✅ SDK信息:');
  console.log('   版本:', sdkInfo.version);
  console.log('   平台:', sdkInfo.platform);
  console.log('   API地址:', sdkInfo.baseURL);
  console.log('   认证状态:', sdkInfo.isAuthenticated ? '已认证' : '未认证');
  console.log('');

  // 15. 优雅关闭
  console.log('15. 优雅关闭SDK...');
  try {
    await sdk.quickLogout();
    await sdk.shutdown();
    console.log('✅ SDK已关闭\n');
  } catch (error) {
    console.error('❌ 关闭SDK失败:', error.message, '\n');
  }

  console.log('=== 示例执行完成 ===');
}

// 运行示例
if (require.main === module) {
  basicUsageExample().catch(console.error);
}

export { basicUsageExample };