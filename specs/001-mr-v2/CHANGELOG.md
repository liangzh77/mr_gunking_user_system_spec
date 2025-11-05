# Changelog - MR游戏运营管理系统

本文档记录项目的重要功能修改和版本历史。

## [v2.1.0] - 2025-11-05

### 新增功能

#### 游戏Session上传覆盖模式 (backend)
- **文件**: `backend/src/api/v1/auth.py` (Lines 487-506)
- **功能**: 实现真正的覆盖模式，当头显Server再次上传同一usage_record的Session信息时，系统会：
  1. 删除该usage_record下所有旧的GameSession记录
  2. 级联删除关联的HeadsetGameRecord记录
  3. 创建新的GameSession和HeadsetGameRecord
- **原因**: 确保每次上传代表完整的最新游戏信息，而非追加的"游戏局"概念
- **相关需求**: FR-034a (spec.md)

#### 头显设备名称更新支持 (backend)
- **文件**: `backend/src/api/v1/auth.py` (Lines 541-550)
- **功能**: 当头显设备已存在时，支持更新device_name字段
  - 如果上传数据提供了新的device_name，则更新设备名称
  - 无论是否提供新名称，都更新last_used_at时间戳
- **原因**: 解决首次上传时device_name为空，后续上传无法更新的问题
- **相关需求**: FR-034b (spec.md)

### 修复问题

#### 前端统计数据无法显示 (frontend)
- **文件**: `frontend/src/stores/operator.ts` (Lines 135, 143, 152, 160, 172, 183)
- **问题**: 统计页面显示"暂无数据"，但数据库有数据
- **原因**: API返回 `{ success: true, data: {...} }` 格式，但前端返回了 `response.data` 而非 `response.data.data`
- **修复**: 修改6个函数的返回值：
  - `getStatisticsBySite`
  - `getStatisticsByApplication`
  - `getStatisticsByTime`
  - `getPlayerDistribution`
  - `exportUsageRecords`
  - `exportStatistics`

#### API路径不匹配导致404错误 (frontend)
- **文件**: `frontend/src/stores/operator.ts` (Lines 142, 151)
- **问题**: "按应用统计"和"消费趋势"返回404错误
- **原因**: 前端调用路径与后端路由不一致
- **修复**:
  - `/operators/me/statistics/by-application` → `/operators/me/statistics/by-app`
  - `/operators/me/statistics/by-time` → `/operators/me/statistics/consumption`

### 界面优化

#### 移除"场次"概念 (frontend)
- **文件**: `frontend/src/pages/operator/Statistics.vue`
- **修改内容**:
  - **按运营点统计**: 删除"总场次"和"平均场次费用"列
  - **按应用统计**: 删除"总场次"和"场均玩家数"列
  - **消费趋势**: 删除汇总中的"总场次"和"场均玩家数"，删除表格中的"场次"列
- **保留内容**: 只显示"总玩家数"和"总费用"
- **原因**:
  1. 一个usage_record代表一次完整的游戏信息，不是"多局游戏"的概念
  2. 与使用记录详情中已移除的"游戏局"概念保持一致
  3. 简化界面，聚焦核心指标（玩家数和费用）
- **相关需求**: FR-037, FR-038 (spec.md)
- **验收场景**: User Story 4 - Scenario 4, 5, 7 (spec.md)

### 文档更新

#### spec.md
- 新增功能需求:
  - **FR-034a**: 游戏Session上传覆盖模式
  - **FR-034b**: 头显设备信息完整更新
- 更新功能需求:
  - **FR-037**: 明确不包含"场次"概念
  - **FR-038**: 明确不包含"场次"概念
- 更新验收场景 (User Story 4):
  - Scenario 2: 验证Session上传覆盖功能
  - Scenario 3: 验证device_name更新功能
  - Scenario 4, 5, 7: 更新统计场景，去除"场次"相关验证

---

## [v2.0.0] - 2025-10-27

### 初始发布
- 完整的MR游戏运营管理系统
- 3端界面：运营商端、管理员端、财务端
- 核心功能：游戏授权、充值计费、运营点管理、统计分析
- Docker Compose部署支持
- Playwright E2E测试集成

---

## 版本说明

### 版本号规则
- **主版本号 (Major)**: 重大架构变更或不兼容更新
- **次版本号 (Minor)**: 新增功能或重要优化
- **修订号 (Patch)**: Bug修复或小改进

### 相关文档
- **spec.md**: 功能规格说明
- **plan.md**: 实施计划
- **tasks.md**: 任务清单
- **data-model.md**: 数据模型
- **contracts/**: API契约定义
