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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/format'
import http from '@/utils/http'

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
}

const loading = ref(false)
const requests = ref<AppRequest[]>([])
const detailsVisible = ref(false)
const currentRequest = ref<AppRequest | null>(null)
const statusFilter = ref('')

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
    let rejectReason = ''

    if (action === 'reject') {
      const { value } = await ElMessageBox.prompt('请输入拒绝原因', '拒绝申请', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPattern: /.+/,
        inputErrorMessage: '拒绝原因不能为空',
      })

      if (!value) return
      rejectReason = value
    } else {
      await ElMessageBox.confirm(
        `确定要通过此申请吗？通过后运营商将获得 "${row.app_name}" 的使用权限。`,
        '通过申请',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'success',
        }
      )
    }

    loading.value = true

    const payload = {
      action,
      reject_reason: rejectReason || undefined,
    }

    await http.post(`/admins/applications/requests/${row.request_id}/review`, payload)

    ElMessage.success(action === 'approve' ? '申请已通过' : '申请已拒绝')

    // 刷新列表
    await fetchRequests()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Review failed:', error)
    }
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
