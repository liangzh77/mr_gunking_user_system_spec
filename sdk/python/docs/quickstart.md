# MR游戏SDK快速开始指南

本指南帮助您在10分钟内完成MR游戏SDK的集成和测试。

## 前置条件

- Python 3.8+
- 有效的MR游戏运营商账户
- API密钥和Secret

## 第一步：安装SDK

```bash
pip install mr-game-sdk
```

## 第二步：获取API密钥

1. 登录MR游戏管理后台
2. 进入"开发者设置" → "API密钥"
3. 创建新的API密钥对
4. 记录API Key和Secret

## 第三步：基本集成

创建 `test_integration.py` 文件：

```python
#!/usr/bin/env python3
from mr_game_sdk import MRGameClient
import time

# 替换为您的实际API密钥
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"

# 初始化客户端
client = MRGameClient(
    api_key=API_KEY,
    api_secret=API_SECRET,
    base_url="http://localhost:8000"  # 开发环境
)

def test_basic_flow():
    """测试基本流程"""
    print("=== MR游戏SDK集成测试 ===\n")

    try:
        # 1. 查询余额
        print("1. 查询账户余额...")
        balance = client.get_balance()
        if balance.success:
            print(f"✅ 当前余额: ¥{balance.balance}")
        else:
            print(f"❌ 余额查询失败: {balance.message}")
            return

        # 2. 游戏授权
        print("\n2. 请求游戏授权...")
        session_id = f"test_{int(time.time())}"

        auth_result = client.authorize_game(
            app_id=1,
            player_count=3,
            session_id=session_id
        )

        if auth_result.success:
            print(f"✅ 授权成功!")
            print(f"   会话ID: {auth_result.session_id}")
            print(f"   授权Token: {auth_result.auth_token}")
            print(f"   预估费用: ¥{auth_result.estimated_cost}")
        else:
            print(f"❌ 授权失败: {auth_result.message}")
            return

        # 3. 模拟游戏运行
        print("\n3. 模拟游戏运行 (5秒)...")
        time.sleep(5)

        # 4. 结束会话
        print("\n4. 结束游戏会话...")
        end_result = client.end_game_session(
            app_id=1,
            session_id=session_id,
            player_count=3
        )

        if end_result.success:
            print(f"✅ 会话结束成功!")
            print(f"   总费用: ¥{end_result.total_cost}")
            print(f"   交易ID: {end_result.transaction_id}")
        else:
            print(f"❌ 会话结束失败: {end_result.message}")

        print("\n=== 测试完成 ===")

    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_basic_flow()
```

## 第四步：运行测试

```bash
python test_integration.py
```

## 第五步：查看结果

成功运行后，您应该看到类似输出：

```
=== MR游戏SDK集成测试 ===

1. 查询账户余额...
✅ 当前余额: ¥1000.00

2. 请求游戏授权...
✅ 授权成功!
   会话ID: test_1640995200
   授权Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   预估费用: ¥30.00

3. 模拟游戏运行 (5秒)...

4. 结束游戏会话...
✅ 会话结束成功!
   总费用: ¥2.50
   交易ID: tx_1640995205_abc123

=== 测试完成 ===
```

## 常见问题

### Q: 认证失败怎么办？

A: 检查以下几点：
1. API密钥是否正确复制
2. 是否使用了正确的环境URL
3. 系统时间是否准确

### Q: 余额不足如何处理？

A:
1. 登录管理后台充值
2. 实现余额预警机制
3. 在启动游戏前检查余额

### Q: 如何在生产环境使用？

A: 修改 `base_url` 为生产地址：
```python
client = MRGameClient(
    api_key=API_KEY,
    api_secret=API_SECRET,
    base_url="https://api.mr-game.com"  # 生产环境
)
```

## 下一步

- 查看 [集成指南](integration_guide.md) 了解详细用法
- 查看 [API文档](../README.md) 了解所有API
- 查看 [示例代码](../examples/) 了解最佳实践

## 技术支持

如有问题，请联系：
- 邮箱: support@mr-game.com
- QQ群: 123456789
- 微信群: 扫描二维码加入