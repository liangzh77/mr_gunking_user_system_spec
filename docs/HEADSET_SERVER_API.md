# 头显Server对接API文档

**版本**: v1.0
**更新时间**: 2025-10-31
**适用对象**: 头显Server开发者

---

## 目录

- [概述](#概述)
- [接入准备](#接入准备)
- [认证机制](#认证机制)
- [核心接口](#核心接口)
- [集成示例](#集成示例)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)
- [FAQ](#faq)

---

## 概述

### 系统架构

```
┌─────────────────┐          ┌──────────────────┐
│   头显Server    │  HTTPS   │  MR运营管理系统   │
│  (您的设备)     │ ◄──────► │   (本系统)       │
└─────────────────┘          └──────────────────┘
```

### 核心流程

```
1. 玩家启动游戏
   ↓
2. 头显Server请求授权 [POST /api/v1/game/authorize]
   ↓
3. 系统验证运营商资质、余额，扣费
   ↓
4. 返回授权Token
   ↓
5. 游戏运行
   ↓
6. 游戏结束（可选：主动结束会话）
```

---

## 接入准备

### 1. 获取API凭证

登录运营商后台（https://mrgun.chu-jiao.com/operator），进入"个人中心"：

- **运营商ID**: `operator_id` (示例: `e930ecfe-28e9-4360-afdd-76caf6bf7bb1`)
- **API Key**: 64位字符串 (示例: `api_key_1234567890abcdef...`)

### 2. 环境信息

| 环境 | Base URL | 用途 |
|------|----------|------|
| 生产环境 | `https://mrgun.chu-jiao.com/api/v1` | 正式使用 |
| 测试环境 | `https://localhost/api/v1` | 开发测试 |

### 3. 技术要求

- **协议**: HTTPS (生产环境必须)
- **请求格式**: JSON
- **编码**: UTF-8
- **超时设置**: 建议30秒

---

## 认证机制

### 请求头认证

所有API请求需要在HTTP Header中携带：

```http
X-API-Key: your_api_key_here
Content-Type: application/json
```

**示例**:
```http
POST /api/v1/game/authorize HTTP/1.1
Host: mrgun.chu-jiao.com
X-API-Key: api_key_1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd
Content-Type: application/json

{
  "app_code": "space_adventure",
  "player_count": 5,
  "site_id": "9afdc97b-7d33-485e-845c-55f041a6b5a7"
}
```

---

## 核心接口

### 1. 游戏授权（最重要）

**接口**: `POST /api/v1/game/authorize`

**用途**: 启动游戏前请求授权并扣费

**请求参数**:

```json
{
  "app_code": "space_adventure",
  "player_count": 5,
  "site_id": "9afdc97b-7d33-485e-845c-55f041a6b5a7"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| app_code | string | 是 | 应用代码（如：space_adventure） |
| player_count | integer | 是 | 玩家数量（2-8人） |
| site_id | string(UUID) | 是 | 运营点ID |

**成功响应** (HTTP 200):

```json
{
  "success": true,
  "data": {
    "usage_record_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_id": "sess_1234567890",
    "price_per_player": "10.00",
    "total_cost": "50.00",
    "authorization_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_at": "2025-10-31T18:00:00Z",
    "balance_before": "1000.00",
    "balance_after": "950.00"
  },
  "message": "游戏授权成功"
}
```

**失败响应** (HTTP 400/403):

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "账户余额不足，当前余额: ¥30.00，需要: ¥50.00"
  }
}
```

**常见错误码**:

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| `INSUFFICIENT_BALANCE` | 余额不足 | 提示运营商充值 |
| `INVALID_APP_CODE` | 应用代码不存在 | 检查app_code是否正确 |
| `APP_NOT_AUTHORIZED` | 应用未授权 | 联系管理员授权 |
| `INVALID_PLAYER_COUNT` | 玩家数量超出范围 | 检查player_count是否在允许范围内 |
| `SITE_NOT_FOUND` | 运营点不存在 | 检查site_id是否正确 |
| `INVALID_API_KEY` | API密钥无效 | 检查API Key是否正确 |

---

### 2. 查询余额

**接口**: `GET /api/v1/operators/balance`

**用途**: 查询运营商账户余额

**请求参数**: 无

**成功响应** (HTTP 200):

```json
{
  "balance": "1000.00",
  "currency": "CNY"
}
```

---

### 3. 查询已授权应用

**接口**: `GET /api/v1/operators/applications`

**用途**: 获取运营商已授权的应用列表

**请求参数**: 无

**成功响应** (HTTP 200):

```json
{
  "items": [
    {
      "id": "32d012d9-b798-4f78-8e96-3ce87bbbd3f5",
      "app_code": "space_adventure",
      "app_name": "太空探险",
      "description": "VR太空探险游戏",
      "price_per_player": "10.00",
      "min_players": 2,
      "max_players": 8,
      "is_active": true
    },
    {
      "id": "d64de826-4044-4a5a-811f-2ab3d3d8d739",
      "app_code": "star_war",
      "app_name": "星际战争",
      "description": "多人星际对战",
      "price_per_player": "15.00",
      "min_players": 4,
      "max_players": 8,
      "is_active": true
    }
  ],
  "total": 2
}
```

---

### 4. 查询运营点列表

**接口**: `GET /api/v1/operators/sites`

**用途**: 获取运营商的运营点列表

**请求参数**: 无

**成功响应** (HTTP 200):

```json
{
  "items": [
    {
      "id": "9afdc97b-7d33-485e-845c-55f041a6b5a7",
      "name": "北京朝阳店",
      "address": "北京市朝阳区xxx路xxx号",
      "contact_person": "张三",
      "contact_phone": "13800138000",
      "is_active": true
    }
  ],
  "total": 1
}
```

---

## 集成示例

### Python示例

```python
import requests
import uuid

class MRGameClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }

    def check_balance(self) -> dict:
        """查询余额"""
        url = f"{self.base_url}/operators/balance"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def authorize_game(self, app_code: str, player_count: int, site_id: str) -> dict:
        """游戏授权"""
        url = f"{self.base_url}/game/authorize"
        payload = {
            "app_code": app_code,
            "player_count": player_count,
            "site_id": site_id
        }
        response = requests.post(url, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

# 使用示例
if __name__ == "__main__":
    # 初始化客户端
    client = MRGameClient(
        api_key="your_api_key_here",
        base_url="https://mrgun.chu-jiao.com/api/v1"
    )

    try:
        # 1. 检查余额
        balance_result = client.check_balance()
        print(f"当前余额: ¥{balance_result['balance']}")

        # 2. 请求游戏授权
        auth_result = client.authorize_game(
            app_code="space_adventure",
            player_count=5,
            site_id="9afdc97b-7d33-485e-845c-55f041a6b5a7"
        )

        if auth_result['success']:
            print(f"✅ 授权成功")
            print(f"   会话ID: {auth_result['data']['session_id']}")
            print(f"   费用: ¥{auth_result['data']['total_cost']}")
            print(f"   剩余余额: ¥{auth_result['data']['balance_after']}")

            # 启动游戏
            # start_game_with_token(auth_result['data']['authorization_token'])
        else:
            print(f"❌ 授权失败: {auth_result['error']['message']}")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            error = e.response.json()
            print(f"请求错误: {error['error']['message']}")
        elif e.response.status_code == 403:
            print("认证失败，请检查API Key")
        else:
            print(f"HTTP错误: {e}")
    except Exception as e:
        print(f"系统错误: {e}")
```

### C# 示例

```csharp
using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

public class MRGameClient
{
    private readonly string _apiKey;
    private readonly string _baseUrl;
    private readonly HttpClient _httpClient;

    public MRGameClient(string apiKey, string baseUrl)
    {
        _apiKey = apiKey;
        _baseUrl = baseUrl.TrimEnd('/');
        _httpClient = new HttpClient();
        _httpClient.DefaultRequestHeaders.Add("X-API-Key", apiKey);
    }

    public async Task<BalanceResponse> CheckBalance()
    {
        var response = await _httpClient.GetAsync($"{_baseUrl}/operators/balance");
        response.EnsureSuccessStatusCode();
        var json = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<BalanceResponse>(json);
    }

    public async Task<AuthorizeResponse> AuthorizeGame(
        string appCode,
        int playerCount,
        string siteId)
    {
        var payload = new
        {
            app_code = appCode,
            player_count = playerCount,
            site_id = siteId
        };

        var content = new StringContent(
            JsonSerializer.Serialize(payload),
            Encoding.UTF8,
            "application/json"
        );

        var response = await _httpClient.PostAsync(
            $"{_baseUrl}/game/authorize",
            content
        );

        response.EnsureSuccessStatusCode();
        var json = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<AuthorizeResponse>(json);
    }
}

// 使用示例
public class Program
{
    public static async Task Main()
    {
        var client = new MRGameClient(
            "your_api_key_here",
            "https://mrgun.chu-jiao.com/api/v1"
        );

        try
        {
            // 查询余额
            var balance = await client.CheckBalance();
            Console.WriteLine($"当前余额: ¥{balance.Balance}");

            // 请求授权
            var auth = await client.AuthorizeGame(
                "space_adventure",
                5,
                "9afdc97b-7d33-485e-845c-55f041a6b5a7"
            );

            if (auth.Success)
            {
                Console.WriteLine($"✅ 授权成功");
                Console.WriteLine($"   费用: ¥{auth.Data.TotalCost}");
            }
        }
        catch (HttpRequestException ex)
        {
            Console.WriteLine($"请求错误: {ex.Message}");
        }
    }
}
```

---

## 错误处理

### HTTP状态码

| 状态码 | 说明 | 处理方式 |
|--------|------|----------|
| 200 | 成功 | 正常处理响应数据 |
| 400 | 请求参数错误 | 检查请求参数，显示错误信息 |
| 401 | 未认证 | 检查API Key是否设置 |
| 403 | 认证失败/无权限 | 检查API Key是否正确 |
| 404 | 资源不存在 | 检查请求URL和资源ID |
| 500 | 服务器错误 | 稍后重试，或联系技术支持 |
| 503 | 服务不可用 | 稍后重试 |

### 重试策略

建议实现指数退避重试：

```python
import time
from typing import Optional

def retry_request(func, max_retries=3, initial_delay=1):
    """带重试的请求"""
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func()
        except requests.exceptions.RequestException as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                print(f"请求失败，{delay}秒后重试... ({attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                raise

    raise last_exception
```

---

## 最佳实践

### 1. 启动前检查余额

```python
def safe_start_game(client, app_code, player_count, site_id):
    """安全启动游戏"""
    # 1. 先查询余额
    balance = client.check_balance()

    # 2. 预估费用（假设单价10元）
    estimated_cost = player_count * 10

    # 3. 余额检查
    if float(balance['balance']) < estimated_cost:
        return {
            'success': False,
            'message': f'余额不足，需要¥{estimated_cost}，当前余额¥{balance["balance"]}'
        }

    # 4. 请求授权
    return client.authorize_game(app_code, player_count, site_id)
```

### 2. 会话ID管理

会话ID由系统自动生成，无需客户端提供。每次授权请求会返回唯一的`session_id`。

### 3. 离线处理

如果网络断开，建议：
- 记录离线期间的游戏会话
- 网络恢复后补发授权请求
- 实现本地队列机制

### 4. 日志记录

记录所有API请求和响应，便于问题排查：

```python
import logging

logger = logging.getLogger('mr_game_client')
logger.setLevel(logging.INFO)

def log_api_call(method, url, request_data, response_data, status_code):
    logger.info(f"""
    API调用记录:
    - 方法: {method}
    - URL: {url}
    - 请求: {request_data}
    - 响应: {response_data}
    - 状态码: {status_code}
    """)
```

---

## FAQ

### Q1: 如何获取运营点ID (site_id)？

**A**: 调用 `GET /api/v1/operators/sites` 接口获取运营点列表，使用返回的 `id` 字段。

### Q2: 游戏中途玩家退出如何处理？

**A**: 本系统按启动时的玩家数量扣费，游戏中途玩家变化不影响费用。无需额外通知系统。

### Q3: 授权Token有什么用？

**A**: `authorization_token` 用于验证游戏启动的合法性，可用于：
- 游戏启动时验证
- 防止未授权启动
- 日志追踪

### Q4: 余额不足怎么办？

**A**:
1. 在UI上提示运营商
2. 引导运营商登录后台充值：https://mrgun.chu-jiao.com/operator
3. 建议实现余额预警（如低于100元提示）

### Q5: 如何测试接口？

**A**:
1. 使用测试环境：`https://localhost/api/v1`
2. 使用测试账号（从运营商后台注册）
3. 使用Postman等工具测试API

### Q6: 一个运营商可以有多个运营点吗？

**A**: 可以。一个运营商账号可以创建多个运营点，每个运营点对应一个物理门店。

### Q7: 授权失败是否会扣费？

**A**: 不会。只有授权成功（返回200状态码）才会扣费。

### Q8: 支持批量授权吗？

**A**: 暂不支持。每个游戏会话需要单独调用授权接口。

---

## 技术支持

### 联系方式

- **邮箱**: support@chu-jiao.com
- **运营商后台**: https://mrgun.chu-jiao.com/operator
- **项目地址**: https://github.com/liangzh77/mr_gunking_user_system_spec

### 在线文档

- **API完整文档**: `backend/docs/API_DOCUMENTATION.md`
- **Python SDK**: `sdk/python/README.md`
- **数据模型**: `specs/001-mr-v2/data-model.md`

---

**文档版本**: v1.0
**最后更新**: 2025-10-31
