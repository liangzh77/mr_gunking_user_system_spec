# API变更说明 v2.0

**版本**: v2.0
**更新时间**: 2025-11-02
**影响范围**: 头显Server集成

---

## 概述

本次更新对游戏授权API进行了重要优化，简化了认证流程和接口参数，提升了安全性和易用性。

## 主要变更

### 1. 统一使用app_code代替app_id

**变更原因**:
- 启动URL传递的是`app_code`（业务标识），但API要求`app_id`（UUID）
- 导致头显Server需要维护`app_code → app_id`的映射关系
- 增加了集成复杂度

**变更内容**:

#### 游戏授权接口 (POST /v1/auth/game/authorize)

**之前**:
```json
{
  "app_id": "32d012d9-b798-4f78-8e96-3ce87bbbd3f5",
  "site_id": "uuid-here",
  "player_count": 5
}
```

**现在**:
```json
{
  "app_code": "APP_20251030_001",
  "site_id": "uuid-here",
  "player_count": 5
}
```

#### 游戏预授权接口 (POST /v1/auth/game/pre-authorize)

**之前**:
```json
{
  "app_id": "32d012d9-b798-4f78-8e96-3ce87bbbd3f5",
  "site_id": "uuid-here",
  "estimated_player_count": 5
}
```

**现在**:
```json
{
  "app_code": "APP_20251030_001",
  "site_id": "uuid-here",
  "estimated_player_count": 5
}
```

**预授权响应增加app_code字段**:
```json
{
  "success": true,
  "data": {
    "can_authorize": true,
    "app_code": "APP_20251030_001",  // ← 新增
    "app_name": "太空射击",
    "unit_price": "10.00",
    ...
  }
}
```

**优势**:
- ✅ 头显Server可直接使用启动URL中的`app_code`
- ✅ 无需维护ID映射表
- ✅ API更直观易懂

---

### 2. 统一使用Headset Token认证

**变更原因**:
- 预授权接口使用Headset Token，但正式授权使用API Key
- 头显Server需要维护两套认证机制
- API Key是长期密钥，安全性不如短期Token

**变更内容**:

#### 游戏授权接口 (POST /v1/auth/game/authorize)

**之前 (API Key认证)**:
```http
POST /v1/auth/game/authorize
X-API-Key: your_64_char_api_key_here
X-Session-ID: session_id_here
X-Timestamp: 1730451234
X-Signature: hmac_sha256_signature_here
Content-Type: application/json

{
  "app_id": "uuid-here",
  "site_id": "uuid-here",
  "player_count": 5
}
```

**现在 (Headset Token认证)**:
```http
POST /v1/auth/game/authorize
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
X-Session-ID: {operator_id}_{timestamp_ms}_{random16}
Content-Type: application/json

{
  "app_code": "APP_20251030_001",
  "site_id": "uuid-here",
  "player_count": 5
}
```

**移除的请求头**:
- ❌ `X-API-Key` - 不再使用
- ❌ `X-Timestamp` - 不再使用
- ❌ `X-Signature` - 不再使用HMAC签名

**保留的请求头**:
- ✅ `Authorization: Bearer {headset_token}` - 24小时有效的JWT Token
- ✅ `X-Session-ID` - 会话ID（幂等性保护）

**Headset Token获取方式**:
- 运营商在Web后台点击"启动应用"时自动生成
- 通过自定义协议URL传递：`mrgun-{exe_name}://start?token={headset_token}&app_code={app_code}&site_id={site_id}`

**优势**:
- ✅ 统一认证方式 - 预授权和正式授权都用Headset Token
- ✅ 简化实现 - 只需维护一个Token
- ✅ 更安全 - Token 24小时自动过期
- ✅ 更简洁 - 只需2个请求头，无需HMAC签名计算

---

## 迁移指南

### 头显Server代码更新

#### Python示例

**之前**:
```python
# 需要维护API Key
api_key = "your_64_char_api_key"

# 需要计算HMAC签名
import hmac
import hashlib
timestamp = int(time.time())
signature = hmac.new(
    api_key.encode(),
    f"{session_id}{timestamp}{json_body}".encode(),
    hashlib.sha256
).hexdigest()

# 使用app_id
response = requests.post(
    url,
    headers={
        "X-API-Key": api_key,
        "X-Session-ID": session_id,
        "X-Timestamp": str(timestamp),
        "X-Signature": signature
    },
    json={
        "app_id": "uuid-from-mapping",
        "site_id": site_id,
        "player_count": 5
    }
)
```

**现在**:
```python
# 从启动URL获取Token和app_code
launch_url = "mrgun-HeadsetServer://start?token=xxx&app_code=APP_001&site_id=xxx"
params = parse_url(launch_url)

# 直接使用，无需签名计算
response = requests.post(
    url,
    headers={
        "Authorization": f"Bearer {params['token']}",
        "X-Session-ID": session_id
    },
    json={
        "app_code": params['app_code'],  # 直接使用
        "site_id": params['site_id'],
        "player_count": 5
    }
)
```

#### C#示例

**之前**:
```csharp
// 需要计算HMAC签名
var timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
var signature = ComputeHmacSha256(apiKey, $"{sessionId}{timestamp}{jsonBody}");

request.Headers.Add("X-API-Key", apiKey);
request.Headers.Add("X-Timestamp", timestamp.ToString());
request.Headers.Add("X-Signature", signature);

// 使用app_id
var payload = new { app_id = appIdFromMapping, site_id = siteId, player_count = 5 };
```

**现在**:
```csharp
// 直接使用Token
request.Headers.Add("Authorization", $"Bearer {headsetToken}");
request.Headers.Add("X-Session-ID", sessionId);

// 直接使用app_code
var payload = new { app_code = appCode, site_id = siteId, player_count = 5 };
```

---

## 错误码更新

### 新增错误码

| 错误码 | HTTP状态 | 说明 |
|--------|----------|------|
| `APP_NOT_FOUND` | 404 | 应用代码不存在 |

### 修改的错误码

| 旧错误码 | 新错误码 | HTTP状态 | 说明 |
|---------|---------|----------|------|
| `INVALID_APP_ID` | `INVALID_APP_CODE` | 400 | 应用标识格式错误 |

---

## 向后兼容性

⚠️ **重要提示**: 本次更新**不兼容**旧版本API。

### 影响范围
- 所有使用游戏授权API的头显Server客户端
- 所有调用预授权API的客户端

### 升级要求
1. 更新请求参数：`app_id` → `app_code`
2. 更新认证方式：API Key → Headset Token
3. 移除HMAC签名计算代码
4. 从启动URL获取Token和app_code

### 升级时间表
- **测试环境**: 已上线 (2025-11-02)
- **生产环境**: 待定（需协调所有头显Server客户端升级）

---

## API Key现状

### API Key的新角色

API Key **不再用于API认证**，现在仅作为：
1. 运营商账户的唯一标识符
2. 运营商信息展示（如在后台界面显示）

### API Key管理

- ✅ 仍保留在运营商账户中
- ✅ 仍可在管理后台查看和重置
- ❌ 不再用于游戏授权API认证
- ❌ 不再需要在头显Server中配置

---

## 常见问题 (FAQ)

### Q1: 为什么要改用app_code？

**A**: 启动URL已经包含`app_code`，头显Server直接使用即可，无需额外查询或维护映射表。这简化了集成流程。

### Q2: Headset Token在哪里获取？

**A**: 运营商在Web后台点击"启动应用"时，系统自动生成Headset Token并通过自定义协议URL传递给头显Server。Token有效期24小时。

### Q3: 旧的API Key还能用吗？

**A**: API Key仍然存在于系统中，但**不再用于游戏授权API认证**。如果您使用旧版本API，将收到401认证失败错误。

### Q4: 会话ID格式有变化吗？

**A**: 会话ID格式已更新为 `{operatorId}_{13位毫秒时间戳}_{16位随机字符}`。这个格式提供了更好的唯一性保证和时间戳验证能力。

### Q5: 如何测试新版API？

**A**:
1. 登录运营商后台
2. 点击"启动应用"获取启动URL
3. 从URL中提取Token和app_code
4. 使用Postman等工具测试，设置Authorization头

---

## 技术支持

如有疑问，请联系：
- **邮箱**: support@chu-jiao.com
- **文档**: `docs/HEADSET_SERVER_API.md`
- **项目地址**: https://github.com/liangzh77/mr_gunking_user_system_spec

---

**文档版本**: v2.0
**发布日期**: 2025-11-02
**维护者**: 后端开发团队
