<template>
  <div class="refunds-page">
    <!-- 页面标题 -->
    <el-card class="header-card">
      <div class="header-content">
        <div class="title-section">
          <el-icon :size="24"><RefreshLeft /></el-icon>
          <h2>退款管理</h2>
        </div>
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          申请退款
        </el-button>
      </div>
    </el-card>

    <!-- 退款申请列表 -->
    <el-card class="list-card" style="margin-top: 20px">
      <el-table
        v-loading="loading"
        :data="refunds"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="refund_id" label="退款ID" width="200" show-overflow-tooltip />
        <el-table-column prop="requested_amount" label="退款金额" width="120">
          <template #default="{ row }">
            <span class="refund-amount">¥{{ row.requested_amount }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="退款原因" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reject_reason" label="拒绝原因" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.reject_reason">{{ row.reject_reason }}</span>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending'"
              type="danger"
              size="small"
              text
              @click="handleCancel(row)"
            >
              取消
            </el-button>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && refunds.length === 0" class="empty-state">
        <el-empty description="暂无退款申请">
          <el-button type="primary" @click="handleCreate">申请退款</el-button>
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
          @current-change="loadRefunds"
          @size-change="handlePageSizeChange"
        />
      </div>
    </el-card>

    <!-- 创建退款申请对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="申请退款"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-alert
          title="退款说明"
          type="info"
          :closable="false"
          style="margin-bottom: 20px"
        >
          <template #default>
            <div>当前账户余额: ¥{{ balance }}</div>
            <div>您可以申请退还部分或全部余额，已消费金额不可退还</div>
          </template>
        </el-alert>

        <el-form-item label="退款金额" prop="amount">
          <el-input
            v-model="formData.amount"
            placeholder="请输入退款金额"
            type="number"
            step="0.01"
            min="0"
          >
            <template #prepend>¥</template>
          </el-input>
          <div class="form-tip">最大可退款金额: ¥{{ balance }}</div>
        </el-form-item>

        <el-form-item label="退款原因" prop="reason">
          <el-input
            v-model="formData.reason"
            type="textarea"
            :rows="4"
            placeholder="请详细说明退款原因"
            maxlength="500"
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
import type { Refund } from '@/types'
import { formatDateTime } from '@/utils/format'

const operatorStore = useOperatorStore()

const loading = ref(false)
const refunds = ref<Refund[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const balance = ref('0.00')

const formData = ref({
  amount: '',
  reason: '',
})

const pagination = ref({
  page: 1,
  page_size: 20,
  total: 0,
})

const formRules: FormRules = {
  amount: [
    { required: true, message: '请输入退款金额', trigger: 'blur' },
    {
      validator: (rule: any, value: any, callback: any) => {
        if (!value) {
          callback(new Error('请输入退款金额'))
          return
        }
        const num = Number(value)
        if (isNaN(num) || num <= 0) {
          callback(new Error('退款金额必须大于0'))
          return
        }
        const balanceNum = Number(balance.value)
        if (num > balanceNum) {
          callback(new Error(`退款金额不能超过当前余额 ¥${balance.value}`))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ],
  reason: [
    { required: true, message: '请输入退款原因', trigger: 'blur' },
    { min: 1, max: 500, message: '退款原因长度应在 1-500 个字符之间', trigger: 'blur' },
  ],
}

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  const map: Record<string, any> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
    completed: 'info',
  }
  return map[status] || 'info'
}

// 获取状态标签文本
const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝',
    completed: '已完成',
  }
  return map[status] || status
}

// 加载账户余额
const loadBalance = async () => {
  try {
    const response = await operatorStore.getBalance()
    balance.value = response.balance
  } catch (error) {
    console.error('Load balance error:', error)
  }
}

// 加载退款申请列表
const loadRefunds = async () => {
  loading.value = true
  try {
    const response = await operatorStore.getRefunds({
      page: pagination.value.page,
      page_size: pagination.value.page_size,
    })
    refunds.value = response.items
    pagination.value.total = response.total
  } catch (error) {
    console.error('Load refunds error:', error)
    ElMessage.error('加载退款申请失败')
  } finally {
    loading.value = false
  }
}

// 打开创建对话框
const handleCreate = async () => {
  // 先加载最新余额
  await loadBalance()

  formData.value = {
    amount: balance.value,
    reason: '',
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
    await operatorStore.applyRefund({
      amount: Number(formData.value.amount),
      reason: formData.value.reason,
    })
    ElMessage.success('退款申请已提交，请等待审核')

    dialogVisible.value = false
    await loadRefunds()
  } catch (error) {
    console.error('Submit refund error:', error)
    ElMessage.error('提交退款申请失败')
  } finally {
    submitting.value = false
  }
}

// 页大小变化
const handlePageSizeChange = () => {
  pagination.value.page = 1
  loadRefunds()
}

// 对话框关闭时重置表单
const handleDialogClose = () => {
  formRef.value?.resetFields()
}

// 取消退款申请
const handleCancel = async (refund: Refund) => {
  try {
    await ElMessageBox.confirm(
      `确定要取消这个退款申请吗？退款金额: ¥${refund.requested_amount}`,
      '取消退款申请',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await operatorStore.cancelRefund(refund.refund_id)
    ElMessage.success('退款申请已取消')
    await loadRefunds()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Cancel refund error:', error)
      ElMessage.error('取消退款申请失败')
    }
  }
}

onMounted(() => {
  loadBalance()
  loadRefunds()
})
</script>

<style scoped>
.refunds-page {
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

.refund-amount {
  color: #F56C6C;
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

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}
</style>
