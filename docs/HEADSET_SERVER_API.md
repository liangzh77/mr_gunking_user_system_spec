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
5. 玩家佩戴头显，确定玩家数量
   ↓
6. 头显Server调用 POST /api/v1/auth/game/pre-authorize 预授权（可选，传入确定的玩家数量）
   ↓
7. 头显Server请求正式授权 [POST /api/v1/auth/game/authorize]
   ↓
8. 系统验证Token、运营商资质、余额，扣费
   ↓
9. 返回session_id和扣费信息
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

**用途**: 查询游戏授权资格，不执行实际扣费操作。可在游戏启动前进行预检查，验证应用授权、余额等。

**认证**: Bearer Token (Headset Token，24小时有效)

**业务逻辑**:
1. 验证Bearer Token有效性
2. 验证运营商对应用的授权状态
3. 验证玩家数量在应用允许范围内
4. 计算费用
5. 检查账户余额是否充足
6. 返回授权资格信息（**不扣费**）

**请求参数**:

```json
{
  "app_code": "APP_20251030_001",
  "site_id": "site_beijing_001",
  "player_count": 5,
  "headset_ids": ["headset_001", "headset_002"]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| app_code | string | 是 | 应用代码（最小长度1） |
| site_id | string | 是 | 运营点ID（支持带"site_"前缀或纯UUID格式） |
| player_count | integer | 是 | 玩家数量（范围：1-100） |
| headset_ids | array[string] | 否 | 头显设备ID列表（用于记录和统计） |

**成功响应** (HTTP 200):

```json
{
  "success": true,
  "data": {
    "can_authorize": true,
    "app_code": "APP_20251030_001",
    "app_name": "太空射击",
    "player_count": 5,
    "unit_price": "10.00",
    "total_cost": "50.00",
    "current_balance": "450.00"
  }
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| can_authorize | boolean | 是否可以授权 |
| app_code | string | 应用代码 |
| app_name | string | 应用名称 |
| player_count | integer | 玩家数量 |
| unit_price | string | 单人价格（保留2位小数） |
| total_cost | string | 总费用（保留2位小数） |
| current_balance | string | 当前账户余额（保留2位小数） |

**失败响应** (HTTP 402 余额不足):

```json
{
  "success": false,
  "error": {
    "error_code": "INSUFFICIENT_BALANCE",
    "message": "账户余额不足，当前余额: ¥30.00，需要: ¥50.00"
  }
}
```

**错误码**:

| HTTP状态码 | 错误代码 | 说明 |
|-----------|---------|------|
| 400 | - | 请求参数错误 |
| 401 | OPERATOR_NOT_FOUND | 认证失败（Token无效或过期） |
| 402 | INSUFFICIENT_BALANCE | 余额不足 |
| 403 | - | 应用未授权、账户已锁定、或使用了错误的Token类型（必须使用Headset Token） |
| 500 | - | 服务器内部错误 |

---

### 2. 游戏授权 (最重要)

**接口**: `POST /api/v1/auth/game/authorize`

**用途**: 头显Server请求游戏授权并扣费。这是最核心的接口，会执行实际的扣费操作。

**认证**: Bearer Token (Headset Token，24小时有效)

**业务逻辑**:
1. 验证Headset Token有效性
2. **检查幂等性**（基于业务键：operator + app + site + player_count + 时间窗口）
3. 验证运营商对应用的授权状态
4. 验证玩家数量在应用允许范围内
5. 计算费用：总费用 = 玩家数量 × 应用单人价格
6. 检查账户余额是否充足
7. 使用数据库事务扣费并创建使用记录
8. **服务器自动生成唯一的session_id**
9. 返回session_id和扣费信息

**请求头**:

```http
Authorization: Bearer {headset_token}
Content-Type: application/json
```

> ⚠️ **v2.1 重要变更**:
> - 移除了 `X-Session-ID` 请求头，服务器会自动生成 session_id
> - 实现了30秒业务键幂等性保护（相同运营商+应用+运营点+玩家数量）

**请求参数**:

```json
{
  "app_code": "APP_20251030_001",
  "site_id": "site_beijing_001",
  "player_count": 5,
  "headset_ids": ["headset_001", "headset_002", "headset_003", "headset_004", "headset_005"]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| app_code | string | 是 | 应用代码（最小长度1，与启动URL中的app_code一致） |
| site_id | string | 是 | 运营点ID（支持带"site_"前缀或纯UUID格式） |
| player_count | integer | 是 | 实际玩家数量（范围：1-100） |
| headset_ids | array[string] | 否 | 头显设备ID列表（用于记录和统计） |

**成功响应** (HTTP 200):

```json
{
  "success": true,
  "data": {
    "session_id": "op_12345_1704067200000_a1b2c3d4e5f6g7h8",
    "app_name": "太空射击",
    "player_count": 5,
    "unit_price": "10.00",
    "total_cost": "50.00",
    "balance_after": "450.00",
    "authorized_at": "2025-01-01T12:30:00.000Z"
  }
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| session_id | string | **[v2.1]** 服务器生成的会话ID，格式：`{operatorId}_{13位毫秒时间戳}_{16位随机字符}` |
| app_name | string | 应用名称 |
| player_count | integer | 玩家数量 |
| unit_price | string | 单人价格（保留2位小数） |
| total_cost | string | 本次扣费总额（保留2位小数） |
| balance_after | string | 扣费后账户余额（保留2位小数） |
| authorized_at | datetime | 授权时间（ISO 8601格式） |

**session_id格式说明**:
- 正则表达式: `^[a-zA-Z0-9\-]+_\d{13}_[a-zA-Z0-9]{16}$`
- 结构: `{operatorId}_{13位毫秒时间戳}_{16位随机字符}`
- 示例: `op_12345_1704067200000_a1b2c3d4e5f6g7h8`
- 用途: 用于后续上传游戏会话数据

**失败响应** (HTTP 402 余额不足):

```json
{
  "success": false,
  "error": {
    "error_code": "INSUFFICIENT_BALANCE",
    "message": "账户余额不足，当前余额: ¥30.00，需要: ¥50.00"
  }
}
```

**错误码**:

| HTTP状态码 | 错误代码 | 说明 | 处理建议 |
|-----------|---------|------|----------|
| 200 | - | 成功 | 正常处理响应 |
| 400 | INVALID_SITE_ID | 请求参数错误（玩家数量超出范围等） | 检查请求参数 |
| 401 | OPERATOR_NOT_FOUND | 认证失败（Headset Token无效或过期） | 重新获取Token |
| 402 | INSUFFICIENT_BALANCE | 余额不足 | 提示运营商充值 |
| 403 | - | 应用未授权、账户已锁定、或使用了错误的Token类型 | 检查授权状态 |
| 409 | - | 会话重复（幂等性保护，返回已授权信息） | 使用返回的信息继续 |
| 500 | UPLOAD_FAILED | 服务器内部错误 | 稍后重试 |

**幂等性保护机制**:
- **业务键组成**: operator_id + application_id + site_id + player_count
- **时间窗口**: 30秒
- **行为**: 30秒内相同业务键的重复请求会返回**相同的授权结果**（HTTP 200）
- **特点**: 不会重复扣费，适用于网络重试场景
- **注意**: 不同于传统的session_id幂等性，这是基于业务语义的幂等性保护

---

### 3. 上传游戏会话数据 (可选)

**接口**: `POST /api/v1/auth/game/session/upload`

> ⚠️ **路径更正**: 注意是 `/session/upload` (单数)，不是 `/sessions/upload`

**用途**: 游戏结束后上传Session的详细信息，包括游戏时间、过程信息和头显设备记录。

**认证**: Bearer Token (Headset Token，24小时有效)

**业务逻辑**:
1. 验证Bearer Token有效性
2. 根据session_id查找授权记录
3. 创建游戏Session记录（**覆盖模式**：删除旧记录后创建新记录）
4. 为每个头显设备创建/更新记录（自动注册新设备，更新已有设备的device_name）

**请求参数**:

```json
{
  "session_id": "op_12345_1704067200000_a1b2c3d4e5f6g7h8",
  "start_time": "2025-01-01T12:30:00.000Z",
  "end_time": "2025-01-01T13:00:00.000Z",
  "process_info": "total_rounds: 5\nwinners: [player1, player3]\naverage_score: 1450",
  "headset_devices": [
    {
      "device_id": "headset_001",
      "device_name": "头显设备1",
      "start_time": "2025-01-01T12:30:00.000Z",
      "end_time": "2025-01-01T13:00:00.000Z",
      "process_info": "score: 1500\nkills: 10\ndeaths: 3"
    },
    {
      "device_id": "headset_002",
      "device_name": "头显设备2",
      "start_time": "2025-01-01T12:30:15.000Z",
      "end_time": "2025-01-01T12:59:45.000Z",
      "process_info": "score: 1400\nkills: 8\ndeaths: 5"
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | 会话ID（从授权API响应中获取） |
| start_time | datetime | 否 | 游戏开始时间（ISO 8601格式） |
| end_time | datetime | 否 | 游戏结束时间（ISO 8601格式） |
| process_info | string | 否 | 游戏过程信息（YAML/JSON格式，用于记录游戏数据） |
| headset_devices | array | 否 | 头显设备记录列表 |
| headset_devices[].device_id | string | 是 | 设备ID（必填） |
| headset_devices[].device_name | string | 否 | 设备名称（首次上传或更新时提供） |
| headset_devices[].start_time | datetime | 否 | 设备开始时间（ISO 8601格式） |
| headset_devices[].end_time | datetime | 否 | 设备结束时间（ISO 8601格式） |
| headset_devices[].process_info | string | 否 | 设备过程信息（YAML/JSON格式） |

**覆盖模式说明**:
- 当同一 `session_id` 再次上传时，系统会**删除旧的GameSession和HeadsetGameRecord记录**，然后创建新记录
- 这确保数据为最新完整信息，而非追加模式
- 适用场景：游戏崩溃后重新上传、数据修正等

**头显设备自动管理**:
- 如果设备（通过device_id识别）不存在：创建新的HeadsetDevice记录
- 如果设备已存在：
  - 如果提供了新的`device_name`，则更新设备名称
  - 更新`last_used_at`时间戳为游戏结束时间或当前时间

**成功响应** (HTTP 200):

```json
{
  "success": true,
  "message": "游戏信息上传成功"
}
```

**错误响应**:

| HTTP状态码 | 错误代码 | 说明 |
|-----------|---------|------|
| 200 | - | 成功 |
| 400 | - | 请求参数错误 |
| 401 | - | 认证失败（Token无效） |
| 403 | SESSION_ACCESS_DENIED | 无权访问此会话 |
| 404 | SESSION_NOT_FOUND | 会话不存在 |
| 500 | UPLOAD_FAILED | 服务器内部错误 |
