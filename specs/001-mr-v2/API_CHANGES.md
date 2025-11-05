# API Changes and Deprecations

本文档记录API的变更、废弃字段和向后兼容性说明。

## v2.1.0 (2025-11-05)

### 废弃字段 (Deprecated Fields)

以下字段在统计API响应中仍然存在（为保持向后兼容），但前端已不再使用，未来版本可能移除：

#### 1. 消费趋势统计 API
**端点**: `GET /api/v1/operators/me/statistics/consumption`

废弃字段：
- `summary.total_sessions` - 总场次
- `summary.avg_players_per_session` - 场均玩家数
- `chart_data[].total_sessions` - 每个时间点的场次数

**原因**: "场次"概念与系统设计不符。一个 usage_record 代表一次完整的游戏信息，而非多个"游戏场次"。

**前端处理**:
- 文件: `frontend/src/pages/operator/Statistics.vue`
- 不显示这些字段，只显示 `total_players` 和 `total_cost`

**推荐做法**: 新客户端应忽略这些字段，只使用 `total_players` 和 `total_cost`

---

#### 2. 按应用统计 API
**端点**: `GET /api/v1/operators/me/statistics/by-app`

废弃字段：
- `applications[].total_sessions` - 总场次
- `applications[].avg_players_per_session` - 场均玩家数

**原因**: 同上，"场次"概念已被移除。

**前端处理**:
- 文件: `frontend/src/pages/operator/Statistics.vue`
- 不显示这些字段，只显示 `total_players` 和 `total_cost`

---

#### 3. 按运营点统计 API
**端点**: `GET /api/v1/operators/me/statistics/by-site`

废弃字段：
- `sites[].total_sessions` - 总场次

**原因**: 同上。

**前端处理**:
- 文件: `frontend/src/pages/operator/Statistics.vue`
- 不显示这些字段，只显示 `total_players` 和 `total_cost`

---

### API路径更正

以下API路径在文档中的描述与实际实现不符，已在v2.1.0中修正前端调用：

| 文档中的路径 (错误) | 实际路径 (正确) | 状态 |
|------------------|--------------|------|
| `/operators/me/statistics/by-application` | `/operators/me/statistics/by-app` | ✅ 已修正 |
| `/operators/me/statistics/by-time` | `/operators/me/statistics/consumption` | ✅ 已修正 |

**影响范围**: 前端调用
**修复位置**: `frontend/src/stores/operator.ts` (Lines 142, 151)

---

### 数据响应格式说明

#### 统一响应包装
所有API响应都遵循以下格式：

```json
{
  "success": true,
  "data": {
    // 实际业务数据
  }
}
```

**前端处理要点**:
- ✅ 正确: `response.data.data`
- ❌ 错误: `response.data`

**已修复的函数** (`frontend/src/stores/operator.ts`):
- `getStatisticsBySite` (Line 135)
- `getStatisticsByApplication` (Line 143)
- `getStatisticsByTime` (Line 152)
- `getPlayerDistribution` (Line 160)
- `exportUsageRecords` (Line 172)
- `exportStatistics` (Line 183)

---

### 新增API功能

#### 游戏Session上传 (覆盖模式)
**端点**: `POST /api/v1/auth/game/session/upload`

**行为变更**:
- **之前**: 追加模式，每次上传创建新的 GameSession 记录
- **现在**: 覆盖模式，删除旧记录后创建新记录

**详细说明**:
1. 当同一 `usage_record_id` 再次上传时，系统会：
   - 删除该 usage_record 下所有旧的 GameSession 记录
   - 级联删除关联的 HeadsetGameRecord 记录
   - 创建新的 GameSession 和 HeadsetGameRecord

2. 头显设备更新逻辑：
   - 如果设备已存在（通过 device_id 识别）：
     - 如果提供了新的 `device_name`，则更新设备名称
     - 更新 `last_used_at` 时间戳
   - 如果设备不存在：
     - 创建新的 HeadsetDevice 记录

**相关需求**: FR-034a, FR-034b (spec.md)

**实现位置**: `backend/src/api/v1/auth.py` (Lines 487-550)

---

## 向后兼容性保证

### 保留的废弃字段
为了不破坏现有客户端，以下废弃字段仍然在API响应中返回：

- `total_sessions` (所有统计API)
- `avg_players_per_session` (消费趋势、按应用统计)

**计划**: 这些字段将在 v3.0.0 中移除（预计2026年Q2）。

### 客户端迁移建议

如果你的客户端代码仍在使用废弃字段，请按以下步骤迁移：

1. **立即行动** (v2.1.0):
   - 停止依赖 `total_sessions`、`avg_players_per_session` 字段
   - 使用 `total_players` 和 `total_cost` 替代

2. **测试验证**:
   - 确认UI显示正确（只显示玩家数和费用）
   - 确认数据导出功能正常

3. **代码示例**:

```typescript
// ❌ 旧代码 (使用废弃字段)
const totalSessions = response.data.summary.total_sessions
const avgPlayers = response.data.summary.avg_players_per_session

// ✅ 新代码 (只使用有效字段)
const totalPlayers = response.data.summary.total_players
const totalCost = response.data.summary.total_cost
```

---

## 相关文档

- **CHANGELOG.md**: 完整的版本变更历史
- **spec.md**: 功能需求规格（已更新FR-037, FR-038）
- **contracts/operator.yaml**: API契约定义（待更新）
- **frontend/src/pages/operator/Statistics.vue**: 统计页面实现

---

## 问题反馈

如果你在API迁移过程中遇到问题，请：
1. 查看 CHANGELOG.md 确认版本
2. 检查 spec.md 中的相关功能需求
3. 提交 GitHub Issue 并附上错误日志
