<template>
  <div class="invoices-page">
    <!-- 页面标题 -->
    <el-card class="header-card">
      <div class="header-content">
        <div class="title-section">
          <el-icon :size="24"><Document /></el-icon>
          <h2>发票管理</h2>
        </div>
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          申请发票
        </el-button>
      </div>
    </el-card>

    <!-- 发票申请列表 -->
    <el-card class="list-card" style="margin-top: 20px">
      <el-table
        v-loading="loading"
        :data="invoices"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="invoice_number" label="发票号码" width="180">
          <template #default="{ row }">
            <span v-if="row.invoice_number">{{ row.invoice_number }}</span>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="开票金额" width="110" align="right">
          <template #default="{ row }">
            <span class="invoice-amount">¥{{ row.amount }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="invoice_title" label="发票抬头" min-width="150" show-overflow-tooltip />
        <el-table-column prop="tax_id" label="税号" width="180" show-overflow-tooltip />
        <el-table-column prop="invoice_type" label="发票类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.invoice_type === 'vat' ? 'success' : 'info'" size="small">
              {{ row.invoice_type === 'vat' ? '专用' : '普通' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reject_reason" label="拒绝原因" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.status === 'rejected' && row.reject_reason" class="reject-reason">
              {{ row.reject_reason }}
            </span>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button
                type="danger"
                size="small"
                text
                @click="handleCancel(row)"
              >
                取消
              </el-button>
            </template>
            <template v-else-if="row.status === 'issued' && row.invoice_url">
              <el-button
                type="primary"
                size="small"
                text
                @click="downloadInvoice(row)"
              >
                下载
              </el-button>
            </template>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && invoices.length === 0" class="empty-state">
        <el-empty description="暂无发票记录">
          <el-button type="primary" @click="handleCreate">申请发票</el-button>
        </el-empty>
      </div>

      <!-- 分页 -->
      <div v-if="pagination.total > 0" class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="loadInvoices"
          @size-change="handlePageSizeChange"
        />
      </div>
    </el-card>

    <!-- 创建发票申请对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="申请发票"
      width="600px"
      :close-on-press-escape="false"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="发票金额" prop="amount">
          <el-input
            v-model="formData.amount"
            placeholder="请输入发票金额"
            type="number"
            min="0"
            step="0.01"
          >
            <template #prefix>¥</template>
          </el-input>
        </el-form-item>

        <el-form-item label="发票抬头" prop="invoice_title">
          <el-input
            v-model="formData.invoice_title"
            placeholder="请输入发票抬头"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="税号" prop="tax_id">
          <el-input
            v-model="formData.tax_id"
            placeholder="请输入纳税人识别号（15-20位大写字母或数字）"
            maxlength="20"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          提交申请
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { useOperatorStore } from '@/stores/operator'
import type { Invoice } from '@/types'
import { formatDateTime } from '@/utils/format'

const operatorStore = useOperatorStore()

const loading = ref(false)
const invoices = ref<Invoice[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

const formData = ref({
  amount: '',
  invoice_title: '',
  tax_id: '',
})

const pagination = ref({
  page: 1,
  page_size: 20,
  total: 0,
})

const formRules: FormRules = {
  amount: [
    { required: true, message: '请输入发票金额', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        const amount = parseFloat(value)
        if (isNaN(amount)) {
          callback(new Error('请输入有效的金额'))
        } else if (amount <= 0) {
          callback(new Error('发票金额必须大于0'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  invoice_title: [
    { required: true, message: '请输入发票抬头', trigger: 'blur' },
    { min: 2, max: 100, message: '发票抬头长度应在 2-100 个字符之间', trigger: 'blur' },
  ],
  tax_id: [
    { required: true, message: '请输入税号', trigger: 'blur' },
    {
      pattern: /^[A-Z0-9]{15,20}$/,
      message: '税号格式不正确（应为15-20位大写字母或数字）',
      trigger: 'blur',
    },
  ],
}

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  const map: Record<string, any> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
    issued: 'info',
  }
  return map[status] || 'info'
}

// 获取状态标签文本
const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝',
    issued: '已开具',
  }
  return map[status] || status
}

// 加载发票列表
const loadInvoices = async () => {
  loading.value = true
  try {
    const response = await operatorStore.getInvoices({
      page: pagination.value.page,
      page_size: pagination.value.page_size,
    })
    invoices.value = response?.items || []
    pagination.value.total = response?.total || 0
  } catch (error) {
    console.error('Load invoices error:', error)
    ElMessage.error('加载发票列表失败')
    invoices.value = []
    pagination.value.total = 0
  } finally {
    loading.value = false
  }
}

// 打开创建对话框
const handleCreate = () => {
  formData.value = {
    amount: '',
    invoice_title: '',
    tax_id: '',
  }
  dialogVisible.value = true
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    await operatorStore.applyInvoice(formData.value)
    ElMessage.success('发票申请已提交，请等待审核')

    dialogVisible.value = false
    await loadInvoices()
  } catch (error) {
    console.error('Submit invoice error:', error)
    ElMessage.error('提交发票申请失败')
  } finally {
    submitting.value = false
  }
}

// 下载发票
const downloadInvoice = (invoice: Invoice) => {
  if (!invoice.invoice_url) return

  // 打开新窗口下载
  window.open(invoice.invoice_url, '_blank')
  ElMessage.success('发票下载中...')
}

// 取消发票申请
const handleCancel = async (invoice: Invoice) => {
  try {
    await ElMessageBox.confirm(
      '确定要取消这个发票申请吗？取消后将无法恢复。',
      '取消发票申请',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await operatorStore.cancelInvoice(invoice.invoice_id)
    ElMessage.success('发票申请已取消')
    await loadInvoices()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Cancel invoice error:', error)
      ElMessage.error('取消发票申请失败')
    }
  }
}

// 页大小变化
const handlePageSizeChange = () => {
  pagination.value.page = 1
  loadInvoices()
}

// 对话框关闭时重置表单
const handleDialogClose = () => {
  formRef.value?.resetFields()
}

onMounted(() => {
  loadInvoices()
})
</script>

<style scoped>
.invoices-page {
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

.list-card :deep(.el-card__body) {
  padding: 20px;
}

.invoice-amount {
  color: #409EFF;
  font-weight: 600;
}

.empty-text {
  color: #909399;
}

.empty-state {
  padding: 40px 0;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
