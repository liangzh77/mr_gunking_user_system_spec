# MR游戏运营管理系统 - OpenAPI 3.0 契约文档

## 概述

本目录包含MR游戏运营管理系统的完整RESTful API契约定义，基于OpenAPI 3.0.3规范。

## 文件结构

```
contracts/
├── openapi.yaml       # 主契约文件（入口）
├── auth.yaml          # 授权相关接口
├── operator.yaml      # 运营商接口
├── admin.yaml         # 管理员接口
└── finance.yaml       # 财务接口
```

## 契约文件说明

### 1. openapi.yaml - 主契约文件

**职责**：
- 定义API基本信息（版本、服务器地址、联系方式）
- 定义公共组件（安全方案、通用Schema、公共参数、通用响应）
- 通过引用方式整合其他模块化契约文件

**核心内容**：
- **安全方案**：
  - `ApiKeyAuth`: API Key认证（头显Server）
  - `HmacAuth`: HMAC-SHA256签名认证（头显Server游戏授权）
  - `BearerAuth`: JWT Token认证（运营商/管理员/财务Web端）

- **公共Schema**：
  - `ErrorResponse`: 标准错误响应
  - `SuccessResponse`: 标准成功响应
  - `PaginatedResponse`: 分页响应模板

- **公共参数**：
  - 分页参数（page, page_size）
  - 时间范围参数（start_time, end_time）
  - 排序参数（sort_by, sort_order）

### 2. auth.yaml - 授权相关接口

**包含接口**：
- `POST /v1/auth/game/authorize` - **游戏授权请求**（核心接口）
  - 头显Server请求游戏授权并扣费
  - 需要API Key + HMAC签名 + 时间戳 + 会话ID
  - 支持幂等性（相同会话ID不重复扣费）

- `POST /v1/auth/operators/register` - 运营商注册
- `POST /v1/auth/operators/login` - 运营商登录
- `POST /v1/auth/operators/logout` - 运营商退出
- `POST /v1/auth/admin/login` - 管理员登录
- `POST /v1/auth/finance/login` - 财务人员登录

**关键特性**：
- HMAC签名验证（防篡改）
- 时间戳验证（防重放攻击，5分钟有效期）
- 会话ID幂等性保证

### 3. operator.yaml - 运营商接口

**功能模块**（共23个接口）：

#### 账户管理
- `GET /v1/operators/me` - 获取当前运营商信息
- `PUT /v1/operators/me` - 更新运营商信息
- `DELETE /v1/operators/me` - 注销账户（逻辑删除）
- `POST /v1/operators/me/api-key/regenerate` - 重新生成API Key

#### 财务管理
- `GET /v1/operators/me/balance` - 查询账户余额
- `POST /v1/operators/me/recharge` - 发起充值（微信/支付宝）
- `GET /v1/operators/me/transactions` - 查询交易记录
- `POST /v1/operators/me/refunds` - 申请退款
- `GET /v1/operators/me/refunds` - 查询退款申请列表
- `POST /v1/operators/me/invoices` - 申请开具发票
- `GET /v1/operators/me/invoices` - 查询发票列表

#### 运营点管理
- `GET /v1/operators/me/sites` - 查询运营点列表
- `POST /v1/operators/me/sites` - 创建运营点
- `PUT /v1/operators/me/sites/{site_id}` - 更新运营点
- `DELETE /v1/operators/me/sites/{site_id}` - 删除运营点

#### 应用授权管理
- `GET /v1/operators/me/authorized-apps` - 查询已授权应用列表
- `POST /v1/operators/me/app-requests` - 申请应用授权
- `GET /v1/operators/me/app-requests` - 查询申请列表

#### 使用记录与统计
- `GET /v1/operators/me/usage-records` - 查询使用记录
- `GET /v1/operators/me/statistics/consumption` - 消费统计（按日/周/月）
- `GET /v1/operators/me/statistics/by-app` - 按应用统计
- `GET /v1/operators/me/statistics/by-site` - 按运营点统计

#### 消息通知
- `GET /v1/operators/me/messages` - 查询消息列表
- `PUT /v1/operators/me/messages/{message_id}/read` - 标记已读

### 4. admin.yaml - 管理员接口

**功能模块**（共16个接口）：

#### 运营商管理
- `GET /v1/admin/operators` - 查询运营商列表
- `POST /v1/admin/operators` - 创建运营商
- `GET /v1/admin/operators/{operator_id}` - 查询运营商详情
- `PUT /v1/admin/operators/{operator_id}` - 更新运营商信息
- `PUT /v1/admin/operators/{operator_id}/category` - 调整客户分类
- `GET /v1/admin/operators/{operator_id}/api-key` - 查看API Key
- `POST /v1/admin/operators/{operator_id}/api-key/reset` - 强制重置API Key

#### 应用管理
- `GET /v1/admin/applications` - 查询应用列表
- `POST /v1/admin/applications` - 创建应用
- `PUT /v1/admin/applications/{app_id}` - 更新应用信息
- `PUT /v1/admin/applications/{app_id}/price` - 调整价格

#### 应用授权审批
- `GET /v1/admin/app-requests` - 查询待审批申请
- `POST /v1/admin/app-requests/{request_id}/approve` - 批准申请
- `POST /v1/admin/app-requests/{request_id}/reject` - 拒绝申请
- `POST /v1/admin/authorizations` - 直接为运营商授权应用

#### 系统公告
- `POST /v1/admin/announcements` - 发布公告

### 5. finance.yaml - 财务接口

**功能模块**（共14个接口）：

#### 财务仪表盘
- `GET /v1/finance/dashboard` - 今日收入概览
- `GET /v1/finance/dashboard/trends` - 本月趋势
- `GET /v1/finance/top-customers` - TOP客户列表
- `GET /v1/finance/customers/{operator_id}/details` - 客户详细财务信息

#### 退款审核
- `GET /v1/finance/refunds` - 查询待审核退款
- `GET /v1/finance/refunds/{refund_id}` - 查询退款详情
- `POST /v1/finance/refunds/{refund_id}/approve` - 批准退款
- `POST /v1/finance/refunds/{refund_id}/reject` - 拒绝退款

#### 发票审核
- `GET /v1/finance/invoices` - 查询待审核发票
- `POST /v1/finance/invoices/{invoice_id}/approve` - 批准发票

#### 财务报表
- `POST /v1/finance/reports/generate` - 生成报表
- `GET /v1/finance/reports` - 查询历史报表
- `GET /v1/finance/reports/{report_id}/download` - 下载报表

#### 操作审计
- `GET /v1/finance/audit-logs` - 查询操作日志

## 使用指南

### 1. 查看完整契约

使用OpenAPI工具查看完整契约：

```bash
# 使用Swagger UI（在线工具）
https://editor.swagger.io/

# 使用Redoc（命令行工具）
npx @redocly/cli preview-docs openapi.yaml

# 使用Stoplight Studio（桌面应用）
# 下载并导入openapi.yaml
```

### 2. 生成API文档

```bash
# 生成静态HTML文档
npx @redocly/cli build-docs openapi.yaml -o index.html

# 生成Postman集合
npx openapi-to-postmanv2 -s openapi.yaml -o postman_collection.json
```

### 3. 生成服务端代码

```bash
# 生成FastAPI服务端代码（Python）
openapi-generator-cli generate \
  -i openapi.yaml \
  -g python-fastapi \
  -o ../server

# 生成TypeScript客户端代码
openapi-generator-cli generate \
  -i openapi.yaml \
  -g typescript-axios \
  -o ../client
```

### 4. 验证契约一致性

```bash
# 验证YAML语法和OpenAPI规范
npx @redocly/cli lint openapi.yaml
```

## API设计规范

### 1. URL版本控制

所有API路径以`/v1`开头，便于后续版本迭代：

```
https://api.mrgame.example.com/v1/auth/game/authorize
```

### 2. 认证方案

#### 头显Server（游戏授权）

使用**API Key + HMAC签名**：

```http
POST /v1/auth/game/authorize
X-Api-Key: a1b2c3d4...（64位）
X-Signature: Jz3kL9mN2pQ5rS8tU1vW4xY7zA+bC/dE=
X-Timestamp: 1704067200
X-Session-ID: op_12345_1704067200_a1b2c3d4e5f6g7h8
```

**签名计算**：
```python
import hmac
import hashlib
import base64

# 待签名字符串
message = f"{timestamp}\n{method}\n{path}\n{json_body}"

# 计算HMAC-SHA256
signature = hmac.new(
    api_key.encode(),
    message.encode(),
    hashlib.sha256
).digest()

# Base64编码
signature_b64 = base64.b64encode(signature).decode()
```

#### 运营商/管理员/财务（Web端）

使用**JWT Bearer Token**：

```http
GET /v1/operators/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. 错误码标准

所有错误响应遵循统一格式：

```json
{
  "error_code": "INSUFFICIENT_BALANCE",
  "message": "账户余额不足，当前余额: 30.00元，需要: 50.00元",
  "details": {
    "current_balance": "30.00",
    "required_amount": "50.00",
    "shortage": "20.00"
  }
}
```

**错误码枚举**：
- `UNAUTHORIZED` - 认证失败
- `INSUFFICIENT_BALANCE` - 余额不足
- `APP_NOT_AUTHORIZED` - 应用未授权
- `PLAYER_COUNT_OUT_OF_RANGE` - 玩家数量超出范围
- `SESSION_DUPLICATE` - 会话重复
- `INVALID_API_KEY` - API Key无效
- `INVALID_SIGNATURE` - HMAC签名无效
- `TIMESTAMP_EXPIRED` - 时间戳过期
- `RATE_LIMIT_EXCEEDED` - 请求频率超限
- `INTERNAL_ERROR` - 服务器内部错误

### 4. 分页标准

所有列表接口遵循统一分页格式：

**请求**：
```http
GET /v1/operators/me/usage-records?page=1&page_size=20
```

**响应**：
```json
{
  "page": 1,
  "page_size": 20,
  "total": 100,
  "items": [...]
}
```

### 5. 时间格式

所有时间字段使用ISO 8601格式（UTC时区）：

```json
{
  "created_at": "2025-01-15T12:30:00.000Z"
}
```

### 6. 金额格式

所有金额字段使用**字符串格式**（避免浮点精度问题）：

```json
{
  "balance": "1234.56",
  "total_cost": "50.00"
}
```

## 核心业务流程

### 流程1：游戏授权与扣费

```mermaid
sequenceDiagram
    participant HS as 头显Server
    participant API as API服务器
    participant DB as 数据库

    HS->>API: POST /v1/auth/game/authorize
    Note right of HS: X-Api-Key + HMAC签名
    API->>API: 验证API Key
    API->>API: 验证HMAC签名
    API->>API: 验证时间戳（5分钟内）
    API->>DB: 检查会话ID是否存在
    alt 会话已存在
        API-->>HS: 返回已授权信息（幂等）
    else 会话不存在
        API->>DB: 验证应用授权
        API->>DB: 验证玩家数量范围
        API->>DB: 锁定账户余额（行级锁）
        API->>DB: 计算费用并扣费
        API->>DB: 创建使用记录
        API->>DB: 提交事务
        API-->>HS: 返回授权Token
    end
```

### 流程2：运营商充值

```mermaid
sequenceDiagram
    participant OP as 运营商
    participant API as API服务器
    participant PAY as 支付平台
    participant DB as 数据库

    OP->>API: POST /v1/operators/me/recharge
    API->>DB: 创建充值订单
    API-->>OP: 返回支付二维码
    OP->>PAY: 扫码支付
    PAY-->>API: 支付成功回调
    API->>DB: 更新余额
    API->>DB: 创建交易记录
    API-->>OP: 推送余额更新通知
```

### 流程3：退款审核

```mermaid
sequenceDiagram
    participant OP as 运营商
    participant API as API服务器
    participant FIN as 财务人员
    participant DB as 数据库

    OP->>API: POST /v1/operators/me/refunds
    API->>DB: 创建退款申请（记录当前余额）
    API-->>OP: 申请已提交
    FIN->>API: GET /v1/finance/refunds/{refund_id}
    API-->>FIN: 返回申请详情+实时余额
    FIN->>API: POST /v1/finance/refunds/{refund_id}/approve
    API->>DB: 重新计算可退余额
    API->>DB: 执行退款（余额清零）
    API->>DB: 记录审计日志
    API-->>FIN: 退款已处理
    API-->>OP: 推送退款成功通知
```

## 安全注意事项

### 1. API Key管理

- **存储**: 服务端使用AES-256加密存储
- **传输**: 仅通过HTTPS传输
- **泄露处理**: 支持强制重置，旧Key立即失效
- **显示规则**: 仅在生成时完整显示一次，后续仅显示部分字符

### 2. HMAC签名验证

- **时间窗口**: 仅接受5分钟内的时间戳
- **防重放**: 结合会话ID实现幂等性
- **签名算法**: HMAC-SHA256 + Base64编码

### 3. 频率限制

- **游戏授权**: 单运营商每分钟最多10次
- **登录接口**: 单IP每分钟最多5次
- **异常检测**: 短时间内多次失败自动锁定账户

### 4. 审计日志

- **财务操作**: 记录所有退款审核、发票审核、报表生成操作
- **敏感操作**: 记录API Key查看、重置操作
- **日志内容**: 操作类型、目标资源、操作详情、IP地址、User-Agent

## 测试建议

### 1. 单元测试

- 使用契约生成Mock数据
- 验证请求/响应Schema
- 测试错误码覆盖率

### 2. 集成测试

- 端到端业务流程测试（注册→充值→授权→退款）
- 并发扣费冲突测试
- 幂等性验证测试

### 3. 性能测试

- 游戏授权接口：目标响应时间 < 2秒（99%）
- 并发授权测试：10个并发请求无冲突
- 数据库压力测试：1000+并发查询

## 常见问题

### Q1: 如何处理会话ID冲突？

会话ID格式必须包含运营商ID前缀：`{operatorId}_{timestamp}_{random16}`

### Q2: 游戏中途崩溃如何处理？

不退费，启动时一次性扣费模式，崩溃风险由运营商承担。

### Q3: 应用调价时正在授权的游戏怎么办？

授权请求时获取并锁定价格，请求完成前不受调价影响。

### Q4: 退款审核期间运营商又消费了怎么办？

审核通过时重新计算当前余额并扣除，不退历史余额。

### Q5: 如何避免API Key泄露后的恶意扣费？

实施频率限制（每分钟10次）、异常IP检测、账户锁定机制。

## 更新日志

### v1.0.0 (2025-01-15)

- 初始版本发布
- 包含授权、运营商、管理员、财务四大模块
- 总计57个功能需求（FR-001 ~ FR-057）
- 69个API接口

## 联系方式

- **技术支持**: support@example.com
- **API文档**: https://docs.mrgame.example.com
- **问题反馈**: https://github.com/example/mr-game-api/issues
