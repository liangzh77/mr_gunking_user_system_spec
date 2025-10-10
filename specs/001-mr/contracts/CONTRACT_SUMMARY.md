# OpenAPI契约文件总结

## 生成时间

**生成日期**: 2025-10-10
**OpenAPI版本**: 3.0.3
**API版本**: v1.0.0

## 文件清单

| 文件名 | 行数 | 接口数 | 说明 |
|--------|------|--------|------|
| `openapi.yaml` | 419 | 0 | 主契约文件（公共组件定义） |
| `auth.yaml` | 653 | 6 | 授权认证相关接口 |
| `operator.yaml` | 1,714 | 24 | 运营商功能接口 |
| `admin.yaml` | 1,240 | 16 | 管理员功能接口 |
| `finance.yaml` | 1,208 | 14 | 财务功能接口 |
| `README.md` | 481 | - | 使用文档 |
| `validate.sh` | - | - | Linux/Mac验证脚本 |
| `validate.bat` | - | - | Windows验证脚本 |
| **总计** | **5,715** | **60** | **8个文件** |

## 接口统计

### 按模块统计

```
授权模块 (auth.yaml)          6个接口  (10.0%)
├── 游戏授权                  1个
├── 运营商认证                3个
├── 管理员认证                1个
└── 财务人员认证              1个

运营商模块 (operator.yaml)    24个接口 (40.0%)
├── 账户管理                  4个
├── 财务管理                  7个
├── 运营点管理                4个
├── 应用授权管理              3个
├── 使用统计                  4个
└── 消息通知                  2个

管理员模块 (admin.yaml)       16个接口 (26.7%)
├── 运营商管理                7个
├── 应用管理                  4个
├── 授权审批                  4个
└── 系统公告                  1个

财务模块 (finance.yaml)       14个接口 (23.3%)
├── 财务仪表盘                4个
├── 退款审核                  4个
├── 发票审核                  2个
├── 财务报表                  3个
└── 操作审计                  1个

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总计                         60个接口 (100%)
```

### 按HTTP方法统计

| HTTP方法 | 数量 | 百分比 | 典型用途 |
|---------|------|--------|---------|
| GET | 25 | 41.7% | 查询数据 |
| POST | 23 | 38.3% | 创建/执行操作 |
| PUT | 10 | 16.7% | 更新数据 |
| DELETE | 2 | 3.3% | 删除数据 |

### 按认证方式统计

| 认证方式 | 接口数 | 使用场景 |
|---------|--------|---------|
| BearerAuth (JWT) | 54 | 运营商/管理员/财务Web端 |
| ApiKeyAuth + HmacAuth | 1 | 头显Server游戏授权 |
| 无认证 | 5 | 注册/登录接口 |

## 核心Schema统计

### 公共Schema (openapi.yaml)

| Schema名称 | 用途 |
|-----------|------|
| `ErrorResponse` | 统一错误响应格式 |
| `SuccessResponse` | 统一成功响应格式 |
| `PaginatedResponse` | 分页响应模板 |

### 运营商Schema (operator.yaml)

| Schema名称 | 说明 |
|-----------|------|
| `OperatorProfile` | 运营商账户信息 |
| `Transaction` | 交易记录（充值/消费） |
| `RefundRequest` | 退款申请 |
| `Invoice` | 发票记录 |
| `OperationSite` | 运营点信息 |
| `AuthorizedApplication` | 已授权应用 |
| `AppRequest` | 应用授权申请 |
| `UsageRecord` | 游戏使用记录 |
| `Message` | 消息通知 |

### 管理员Schema (admin.yaml)

| Schema名称 | 说明 |
|-----------|------|
| `OperatorSummary` | 运营商摘要信息 |
| `OperatorDetails` | 运营商详细信息 |
| `Application` | 应用信息 |
| `AppRequestAdmin` | 应用授权申请（管理员视角） |

### 财务Schema (finance.yaml)

| Schema名称 | 说明 |
|-----------|------|
| `TopCustomer` | TOP客户信息 |
| `CustomerFinanceDetails` | 客户财务详情 |
| `RefundRequestFinance` | 退款申请（财务视角） |
| `InvoiceRequestFinance` | 发票申请（财务视角） |
| `FinanceReport` | 财务报表 |
| `AuditLog` | 审计日志 |

## 安全方案

### 1. API Key认证 (ApiKeyAuth)

**请求头**: `X-Api-Key`
**格式**: 64位随机字符串
**用途**: 头显Server身份识别

### 2. HMAC签名认证 (HmacAuth)

**请求头**:
- `X-Api-Key`: 运营商API Key
- `X-Signature`: HMAC-SHA256签名（Base64编码）
- `X-Timestamp`: Unix时间戳（秒）
- `X-Session-ID`: 会话ID（幂等性标识）

**签名算法**:
```
signature = HMAC-SHA256(api_key, message)
message = "{timestamp}\n{method}\n{path}\n{body}"
```

**安全特性**:
- 时间窗口验证（5分钟内有效）
- 防重放攻击（时间戳检查）
- 会话ID幂等性（防重复扣费）

### 3. JWT Bearer认证 (BearerAuth)

**请求头**: `Authorization: Bearer {token}`
**Token格式**: JWT
**有效期**: 30天（可配置）
**用途**: 运营商/管理员/财务Web端

**JWT Claims**:
- `sub`: 用户ID
- `role`: 用户角色（operator/admin/finance）
- `exp`: 过期时间
- `iat`: 签发时间

## 错误码标准

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| `UNAUTHORIZED` | 401 | 认证失败 |
| `PERMISSION_DENIED` | 403 | 无权限访问 |
| `INSUFFICIENT_BALANCE` | 402 | 余额不足 |
| `APP_NOT_AUTHORIZED` | 403 | 应用未授权 |
| `PLAYER_COUNT_OUT_OF_RANGE` | 400 | 玩家数量超出范围 |
| `SESSION_DUPLICATE` | 409 | 会话重复 |
| `INVALID_API_KEY` | 401 | API Key无效 |
| `INVALID_SIGNATURE` | 400 | HMAC签名无效 |
| `TIMESTAMP_EXPIRED` | 400 | 时间戳过期 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求频率超限 |
| `INVALID_PARAMS` | 400 | 请求参数错误 |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

## 数据格式标准

### 时间格式

**标准**: ISO 8601 (UTC时区)
**格式**: `YYYY-MM-DDTHH:mm:ss.sssZ`
**示例**: `2025-01-15T12:30:00.000Z`

### 金额格式

**类型**: 字符串（避免浮点精度问题）
**格式**: 最多2位小数
**示例**: `"1234.56"`, `"50.00"`

### 分页格式

**请求参数**:
- `page`: 页码（从1开始）
- `page_size`: 每页条数（默认20，最大100）

**响应格式**:
```json
{
  "page": 1,
  "page_size": 20,
  "total": 100,
  "items": [...]
}
```

## 业务规则摘要

### 游戏授权规则

1. **扣费公式**: `总费用 = 玩家数量 × 应用单人价格`
2. **幂等性**: 相同会话ID重复请求不重复扣费
3. **并发控制**: 使用数据库行级锁防止并发扣费冲突
4. **频率限制**: 单运营商每分钟最多10次授权请求

### 财务规则

1. **退款规则**: 仅退还当前账户余额，已消费金额不退
2. **退款审核**: 审核通过时重新计算可退余额（防审核期间新消费）
3. **充值渠道**: 支持微信支付、支付宝
4. **发票申请**: 开票金额不能超过已充值金额

### 应用授权规则

1. **授权方式**: 运营商申请 → 管理员审批 → 授权生效
2. **价格调整**: 新价格立即生效，不影响历史记录
3. **授权有效期**: 支持永久授权和指定日期授权
4. **玩家数量**: 每个应用定义最小/最大玩家数范围

### 客户分类规则

**自动判定标准**:
- **试用客户**: 0消费
- **普通客户**: 月消费 < 1000元
- **VIP客户**: 月消费 ≥ 10000元

**管理员可手动调整分类**

## 合规与审计

### 数据保留

- **逻辑删除**: 所有删除操作为逻辑删除，数据永久保留
- **历史记录**: 价格调整、授权变更等保留历史快照
- **审计日志**: 财务操作、敏感操作记录完整日志

### 审计内容

**财务操作审计**:
- 退款审核（批准/拒绝）
- 发票审核
- 报表生成
- API Key查看/重置

**日志字段**:
- 操作人ID和姓名
- 操作类型
- 目标资源ID
- 操作详情（JSON格式）
- IP地址
- User-Agent
- 操作时间

## 性能指标

### 响应时间目标

| 接口类型 | 目标响应时间 | 说明 |
|---------|------------|------|
| 游戏授权 | < 2秒 (99%) | 核心业务接口 |
| 查询接口 | < 1秒 (95%) | 包括列表和详情查询 |
| 统计报表 | < 5秒 (90%) | 复杂数据聚合 |

### 并发支持

- **游戏授权**: 单运营商同时最多10个并发请求
- **数据库查询**: 支持1000+并发查询
- **系统可用性**: 99.5%（每月停机时间不超过3.6小时）

## 使用工具推荐

### 文档查看

- **Swagger UI**: https://editor.swagger.io/
- **Redoc**: `npx @redocly/cli preview-docs openapi.yaml`
- **Stoplight Studio**: 桌面应用，支持可视化编辑

### 代码生成

```bash
# 生成FastAPI服务端代码（Python）
npx @openapitools/openapi-generator-cli generate \
  -i openapi.yaml \
  -g python-fastapi \
  -o ../server

# 生成TypeScript客户端代码
npx @openapitools/openapi-generator-cli generate \
  -i openapi.yaml \
  -g typescript-axios \
  -o ../client
```

### 契约验证

```bash
# Linux/Mac
./validate.sh

# Windows
validate.bat
```

### 测试工具

- **Postman**: 导入OpenAPI契约自动生成测试集合
- **Insomnia**: 支持OpenAPI导入和环境管理
- **REST Client (VS Code插件)**: 直接在编辑器中测试API

## 后续扩展建议

### 短期扩展（v1.1）

1. **Webhook支持**: 充值成功、退款完成等事件回调
2. **批量操作**: 批量授权、批量调价
3. **数据导出**: 支持CSV/Excel导出更多数据
4. **GraphQL支持**: 提供GraphQL查询接口

### 中期扩展（v1.2）

1. **OAuth2.0支持**: 支持第三方应用接入
2. **多语言支持**: i18n国际化
3. **实时通知**: WebSocket推送
4. **高级统计**: 更多维度的数据分析

### 长期扩展（v2.0）

1. **微服务拆分**: 按业务模块拆分独立服务
2. **gRPC支持**: 高性能内部服务调用
3. **分布式追踪**: OpenTelemetry集成
4. **API网关**: 统一入口、限流、熔断

## 版本规划

| 版本 | 计划时间 | 主要功能 |
|-----|---------|---------|
| v1.0.0 | 2025-01 | 基础功能（当前版本） |
| v1.1.0 | 2025-Q2 | Webhook、批量操作 |
| v1.2.0 | 2025-Q3 | OAuth2.0、实时通知 |
| v2.0.0 | 2025-Q4 | 微服务架构、gRPC |

## 贡献指南

### 修改契约文件

1. 修改对应模块的YAML文件
2. 运行验证脚本: `./validate.sh` 或 `validate.bat`
3. 更新`CONTRACT_SUMMARY.md`文档
4. 提交Git Commit并关联Issue

### 添加新接口

1. 在对应模块YAML文件中添加path定义
2. 在`openapi.yaml`的`paths`部分添加引用
3. 更新接口统计信息
4. 运行验证脚本确保无错误

### 添加新Schema

1. 在对应模块YAML文件的`components/schemas`中定义
2. 更新`CONTRACT_SUMMARY.md`的Schema统计
3. 确保所有引用路径正确

## 联系方式

- **技术支持**: support@example.com
- **问题反馈**: https://github.com/example/mr-game-api/issues
- **API文档**: https://docs.mrgame.example.com
- **Slack频道**: #mr-game-api

---

**文档版本**: 1.0.0
**最后更新**: 2025-10-10
**维护者**: API团队
