# 更新日志 (Changelog)

本文档记录MR游戏运营管理系统的重要更新和变更。

---

## [v2.1.0] - 2025-11-04

### 🚨 破坏性变更 (Breaking Changes)

#### 头显Server API - 移除X-Session-ID请求头
- **影响**: 所有调用授权API的头显Server客户端
- **变更**: `POST /api/v1/auth/game/authorize` 不再需要客户端提供 `X-Session-ID` 请求头
- **原因**: 简化客户端实现，提高安全性，服务器端统一生成session_id
- **迁移**:
  1. 移除客户端的session_id生成逻辑
  2. 移除请求头中的 `X-Session-ID`
  3. 从API响应中获取服务器生成的 `session_id`
  4. 使用响应中的 `session_id` 进行后续游戏会话数据上传

**迁移示例**:
```diff
# 请求头
  Authorization: Bearer {headset_token}
- X-Session-ID: {client_generated_session_id}

# 响应
  {
    "success": true,
    "data": {
+     "session_id": "abac65d7-..._{timestamp}_{random}",  // 新增
      "authorization_token": "...",
      ...
    }
  }
```

### ✨ 新特性 (Features)

#### 1. 服务器端Session ID生成
- 授权时自动生成唯一session_id
- 格式: `{operator_id}_{timestamp_ms}_{random16}`
- 确保全局唯一性和时间可追溯性

#### 2. 业务键幂等性保护
- **保护机制**: 30秒窗口期内，相同业务键的重复请求返回相同结果
- **业务键组成**: `operator_id` + `application_id` + `site_id` + `player_count`
- **作用**: 防止网络超时重试导致的重复扣费
- **使用场景**: 客户端可以安全地重试授权请求，系统会自动识别重复请求

**示例场景**:
```
时间 00:00:00 - 首次请求授权(运营商A, 应用X, 运营点B, 5人) -> 扣费成功
时间 00:00:15 - 网络超时重试相同请求 -> 返回首次结果，不重复扣费 ✅
时间 00:00:35 - 超过30秒窗口期，再次请求 -> 视为新授权，再次扣费
```

### 🐛 Bug修复 (Bug Fixes)

#### 1. Site ID格式支持
- **问题**: 只支持纯UUID格式的site_id
- **修复**: 同时支持 "site_" 前缀和纯UUID两种格式
- **示例**:
  - `site_144c10e2-7c9b-4d07-a42c-05f736654d87` ✅
  - `144c10e2-7c9b-4d07-a42c-05f736654d87` ✅

#### 2. 退款业务逻辑错误（已修正）
- **问题**: 退款审核通过后错误地增加了运营商余额
- **正确理解**: 退款是运营商从系统提现到银行账户，系统余额应该减少
- **修复**:
  - 后端：修正余额计算为减法操作
  - 后端：交易记录金额改为负数
  - 前端：退款显示为红色负数（与消费一致）
- **影响范围**:
  - `backend/src/services/finance_refund_service.py:235-253`
  - `frontend/src/pages/operator/Transactions.vue:180-217`
  - `frontend/src/pages/operator/Dashboard.vue:210-221`

#### 3. 交易记录API字段缺失
- **问题**: GET `/api/v1/operators/transactions` 缺少关键字段
- **修复**: 添加以下字段:
  - `transaction_type`: 交易类型（recharge/consumption/refund）
  - `balance_before`: 交易前余额
  - `description`: 交易描述
- **影响**: 运营商端和管理员端交易记录查询

#### 4. Swagger UI认证支持
- **问题**: Swagger UI无法使用Bearer Token认证
- **修复**: 添加HTTPBearer支持，支持"Authorize"按钮
- **改进**: 开发者可以直接在Swagger UI中测试需要认证的接口

### 🎨 UI修复 (UI Fixes)

#### 1. 交易记录金额显示双重负号
- **问题**: 消费记录显示为 `-¥-400.00`
- **原因**: 后端返回负数金额，前端又基于类型添加负号
- **修复**: 改为基于金额实际符号判断，取绝对值后添加正确前缀
- **结果**:
  - 充值: `+¥500.00` ✅（绿色）
  - 消费: `-¥400.00` ✅（红色，不再是 `-¥-400.00`）
  - 退款: `-¥50.00` ✅（红色，提现操作）
- **影响文件**:
  - `frontend/src/pages/operator/Transactions.vue`
  - `frontend/src/pages/operator/Dashboard.vue`

#### 2. 交易类型显示英文
- **问题**: 消费记录显示 "consumption" 而不是 "消费"
- **原因**: 前端类型映射使用 "billing" 但后端返回 "consumption"
- **修复**: 统一使用 "consumption" 并正确映射到中文
- **结果**: 所有交易类型正确显示中文标签

### 📚 文档更新 (Documentation)

#### 1. 头显Server API文档 (v2.1)
- 更新为v2.1版本
- 添加详细的破坏性变更说明
- 添加迁移指南
- 更新所有代码示例
- 添加版本历史记录

#### 2. Swagger文档改进
- 支持在线认证测试
- 改进安全方案配置
- 更清晰的API分组

### 🔧 技术改进 (Technical Improvements)

#### 1. 数据库分区自动维护
- 实现分区表自动维护机制
- 支持非分区表环境（自动降级）
- 提高大数据量场景下的查询性能

#### 2. Redis密码配置改进
- 支持通过环境变量配置Redis密码
- 提高部署灵活性

### 📊 测试改进 (Testing)

#### 1. 头显Server API手动测试工具
- 添加完整的Python测试脚本
- 支持预授权、授权、会话上传全流程测试
- 方便开发者快速验证集成

---

## [v2.0.0] - 2025-11-02

### ✨ 新特性

#### 1. Headset Token认证机制
- 24小时有效期
- 通过自定义协议传递
- JWT格式，包含运营商身份信息

#### 2. 自定义协议启动
- 协议格式: `mrgun-{exe_name}://start?token=...&app_code=...&site_id=...`
- Windows注册表自动注册
- 支持参数传递

#### 3. 预授权接口
- 余额检查
- 价格预估
- 应用信息查询

### 📚 文档

- 完整的头显Server对接文档
- Python和C#集成示例
- FAQ和最佳实践

---

## 版本号说明

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范:

- **主版本号(MAJOR)**: 不兼容的API变更
- **次版本号(MINOR)**: 向后兼容的新功能
- **修订号(PATCH)**: 向后兼容的bug修复

---

## 相关文档

- [头显Server API文档](docs/HEADSET_SERVER_API.md)
- [API完整文档](backend/docs/API_DOCUMENTATION.md)
- [数据模型文档](specs/001-mr-v2/data-model.md)
- [部署文档](deploy/README.md)

---

**最后更新**: 2025-11-04
