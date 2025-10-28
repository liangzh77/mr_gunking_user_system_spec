# MR游戏运营管理系统 Python SDK

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI Version](https://img.shields.io/badge/pypi-v1.0.0-orange.svg)](https://pypi.org/project/mr-game-sdk/)

为MR头显Server提供游戏授权、计费功能的官方Python SDK。

## ✨ 特性

- 🚀 **简单易用** - 几行代码即可完成集成
- 🔒 **安全可靠** - HMAC-SHA256签名认证
- 🔄 **自动重试** - 网络异常自动重试机制
- 📊 **类型安全** - 完整的TypeScript风格类型提示
- 📝 **详细日志** - 结构化日志便于调试
- 🛡️ **异常处理** - 详细的异常分类和处理

## 📦 安装

```bash
pip install mr-game-sdk
```

## 🚀 快速开始

```python
from mr_game_sdk import MRGameClient

# 初始化客户端
client = MRGameClient(
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# 游戏授权
result = client.authorize_game(
    app_id=1,
    player_count=5,
    session_id="unique_session_id"
)

if result.success:
    print(f"授权成功！Token: {result.auth_token}")

    # 游戏结束后
    end_result = client.end_game_session(
        app_id=1,
        session_id="unique_session_id",
        player_count=5
    )
    print(f"总费用: ¥{end_result.total_cost}")
else:
    print(f"授权失败: {result.error_message}")
```

## 📖 文档

- [快速开始指南](docs/quickstart.md) - 10分钟完成集成
- [详细集成指南](docs/integration_guide.md) - 完整的集成说明
- [API参考文档](https://mr-game-sdk.readthedocs.io/) - 完整的API文档
- [示例代码](examples/) - 实际项目示例

## 🔧 开发

### 克隆仓库

```bash
git clone https://github.com/mr-game/mr-game-sdk-python.git
cd mr-game-sdk-python
```

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
black .
flake8 .
mypy .
```

## 🎯 使用场景

### 1. MR头显Server集成

```python
import asyncio
from mr_game_sdk import MRGameClient

class HeadsetServer:
    def __init__(self):
        self.client = MRGameClient(api_key="xxx", api_secret="yyy")
        self.active_sessions = {}

    async def start_game(self, app_id: int, players: int, device_id: str):
        session_id = f"{device_id}_{int(time.time())}"

        result = self.client.authorize_game(app_id, players, session_id)
        if result.success:
            self.active_sessions[session_id] = {
                "start_time": time.time(),
                "players": players
            }
            return True
        return False
```

### 2. 实时余额监控

```python
import asyncio

async def balance_monitor():
    client = MRGameClient(api_key="xxx", api_secret="yyy")

    while True:
        balance = client.get_balance()
        if balance.success and balance.balance < 100:
            send_alert("余额不足警告")
        await asyncio.sleep(300)  # 每5分钟检查
```

## 🔐 认证机制

SDK使用HMAC-SHA256签名认证：

1. **请求签名** - 每个API请求都包含唯一签名
2. **时间戳验证** - 防止重放攻击
3. **密钥安全** - API Secret仅在客户端存储

## 🚨 异常处理

```python
from mr_game_sdk import (
    MRGameClient,
    MRGameAPIError,
    MRGameAuthError,
    MRGameInsufficientBalanceError
)

try:
    result = client.authorize_game(app_id=1, player_count=5, session_id="test")
except MRGameAuthError:
    print("API密钥错误")
except MRGameInsufficientBalanceError:
    print("余额不足")
except MRGameAPIError as e:
    print(f"API错误: {e}")
```

## 📊 版本历史

- **v1.0.0** (2025-01-01)
  - 初始版本发布
  - 支持游戏授权和会话管理
  - 完整的异常处理机制
  - 详细的文档和示例

## 🤝 贡献

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持

- 📧 邮箱: support@mr-game.com
- 📖 文档: https://mr-game-sdk.readthedocs.io/
- 🐛 问题反馈: https://github.com/mr-game/mr-game-sdk-python/issues
- 💬 QQ群: 123456789

## 🏢 关于我们

MR游戏是领先的MR/VR游戏运营平台，为游戏开发商和运营商提供完整的授权、计费和管理解决方案。

---

**注意**: 本SDK需要有效的MR游戏运营商账户才能使用。如需账户，请联系我们的销售团队。