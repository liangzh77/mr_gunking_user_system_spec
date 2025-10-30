# API Key 轮换操作手册

## 概述

本文档描述运营商API Key的轮换流程、最佳实践和自动化脚本使用方法。

API Key是运营商访问系统API的唯一凭证，定期轮换API Key是保障系统安全的重要措施。

## 何时需要轮换API Key

### 必须轮换的场景

1. **安全事件**
   - API Key泄露或疑似泄露
   - 运营商报告异常API调用
   - 检测到未授权的API访问尝试
   - 员工离职（如果该员工知晓API Key）

2. **定期轮换**
   - 建议每90天轮换一次（符合安全最佳实践）
   - VIP客户建议每60天轮换一次

3. **合规要求**
   - 满足行业安全标准（如PCI DSS、ISO 27001）
   - 满足客户合同中的安全条款

### 建议轮换的场景

1. 运营商申请主动轮换
2. 系统检测到异常IP访问（FR-056a）
3. 运营商账户解锁后
4. 重大系统升级前后

## 轮换前准备

### 1. 确认影响范围

```bash
# 使用管理员账户查看运营商当前API Key
# GET /v1/admins/operators/{operator_id}/api-key

curl -X GET "https://api.example.com/v1/admins/operators/{operator_id}/api-key" \
  -H "Authorization: Bearer {admin_token}"
```

**检查清单**：
- [ ] 确认运营商当前使用的API Key
- [ ] 确认运营商拥有的运营点数量
- [ ] 确认是否有未完成的游戏会话
- [ ] 确认轮换窗口期（避开业务高峰期）

### 2. 通知运营商

**提前通知时间**：
- 常规轮换：至少提前3天
- 紧急轮换（安全事件）：至少提前4小时

**通知内容模板**：
```
尊敬的{运营商名称}：

为保障系统安全，我们将于{时间}对您的API Key进行轮换。

旧API Key将于{失效时间}失效。
新API Key将通过加密邮件发送给您。

请在收到新API Key后，尽快更新您所有运营点的配置文件。

如有疑问，请联系技术支持：support@example.com

此致
MR游戏运营管理系统
```

### 3. 备份当前配置

```bash
# 备份运营商当前信息
curl -X GET "https://api.example.com/v1/admins/operators/{operator_id}" \
  -H "Authorization: Bearer {admin_token}" \
  > operator_backup_$(date +%Y%m%d_%H%M%S).json
```

## 轮换步骤

### 方式一：使用管理后台（推荐）

1. 登录管理后台
2. 导航至 **运营商管理** → **运营商列表**
3. 找到目标运营商，点击 **操作** → **重置API Key**
4. 确认轮换操作
5. 复制新生成的API Key（仅显示一次！）
6. 通过安全渠道发送给运营商

### 方式二：使用API端点（需要实现）

```bash
# POST /v1/admins/operators/{operator_id}/reset-api-key
curl -X POST "https://api.example.com/v1/admins/operators/{operator_id}/reset-api-key" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "定期轮换",
    "notify_operator": true
  }'
```

**响应示例**：
```json
{
  "operator_id": "123e4567-e89b-12d3-a456-426614174000",
  "new_api_key": "abc...xyz",  // 64字符
  "old_api_key_revoked_at": "2025-10-30T10:00:00Z",
  "message": "API Key已成功轮换"
}
```

### 方式三：使用自动化脚本

```bash
# 使用项目提供的轮换脚本
cd scripts/
python rotate_api_key.py \
  --operator-id {operator_id} \
  --reason "定期轮换" \
  --notify \
  --admin-token {admin_token}
```

## 轮换后验证

### 1. 验证新API Key

```bash
# 使用新API Key测试游戏授权接口
curl -X POST "https://api.example.com/v1/game/authorize" \
  -H "X-API-Key: {new_api_key}" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_001",
    "site_id": "{site_id}",
    "app_id": "{app_id}",
    "player_count": 2
  }'
```

**期望结果**：
- HTTP 200 OK
- 返回授权令牌

### 2. 验证旧API Key已失效

```bash
# 使用旧API Key测试（应该失败）
curl -X POST "https://api.example.com/v1/game/authorize" \
  -H "X-API-Key: {old_api_key}" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_002",
    "site_id": "{site_id}",
    "app_id": "{app_id}",
    "player_count": 2
  }'
```

**期望结果**：
- HTTP 401 Unauthorized
- 错误信息：Invalid API Key

### 3. 监控运营商调用

轮换后24小时内，密切监控：
- API调用成功率（应>99%）
- 401错误数量（旧Key使用次数，应逐渐降为0）
- 运营商反馈

### 4. 确认通知已读

```bash
# 检查通知状态
curl -X GET "https://api.example.com/v1/admins/operators/{operator_id}/messages" \
  -H "Authorization: Bearer {admin_token}"
```

## 回滚方案

### 场景1：运营商未收到新API Key

**解决方案**：
1. 通过安全渠道重新发送新API Key
2. 或使用管理后台查看API Key功能获取
3. 延长旧Key失效时间（如果技术上可行）

### 场景2：轮换后业务中断

**紧急回滚步骤**：
```bash
# 方案1：临时启用旧API Key（需要数据库操作）
# 警告：仅在紧急情况下使用

# 1. 连接数据库
psql -h localhost -U postgres -d mr_game_ops

# 2. 临时恢复旧API Key
UPDATE operator_accounts
SET api_key = '{old_api_key}',
    api_key_hash = '{old_api_key_hash}'
WHERE id = '{operator_id}';

# 方案2：生成临时API Key
# 使用管理后台快速生成新的临时Key
```

**回滚后操作**：
1. 立即通知运营商使用临时Key
2. 分析轮换失败原因
3. 制定改进方案后重新轮换

## 批量轮换

### 定期批量轮换流程

对于定期轮换（如每90天），建议分批进行：

**第1批**：试点轮换（占10%）
- 选择1-2个非关键运营商
- 提前7天通知
- 验证流程无误

**第2批**：主要轮换（占80%）
- 分3个时间窗口
- 每个窗口间隔1天
- 避开周末和节假日

**第3批**：剩余轮换（占10%）
- VIP客户单独安排
- 提供1对1技术支持

### 批量轮换脚本

```bash
# 使用批量轮换脚本
cd scripts/
python batch_rotate_api_keys.py \
  --config rotation_config.json \
  --dry-run  # 先运行测试模式

# 确认无误后执行
python batch_rotate_api_keys.py \
  --config rotation_config.json \
  --execute
```

**配置文件示例** (`rotation_config.json`):
```json
{
  "batches": [
    {
      "name": "试点批次",
      "operator_ids": ["op1", "op2"],
      "schedule_time": "2025-11-01T02:00:00Z",
      "notify_days_before": 7
    },
    {
      "name": "主要批次-第1组",
      "operator_ids": ["op3", "op4", "op5"],
      "schedule_time": "2025-11-02T02:00:00Z",
      "notify_days_before": 7
    }
  ],
  "notification": {
    "email": true,
    "sms": false,
    "in_app": true
  },
  "validation": {
    "test_endpoint": true,
    "monitor_hours": 24
  }
}
```

## 安全最佳实践

### 1. API Key传输安全

- ✅ **使用加密邮件**（PGP/GPG）发送新Key
- ✅ **使用加密即时通讯**（Signal、企业微信加密会话）
- ❌ **禁止**通过普通邮件、短信、微信发送
- ❌ **禁止**截图发送

### 2. API Key存储安全

**运营商端**：
```bash
# 推荐：使用环境变量
export MR_API_KEY="your_api_key_here"

# 推荐：使用配置文件（需加密）
# /etc/mr-client/config.encrypted

# 不推荐：硬编码在代码中
```

**管理端**：
- API Key明文仅在生成时显示一次
- 数据库存储API Key哈希值（bcrypt）
- 管理员无法查看完整API Key（只能重置）

### 3. 审计日志

所有API Key轮换操作自动记录：
```sql
SELECT * FROM finance_operation_logs
WHERE operation_type = 'reset_api_key'
AND target_resource_id = '{operator_id}'
ORDER BY created_at DESC;
```

## 常见问题

### Q1: 轮换API Key会影响正在进行的游戏会话吗？

**A**: 不会。已授权的游戏会话使用authorization_token，不依赖API Key。只有新的授权请求才需要新API Key。

### Q2: 运营商有多个运营点，需要分别轮换吗？

**A**: 不需要。一个运营商账户只有一个API Key，所有运营点共享。轮换后，所有运营点需要同时更新配置。

### Q3: API Key轮换失败，怎么办？

**A**: 参考"回滚方案"章节。如果无法自行解决，立即联系技术团队，提供：
- 运营商ID
- 轮换时间
- 错误日志
- 影响范围

### Q4: 可以延长API Key有效期吗？

**A**: 当前系统设计为：新Key生成后，旧Key立即失效。建议运营商提前做好轮换准备，而不是延期。

### Q5: 如何监控API Key使用情况？

**A**: 使用监控API：
```bash
curl -X GET "https://api.example.com/v1/admins/operators/{operator_id}/api-usage" \
  -H "Authorization: Bearer {admin_token}"
```

## 相关文档

- [运营商接入指南](./quickstart.md)
- [API认证机制](./spec.md#api认证)
- [安全事件响应流程](./PRODUCTION_DEPLOYMENT.md#安全)

## 附录：自动化脚本

### A. 单个运营商轮换脚本

脚本位置：`scripts/rotate_api_key.py`

**使用方法**：
```bash
python scripts/rotate_api_key.py --help

# 示例：为运营商op1轮换API Key
python scripts/rotate_api_key.py \
  --operator-id op1 \
  --admin-token {token} \
  --reason "定期轮换" \
  --notify
```

### B. 批量轮换脚本

脚本位置：`scripts/batch_rotate_api_keys.py`

**使用方法**：
```bash
python scripts/batch_rotate_api_keys.py --help

# 测试运行
python scripts/batch_rotate_api_keys.py \
  --config rotation_config.json \
  --dry-run

# 正式执行
python scripts/batch_rotate_api_keys.py \
  --config rotation_config.json \
  --execute \
  --log-file rotation_$(date +%Y%m%d).log
```

### C. 监控脚本

脚本位置：`scripts/monitor_api_key_usage.py`

**使用方法**：
```bash
# 监控单个运营商
python scripts/monitor_api_key_usage.py \
  --operator-id op1 \
  --hours 24

# 监控所有运营商
python scripts/monitor_api_key_usage.py \
  --all \
  --hours 24 \
  --report report_$(date +%Y%m%d).html
```

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| 1.0.0 | 2025-10-30 | 初始版本 | System |

## 联系方式

- 技术支持：support@example.com
- 安全团队：security@example.com
- 紧急热线：400-xxx-xxxx
