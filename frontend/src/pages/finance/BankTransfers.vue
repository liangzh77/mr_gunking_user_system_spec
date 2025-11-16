<template>
  <div class="bank-transfers-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>银行转账审核</span>
          <el-button type="primary" size="small" @click="fetchTransfers">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <!-- 筛选条件 -->
      <div class="filter-container">
        <el-select v-model="queryParams.status" placeholder="状态" clearable @change="fetchTransfers" style="width: 150px">
          <el-option label="全部" value="" />
          <el-option label="待审核" value="pending" />
          <el-option label="已批准" value="approved" />
          <el-option label="已拒绝" value="rejected" />
          <el-option label="已取消" value="cancelled" />
        </el-select>

        <el-input
          v-model="queryParams.search"
          placeholder="搜索运营商名称或申请ID"
          clearable
          @keyup.enter="fetchTransfers"
          style="width: 300px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 240px"
          @change="handleDateChange"
        />

        <el-button type="primary" @click="fetchTransfers">查询</el-button>
      </div>

      <!-- 银行转账申请列表 -->
      <el-table :data="transfers" v-loading="loading" stripe>
        <el-table-column label="申请ID" width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.application_id }}
          </template>
        </el-table-column>
        <el-table-column prop="operator_name" label="运营商" width="150" />
        <el-table-column prop="operator_username" label="用户名" width="120" />
        <el-table-column prop="amount" label="充值金额" width="120" align="right">
          <template #default="{ row }">
            <span class="amount-text">¥{{ row.amount }}</span>
          </template>
        </el-table-column>
        <el-table-column label="转账凭证" width="120" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewVoucher(row)">
              查看凭证
            </el-button>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.remark">{{ row.remark }}</span>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reject_reason" label="拒绝原因" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.reject_reason" class="reject-reason">{{ row.reject_reason }}</span>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending'"
              type="success"
              size="small"
              @click="handleApprove(row)"
            >
              批准
            </el-button>
            <el-button
              v-if="row.status === 'pending'"
              type="danger"
              size="small"
              @click="handleReject(row)"
            >
              拒绝
            </el-button>
            <el-button
              v-if="['approved', 'rejected'].includes(row.status)"
              type="info"
              size="small"
              @click="viewDetails(row)"
            >
              查看详情
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
          @current-change="fetchTransfers"
          @size-change="fetchTransfers"
        />
      </div>
    </el-card>

    <!-- 转账凭证查看对话框 -->
    <el-dialog v-model="voucherDialogVisible" title="转账凭证" width="600px">
      <div class="voucher-view">
        <el-image
          :src="currentVoucher"
          fit="contain"
          style="width: 100%; max-height: 500px"
        >
          <template #error>
            <div class="image-error">
              <el-icon :size="60"><Picture /></el-icon>
              <div>图片加载失败</div>
            </div>
          </template>
        </el-image>
      </div>
    </el-dialog>

    <!-- 审核对话框（批准/拒绝） -->
    <el-dialog v-model="reviewDialogVisible" :title="reviewDialogTitle" width="500px">
      <el-form :model="reviewForm" :rules="reviewRules" ref="reviewFormRef">
        <!-- 批准时显示 -->
        <template v-if="reviewAction === 'approve'">
          <el-alert title="确认批准此转账申请？" type="success" :closable="false" />
          <div class="review-summary">
            <p>运营商：{{ currentTransfer?.operator_name }}</p>
            <p>充值金额：<span class="amount-highlight">¥{{ currentTransfer?.amount }}</span></p>
            <p>申请时间：{{ formatDateTime(currentTransfer?.created_at) }}</p>
            <p>备注：{{ currentTransfer?.remark || '无' }}</p>
          </div>
        </template>

        <!-- 拒绝时显示 -->
        <template v-if="reviewAction === 'reject'">
          <el-form-item label="拒绝原因" prop="reject_reason">
            <el-input
              v-model="reviewForm.reject_reason"
              type="textarea"
              :rows="4"
              placeholder="请输入拒绝原因"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button :type="reviewButtonType" @click="confirmReview" :loading="reviewing">
          {{ reviewButtonText }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Refresh, Search, Picture } from '@element-plus/icons-vue'
import http from '@/utils/http'
import { formatDateTime } from '@/utils/format'

// 查询参数
const queryParams = reactive({
  status: '',
  search: '',
  page: 1,
  page_size: 20,
  start_date: '',
  end_date: '',
})

// 日期范围
const dateRange = ref<[Date, Date] | null>(null)

// 银行转账列表
const transfers = ref<any[]>([])
const total = ref(0)
const loading = ref(false)

// 凭证查看对话框
const voucherDialogVisible = ref(false)
const currentVoucher = ref('')

// 审核对话框
const reviewDialogVisible = ref(false)
const currentTransfer = ref<any>(null)
const reviewAction = ref<'approve' | 'reject'>('approve')
const reviewing = ref(false)

// 审核表单
const reviewFormRef = ref<FormInstance>()
const reviewForm = reactive({
  reject_reason: '',
})
const reviewRules: FormRules = {
  reject_reason: [
    { required: true, message: '请输入拒绝原因', trigger: 'blur' },
    { min: 1, message: '拒绝原因至少1个字符', trigger: 'blur' },
    { max: 500, message: '拒绝原因不能超过500个字符', trigger: 'blur' },
  ],
}

// 计算属性
const reviewDialogTitle = computed(() => {
  return reviewAction.value === 'approve' ? '批准银行转账申请' : '拒绝银行转账申请'
})

const reviewButtonType = computed(() => {
  return reviewAction.value === 'approve' ? 'success' : 'danger'
})

const reviewButtonText = computed(() => {
  return reviewAction.value === 'approve' ? '确认批准' : '确认拒绝'
})

// 获取银行转账列表
const fetchTransfers = async () => {
  loading.value = true
  try {
    const response = await http.get('/finance/bank-transfers', {
      params: queryParams,
    })
    transfers.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error: any) {
    ElMessage.error('获取银行转账列表失败')
  } finally {
    loading.value = false
  }
}

// 处理日期变化
const handleDateChange = (dates: [Date, Date] | null) => {
  if (dates && dates.length === 2) {
    queryParams.start_date = dates[0].toISOString().split('T')[0]
    queryParams.end_date = dates[1].toISOString().split('T')[0]
  } else {
    queryParams.start_date = ''
    queryParams.end_date = ''
  }
}

// 查看凭证
const viewVoucher = (transfer: any) => {
  // 确保图片路径以 / 开头，避免相对路径问题
  const imagePath = transfer.voucher_image_url
  currentVoucher.value = imagePath.startsWith('/') ? imagePath : `/${imagePath}`
  voucherDialogVisible.value = true
}

// 批准转账
const handleApprove = (transfer: any) => {
  currentTransfer.value = transfer
  reviewAction.value = 'approve'
  reviewForm.reject_reason = ''
  reviewDialogVisible.value = true
}

// 拒绝转账
const handleReject = (transfer: any) => {
  currentTransfer.value = transfer
  reviewAction.value = 'reject'
  reviewForm.reject_reason = ''
  reviewDialogVisible.value = true
}

// 确认审核
const confirmReview = async () => {
  if (!reviewFormRef.value) return

  try {
    if (reviewAction.value === 'approve') {
      // 批准无需验证表单
      reviewing.value = true
    } else {
      // 拒绝需要验证表单
      await reviewFormRef.value.validate()
      reviewing.value = true
    }

    const url = `/finance/bank-transfers/${currentTransfer.value.application_id}/${reviewAction.value}`
    const payload = reviewAction.value === 'approve'
      ? {}
      : { reject_reason: reviewForm.reject_reason }

    await http.post(url, payload)

    ElMessage.success(reviewAction.value === 'approve' ? '转账申请已批准' : '已拒绝转账申请')
    reviewDialogVisible.value = false
    fetchTransfers()
  } catch (error: any) {
    if (!error.errors) {
      ElMessage.error(reviewAction.value === 'approve' ? '批准失败' : '拒绝失败')
    }
  } finally {
    reviewing.value = false
  }
}

// 查看详情
const viewDetails = (transfer: any) => {
  const statusText = getStatusLabel(transfer.status)
  const reviewedAt = transfer.reviewed_at ? formatDateTime(transfer.reviewed_at) : '未审核'

  ElMessageBox.alert(
    `<div style="line-height: 1.8;">
      <p><strong>申请ID：</strong>${transfer.application_id}</p>
      <p><strong>运营商：</strong>${transfer.operator_name} (${transfer.operator_username})</p>
      <p><strong>充值金额：</strong>¥${transfer.amount}</p>
      <p><strong>申请时间：</strong>${formatDateTime(transfer.created_at)}</p>
      <p><strong>备注：</strong>${transfer.remark || '无'}</p>
      <p><strong>状态：</strong>${statusText}</p>
      <p><strong>审核时间：</strong>${reviewedAt}</p>
      ${transfer.reject_reason ? `<p><strong>拒绝原因：</strong>${transfer.reject_reason}</p>` : ''}
    </div>`,
    '转账申请详情',
    {
      dangerouslyUseHTMLString: true,
    }
  )
}

// 状态标签
const getStatusType = (status: string) => {
  switch (status) {
    case 'pending': return 'warning'
    case 'approved': return 'success'
    case 'rejected': return 'danger'
    case 'cancelled': return 'info'
    default: return 'info'
  }
}

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'pending': return '待审核'
    case 'approved': return '已批准'
    case 'rejected': return '已拒绝'
    case 'cancelled': return '已取消'
    default: return '未知'
  }
}

// 页面加载时获取数据
onMounted(() => {
  fetchTransfers()
})
</script>

<style scoped>
.bank-transfers-page {
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
  flex-wrap: wrap;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.amount-text {
  color: #67c23a;
  font-weight: bold;
}

.empty-text {
  color: #909399;
}

.reject-reason {
  color: #f56c6c;
}

.voucher-view {
  text-align: center;
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #909399;
}

.review-summary {
  margin: 20px 0;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.review-summary p {
  margin: 8px 0;
  line-height: 1.6;
}

.amount-highlight {
  color: #67c23a;
  font-weight: bold;
  font-size: 16px;
}
</style>