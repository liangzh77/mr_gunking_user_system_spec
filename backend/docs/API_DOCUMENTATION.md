# API 文档

MR 游戏运营管理系统后端 API 参考文档。

## 目录

- [API 概述](#api-概述)
- [认证方式](#认证方式)
- [错误处理](#错误处理)
- [速率限制](#速率限制)
- [API 端点](#api-端点)
  - [管理员认证](#管理员认证)
  - [运营商管理](#运营商管理)
  - [财务管理](#财务管理)
  - [系统管理](#系统管理)
- [数据模型](#数据模型)

---

## API 概述

### 基本信息

- **Base URL**: `https://api.example.com` (生产环境)
- **Base URL**: `http://localhost:8000` (开发环境)
- **API 版本**: v1
- **协议**: HTTPS (生产环境), HTTP (开发环境)
- **数据格式**: JSON
- **字符编码**: UTF-8

### 环境

| 环境 | Base URL | 说明 |
|------|---------|------|
| 生产 | `https://api.mr-game.com` | 正式环境 |
| 测试 | `https://test-api.mr-game.com` | 测试环境 |
| 开发 | `http://localhost:8000` | 本地开发 |

### 自动文档

- **Swagger UI**: `GET /api/docs` (仅开发/测试环境)
- **ReDoc**: `GET /api/redoc` (仅开发/测试环境)
- **OpenAPI Schema**: `GET /api/openapi.json` (仅开发/测试环境)

---

## 认证方式

系统支持两种认证方式：

### 1. JWT Token 认证（管理员）

管理员使用 JWT (JSON Web Token) 进行认证。

**获取 Token**:
```http
POST /v1/admin/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your_password"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**使用 Token**:
```http
GET /v1/admin/profile
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token 过期**:
- 有效期: 24 小时
- 刷新: 使用 `/v1/admin/refresh-token` 端点

### 2. API Key 认证（运营商）

运营商使用 API Key 进行认证。

**使用 API Key**:
```http
GET /v1/operator/balance
X-API-Key: your_api_key_here
```

**API Key 格式**:
- 长度: 64 字符
- 字符集: `[a-zA-Z0-9_-]`
- 示例: `api_1234567890abcdef_1234567890abcdef1234567890abcdef1234567890abcd`

**API Key 管理**:
- 申请: 通过管理后台提交申请
- 审核: 管理员审核通过后生成
- 重置: 联系管理员

---

## 错误处理

### 标准错误响应

所有错误响应遵循统一格式：

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "field": "Additional error details"
  }
}
```

### HTTP 状态码

| 状态码 | 说明 | 示例 |
|--------|------|------|
| 200 | 成功 | 查询成功 |
| 201 | 创建成功 | 资源创建成功 |
| 400 | 请求错误 | 参数验证失败 |
| 401 | 未认证 | Token 无效或过期 |
| 403 | 无权限 | 权限不足 |
| 404 | 未找到 | 资源不存在 |
| 409 | 冲突 | 用户名已存在 |
| 422 | 无法处理 | 数据验证失败 |
| 429 | 请求过多 | 超出速率限制 |
| 500 | 服务器错误 | 内部服务器错误 |

### 常见错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|----------|------|
| `INVALID_CREDENTIALS` | 401 | 用户名或密码错误 |
| `TOKEN_EXPIRED` | 401 | Token 已过期 |
| `INVALID_API_KEY` | 401 | API Key 无效 |
| `INSUFFICIENT_BALANCE` | 400 | 余额不足 |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 |
| `DUPLICATE_USERNAME` | 409 | 用户名已存在 |
| `RATE_LIMIT_EXCEEDED` | 429 | 超出速率限制 |
| `IP_BLOCKED` | 403 | IP 已被封禁 |

### 错误响应示例

**401 Unauthorized**:
```json
{
  "error": "INVALID_CREDENTIALS",
  "message": "Invalid username or password"
}
```

**422 Validation Error**:
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "details": [
    {
      "loc": ["body", "email"],
      "msg": "invalid email format",
      "type": "value_error.email"
    }
  ]
}
```

---

## 速率限制

### 限制规则

| 用户类型 | 限制 | 时间窗口 | 适用范围 |
|---------|------|---------|---------|
| IP 地址 | 100 次 | 1 分钟 | 全局 |
| 运营商 | 10 次 | 1 分钟 | 认证端点 |
| 管理员 | 20 次 | 1 分钟 | 敏感操作 |

### 响应头

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

### 超限响应

**429 Too Many Requests**:
```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Retry after 60 seconds",
  "retry_after": "60"
}
```

---

## API 端点

### 管理员认证

#### POST /v1/admin/login

管理员登录。

**请求**:
```json
{
  "username": "admin",
  "password": "secure_password"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**错误**:
- `401`: 用户名或密码错误
- `403`: IP 被封禁（登录失败次数过多）
- `429`: 请求过多

---

#### GET /v1/admin/profile

获取当前管理员信息。

**请求头**:
```http
Authorization: Bearer {token}
```

**响应**:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "username": "admin",
  "role": "super_admin",
  "email": "admin@example.com",
  "created_at": 1640995200
}
```

**错误**:
- `401`: Token 无效或过期

---

### 运营商管理

#### POST /v1/operator/authorize

运营商 API Key 授权（首次接入）。

**请求头**:
```http
X-API-Key: {api_key}
```

**请求**:
```json
{
  "app_id": "app_123456",
  "redirect_uri": "https://operator.example.com/callback"
}
```

**响应**:
```json
{
  "authorization_code": "auth_abc123...",
  "expires_in": 600,
  "redirect_url": "https://operator.example.com/callback?code=auth_abc123..."
}
```

**错误**:
- `401`: API Key 无效
- `403`: 运营商未激活

---

#### GET /v1/operator/balance

查询运营商余额。

**请求头**:
```http
X-API-Key: {api_key}
```

**响应**:
```json
{
  "operator_id": "op_123456",
  "balance": {
    "total_cents": 1000000,
    "total_yuan": "10000.00",
    "available_cents": 950000,
    "available_yuan": "9500.00",
    "frozen_cents": 50000,
    "frozen_yuan": "500.00"
  },
  "currency": "CNY",
  "updated_at": 1640995200
}
```

**错误**:
- `401`: API Key 无效
- `429`: 请求过多

---

### 财务管理

#### GET /v1/finance/dashboard

财务控制台仪表板数据（管理员）。

**请求头**:
```http
Authorization: Bearer {token}
```

**查询参数**:
- `start_date` (可选): 起始日期，格式 `YYYY-MM-DD`
- `end_date` (可选): 结束日期，格式 `YYYY-MM-DD`

**响应**:
```json
{
  "summary": {
    "total_revenue": "125000.00",
    "total_refunds": "5000.00",
    "pending_invoices": 15,
    "pending_refunds": 3
  },
  "top_customers": [
    {
      "operator_id": "op_123",
      "operator_name": "运营商A",
      "consumption_amount": "50000.00",
      "rank": 1
    }
  ],
  "recent_transactions": [...]
}
```

**错误**:
- `401`: Token 无效
- `403`: 权限不足（需要财务角色）

---

#### POST /v1/finance/invoice/apply

申请发票（运营商）。

**请求头**:
```http
X-API-Key: {api_key}
```

**请求**:
```json
{
  "amount_cents": 100000,
  "invoice_type": "vat_special",
  "tax_id": "91110000XXXXXXXXX",
  "company_name": "XX科技有限公司",
  "company_address": "北京市朝阳区...",
  "company_phone": "010-12345678",
  "bank_name": "中国银行北京分行",
  "bank_account": "1234567890123456789"
}
```

**响应**:
```json
{
  "invoice_id": "inv_123456",
  "status": "pending",
  "amount": "1000.00",
  "created_at": 1640995200,
  "estimated_days": 7
}
```

**错误**:
- `400`: 金额超出可开票额度
- `401`: API Key 无效

---

#### GET /v1/finance/invoice/list

查询发票列表（运营商）。

**请求头**:
```http
X-API-Key: {api_key}
```

**查询参数**:
- `status` (可选): 发票状态，`pending` | `approved` | `rejected`
- `page` (可选): 页码，默认 1
- `page_size` (可选): 每页数量，默认 20

**响应**:
```json
{
  "invoices": [
    {
      "invoice_id": "inv_123",
      "amount": "1000.00",
      "status": "approved",
      "created_at": 1640995200,
      "approved_at": 1640998800
    }
  ],
  "pagination": {
    "total": 50,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  }
}
```

---

### 系统管理

#### GET /health

健康检查端点。

**响应**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": 1640995200,
  "checks": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

---

#### GET /metrics

Prometheus 监控指标（仅内网访问）。

**响应**:
```text
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",path="/v1/operator/balance",status="200"} 1234
...
```

---

## 数据模型

### 余额 (Balance)

```json
{
  "total_cents": 1000000,
  "total_yuan": "10000.00",
  "available_cents": 950000,
  "available_yuan": "9500.00",
  "frozen_cents": 50000,
  "frozen_yuan": "500.00"
}
```

**字段说明**:
- `total_cents`: 总余额（分）
- `total_yuan`: 总余额（元，字符串格式）
- `available_cents`: 可用余额（分）
- `frozen_cents`: 冻结余额（分）

---

### 交易记录 (Transaction)

```json
{
  "transaction_id": "tx_123456",
  "operator_id": "op_123",
  "type": "recharge",
  "amount_cents": 100000,
  "amount_yuan": "1000.00",
  "balance_after_cents": 1100000,
  "description": "管理员充值",
  "created_at": 1640995200
}
```

**交易类型**:
- `recharge`: 充值
- `consumption`: 消费
- `refund`: 退款
- `adjustment`: 调整

---

### 发票记录 (Invoice)

```json
{
  "invoice_id": "inv_123456",
  "operator_id": "op_123",
  "amount_cents": 100000,
  "amount_yuan": "1000.00",
  "invoice_type": "vat_special",
  "status": "approved",
  "tax_id": "91110000XXXXXXXXX",
  "company_name": "XX科技有限公司",
  "pdf_url": "https://cdn.example.com/invoices/inv_123.pdf",
  "created_at": 1640995200,
  "approved_at": 1640998800
}
```

**发票类型**:
- `vat_normal`: 增值税普通发票
- `vat_special`: 增值税专用发票

**发票状态**:
- `pending`: 待审核
- `approved`: 已通过
- `rejected`: 已拒绝

---

### 退款记录 (Refund)

```json
{
  "refund_id": "ref_123456",
  "operator_id": "op_123",
  "amount_cents": 50000,
  "amount_yuan": "500.00",
  "reason": "服务终止",
  "status": "approved",
  "created_at": 1640995200,
  "processed_at": 1640998800
}
```

**退款状态**:
- `pending`: 待审核
- `approved`: 已通过
- `rejected`: 已拒绝
- `completed`: 已完成

---

## 最佳实践

### 1. 安全

- ✅ 始终使用 HTTPS（生产环境）
- ✅ 安全存储 API Key 和 Token
- ✅ 定期轮换 API Key
- ✅ 不在 URL 中传递敏感信息
- ✅ 实施请求签名（高安全场景）

### 2. 性能

- ✅ 使用分页查询大量数据
- ✅ 缓存频繁访问的数据
- ✅ 批量请求替代多次单独请求
- ✅ 设置合理的超时时间

### 3. 错误处理

- ✅ 检查 HTTP 状态码
- ✅ 解析 error_code 做精确处理
- ✅ 实施重试机制（幂等接口）
- ✅ 记录错误日志

### 4. 速率限制

- ✅ 检查 X-RateLimit-Remaining 响应头
- ✅ 实施指数退避重试
- ✅ 缓存数据减少 API 调用

---

## 支持

### 技术支持

- **邮箱**: support@example.com
- **文档**: https://docs.example.com
- **状态页**: https://status.example.com

### 变更日志

查看 [CHANGELOG.md](../CHANGELOG.md) 了解 API 变更历史。

### SDK 和工具

- **Python SDK**: `pip install mr-game-sdk`
- **Postman Collection**: [下载](https://example.com/postman.json)
- **OpenAPI Spec**: `/api/openapi.json`

---

## 附录

### 时区

所有时间戳使用 **Unix 时间戳（秒）**，UTC 时区。

### 金额格式

- 存储: 整数（分）
- 显示: 字符串（元，保留2位小数）
- 示例: `100000` (分) = `"1000.00"` (元)

### 日期格式

- ISO 8601: `YYYY-MM-DDTHH:mm:ss.sssZ`
- 日期: `YYYY-MM-DD`
- 时间: `HH:mm:ss`

### 分页

标准分页参数：
- `page`: 页码（从 1 开始）
- `page_size`: 每页数量（默认 20，最大 100）

标准分页响应：
```json
{
  "data": [...],
  "pagination": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```
