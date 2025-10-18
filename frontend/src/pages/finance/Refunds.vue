<template>
  <div class="refunds-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>退款审核</span>
          <el-button type="primary" size="small" @click="fetchRefunds">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <!-- 筛选条件 -->
      <div class="filter-container">
        <el-select v-model="queryParams.status" placeholder="状态" clearable @change="fetchRefunds" style="width: 150px">
          <el-option label="全部" value="" />
          <el-option label="待审核" value="pending" />
          <el-option label="已批准" value="approved" />
          <el-option label="已拒绝" value="rejected" />
        </el-select>

        <el-input
          v-model="queryParams.search"
          placeholder="搜索运营商名称或退款ID"
          clearable
          @keyup.enter="fetchRefunds"
          style="width: 300px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-button type="primary" @click="fetchRefunds">查询</el-button>
      </div>

      <!-- 退款列表 -->
      <el-table :data="refunds" v-loading="loading" stripe>
        <el-table-column prop="refund_id" label="退款ID" width="120" />
        <el-table-column prop="operator_name" label="运营商" />
        <el-table-column prop="amount" label="退款金额" align="right">
          <template #default="scope">
            ¥{{ scope.row.amount }}
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="退款原因" />
        <el-table-column prop="requested_at" label="申请时间" width="160" />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusLabel(scope.row.status) }}
            </el-tag>
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
          @current-change="fetchRefunds"
          @size-change="fetchRefunds"
        />
      </div>
    </el-card>

    <!-- 退款详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="退款详情" width="600px">
      <el-descriptions :column="2" border v-if="currentRefund">
        <el-descriptions-item label="退款ID">{{ currentRefund.refund_id }}</el-descriptions-item>
        <el-descriptions-item label="运营商">{{ currentRefund.operator_name }}</el-descriptions-item>
        <el-descriptions-item label="退款金额">¥{{ currentRefund.amount }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentRefund.status)">
            {{ getStatusLabel(currentRefund.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="申请时间" :span="2">{{ currentRefund.requested_at }}</el-descriptions-item>
        <el-descriptions-item label="退款原因" :span="2">{{ currentRefund.reason }}</el-descriptions-item>
        <el-descriptions-item label="审核人" v-if="currentRefund.reviewed_by">
          {{ currentRefund.reviewed_by }}
        </el-descriptions-item>
        <el-descriptions-item label="审核时间" v-if="currentRefund.reviewed_at">
          {{ currentRefund.reviewed_at }}
        </el-descriptions-item>
        <el-descriptions-item label="拒绝原因" :span="2" v-if="currentRefund.reject_reason">
          {{ currentRefund.reject_reason }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 拒绝退款对话框 -->
    <el-dialog v-model="rejectDialogVisible" title="拒绝退款" width="500px">
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

// 查询参数
const queryParams = reactive({
  status: '',
  search: '',
  page: 1,
  page_size: 20,
})

// 退款列表
const refunds = ref<any[]>([])
const total = ref(0)
const loading = ref(false)

// 对话框
const detailDialogVisible = ref(false)
const rejectDialogVisible = ref(false)
const currentRefund = ref<any>(null)

// 拒绝表单
const rejectFormRef = ref<FormInstance>()
const rejectForm = reactive({
  reject_reason: '',
})
const rejectRules: FormRules = {
  reject_reason: [
    { required: true, message: '请输入拒绝原因', trigger: 'blur' },
    { min: 10, message: '拒绝原因至少10个字符', trigger: 'blur' },
  ],
}
const rejecting = ref(false)

// 获取退款列表
const fetchRefunds = async () => {
  loading.value = true
  try {
    const response = await http.get('/v1/finance/refunds', {
      params: queryParams,
    })
    refunds.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error: any) {
    ElMessage.error('获取退款列表失败')
  } finally {
    loading.value = false
  }
}

// 查看详情
const handleView = (refund: any) => {
  currentRefund.value = refund
  detailDialogVisible.value = true
}

// 批准退款
const handleApprove = async (refund: any) => {
  try {
    await ElMessageBox.confirm(`确定批准退款 ¥${refund.amount} 吗?`, '确认批准', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'success',
    })

    await http.post(`/v1/finance/refunds/${refund.refund_id}/approve`)
    ElMessage.success('退款已批准')
    fetchRefunds()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('批准失败')
    }
  }
}

// 拒绝退款
const handleReject = (refund: any) => {
  currentRefund.value = refund
  rejectForm.reject_reason = ''
  rejectDialogVisible.value = true
}

// 确认拒绝
const confirmReject = async () => {
  if (!rejectFormRef.value) return

  try {
    await rejectFormRef.value.validate()
    rejecting.value = true

    await http.post(`/v1/finance/refunds/${currentRefund.value.refund_id}/reject`, {
      reject_reason: rejectForm.reject_reason,
    })

    ElMessage.success('已拒绝退款申请')
    rejectDialogVisible.value = false
    fetchRefunds()
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
  fetchRefunds()
})
</script>

<style scoped>
.refunds-page {
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

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
