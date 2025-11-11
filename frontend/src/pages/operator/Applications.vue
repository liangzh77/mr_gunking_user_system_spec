<template>
  <div class="applications-page">
    <!-- 页面标题和操作栏 -->
    <el-card class="header-card">
      <div class="header-content">
        <div class="title-section">
          <el-icon :size="24"><Grid /></el-icon>
          <h2>已授权应用</h2>
        </div>
        <el-button type="primary" @click="handleViewRequests">
          <el-icon><List /></el-icon>
          查看申请记录
        </el-button>
      </div>
    </el-card>

    <!-- 应用列表 -->
    <el-card class="list-card" style="margin-top: 20px">
      <el-table
        v-loading="loading"
        :data="applications"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="app_name" label="应用名称" min-width="150" />
        <el-table-column prop="description" label="应用描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="unit_price" label="单价" width="120">
          <template #default="{ row }">
            <span class="price">¥{{ row.unit_price }}</span>
          </template>
        </el-table-column>
        <el-table-column label="玩家限制" width="150">
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

    <!-- 申请记录对话框 -->
    <el-dialog
      v-model="requestsDialogVisible"
      title="应用授权申请记录"
      width="800px"
      @close="handleRequestsDialogClose"
    >
      <el-table
        v-loading="requestsLoading"
        :data="requests"
        stripe
        max-height="400px"
      >
        <el-table-column prop="app_name" label="应用名称" min-width="120" />
        <el-table-column prop="reason" label="申请理由" min-width="180" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="admin_note" label="管理员备注" min-width="150" show-overflow-tooltip />
        <el-table-column prop="created_at" label="申请时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!requestsLoading && requests.length === 0" class="empty-state">
        <el-empty description="暂无申请记录" />
      </div>

      <template #footer>
        <el-button @click="requestsDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useOperatorStore } from '@/stores/operator'
import type { AuthorizedApplication, ApplicationRequest } from '@/types'
import { formatDateTime } from '@/utils/format'

const operatorStore = useOperatorStore()

const loading = ref(false)
const applications = ref<AuthorizedApplication[]>([])
const requestsDialogVisible = ref(false)
const requestsLoading = ref(false)
const requests = ref<ApplicationRequest[]>([])

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  const map: Record<string, any> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
  }
  return map[status] || 'info'
}

// 获取状态标签文本
const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: '待审批',
    approved: '已通过',
    rejected: '已拒绝',
  }
  return map[status] || status
}

// 加载已授权应用列表
const loadApplications = async () => {
  loading.value = true
  try {
    applications.value = await operatorStore.getAuthorizedApplications()
  } catch (error) {
    console.error('Load applications error:', error)
    ElMessage.error('加载应用列表失败')
  } finally {
    loading.value = false
  }
}

// 查看申请记录
const handleViewRequests = async () => {
  requestsDialogVisible.value = true
  requestsLoading.value = true

  try {
    requests.value = await operatorStore.getApplicationRequests()
  } catch (error) {
    console.error('Load requests error:', error)
    ElMessage.error('加载申请记录失败')
  } finally {
    requestsLoading.value = false
  }
}

// 关闭申请记录对话框
const handleRequestsDialogClose = () => {
  requests.value = []
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

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.empty-state {
  padding: 40px 0;
  text-align: center;
}

.list-card :deep(.el-card__body) {
  padding: 20px;
}
</style>
