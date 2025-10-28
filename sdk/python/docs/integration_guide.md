# MR游戏SDK集成指南

本指南详细说明如何在头显Server中集成MR游戏SDK。

## 目录

1. [快速开始](#快速开始)
2. [认证机制](#认证机制)
3. [核心功能](#核心功能)
4. [错误处理](#错误处理)
5. [最佳实践](#最佳实践)
6. [故障排除](#故障排除)

## 快速开始

### 1. 安装SDK

```bash
pip install mr-game-sdk
```

### 2. 基本集成

```python
from mr_game_sdk import MRGameClient

# 初始化客户端
client = MRGameClient(
    api_key="your_api_key",
    api_secret="your_api_secret",
    base_url="https://api.mr-game.com"  # 生产环境
)

# 游戏授权
result = client.authorize_game(
    app_id=1,
    player_count=5,
    session_id="unique_session_id"
)

if result.success:
    print(f"授权成功: {result.auth_token}")
else:
    print(f"授权失败: {result.error_message}")
```

## 认证机制

MR游戏SDK使用HMAC-SHA256签名认证机制：

### 请求签名算法

```
签名字符串 = HTTP方法 + "\n" +
             API路径 + "\n" +
             查询参数 + "\n" +
             时间戳 + "\n" +
             API密钥 + "\n" +
             请求体

签名 = HMAC-SHA256(API密钥, 签名字符串).hexdigest()
```

### 请求头

所有API请求需要包含以下认证头：

```
X-API-Key: your_api_key
X-Timestamp: 1640995200
X-Signature: computed_hmac_signature
```

### 时间同步

确保服务器时间与API服务器时间同步，误差不超过300秒。

## 核心功能

### 1. 游戏授权

在游戏启动前请求授权：

```python
def start_game(app_id: int, player_count: int, device_id: str):
    session_id = f"{device_id}_{int(time.time())}"

    try:
        result = client.authorize_game(
            app_id=app_id,
            player_count=player_count,
            session_id=session_id,
            site_id="store_001",
            metadata={
                "device_id": device_id,
                "location": "beijing_store_01",
                "headset_version": "v2.1"
            }
        )

        if result.success:
            # 保存授权信息
            active_sessions[session_id] = {
                "auth_token": result.auth_token,
                "expires_at": result.expires_at,
                "start_time": datetime.now(),
                "players": player_count
            }
            return True, result.auth_token
        else:
            logger.error(f"授权失败: {result.message}")
            return False, None

    except Exception as e:
        logger.error(f"授权异常: {e}")
        return False, None
```

### 2. 会话管理

监控活跃游戏会话：

```python
import asyncio
from datetime import datetime

class SessionManager:
    def __init__(self, client: MRGameClient):
        self.client = client
        self.active_sessions = {}

    async def monitor_sessions(self):
        """监控会话状态"""
        while True:
            current_time = datetime.now()
            expired_sessions = []

            for session_id, session_info in self.active_sessions.items():
                # 检查过期时间
                if current_time > session_info["expires_at"]:
                    expired_sessions.append(session_id)

                # 检查超长会话（超过2小时）
                duration = (current_time - session_info["start_time"]).seconds
                if duration > 7200:
                    expired_sessions.append(session_id)

            # 清理过期会话
            for session_id in expired_sessions:
                await self.end_session(session_id)

            await asyncio.sleep(60)  # 每分钟检查一次

    async def end_session(self, session_id: str):
        """结束游戏会话"""
        if session_id not in self.active_sessions:
            return

        session_info = self.active_sessions[session_id]

        try:
            result = self.client.end_game_session(
                app_id=session_info["app_id"],
                session_id=session_id,
                player_count=session_info["players"],
                metadata={
                    "duration": (datetime.now() - session_info["start_time"]).seconds
                }
            )

            if result.success:
                logger.info(f"会话结束成功: {session_id}, 费用: ¥{result.total_cost}")
            else:
                logger.error(f"会话结束失败: {session_id}")

        except Exception as e:
            logger.error(f"结束会话异常: {e}")
        finally:
            del self.active_sessions[session_id]
```

### 3. 玩家数量变化

实时更新玩家数量：

```python
def update_player_count(session_id: str, new_count: int):
    """更新会话玩家数量"""
    if session_id in active_sessions:
        old_count = active_sessions[session_id]["players"]
        active_sessions[session_id]["players"] = new_count

        logger.info(f"玩家数量变化: {session_id}, {old_count} -> {new_count}")

        # 如果玩家数量变为0，考虑结束会话
        if new_count == 0:
            asyncio.create_task(end_session(session_id))
```

### 4. 余额监控

定期检查账户余额：

```python
async def balance_monitor():
    """余额监控任务"""
    while True:
        try:
            balance_result = client.get_balance()
            if balance_result.success:
                balance = balance_result.balance

                # 余额警告阈值
                warning_threshold = 100.0
                critical_threshold = 50.0

                if balance < critical_threshold:
                    # 发送紧急通知
                    send_alert("CRITICAL", f"余额严重不足: ¥{balance}")
                elif balance < warning_threshold:
                    # 发送警告通知
                    send_alert("WARNING", f"余额不足: ¥{balance}")

            await asyncio.sleep(300)  # 每5分钟检查一次

        except Exception as e:
            logger.error(f"余额检查异常: {e}")
            await asyncio.sleep(60)  # 出错时1分钟后重试
```

## 错误处理

### 异常类型

```python
from mr_game_sdk import (
    MRGameAPIError,
    MRGameAuthError,
    MRGameValidationError,
    MRGameNetworkError,
    MRGameInsufficientBalanceError
)

try:
    result = client.authorize_game(app_id=1, player_count=5, session_id="test")
except MRGameAuthError as e:
    # 认证失败，检查API密钥
    logger.critical(f"认证失败: {e}")
    # 可能需要重新配置API密钥
except MRGameInsufficientBalanceError as e:
    # 余额不足，提示用户充值
    logger.warning(f"余额不足: {e}")
    send_balance_alert()
except MRGameValidationError as e:
    # 参数错误，检查调用代码
    logger.error(f"参数错误: {e}")
except MRGameNetworkError as e:
    # 网络问题，可以重试
    logger.warning(f"网络错误: {e}")
    # 实现重试逻辑
except MRGameAPIError as e:
    # 其他API错误
    logger.error(f"API错误: {e}")
```

### 重试机制

```python
import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=1):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except MRGameNetworkError as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"网络错误，{delay}秒后重试 ({attempt + 1}/{max_retries})")
                        time.sleep(delay * (2 ** attempt))  # 指数退避
                    else:
                        raise
                except Exception as e:
                    # 非网络错误不重试
                    raise

            raise last_exception
        return wrapper
    return decorator

@retry_on_failure(max_retries=3, delay=1)
def safe_authorize_game(app_id, player_count, session_id):
    """带重试的游戏授权"""
    return client.authorize_game(app_id, player_count, session_id)
```

## 最佳实践

### 1. 会话ID生成

```python
import uuid
import time

def generate_session_id(device_id: str) -> str:
    """生成唯一的会话ID"""
    # 推荐格式: {device_id}_{timestamp}_{random_uuid}
    timestamp = int(time.time())
    random_id = str(uuid.uuid4())[:8]
    return f"{device_id}_{timestamp}_{random_id}"
```

### 2. 配置管理

```python
import os
from dataclasses import dataclass

@dataclass
class GameConfig:
    api_key: str
    api_secret: str
    base_url: str
    timeout: int = 30
    max_retries: int = 3
    balance_warning_threshold: float = 100.0
    session_timeout: int = 7200  # 2小时

    @classmethod
    def from_env(cls) -> 'GameConfig':
        """从环境变量加载配置"""
        return cls(
            api_key=os.getenv('MR_GAME_API_KEY'),
            api_secret=os.getenv('MR_GAME_API_SECRET'),
            base_url=os.getenv('MR_GAME_BASE_URL', 'https://api.mr-game.com'),
            timeout=int(os.getenv('MR_GAME_TIMEOUT', '30')),
            max_retries=int(os.getenv('MR_GAME_MAX_RETRIES', '3'))
        )

# 使用配置
config = GameConfig.from_env()
client = MRGameClient(
    api_key=config.api_key,
    api_secret=config.api_secret,
    base_url=config.base_url,
    timeout=config.timeout
)
```

### 3. 日志记录

```python
import logging
import json

# 配置结构化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('mr_game_server')

def log_game_event(event_type: str, session_id: str, **kwargs):
    """记录游戏事件"""
    log_data = {
        'event_type': event_type,
        'session_id': session_id,
        'timestamp': datetime.now().isoformat(),
        **kwargs
    }
    logger.info(f"游戏事件: {json.dumps(log_data, ensure_ascii=False)}")

# 使用示例
log_game_event('game_start', session_id, player_count=5, app_id=1)
log_game_event('game_end', session_id, duration=3600, total_cost=50.0)
```

### 4. 监控指标

```python
from collections import defaultdict
import time

class MetricsCollector:
    def __init__(self):
        self.metrics = defaultdict(list)

    def record_latency(self, operation: str, latency: float):
        """记录操作延迟"""
        self.metrics[f"{operation}_latency"].append(latency)

    def record_success(self, operation: str):
        """记录成功操作"""
        self.metrics[f"{operation}_success"].append(1)

    def record_failure(self, operation: str, error_type: str):
        """记录失败操作"""
        self.metrics[f"{operation}_failure"].append(1)
        self.metrics[f"{operation}_failure_{error_type}"].append(1)

    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = {}
        for key, values in self.metrics.items():
            if key.endswith('_latency'):
                stats[key] = {
                    'count': len(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values)
                }
            else:
                stats[key] = len(values)
        return stats

# 使用指标收集器
metrics = MetricsCollector()

start_time = time.time()
try:
    result = client.authorize_game(app_id=1, player_count=5, session_id="test")
    if result.success:
        metrics.record_success('authorize')
    else:
        metrics.record_failure('authorize', result.error_code)
except Exception as e:
    metrics.record_failure('authorize', type(e).__name__)
finally:
    latency = time.time() - start_time
    metrics.record_latency('authorize', latency)
```

## 故障排除

### 常见问题

#### 1. 认证失败

**问题**: `MRGameAuthError: 认证失败，请检查API Key和Secret`

**解决方案**:
- 检查API密钥是否正确
- 确认API密钥已激活且未过期
- 检查服务器时间是否同步
- 验证签名算法实现

#### 2. 余额不足

**问题**: `MRGameInsufficientBalanceError: 余额不足`

**解决方案**:
- 提示用户及时充值
- 实现余额预警机制
- 在启动新游戏前检查余额

#### 3. 网络超时

**问题**: `MRGameNetworkError: 请求超时`

**解决方案**:
- 增加超时时间设置
- 实现重试机制
- 检查网络连接
- 考虑使用CDN或备用API地址

#### 4. 参数验证失败

**问题**: `MRGameValidationError: 参数验证失败`

**解决方案**:
- 检查参数类型和范围
- 确认必填参数不为空
- 验证参数格式（如session_id长度）

### 调试技巧

#### 1. 启用详细日志

```python
import logging

# 启用DEBUG级别日志
logging.getLogger('mr_game_sdk').setLevel(logging.DEBUG)

# 或者单独设置SDK日志
sdk_logger = logging.getLogger('mr_game_sdk.client')
sdk_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
sdk_logger.addHandler(handler)
```

#### 2. 网络请求调试

```python
# 启用requests库的调试日志
import http.client as http_client
http_client.HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
```

#### 3. 签名验证

```python
def verify_signature(api_secret: str, method: str, path: str,
                    params: dict, body: str, timestamp: int,
                    received_signature: str) -> bool:
    """验证签名是否正确"""
    expected_signature = MRGameClient(api_secret)._generate_signature(
        method, path, params, body, timestamp
    )
    return hmac.compare_digest(expected_signature, received_signature)
```

## 技术支持

如需技术支持，请联系：
- 邮箱: support@mr-game.com
- 文档: https://mr-game-sdk.readthedocs.io/
- 问题反馈: https://github.com/mr-game/mr-game-sdk/issues