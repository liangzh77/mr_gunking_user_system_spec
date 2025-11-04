# 开发测试指南

本文档说明如何在开发环境中测试头显Server API接口。

## 目录

- [问题背景](#问题背景)
- [解决方案](#解决方案)
- [使用步骤](#使用步骤)
- [注意事项](#注意事项)

---

## 问题背景

头显Server的三个核心API（预授权、授权、上传会话）要求使用 **Headset Token** 而不是普通的运营商登录token。

**为什么需要Headset Token?**
1. **更长的有效期**: Headset Token有效期24小时，而登录token只有30分钟
2. **更小的权限范围**: Headset Token只能访问游戏授权相关接口，安全性更高
3. **架构设计**: Token应该在启动应用时通过自定义协议传递给头显Server

**测试时的问题**:
- 在Swagger UI中测试时，没有通过自定义协议启动，无法获得Headset Token
- 如果使用登录token测试，会收到 `403 INVALID_TOKEN_TYPE` 错误

---

## 解决方案

我们提供了一个开发环境专用的API端点来生成测试用的Headset Token:

```
POST /api/v1/generate-headset-token
```

**特性**:
- ✅ 仅在开发环境可用（生产环境自动禁用）
- ✅ 需要运营商登录token认证
- ✅ 自动验证参数有效性
- ✅ 生成24小时有效期的Headset Token

---

## 使用步骤

### 步骤1: 运营商登录

在Swagger UI中调用登录接口获取登录token:

```http
POST /api/v1/auth/operators/login

Request Body:
{
  "username": "your_operator_username",
  "password": "your_password"
}

Response:
{
  "access_token": "eyJhbGc...",
  "token_type": "Bearer",
  "user_type": "operator"
}
```

### 步骤2: 在Swagger UI中认证

1. 点击页面右上角的 **"Authorize"** 按钮
2. 在弹出框中输入: `Bearer eyJhbGc...` (你的登录token)
3. 点击 **"Authorize"** 完成认证
4. 点击 **"Close"** 关闭弹窗

### 步骤3: 获取必要的参数

在Swagger UI中调用以下接口获取参数:

#### 3.1 获取 operator_id
```http
GET /api/v1/operators/profile

Response:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",  // 这就是 operator_id
  "username": "test_operator",
  ...
}
```

#### 3.2 获取 application_id
```http
GET /api/v1/operators/applications

Response:
{
  "data": [
    {
      "id": "app_660e8400-e29b-41d4-a716-446655440000",  // 这就是 application_id
      "name": "测试游戏",
      ...
    }
  ]
}
```

#### 3.3 获取 site_id
```http
GET /api/v1/operators/sites

Response:
{
  "data": [
    {
      "id": "site_770e8400-e29b-41d4-a716-446655440000",  // 这就是 site_id
      "name": "测试运营点",
      ...
    }
  ]
}
```

### 步骤4: 生成Headset Token

在Swagger UI中调用开发工具接口:

```http
POST /api/v1/generate-headset-token

Request Body:
{
  "operator_id": "550e8400-e29b-41d4-a716-446655440000",
  "application_id": "app_660e8400-e29b-41d4-a716-446655440000",
  "site_id": "site_770e8400-e29b-41d4-a716-446655440000"
}

Response:
{
  "headset_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 86400,
  "operator_id": "550e8400-e29b-41d4-a716-446655440000",
  "application_id": "app_660e8400-e29b-41d4-a716-446655440000",
  "site_id": "site_770e8400-e29b-41d4-a716-446655440000",
  "usage_example": {
    "description": "在Swagger UI中使用此token",
    "steps": [
      "1. 点击页面右上角的 'Authorize' 按钮",
      "2. 在弹出框中输入: Bearer {headset_token}",
      "3. 点击 'Authorize' 完成认证",
      "4. 现在可以测试头显Server API了"
    ],
    "test_endpoints": [
      "POST /api/v1/auth/game/pre-authorize - 预授权",
      "POST /api/v1/auth/game/authorize - 授权",
      "POST /api/v1/auth/game/session - 上传会话数据"
    ]
  }
}
```

### 步骤5: 使用Headset Token测试头显API

1. **重新认证**: 点击 **"Authorize"** 按钮
2. **替换token**: 输入 `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (你的headset_token)
3. **点击认证**: 点击 **"Authorize"** 完成认证
4. **测试接口**: 现在可以测试以下接口了:

#### 测试预授权
```http
POST /api/v1/auth/game/pre-authorize

Request Body:
{
  "application_id": "app_660e8400-e29b-41d4-a716-446655440000",
  "site_id": "site_770e8400-e29b-41d4-a716-446655440000",
  "player_count": 1
}
```

#### 测试授权
```http
POST /api/v1/auth/game/authorize

Request Body:
{
  "application_id": "app_660e8400-e29b-41d4-a716-446655440000",
  "site_id": "site_770e8400-e29b-41d4-a716-446655440000",
  "player_count": 1
}
```

#### 测试会话上传
```http
POST /api/v1/auth/game/session

Request Body:
{
  "session_id": "{从授权响应中获取的session_id}",
  "total_duration": 1800,
  "total_amount": 30.00
}
```

---

## 注意事项

### ⚠️ 仅限开发环境

此工具**仅在开发环境可用**。如果在生产环境调用，会收到以下错误:

```json
{
  "detail": {
    "error_code": "NOT_AVAILABLE_IN_PRODUCTION",
    "message": "此接口仅在开发环境可用，生产环境已禁用"
  }
}
```

### ⚠️ 参数验证

所有参数必须有效:
- `operator_id` 必须存在
- `application_id` 必须存在
- `site_id` 必须存在且属于该运营商

如果参数无效，会收到 `404 NOT_FOUND` 错误。

### ⚠️ Token有效期

- **Headset Token**: 24小时有效
- **登录Token**: 30分钟有效

测试时如果token过期，需要重新生成。

### ⚠️ 区分不同的Token

系统中有两种token，它们有不同的用途:

| Token类型 | 有效期 | 用途 | token payload中的type字段 |
|-----------|--------|------|--------------------------|
| 登录Token | 30分钟 | 访问运营商后台API | 无此字段 |
| Headset Token | 24小时 | 访问头显Server API | `"type": "headset"` |

**关键区别**:
- 头显Server的三个API **必须使用Headset Token**
- 其他运营商后台API使用登录Token
- 如果用错了token类型，会收到 `403 INVALID_TOKEN_TYPE` 错误

### 💡 快速切换Token

在Swagger UI中:
1. 测试运营商后台API时，使用**登录Token**
2. 测试头显Server API时，使用**Headset Token**
3. 通过 **"Authorize"** 按钮可以随时切换token

---

## 常见错误

### 错误1: 403 INVALID_TOKEN_TYPE

```json
{
  "detail": {
    "error_code": "INVALID_TOKEN_TYPE",
    "message": "This endpoint requires a headset token. Please use the token provided when launching the application."
  }
}
```

**原因**: 使用了登录token而不是Headset Token

**解决**: 使用本文档的步骤生成Headset Token并替换

### 错误2: 401 INVALID_TOKEN

```json
{
  "detail": {
    "error_code": "INVALID_TOKEN",
    "message": "Invalid or expired token"
  }
}
```

**原因**: Token已过期或格式错误

**解决**: 重新登录或重新生成Headset Token

### 错误3: 404 OPERATOR_NOT_FOUND

```json
{
  "detail": {
    "error_code": "OPERATOR_NOT_FOUND",
    "message": "运营商 xxx 不存在"
  }
}
```

**原因**: operator_id不存在或拼写错误

**解决**: 从 `GET /api/v1/operators/profile` 获取正确的operator_id

---

## 生产环境使用

在生产环境中，Headset Token应该通过自定义协议在启动应用时传递:

```
mrgun-{exe_name}://start?token={headset_token}&app_code={app_code}&site_id={site_id}
```

头显Server客户端应该:
1. 从启动参数中获取token
2. 将token保存到内存
3. 调用游戏授权API时使用此token

详细信息请参考: [头显Server API文档](HEADSET_SERVER_API.md)

---

**最后更新**: 2025-11-04
