<template>
  <div class="applications-page">
    <!-- 页面标题和操作栏 -->
    <el-card class="header-card">
      <div class="title-section">
        <el-icon :size="24"><Grid /></el-icon>
        <h2>已授权应用</h2>
      </div>
    </el-card>

    <!-- 应用列表 -->
    <el-card class="list-card" style="margin-top: 20px">
      <!-- 搜索栏 -->
      <div class="filter-container" style="margin-bottom: 16px">
        <el-input
          v-model="searchQuery"
          placeholder="搜索应用名称、描述..."
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
          style="width: 300px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="handleSearch" style="margin-left: 12px">
          <el-icon><Search /></el-icon>
          查询
        </el-button>
      </div>

      <el-table
        v-copyable
        v-loading="loading"
        :data="applications"
        stripe
        style="width: 100%"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div style="padding: 0 20px 20px 60px">
              <div style="font-weight: 600; margin-bottom: 12px; color: #303133">
                已授权游戏模式：
              </div>
              <div v-if="row.authorized_modes && row.authorized_modes.length > 0" class="modes-grid">
                <div
                  v-for="mode in row.authorized_modes"
                  :key="mode.id"
                  class="mode-card"
                >
                  <div class="mode-header">
                    <span class="mode-name">{{ mode.mode_name }}</span>
                    <span class="mode-price">¥{{ mode.price }}</span>
                  </div>
                  <div v-if="mode.description" class="mode-description">
                    {{ mode.description }}
                  </div>
                  <el-tag v-if="!mode.is_active" type="info" size="small" style="margin-top: 8px">
                    已停用
                  </el-tag>
                </div>
              </div>
              <el-empty
                v-else
                description="暂无授权模式"
                :image-size="60"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="app_name" label="应用名称" width="160" />
        <el-table-column prop="description" label="应用描述" min-width="180" show-overflow-tooltip />
        <el-table-column label="模式单价" width="200">
          <template #default="{ row }">
            <div
              v-if="row.authorized_modes && row.authorized_modes.length > 0"
              class="mode-prices clickable"
              @click="showModeDetails(row)"
            >
              <span v-for="(mode, index) in getSortedModes(row.authorized_modes)" :key="mode.id" class="price-item">
                ¥{{ formatAmount(Number(mode.price || 0)) }}<template v-if="index < row.authorized_modes.length - 1">、</template>
              </span>
              <el-icon class="expand-icon" style="margin-left: 4px"><View /></el-icon>
            </div>
            <span v-else class="text-muted">暂无</span>
          </template>
        </el-table-column>
        <el-table-column label="玩家限制" width="130">
          <template #default="{ row }">
            <span>{{ row.min_players }} - {{ row.max_players }} 人</span>
          </template>
        </el-table-column>
        <el-table-column prop="authorized_at" label="授权时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.authorized_at) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default>
            <el-tag type="success" size="small">已授权</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && applications.length === 0" class="empty-state">
        <el-empty description="暂无已授权应用">
          <el-text type="info">请联系管理员申请应用授权</el-text>
        </el-empty>
      </div>
    </el-card>

    <!-- 模式详情对话框 -->
    <el-dialog
      v-model="modeDialogVisible"
      :title="`${selectedApp?.app_name} - 游戏模式详情`"
      width="700px"
    >
      <div v-if="selectedApp && selectedApp.authorized_modes" class="modes-detail-grid">
        <div
          v-for="mode in getSortedModes(selectedApp.authorized_modes)"
          :key="mode.id"
          class="mode-detail-card"
        >
          <div class="mode-detail-header">
            <div class="mode-detail-name">
              <el-icon :size="18" style="color: #409eff"><Medal /></el-icon>
              <span>{{ mode.mode_name }}</span>
            </div>
            <div class="mode-detail-price">¥{{ formatAmount(Number(mode.price || 0)) }}</div>
          </div>
          <div v-if="mode.description" class="mode-detail-description">
            <el-icon :size="14" style="color: #909399"><Document /></el-icon>
            <span>{{ mode.description }}</span>
          </div>
          <div class="mode-detail-footer">
            <el-tag v-if="mode.is_active" type="success" size="small">
              <el-icon><CircleCheckFilled /></el-icon>
              可用
            </el-tag>
            <el-tag v-else type="info" size="small">
              <el-icon><CircleCloseFilled /></el-icon>
              已停用
            </el-tag>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无模式" :image-size="80" />

      <template #footer>
        <el-button @click="modeDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Search,
  View,
  Medal,
  Document,
  CircleCheckFilled,
  CircleCloseFilled
} from '@element-plus/icons-vue'
import { useOperatorStore } from '@/stores/operator'
import type { AuthorizedApplication } from '@/types'
import { formatDateTime, formatAmount} from '@/utils/format'

const operatorStore = useOperatorStore()

const loading = ref(false)
const applications = ref<AuthorizedApplication[]>([])
const searchQuery = ref('')
const modeDialogVisible = ref(false)
const selectedApp = ref<AuthorizedApplication | null>(null)

// 加载已授权应用列表
const loadApplications = async () => {
  loading.value = true
  try {
    const params: any = {}

    if (searchQuery.value) {
      params.search = searchQuery.value
    }

    applications.value = await operatorStore.getAuthorizedApplications(params)
  } catch (error) {
    console.error('Load applications error:', error)
    ElMessage.error('加载应用列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索处理
const handleSearch = () => {
  loadApplications()
}

// 获取按价格排序的模式列表
const getSortedModes = (modes: any[]) => {
  if (!modes || modes.length === 0) return []
  return [...modes].sort((a, b) => Number(a.price) - Number(b.price))
}

// 显示模式详情
const showModeDetails = (app: AuthorizedApplication) => {
  selectedApp.value = app
  modeDialogVisible.value = true
}

onMounted(() => {
  loadApplications()
})
</script>

<style scoped>
.applications-page {
  max-width: 1400px;
  margin: 0 auto;
}

.header-card {
  margin-bottom: 0;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-section h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.price {
  color: #409EFF;
  font-weight: 600;
}

.mode-prices {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  line-height: 1.6;
}

.price-item {
  color: #409EFF;
  font-weight: 500;
  white-space: nowrap;
}

.text-muted {
  color: #909399;
  font-size: 13px;
}

.empty-state {
  padding: 40px 0;
  text-align: center;
}

.list-card :deep(.el-card__body) {
  padding: 20px;
}

.modes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.mode-card {
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background-color: #fafafa;
  transition: all 0.3s;
}

.mode-card:hover {
  border-color: #409eff;
  background-color: #ecf5ff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

.mode-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.mode-name {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

.mode-price {
  color: #f56c6c;
  font-weight: 600;
  font-size: 16px;
}

.mode-description {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

/* 可点击的模式价格 */
.clickable {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.3s;
}

.clickable:hover {
  background-color: #ecf5ff;
}

.clickable:hover .price-item {
  color: #409eff;
}

.expand-icon {
  color: #909399;
  transition: color 0.3s;
}

.clickable:hover .expand-icon {
  color: #409eff;
}

/* 模式详情对话框样式 */
.modes-detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  max-height: 500px;
  overflow-y: auto;
  padding: 4px;
}

.mode-detail-card {
  padding: 20px;
  border: 2px solid #e4e7ed;
  border-radius: 12px;
  background-color: #fafafa;
  transition: all 0.3s;
}

.mode-detail-card:hover {
  border-color: #409eff;
  background-color: #ecf5ff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
  transform: translateY(-2px);
}

.mode-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.mode-detail-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
  color: #303133;
}

.mode-detail-price {
  color: #f56c6c;
  font-weight: 700;
  font-size: 20px;
}

.mode-detail-description {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-bottom: 12px;
  padding: 8px;
  background-color: #f5f7fa;
  border-radius: 6px;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}

.mode-detail-description span {
  flex: 1;
}

.mode-detail-footer {
  display: flex;
  justify-content: flex-end;
}
</style>
