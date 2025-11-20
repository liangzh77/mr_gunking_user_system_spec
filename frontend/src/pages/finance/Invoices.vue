<template>
  <div class="invoices-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>发票审核</span>
          <el-button type="primary" size="small" @click="fetchInvoices">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <!-- 筛选条件 -->
      <div class="filter-container">
        <el-select v-model="queryParams.status" placeholder="状态" clearable @change="fetchInvoices" style="width: 150px">
          <el-option label="全部" value="" />
          <el-option label="待审核" value="pending" />
          <el-option label="已批准" value="approved" />
          <el-option label="已拒绝" value="rejected" />
        </el-select>

        <el-input
          v-model="queryParams.search"
          placeholder="搜索运营商名称或发票ID"
          clearable
          @keyup.enter="fetchInvoices"
          style="width: 300px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-button type="primary" @click="fetchInvoices">查询</el-button>
      </div>

      <!-- 发票列表 -->
      <el-table v-copyable :data="invoices" v-loading="loading" stripe>
        <el-table-column prop="invoice_number" label="发票号码" width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.invoice_number" class="invoice-number">{{ row.invoice_number }}</span>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="operator_name" label="运营商" width="120" show-overflow-tooltip />
        <el-table-column prop="amount" label="开票金额" width="110" align="right">
          <template #default="scope">
            ¥{{ scope.row.amount }}
          </template>
        </el-table-column>
        <el-table-column prop="invoice_title" label="发票抬头" min-width="150" show-overflow-tooltip />
        <el-table-column prop="tax_id" label="税号" width="180" show-overflow-tooltip />
        <el-table-column prop="invoice_type" label="发票类型" width="80" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.invoice_type === 'vat_special' ? 'success' : 'info'" size="small">
              {{ scope.row.invoice_type === 'vat_special' ? '专用' : '普通' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="requested_at" label="申请时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.requested_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)" size="small">
              {{ getStatusLabel(scope.row.status) }}
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
        <el-table-column label="操作" width="200" align="center">
          <template #default="scope">
            <el-button
              v-if="scope.row.status === 'pending'"
              type="success"
              size="small"
              @click="handleApprove(scope.row)"
            >
              批准
            </el-button>
            <el-button
              v-if="scope.row.status === 'pending'"
              type="danger"
              size="small"
              @click="handleReject(scope.row)"
            >
              拒绝
            </el-button>
            <el-button
              type="info"
              size="small"
              @click="handleView(scope.row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="fetchInvoices"
          @size-change="fetchInvoices"
        />
      </div>
    </el-card>

    <!-- 发票详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="发票详情" width="700px">
      <el-descriptions :column="2" border v-if="currentInvoice">
        <el-descriptions-item label="发票ID">{{ currentInvoice.invoice_id }}</el-descriptions-item>
        <el-descriptions-item label="运营商">{{ currentInvoice.operator_name }}</el-descriptions-item>
        <el-descriptions-item label="发票类型">
          {{ currentInvoice.invoice_type === 'vat' ? '增值税专用发票' : '普通发票' }}
        </el-descriptions-item>
        <el-descriptions-item label="开票金额">¥{{ currentInvoice.amount }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentInvoice.status)">
            {{ getStatusLabel(currentInvoice.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="申请时间">{{ currentInvoice.requested_at }}</el-descriptions-item>

        <el-descriptions-item label="发票抬头" :span="2">{{ currentInvoice.invoice_title }}</el-descriptions-item>
        <el-descriptions-item label="税号" :span="2">{{ currentInvoice.tax_id }}</el-descriptions-item>

        <el-descriptions-item label="开户银行" v-if="currentInvoice.bank_name">
          {{ currentInvoice.bank_name }}
        </el-descriptions-item>
        <el-descriptions-item label="银行账号" v-if="currentInvoice.bank_account">
          {{ currentInvoice.bank_account }}
        </el-descriptions-item>
        <el-descriptions-item label="注册地址" :span="2" v-if="currentInvoice.registered_address">
          {{ currentInvoice.registered_address }}
        </el-descriptions-item>
        <el-descriptions-item label="注册电话" :span="2" v-if="currentInvoice.registered_phone">
          {{ currentInvoice.registered_phone }}
        </el-descriptions-item>

        <el-descriptions-item label="收件人" v-if="currentInvoice.receiver_name">
          {{ currentInvoice.receiver_name }}
        </el-descriptions-item>
        <el-descriptions-item label="联系电话" v-if="currentInvoice.receiver_phone">
          {{ currentInvoice.receiver_phone }}
        </el-descriptions-item>
        <el-descriptions-item label="邮寄地址" :span="2" v-if="currentInvoice.receiver_address">
          {{ currentInvoice.receiver_address }}
        </el-descriptions-item>

        <el-descriptions-item label="审核人" v-if="currentInvoice.reviewed_by">
          {{ currentInvoice.reviewed_by }}
        </el-descriptions-item>
        <el-descriptions-item label="审核时间" v-if="currentInvoice.reviewed_at">
          {{ currentInvoice.reviewed_at }}
        </el-descriptions-item>
        <el-descriptions-item label="拒绝原因" :span="2" v-if="currentInvoice.reject_reason">
          {{ currentInvoice.reject_reason }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 拒绝发票对话框 -->
    <el-dialog v-model="rejectDialogVisible" title="拒绝开票" width="500px">
      <el-form :model="rejectForm" :rules="rejectRules" ref="rejectFormRef">
        <el-form-item label="拒绝原因" prop="reject_reason">
          <el-input
            v-model="rejectForm.reject_reason"
            type="textarea"
            :rows="4"
            placeholder="请输入拒绝原因"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject" :loading="rejecting">确认拒绝</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import http from '@/utils/http'
import { formatDateTime } from '@/utils/format'

// 查询参数
const queryParams = reactive({
  status: '',
  search: '',
  page: 1,
  page_size: 20,
})

// 发票列表
const invoices = ref<any[]>([])
const total = ref(0)
const loading = ref(false)

// 对话框
const detailDialogVisible = ref(false)
const rejectDialogVisible = ref(false)
const currentInvoice = ref<any>(null)

// 拒绝表单
const rejectFormRef = ref<FormInstance>()
const rejectForm = reactive({
  reject_reason: '',
})
const rejectRules: FormRules = {
  reject_reason: [
    { required: true, message: '请输入拒绝原因', trigger: 'blur' },
    { min: 1, message: '拒绝原因至少1个字符', trigger: 'blur' },
  ],
}
const rejecting = ref(false)

// 获取发票列表
const fetchInvoices = async () => {
  loading.value = true
  try {
    const response = await http.get('/finance/invoices', {
      params: queryParams,
    })
    invoices.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error: any) {
    ElMessage.error('获取发票列表失败')
  } finally {
    loading.value = false
  }
}

// 查看详情
const handleView = (invoice: any) => {
  currentInvoice.value = invoice
  detailDialogVisible.value = true
}

// 批准发票
const handleApprove = async (invoice: any) => {
  try {
    await ElMessageBox.confirm(`确定批准开票 ¥${invoice.amount} 吗?`, '确认批准', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'success',
    })

    await http.post(`/finance/invoices/${invoice.invoice_id}/approve`, {})
    ElMessage.success('发票已批准')
    fetchInvoices()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('批准失败')
    }
  }
}

// 拒绝发票
const handleReject = (invoice: any) => {
  currentInvoice.value = invoice
  rejectForm.reject_reason = ''
  rejectDialogVisible.value = true
}

// 确认拒绝
const confirmReject = async () => {
  if (!rejectFormRef.value) return

  try {
    await rejectFormRef.value.validate()
    rejecting.value = true

    await http.post(`/finance/invoices/${currentInvoice.value.invoice_id}/reject`, {
      reason: rejectForm.reject_reason,
    })

    ElMessage.success('已拒绝开票申请')
    rejectDialogVisible.value = false
    fetchInvoices()
  } catch (error: any) {
    if (!error.errors) {
      ElMessage.error('拒绝失败')
    }
  } finally {
    rejecting.value = false
  }
}

// 状态标签
const getStatusType = (status: string) => {
  switch (status) {
    case 'pending': return 'warning'
    case 'approved': return 'success'
    case 'rejected': return 'danger'
    default: return 'info'
  }
}

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'pending': return '待审核'
    case 'approved': return '已批准'
    case 'rejected': return '已拒绝'
    default: return '未知'
  }
}

// 页面加载时获取数据
onMounted(() => {
  fetchInvoices()
})
</script>

<style scoped>
.invoices-page {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-container {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.invoice-number {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-text {
  color: #909399;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
