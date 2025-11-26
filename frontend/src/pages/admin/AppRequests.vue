<template>
  <div class="app-requests-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>授权申请审核</span>
          <el-badge :value="pendingCount" :hidden="pendingCount === 0" class="badge">
            <el-tag type="warning">待审核</el-tag>
          </el-badge>
        </div>
      </template>

      <!-- 筛选 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="状态">
          <el-select
            v-model="statusFilter"
            placeholder="全部状态"
            clearable
            style="width: 150px"
            @change="handleFilter"
          >
            <el-option label="待审核" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 申请列表 -->
      <el-table
        v-copyable
        v-loading="loading"
        :data="requests"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="app_name" label="应用名称" width="180" />
        <el-table-column prop="app_code" label="应用代码" width="150" />
        <el-table-column prop="reason" label="申请理由" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'pending'" type="warning" size="small">待审核</el-tag>
            <el-tag v-else-if="row.status === 'approved'" type="success" size="small">已通过</el-tag>
            <el-tag v-else-if="row.status === 'rejected'" type="danger" size="small">已拒绝</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reject_reason" label="拒绝原因" width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.reject_reason || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="reviewed_at" label="审核时间" width="160">
          <template #default="{ row }">
            {{ row.reviewed_at ? formatDateTime(row.reviewed_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button size="small" type="success" @click="handleReview(row, 'approve')">
                通过
              </el-button>
              <el-button size="small" type="danger" @click="handleReview(row, 'reject')">
                拒绝
              </el-button>
            </template>
            <template v-else>
              <el-button size="small" @click="viewDetails(row)">详情</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end"
        @size-change="handleFilter"
        @current-change="handleFilter"
      />
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailsVisible" title="申请详情" width="600px">
      <el-descriptions v-if="currentRequest" :column="2" border>
        <el-descriptions-item label="应用名称">
          {{ currentRequest.app_name }}
        </el-descriptions-item>
        <el-descriptions-item label="应用代码">
          {{ currentRequest.app_code }}
        </el-descriptions-item>
        <el-descriptions-item label="申请理由" :span="2">
          {{ currentRequest.reason }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag v-if="currentRequest.status === 'pending'" type="warning" size="small">
            待审核
          </el-tag>
          <el-tag v-else-if="currentRequest.status === 'approved'" type="success" size="small">
            已通过
          </el-tag>
          <el-tag v-else-if="currentRequest.status === 'rejected'" type="danger" size="small">
            已拒绝
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item v-if="currentRequest.reject_reason" label="拒绝原因" :span="2">
          {{ currentRequest.reject_reason }}
        </el-descriptions-item>
        <el-descriptions-item label="申请时间">
          {{ formatDateTime(currentRequest.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="审核时间">
          {{ currentRequest.reviewed_at ? formatDateTime(currentRequest.reviewed_at) : '-' }}
        </el-descriptions-item>
      </el-descriptions>

      <template #footer>
        <el-button @click="detailsVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 模式选择对话框 -->
    <el-dialog v-model="modeSelectionVisible" title="选择授权模式" width="500px">
      <el-alert
        title="请选择要授权的游戏模式"
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      />
      <el-checkbox-group v-model="selectedModeIds">
        <div
          v-for="mode in applicationModes"
          :key="mode.id"
          style="margin-bottom: 12px; padding: 12px; border: 1px solid #ebeef5; border-radius: 4px"
        >
          <el-checkbox :value="mode.id" :disabled="!mode.is_active">
            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%">
              <div>
                <span style="font-weight: 500">{{ mode.mode_name }}</span>
                <span v-if="mode.description" style="color: #909399; margin-left: 8px; font-size: 12px">
                  ({{ mode.description }})
                </span>
              </div>
              <div style="margin-left: auto; padding-left: 12px">
                <span style="color: #f56c6c; font-weight: 500">¥{{ mode.price }}</span>
                <el-tag v-if="!mode.is_active" type="info" size="small" style="margin-left: 8px">
                  已停用
                </el-tag>
              </div>
            </div>
          </el-checkbox>
        </div>
      </el-checkbox-group>
      <el-alert
        v-if="applicationModes.filter(m => m.is_active).length === 0"
        title="该应用暂无可用模式"
        type="warning"
        :closable="false"
        style="margin-top: 12px"
      />

      <template #footer>
        <el-button @click="modeSelectionVisible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="selectedModeIds.length === 0"
          @click="handleConfirmModeSelection"
        >
          确认授权
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/format'
import http from '@/utils/http'

interface ApplicationMode {
  id: string
  mode_name: string
  price: string
  description?: string
  is_active: boolean
}

interface AppRequest {
  request_id: string
  app_id: string
  app_code: string
  app_name: string
  reason: string
  status: string
  reject_reason?: string
  reviewed_by?: string
  reviewed_at?: string
  created_at: string
  requested_modes?: ApplicationMode[]
}

const loading = ref(false)
const requests = ref<AppRequest[]>([])
const detailsVisible = ref(false)
const currentRequest = ref<AppRequest | null>(null)
const statusFilter = ref('')

// 模式选择对话框
const modeSelectionVisible = ref(false)
const selectedModeIds = ref<string[]>([])
const currentReviewRequest = ref<AppRequest | null>(null)
const applicationModes = ref<ApplicationMode[]>([])

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

// 计算待审核数量
const pendingCount = computed(() => {
  return requests.value.filter(r => r.status === 'pending').length
})

// 获取申请列表
const fetchRequests = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }

    if (statusFilter.value) {
      params.status = statusFilter.value
    }

    const response = await http.get('/admins/applications/requests', { params })
    requests.value = response.data.items
    pagination.total = response.data.total
  } catch (error) {
    console.error('Failed to fetch requests:', error)
  } finally {
    loading.value = false
  }
}

// 筛选
const handleFilter = () => {
  pagination.page = 1
  fetchRequests()
}

// 查看详情
const viewDetails = (row: AppRequest) => {
  currentRequest.value = row
  detailsVisible.value = true
}

// 审核
const handleReview = async (row: AppRequest, action: 'approve' | 'reject') => {
  try {
    if (action === 'reject') {
      const { value } = await ElMessageBox.prompt('请输入拒绝原因', '拒绝申请', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPattern: /.+/,
        inputErrorMessage: '拒绝原因不能为空',
      })

      if (!value) return

      loading.value = true

      const payload = {
        action,
        reject_reason: value,
      }

      await http.post(`/admins/applications/requests/${row.request_id}/review`, payload)
      ElMessage.success('申请已拒绝')
      await fetchRequests()
    } else {
      // 通过申请 - 需要选择授权的模式
      // 首先加载该应用的所有模式
      try {
        const modesResponse = await http.get(`/admins/applications/${row.app_id}/modes`)
        applicationModes.value = modesResponse.data

        if (applicationModes.value.length === 0) {
          ElMessage.error('该应用暂无可用模式，无法授权')
          return
        }

        // 如果申请中包含了请求的模式，默认选中这些模式
        if (row.requested_modes && row.requested_modes.length > 0) {
          selectedModeIds.value = row.requested_modes
            .filter(m => m.is_active)
            .map(m => m.id)
        } else {
          // 否则默认选中所有激活的模式
          selectedModeIds.value = applicationModes.value
            .filter(m => m.is_active)
            .map(m => m.id)
        }

        currentReviewRequest.value = row
        modeSelectionVisible.value = true
      } catch (error: any) {
        console.error('Failed to load modes:', error)
        ElMessage.error('加载应用模式失败')
      }
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Review failed:', error)
    }
  } finally {
    loading.value = false
  }
}

// 确认授权模式选择
const handleConfirmModeSelection = async () => {
  if (selectedModeIds.value.length === 0) {
    ElMessage.warning('请至少选择一个模式')
    return
  }

  if (!currentReviewRequest.value) return

  try {
    loading.value = true

    const payload = {
      action: 'approve',
      mode_ids: selectedModeIds.value,
    }

    await http.post(`/admins/applications/requests/${currentReviewRequest.value.request_id}/review`, payload)
    ElMessage.success('申请已通过')

    modeSelectionVisible.value = false
    await fetchRequests()
  } catch (error: any) {
    console.error('Approve failed:', error)
    ElMessage.error('审批失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchRequests()
})
</script>

<style scoped>
.app-requests-page {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.badge {
  margin-left: 12px;
}

.filter-form {
  margin-bottom: 20px;
}
</style>
