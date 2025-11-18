<template>
  <div class="app-requests-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>应用授权申请</span>
          <el-button type="primary" @click="showCreateDialog">
            <el-icon><Plus /></el-icon>
            申请新应用
          </el-button>
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
        <el-table-column prop="request_reason" label="申请理由" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'pending'" type="warning" size="small">待审核</el-tag>
            <el-tag v-else-if="row.status === 'approved'" type="success" size="small">已通过</el-tag>
            <el-tag v-else-if="row.status === 'rejected'" type="danger" size="small">已拒绝</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="admin_note" label="审核备注" width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.admin_note || '-' }}
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
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetails(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end"
        @size-change="handleFilter"
        @current-change="handleFilter"
      />
    </el-card>

    <!-- 创建申请对话框 -->
    <el-dialog v-model="createDialogVisible" title="申请新应用授权" width="500px">
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="100px"
      >
        <el-form-item label="选择应用" prop="application_id">
          <el-select
            v-model="createForm.application_id"
            placeholder="请选择要申请的应用"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="app in availableApplications"
              :key="app.id"
              :label="`${app.app_name} (${app.app_code})`"
              :value="app.id"
            >
              <div style="display: flex; justify-content: space-between">
                <span>{{ app.app_name }}</span>
                <span style="color: #8492a6; font-size: 12px">{{ app.app_code }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="申请理由" prop="request_reason">
          <el-input
            v-model="createForm.request_reason"
            type="textarea"
            :rows="4"
            placeholder="请简述申请该应用的原因"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">
          提交申请
        </el-button>
      </template>
    </el-dialog>

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
          {{ currentRequest.request_reason }}
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
        <el-descriptions-item v-if="currentRequest.admin_note" label="审核备注" :span="2">
          {{ currentRequest.admin_note }}
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
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/format'
import http from '@/utils/http'

interface AppRequest {
  request_id: string
  application_id: string
  app_code: string
  app_name: string
  request_reason: string
  status: string
  admin_note?: string
  reviewed_by?: string
  reviewed_at?: string
  created_at: string
}

interface Application {
  id: string
  app_code: string
  app_name: string
  description?: string
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

// 创建申请相关
const createDialogVisible = ref(false)
const createFormRef = ref<FormInstance>()
const submitting = ref(false)
const availableApplications = ref<Application[]>([])

const createForm = reactive({
  application_id: '',
  request_reason: '',
})

const createRules: FormRules = {
  application_id: [
    { required: true, message: '请选择要申请的应用', trigger: 'change' },
  ],
  request_reason: [
    { required: true, message: '请输入申请理由', trigger: 'blur' },
    { min: 10, max: 500, message: '申请理由长度在10-500个字符', trigger: 'blur' },
  ],
}

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

    const response = await http.get('/operators/me/applications/requests', { params })
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

// 显示创建对话框
const showCreateDialog = async () => {
  try {
    // 获取所有可用应用列表（未授权的应用）
    const response = await http.get('/operators/me/applications/available')
    availableApplications.value = response.data.items || []

    if (availableApplications.value.length === 0) {
      ElMessage.warning('暂无可申请的应用')
      return
    }

    createDialogVisible.value = true
  } catch (error) {
    console.error('Failed to fetch available applications:', error)
    ElMessage.error('获取可申请应用列表失败')
  }
}

// 创建申请
const handleCreate = async () => {
  if (!createFormRef.value) return

  await createFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      submitting.value = true

      await http.post('/operators/me/applications/requests', {
        application_id: createForm.application_id,
        request_reason: createForm.request_reason,
      })

      ElMessage.success('申请提交成功，请等待管理员审核')
      createDialogVisible.value = false

      // 重置表单并刷新列表
      createFormRef.value?.resetFields()
      await fetchRequests()
    } catch (error: any) {
      console.error('Create request failed:', error)
    } finally {
      submitting.value = false
    }
  })
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

.filter-form {
  margin-bottom: 20px;
}
</style>
