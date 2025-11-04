# 头显Server对接API文档

**版本**: v2.1
**更新时间**: 2025-11-04
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
1. 运营商在后台点击"启动应用"
   ↓
2. 前端生成24小时有效的Headset Token
   ↓
3. 前端通过自定义协议启动头显Server (mrgun-{exe_name}://start?token=...&app_code=...&site_id=...)
   ↓
4. 头显Server解析URL参数，获取Token、app_code、site_id
   ↓
5. 头显Server调用 POST /api/v1/auth/game/pre-authorize 预授权（可选）
   ↓
6. 玩家佩戴头显，确定玩家数量
   ↓
7. 头显Server请求正式授权 [POST /api/v1/auth/game/authorize]
   ↓
8. 系统验证Token、运营商资质、余额，扣费
   ↓
9. 返回授权Token
   ↓
10. 游戏运行
   ↓
11. 游戏结束（可选：上传游戏会话数据）
```

---

## 接入准备

### 1. 获取启动参数

运营商在后台点击"启动应用"时，系统会通过自定义协议启动头显Server：

**协议格式**: `mrgun-{exe_name}://start?token={headset_token}&app_code={app_code}&site_id={site_id}`

**示例URL**:
```
mrgun-HeadsetServer://start?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...&app_code=APP_20251030_001&site_id=site_144c10e2-7c9b-4d07-a42c-05f736654d87
```

**URL参数说明**:

| 参数 | 类型 | 说明 |
|------|------|------|
| token | string | 24小时有效的Headset Token (JWT格式) |
| app_code | string | 应用代码 (如: APP_20251030_001) |
| site_id | string(UUID) | 运营点ID |

### 2. 注册自定义协议

**Windows注册表脚本示例** (mrgun-HeadsetServer.reg):

```reg
Windows Registry Editor Version 5.00

[HKEY_CLASSES_ROOT\mrgun-HeadsetServer]
@="URL:MR Gun HeadsetServer Protocol"
"URL Protocol"=""

[HKEY_CLASSES_ROOT\mrgun-HeadsetServer\shell]

[HKEY_CLASSES_ROOT\mrgun-HeadsetServer\shell\open]

[HKEY_CLASSES_ROOT\mrgun-HeadsetServer\shell\open\command]
@="\"C:\\Program Files\\MRGaming\\HeadsetServer.exe\" \"%1\""
```

**注意**:
- 协议名称格式: `mrgun-{exe文件名}` (使用连字符，不是下划线)
- 运营商可在后台下载注册表脚本，无需手动编写

### 3. 环境信息

| 环境 | Base URL | 用途 |
|------|----------|------|
| 生产环境 | `https://mrgun.chu-jiao.com/api/v1` | 正式使用 |
| 测试环境 | `https://localhost/api/v1` | 开发测试 |

### 4. 技术要求

- **协议**: HTTPS (生产环境必须)
- **请求格式**: JSON
- **编码**: UTF-8
- **超时设置**: 建议30秒

---

## 认证机制

### Headset Token认证

所有游戏授权API请求需要在HTTP Header中携带Headset Token：

```http
Authorization: Bearer {headset_token}
Content-Type: application/json
```

**Token特性**:
- 有效期: 24小时
- 格式: JWT
- 包含信息: operator_id, user_type (headset)
- 用途: 代表运营商身份调用游戏授权API

**示例**:
```http
POST /api/v1/auth/game/authorize HTTP/1.1
Host: mrgun.chu-jiao.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "app_code": "APP_20251030_001",
  "site_id": "9afdc97b-7d33-485e-845c-55f041a6b5a7",
  "player_count": 5,
  "headset_ids": ["headset_001", "headset_002"]
}
```

> ⚠️ **v2.1 变更**: 不再需要 `X-Session-ID` 请求头，服务器会自动生成并在响应中返回 `session_id`

### 会话ID规范 (v2.1更新)

**生成方式**: 由服务器端自动生成（客户端无需生成）

**格式**: `{operatorId}_{13位毫秒时间戳}_{16位随机字符}`

**示例**: `3d4927d0-5c60-407c-9acd-418e789e164d_1730451234567_a1b2c3d4e5f6g7h8`

**说明**:
- 服务器在授权成功后返回 `session_id`
- 用于后续游戏会话数据上传
- 客户端保存此 ID 用于关联游戏会话

**用途**:
- **幂等性保护**: 相同会话ID重复请求不会重复扣费
- **防重放攻击**: 时间戳验证防止请求重放
- **会话追踪**: 唯一标识一次游戏会话

---

## 核心接口

### 1. 游戏预授权 (可选)

**接口**: `POST /api/v1/auth/game/pre-authorize`

**用途**: 游戏启动前进行预检查，验证应用授权、余额等，但不扣费

**认证**: Bearer Token (Headset Token)

**请求参数**:

```json
{
  "app_code": "APP_20251030_001",
  "site_id": "9afdc97b-7d33-485e-845c-55f041a6b5a7",
  "estimated_player_count": 5
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| app_code | string | 是 | 应用代码 |
| site_id | string(UUID) | 是 | 运营点ID |
| estimated_player_count | integer | 是 | 预估玩家数量（1-100） |

**成功响应** (HTTP 200):

```json
{
  "success": true,
  "data": {
    "can_authorize": true,
    "app_code": "APP_20251030_001",
    "app_name": "太空射击",
    "unit_price": "10.00",
    "estimated_cost": "50.00",
    "current_balance": "1000.00",
    "min_players": 2,
    "max_players": 8
  },
  "message": "预授权检查通过"
}
```

**失败响应** (HTTP 402 余额不足):

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "账户余额不足，当前余额: ¥30.00，预估需要: ¥50.00"
  }
}
```

---

### 2. 游戏授权 (最重要)

**接口**: `POST /api/v1/auth/game/authorize`

**用途**: 启动游戏前请求正式授权并扣费

**认证**: Bearer Token (Headset Token)

**请求头**:

```http
Authorization: Bearer {headset_token}
Content-Type: application/json
```

> ⚠️ **v2.1 变更**: 移除了 `X-Session-ID` 请求头，服务器会自动生成 session_id

**请求参数**:

```json
{
  "app_code": "APP_20251030_001",
  "site_id": "9afdc97b-7d33-485e-845c-55f041a6b5a7",
  "player_count": 5,
  "headset_ids": ["headset_001", "headset_002", "headset_003", "headset_004", "headset_005"]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| app_code | string | 是 | 应用代码（与启动URL中的app_code一致） |
| site_id | string(UUID) | 是 | 运营点ID |
| player_count | integer | 是 | 实际玩家数量（1-100） |
| headset_ids | array[string] | 否 | 头显设备ID列表（用于记录和统计） |

**成功响应** (HTTP 200):

```json
{
  "success": true,
  "data": {
    "authorization_token": "550e8400-e29b-41d4-a716-446655440000",
    "session_id": "3d4927d0-5c60-407c-9acd-418e789e164d_1730451234567_a1b2c3d4e5f6g7h8",
    "app_name": "太空射击",
    "player_count": 5,
    "unit_price": "10.00",
    "total_cost": "50.00",
    "balance_after": "950.00",
    "authorized_at": "2025-11-02T10:30:45.123Z"
  }
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| authorization_token | string(UUID) | 授权令牌，用于游戏内验证 |
| session_id | string | **[v2.1新增]** 服务器生成的会话ID，用于游戏会话数据上传 |
| app_name | string | 应用名称 |
| player_count | integer | 玩家数量 |
| unit_price | string | 单人价格（保留2位小数） |
| total_cost | string | 本次扣费总额 |
| balance_after | string | 扣费后账户余额 |
| authorized_at | string(ISO 8601) | 授权时间 |

**失败响应** (HTTP 402 余额不足):

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

| HTTP状态码 | 错误码 | 说明 | 处理建议 |
|-----------|--------|------|----------|
| 400 | `INVALID_APP_CODE` | 应用代码格式错误 | 检查app_code格式 |
| 400 | `INVALID_SITE_ID` | 运营点ID格式错误 | 检查site_id格式 |
| 400 | `INVALID_SESSION_ID` | 会话ID格式错误 | 检查会话ID生成逻辑 |
| 400 | `INVALID_PLAYER_COUNT` | 玩家数量超出范围 | 确认在min_players和max_players之间 |
| 401 | `INVALID_TOKEN` | Token无效或已过期 | 重新获取Token |
| 402 | `INSUFFICIENT_BALANCE` | 余额不足 | 提示运营商充值 |
| 403 | `APP_NOT_AUTHORIZED` | 应用未授权 | 联系管理员授权应用 |
| 403 | `SITE_NOT_OWNED` | 运营点不属于该运营商 | 检查site_id是否正确 |
| 404 | `APP_NOT_FOUND` | 应用不存在 | 检查app_code是否正确 |
| 409 | `SESSION_ALREADY_EXISTS` | 会话ID重复（幂等性保护） | 返回已授权信息,不重复扣费 |

**幂等性保护**:
- 相同会话ID的重复请求会返回已授权的信息
- HTTP状态码: 200 (不是409)
- 不会重复扣费
- 适用场景: 网络重试、客户端重复请求

---

### 3. 上传游戏会话数据 (可选)

**接口**: `POST /api/v1/auth/game/sessions/upload`

**用途**: 游戏结束后上传会话数据（游戏时长、头显信息等）

**认证**: Bearer Token (Headset Token)

**请求参数**:

```json
{
  "session_id": "3d4927d0-5c60-407c-9acd-418e789e164d_1730451234567_a1b2c3d4e5f6g7h8",
  "game_duration_seconds": 1800,
  "headset_records": [
    {
      "headset_id": "headset_001",
      "play_time_seconds": 1800
    },
    {
      "headset_id": "headset_002",
      "play_time_seconds": 1750
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | 会话ID |
| game_duration_seconds | integer | 是 | 游戏总时长（秒） |
| headset_records | array | 否 | 头显游戏记录列表 |
| headset_records[].headset_id | string | 是 | 头显设备ID |
| headset_records[].play_time_seconds | integer | 是 | 该头显游戏时长（秒） |

**成功响应** (HTTP 200):

```json
{
  "success": true,
  "message": "游戏会话数据已上传"
}
```

---

## 集成示例

### Python示例

```python
import requests
import time
import secrets
import urllib.parse
from typing import Optional

class HeadsetServerClient:
    def __init__(self, base_url: str, headset_token: str):
        """初始化客户端

        Args:
            base_url: API基础URL (如: https://mrgun.chu-jiao.com/api/v1)
            headset_token: 从启动URL中提取的Headset Token
        """
        self.base_url = base_url.rstrip('/')
        self.headset_token = headset_token
        self.operator_id = self._extract_operator_id_from_token()

    def _extract_operator_id_from_token(self) -> str:
        """从JWT Token中提取operator_id"""
        import base64
        import json

        # JWT格式: header.payload.signature
        parts = self.headset_token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT token format")

        # 解码payload (需要补充padding)
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        data = json.loads(decoded)

        return data['sub']  # operator_id存储在'sub'字段

    def _get_headers(self) -> dict:
        """构造请求头

        Returns:
            请求头字典
        """
        return {
            'Authorization': f'Bearer {self.headset_token}',
            'Content-Type': 'application/json'
        }

    def pre_authorize(
        self,
        app_code: str,
        site_id: str,
        estimated_player_count: int
    ) -> dict:
        """预授权检查

        Args:
            app_code: 应用代码
            site_id: 运营点ID
            estimated_player_count: 预估玩家数量

        Returns:
            预授权响应数据
        """
        url = f"{self.base_url}/auth/game/pre-authorize"
        headers = {'Authorization': f'Bearer {self.headset_token}'}
        payload = {
            "app_code": app_code,
            "site_id": site_id,
            "estimated_player_count": estimated_player_count
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def authorize_game(
        self,
        app_code: str,
        site_id: str,
        player_count: int,
        headset_ids: Optional[list[str]] = None
    ) -> dict:
        """游戏授权（扣费）

        Args:
            app_code: 应用代码
            site_id: 运营点ID
            player_count: 实际玩家数量
            headset_ids: 头显设备ID列表（可选）

        Returns:
            授权响应数据（包含服务器生成的session_id）
        """
        url = f"{self.base_url}/auth/game/authorize"
        headers = self._get_headers()  # v2.1: 不再需要传入session_id
        payload = {
            "app_code": app_code,
            "site_id": site_id,
            "player_count": player_count
        }

        if headset_ids:
            payload["headset_ids"] = headset_ids

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        # v2.1: 服务器返回session_id，保存用于后续会话数据上传
        return result

    def upload_session_data(
        self,
        session_id: str,
        game_duration_seconds: int,
        headset_records: Optional[list[dict]] = None
    ) -> dict:
        """上传游戏会话数据

        Args:
            session_id: 会话ID
            game_duration_seconds: 游戏总时长（秒）
            headset_records: 头显游戏记录列表

        Returns:
            上传响应数据
        """
        url = f"{self.base_url}/auth/game/sessions/upload"
        headers = {'Authorization': f'Bearer {self.headset_token}'}
        payload = {
            "session_id": session_id,
            "game_duration_seconds": game_duration_seconds
        }

        if headset_records:
            payload["headset_records"] = headset_records

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()


# ========== 使用示例 ==========

def parse_launch_url(url: str) -> dict:
    """解析启动URL

    Args:
        url: 启动URL (如: mrgun-HeadsetServer://start?token=...&app_code=...&site_id=...)

    Returns:
        解析后的参数字典
    """
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)

    return {
        'token': params.get('token', [None])[0],
        'app_code': params.get('app_code', [None])[0],
        'site_id': params.get('site_id', [None])[0]
    }


if __name__ == "__main__":
    # 1. 解析启动URL
    launch_url = "mrgun-HeadsetServer://start?token=eyJhbG...&app_code=APP_20251030_001&site_id=9afdc97b-7d33-485e-845c-55f041a6b5a7"
    params = parse_launch_url(launch_url)

    # 2. 初始化客户端
    client = HeadsetServerClient(
        base_url="https://mrgun.chu-jiao.com/api/v1",
        headset_token=params['token']
    )

    try:
        # 3. 预授权检查（可选）
        print("执行预授权检查...")
        pre_auth_result = client.pre_authorize(
            app_code=params['app_code'],
            site_id=params['site_id'],
            estimated_player_count=5
        )

        if pre_auth_result['data']['can_authorize']:
            print(f"✅ 预授权通过")
            print(f"   应用名称: {pre_auth_result['data']['app_name']}")
            print(f"   预估费用: ¥{pre_auth_result['data']['estimated_cost']}")
            print(f"   当前余额: ¥{pre_auth_result['data']['current_balance']}")
        else:
            print(f"❌ 预授权失败")
            exit(1)

        # 4. 等待玩家佩戴头显，确定实际玩家数量
        actual_player_count = 5  # 实际检测到的玩家数量
        headset_ids = ["headset_001", "headset_002", "headset_003", "headset_004", "headset_005"]

        # 5. 正式授权（扣费）
        print("\n执行游戏授权...")
        auth_result = client.authorize_game(
            app_code=params['app_code'],
            site_id=params['site_id'],
            player_count=actual_player_count,
            headset_ids=headset_ids
        )

        if auth_result['success']:
            print(f"✅ 授权成功")
            print(f"   会话ID: {auth_result['data']['session_id']}")
            print(f"   授权Token: {auth_result['data']['authorization_token']}")
            print(f"   费用: ¥{auth_result['data']['total_cost']}")
            print(f"   剩余余额: ¥{auth_result['data']['balance_after']}")

            # 6. 启动游戏
            session_id = auth_result['data']['session_id']
            auth_token = auth_result['data']['authorization_token']

            print("\n🎮 启动游戏中...")
            # start_game(auth_token, player_count)

            # 7. 游戏结束后上传数据（可选）
            game_duration = 1800  # 30分钟

            print("\n上传游戏会话数据...")
            upload_result = client.upload_session_data(
                session_id=session_id,
                game_duration_seconds=game_duration,
                headset_records=[
                    {"headset_id": "headset_001", "play_time_seconds": 1800},
                    {"headset_id": "headset_002", "play_time_seconds": 1750},
                    {"headset_id": "headset_003", "play_time_seconds": 1800},
                    {"headset_id": "headset_004", "play_time_seconds": 1700},
                    {"headset_id": "headset_005", "play_time_seconds": 1800},
                ]
            )

            if upload_result['success']:
                print(f"✅ 会话数据上传成功")
        else:
            print(f"❌ 授权失败: {auth_result.get('error', {}).get('message')}")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 402:
            error = e.response.json()
            print(f"❌ 余额不足: {error['error']['message']}")
        elif e.response.status_code == 401:
            print(f"❌ Token无效或已过期，请重新启动")
        elif e.response.status_code == 403:
            error = e.response.json()
            print(f"❌ 权限错误: {error['error']['message']}")
        else:
            print(f"❌ HTTP错误: {e}")

    except Exception as e:
        print(f"❌ 系统错误: {e}")
```

### C# 示例

```csharp
using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Security.Cryptography;
using System.Web;

public class HeadsetServerClient
{
    private readonly string _baseUrl;
    private readonly string _headsetToken;
    private readonly string _operatorId;
    private readonly HttpClient _httpClient;

    public HeadsetServerClient(string baseUrl, string headsetToken)
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _headsetToken = headsetToken;
        _operatorId = ExtractOperatorIdFromToken(headsetToken);
        _httpClient = new HttpClient();
    }

    private string ExtractOperatorIdFromToken(string token)
    {
        // JWT格式: header.payload.signature
        var parts = token.Split('.');
        if (parts.Length != 3)
            throw new ArgumentException("Invalid JWT token format");

        // 解码payload
        var payload = parts[1];
        var padding = (4 - payload.Length % 4) % 4;
        payload += new string('=', padding);

        var decoded = Convert.FromBase64String(payload);
        var json = Encoding.UTF8.GetString(decoded);
        var data = JsonDocument.Parse(json);

        return data.RootElement.GetProperty("sub").GetString();
    }

    private string GenerateSessionId()
    {
        // 格式: {operatorId}_{13位毫秒时间戳}_{16位随机字符}
        var timestampMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        var randomBytes = new byte[8];
        using (var rng = RandomNumberGenerator.Create())
        {
            rng.GetBytes(randomBytes);
        }
        var randomHex = BitConverter.ToString(randomBytes).Replace("-", "").ToLower();

        return $"{_operatorId}_{timestampMs}_{randomHex}";
    }

    private HttpRequestMessage CreateRequest(
        HttpMethod method,
        string endpoint,
        string sessionId = null)
    {
        var request = new HttpRequestMessage(method, $"{_baseUrl}{endpoint}");
        request.Headers.Add("Authorization", $"Bearer {_headsetToken}");

        if (!string.IsNullOrEmpty(sessionId))
        {
            request.Headers.Add("X-Session-ID", sessionId);
        }

        return request;
    }

    public async Task<PreAuthResponse> PreAuthorize(
        string appCode,
        string siteId,
        int estimatedPlayerCount)
    {
        var request = CreateRequest(HttpMethod.Post, "/auth/game/pre-authorize");
        var payload = new
        {
            app_code = appCode,
            site_id = siteId,
            estimated_player_count = estimatedPlayerCount
        };

        request.Content = new StringContent(
            JsonSerializer.Serialize(payload),
            Encoding.UTF8,
            "application/json"
        );

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        var json = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<PreAuthResponse>(json);
    }

    public async Task<AuthResponse> AuthorizeGame(
        string appCode,
        string siteId,
        int playerCount,
        string[] headsetIds = null)
    {
        var sessionId = GenerateSessionId();
        var request = CreateRequest(HttpMethod.Post, "/auth/game/authorize", sessionId);

        var payload = new
        {
            app_code = appCode,
            site_id = siteId,
            player_count = playerCount,
            headset_ids = headsetIds
        };

        request.Content = new StringContent(
            JsonSerializer.Serialize(payload),
            Encoding.UTF8,
            "application/json"
        );

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        var json = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<AuthResponse>(json);
    }

    public async Task<UploadResponse> UploadSessionData(
        string sessionId,
        int gameDurationSeconds,
        HeadsetRecord[] headsetRecords = null)
    {
        var request = CreateRequest(HttpMethod.Post, "/auth/game/sessions/upload");
        var payload = new
        {
            session_id = sessionId,
            game_duration_seconds = gameDurationSeconds,
            headset_records = headsetRecords
        };

        request.Content = new StringContent(
            JsonSerializer.Serialize(payload),
            Encoding.UTF8,
            "application/json"
        );

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        var json = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<UploadResponse>(json);
    }
}

// 使用示例
public class Program
{
    public static async Task Main(string[] args)
    {
        // 1. 解析启动URL参数
        var launchUrl = "mrgun-HeadsetServer://start?token=eyJhbG...&app_code=APP_20251030_001&site_id=9afdc97b-7d33-485e-845c-55f041a6b5a7";
        var uri = new Uri(launchUrl);
        var query = HttpUtility.ParseQueryString(uri.Query);

        var headsetToken = query["token"];
        var appCode = query["app_code"];
        var siteId = query["site_id"];

        // 2. 初始化客户端
        var client = new HeadsetServerClient(
            "https://mrgun.chu-jiao.com/api/v1",
            headsetToken
        );

        try
        {
            // 3. 预授权检查
            Console.WriteLine("执行预授权检查...");
            var preAuth = await client.PreAuthorize(appCode, siteId, 5);

            if (preAuth.Data.CanAuthorize)
            {
                Console.WriteLine($"✅ 预授权通过");
                Console.WriteLine($"   应用名称: {preAuth.Data.AppName}");
                Console.WriteLine($"   预估费用: ¥{preAuth.Data.EstimatedCost}");

                // 4. 正式授权
                Console.WriteLine("\n执行游戏授权...");
                var auth = await client.AuthorizeGame(
                    appCode,
                    siteId,
                    5,
                    new[] { "headset_001", "headset_002", "headset_003", "headset_004", "headset_005" }
                );

                if (auth.Success)
                {
                    Console.WriteLine($"✅ 授权成功");
                    Console.WriteLine($"   费用: ¥{auth.Data.TotalCost}");
                    Console.WriteLine($"   剩余余额: ¥{auth.Data.BalanceAfter}");

                    // 5. 启动游戏
                    Console.WriteLine("\n🎮 启动游戏中...");
                    // StartGame(auth.Data.AuthorizationToken, auth.Data.PlayerCount);

                    // 6. 游戏结束后上传数据
                    Console.WriteLine("\n上传游戏会话数据...");
                    var upload = await client.UploadSessionData(
                        auth.Data.SessionId,
                        1800,
                        new[]
                        {
                            new HeadsetRecord { HeadsetId = "headset_001", PlayTimeSeconds = 1800 },
                            new HeadsetRecord { HeadsetId = "headset_002", PlayTimeSeconds = 1750 }
                        }
                    );

                    Console.WriteLine("✅ 会话数据上传成功");
                }
            }
        }
        catch (HttpRequestException ex)
        {
            Console.WriteLine($"❌ 请求错误: {ex.Message}");
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
| 401 | Token无效或已过期 | 提示用户重新启动应用 |
| 402 | 余额不足 | 提示运营商充值 |
| 403 | 无权限（应用未授权等） | 显示错误信息，联系管理员 |
| 409 | 会话重复（幂等性） | 使用返回的授权信息，继续游戏 |
| 500 | 服务器错误 | 稍后重试，或联系技术支持 |

### 重试策略

建议实现指数退避重试（仅针对网络错误和5xx错误）：

```python
import time
import requests

def retry_request(func, max_retries=3, initial_delay=1):
    """带重试的请求

    Args:
        func: 请求函数
        max_retries: 最大重试次数
        initial_delay: 初始延迟（秒）
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func()
        except requests.exceptions.RequestException as e:
            last_exception = e

            # 只重试网络错误和5xx错误
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code < 500:
                    # 4xx错误不重试
                    raise

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

### 1. 启动流程推荐

```python
def safe_start_game(launch_url: str):
    """安全启动游戏流程"""

    # 1. 解析启动URL
    params = parse_launch_url(launch_url)

    # 2. 初始化客户端
    client = HeadsetServerClient(BASE_URL, params['token'])

    try:
        # 3. 预授权检查（推荐）
        pre_auth = client.pre_authorize(
            app_code=params['app_code'],
            site_id=params['site_id'],
            estimated_player_count=MAX_PLAYERS
        )

        # 4. 显示预授权信息给操作员
        show_pre_auth_info(
            app_name=pre_auth['data']['app_name'],
            estimated_cost=pre_auth['data']['estimated_cost'],
            current_balance=pre_auth['data']['current_balance'],
            min_players=pre_auth['data']['min_players'],
            max_players=pre_auth['data']['max_players']
        )

        # 5. 等待玩家准备
        actual_players, headset_ids = wait_for_players(
            min_players=pre_auth['data']['min_players'],
            max_players=pre_auth['data']['max_players']
        )

        # 6. 正式授权
        auth = client.authorize_game(
            app_code=params['app_code'],
            site_id=params['site_id'],
            player_count=actual_players,
            headset_ids=headset_ids
        )

        # 7. 启动游戏
        start_game(auth['data']['authorization_token'], actual_players)

        # 8. 记录会话ID，游戏结束后上传数据
        save_session_id(auth['data']['session_id'])

    except requests.exceptions.HTTPError as e:
        handle_http_error(e)
```

### 2. 会话ID管理

```python
import secrets
import time

class SessionManager:
    """会话ID管理器"""

    def __init__(self, operator_id: str):
        self.operator_id = operator_id
        self.current_session_id = None

    def generate_new_session(self) -> str:
        """生成新的会话ID"""
        timestamp_ms = int(time.time() * 1000)
        random_str = secrets.token_hex(8)  # 16位十六进制

        self.current_session_id = f"{self.operator_id}_{timestamp_ms}_{random_str}"
        return self.current_session_id

    def get_current_session(self) -> str:
        """获取当前会话ID（用于重试）"""
        if not self.current_session_id:
            raise ValueError("No active session")
        return self.current_session_id

    def clear_session(self):
        """清除当前会话"""
        self.current_session_id = None
```

### 3. 离线处理

如果网络断开，建议：
- 记录离线期间的游戏会话信息
- 网络恢复后补发授权请求（使用相同会话ID，利用幂等性）
- 实现本地队列机制

```python
import json
import os

class OfflineQueue:
    """离线请求队列"""

    def __init__(self, queue_file='offline_queue.json'):
        self.queue_file = queue_file
        self.queue = self._load_queue()

    def _load_queue(self) -> list:
        """加载离线队列"""
        if os.path.exists(self.queue_file):
            with open(self.queue_file, 'r') as f:
                return json.load(f)
        return []

    def _save_queue(self):
        """保存离线队列"""
        with open(self.queue_file, 'w') as f:
            json.dump(self.queue, f, indent=2)

    def add_request(self, request_data: dict):
        """添加离线请求"""
        self.queue.append({
            'timestamp': time.time(),
            'data': request_data
        })
        self._save_queue()

    def process_queue(self, client):
        """处理离线队列"""
        while self.queue:
            item = self.queue[0]

            try:
                # 尝试发送请求
                client.authorize_game(**item['data'])
                # 成功后移除
                self.queue.pop(0)
                self._save_queue()
            except Exception as e:
                print(f"离线请求处理失败: {e}")
                break
```

### 4. 日志记录

记录所有API请求和响应，便于问题排查：

```python
import logging
import json

logger = logging.getLogger('headset_server_client')
logger.setLevel(logging.INFO)

# 文件处理器
file_handler = logging.FileHandler('headset_api.log')
file_handler.setLevel(logging.INFO)

# 格式化器
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log_api_call(method, url, request_data, response_data, status_code):
    """记录API调用"""
    logger.info(f"""
    API调用记录:
    - 方法: {method}
    - URL: {url}
    - 请求: {json.dumps(request_data, ensure_ascii=False, indent=2)}
    - 响应: {json.dumps(response_data, ensure_ascii=False, indent=2)}
    - 状态码: {status_code}
    """)
```

---

## FAQ

### Q1: 如何从启动URL中提取参数？

**A**: 启动URL格式为 `mrgun-{exe_name}://start?token=...&app_code=...&site_id=...`

Python示例:
```python
import urllib.parse

def parse_launch_url(url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)

    return {
        'token': params.get('token', [None])[0],
        'app_code': params.get('app_code', [None])[0],
        'site_id': params.get('site_id', [None])[0]
    }
```

### Q2: Headset Token的有效期是多久？

**A**: 24小时。如果Token过期，用户需要在运营商后台重新点击"启动应用"。

### Q3: 游戏中途玩家退出如何处理？

**A**: 本系统按启动时的玩家数量扣费，游戏中途玩家变化不影响费用。无需额外通知系统。

### Q4: 如何注册自定义协议？

**A**:
1. 运营商在后台"启动应用"对话框中，选择应用后会显示"下载注册表脚本"按钮
2. 下载并双击运行`.reg`文件
3. 注册表脚本会自动配置协议关联

### Q5: 会话ID重复会怎样？

**A**:
- 系统会返回已授权的信息（HTTP 200）
- 不会重复扣费
- 这是幂等性保护机制，允许安全重试

### Q6: 如何测试接口？

**A**:
1. 使用测试环境：`https://localhost/api/v1`
2. 在运营商后台点击"启动应用"获取真实的Headset Token
3. 使用Postman等工具测试API（记得设置正确的Headers）

### Q7: 预授权接口是必须的吗？

**A**: 不是必须的，但**强烈推荐**。预授权可以：
- 提前检查余额，避免授权时才发现余额不足
- 获取应用的玩家数量限制，用于UI提示
- 提供更好的用户体验

### Q8: 上传游戏会话数据有什么用？

**A**:
- 记录实际游戏时长，用于统计分析
- 记录每个头显的使用情况
- 帮助运营商了解设备使用率
- 可选功能，不影响计费

### Q9: 如何处理网络不稳定？

**A**:
- 实现重试机制（参考"重试策略"章节）
- 使用相同会话ID重试，利用幂等性保护
- 实现离线队列，网络恢复后补发请求

### Q10: 协议名称为什么要用连字符？

**A**: Windows自定义协议不支持下划线，必须使用连字符（`mrgun-HeadsetServer`），否则无法注册成功。

---

## 技术支持

### 联系方式

- **邮箱**: support@chu-jiao.com
- **运营商后台**: https://mrgun.chu-jiao.com/operator
- **项目地址**: https://github.com/liangzh77/mr_gunking_user_system_spec

### 在线文档

- **API完整文档**: `backend/docs/API_DOCUMENTATION.md`
- **数据模型**: `specs/001-mr-v2/data-model.md`
- **头显Server API**: `docs/HEADSET_SERVER_API.md` (本文档)

---

## 版本历史

### v2.1 (2025-11-04)
**重要变更**:
- ⚠️ **破坏性变更**: 授权接口不再需要客户端提供 `X-Session-ID` 请求头
- ✨ **新特性**: 服务器端自动生成 session_id，格式为 `{operator_id}_{timestamp_ms}_{random16}`
- ✨ **新特性**: 实现业务键幂等性保护（30秒窗口期）
  - 业务键组成：`operator_id` + `application_id` + `site_id` + `player_count`
  - 30秒内相同业务键的重复请求返回相同授权结果（不重复扣费）
- 🐛 **Bug修复**: 修复 site_id 格式支持问题，现支持带 "site_" 前缀和纯UUID两种格式
- 🐛 **Bug修复**: 修复退款审核通过后错误扣减余额的bug
- 🐛 **Bug修复**: 修复交易记录API返回字段缺失问题（transaction_type, balance_before, description）
- 🎨 **UI修复**: 修复前端交易记录金额显示双重负号问题（-¥-400.00 → -¥400.00）

**迁移指南**:
1. **移除 X-Session-ID 请求头**: 授权请求时不再需要生成和传递 X-Session-ID
2. **使用响应中的 session_id**: 服务器返回的 session_id 用于后续游戏会话数据上传
3. **幂等性保护**: 如需重试授权请求，直接重发即可，系统会自动检测重复请求（30秒内）

**API变更详情**:

```diff
POST /api/v1/auth/game/authorize

请求头:
  Authorization: Bearer {headset_token}
- X-Session-ID: {client_generated_session_id}  # 移除

响应:
  {
    "success": true,
    "data": {
+     "session_id": "abac65d7-..._{timestamp}_{random}",  # 新增：服务器生成
      "authorization_token": "...",
      ...
    }
  }
```

### v2.0 (2025-11-02)
**主要更新**:
- 更新认证机制：改用Headset Token（24小时有效）
- 新增自定义协议启动流程说明
- 新增预授权接口
- 更新会话ID格式规范
- 新增完整的Python和C#集成示例
- 补充自定义协议注册方法
