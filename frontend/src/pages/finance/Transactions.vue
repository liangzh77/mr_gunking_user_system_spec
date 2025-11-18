<template>
  <div class="transactions-page">
    <!-- 页面标题 -->
    <el-card class="header-card">
      <div class="header-content">
        <div class="title-section">
          <el-icon :size="24"><Coin /></el-icon>
          <h2>交易记录</h2>
        </div>
      </div>
    </el-card>

    <!-- 筛选条件 -->
    <el-card class="filter-card" style="margin-top: 20px">
      <el-form :model="filterForm" label-width="80px" :inline="true">
        <el-form-item label="运营商">
          <el-select
            v-model="filterForm.operator_id"
            placeholder="全部运营商"
            clearable
            filterable
            style="width: 200px"
          >
            <el-option
              v-for="op in operators"
              :key="op.id"
              :label="`${op.full_name} (${op.username})`"
              :value="op.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="交易类型">
          <el-select
            v-model="filterForm.transaction_type"
            placeholder="全部类型"
            clearable
            style="width: 150px"
          >
            <el-option label="充值" value="recharge" />
            <el-option label="消费" value="consumption" />
            <el-option label="退款" value="refund" />
          </el-select>
        </el-form-item>

        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 380px"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><RefreshLeft /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 交易记录列表 -->
    <el-card class="list-card" style="margin-top: 20px">
      <el-table
        v-copyable
        v-loading="loading"
        :data="transactions"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="transaction_id" label="交易ID" width="220" show-overflow-tooltip />
        <el-table-column prop="operator_name" label="运营商" width="150" show-overflow-tooltip />
        <el-table-column prop="transaction_type" label="交易类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTransactionTypeTag(row)" size="small">
              {{ getTransactionTypeLabel(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="交易金额" width="150">
          <template #default="{ row }">
            <span :class="getAmountClass(row.transaction_type)">
              {{ getAmountDisplay(row.transaction_type, row.amount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="balance_before" label="交易前余额" width="120">
          <template #default="{ row }">
            ¥{{ row.balance_before }}
          </template>
        </el-table-column>
        <el-table-column prop="balance_after" label="交易后余额" width="120">
          <template #default="{ row }">
            ¥{{ row.balance_after }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="交易时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && transactions.length === 0" class="empty-state">
        <el-empty description="暂无交易记录" />
      </div>

      <!-- 分页 -->
      <div v-if="pagination.total > 0" class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="loadTransactions"
          @size-change="handlePageSizeChange"
        />
      </div>
    </el-card>

    <!-- 统计信息 -->
    <el-card v-if="transactions.length > 0" style="margin-top: 20px">
      <div class="statistics">
        <div class="stat-item">
          <div class="stat-label">总记录数</div>
          <div class="stat-value">{{ pagination.total }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">当前页记录</div>
          <div class="stat-value">{{ transactions.length }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">充值总额</div>
          <div class="stat-value recharge-total">+¥{{ pageRechargeTotal }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">消费总额</div>
          <div class="stat-value billing-total">-¥{{ pageBillingTotal }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">退款总额</div>
          <div class="stat-value refund-total">-¥{{ pageRefundTotal }}</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { formatDateTime } from '@/utils/format'
import http from '@/utils/http'

const loading = ref(false)
const transactions = ref<any[]>([])
const operators = ref<any[]>([])
const dateRange = ref<[string, string] | null>(null)

const filterForm = ref({
  operator_id: '',
  transaction_type: '',
})

const pagination = ref({
  page: 1,
  page_size: 20,
  total: 0,
})

// 计算当前页各类交易总额
const pageRechargeTotal = computed(() => {
  return transactions.value
    .filter(t => t.transaction_type === 'recharge')
    .reduce((sum, t) => sum + parseFloat(t.amount), 0)
    .toFixed(2)
})

const pageBillingTotal = computed(() => {
  const total = transactions.value
    .filter(t => t.transaction_type === 'consumption')
    .reduce((sum, t) => sum + parseFloat(t.amount), 0)
  return Math.abs(total).toFixed(2)
})

const pageRefundTotal = computed(() => {
  const total = transactions.value
    .filter(t => t.transaction_type === 'refund')
    .reduce((sum, t) => sum + parseFloat(t.amount), 0)
  return Math.abs(total).toFixed(2)
})

// 获取交易类型标签
const getTransactionTypeTag = (row: any) => {
  const type = row.transaction_type

  // 如果是充值类型，根据description区分
  if (type === 'recharge') {
    if (row.description && row.description.includes('银行转账')) {
      return 'primary'  // 蓝色
    } else if (row.description && (row.description.includes('财务') || row.description.includes('手动'))) {
      return 'success'  // 绿色
    }
    return 'success'  // 默认绿色
  }

  const map: Record<string, any> = {
    consumption: 'warning',
    refund: 'info',
  }
  return map[type] || 'info'
}

// 获取交易类型标签文本
const getTransactionTypeLabel = (row: any) => {
  const type = row.transaction_type

  // 如果是充值类型，根据description区分
  if (type === 'recharge') {
    if (row.description && row.description.includes('银行转账')) {
      return '银行充值'
    } else if (row.description && (row.description.includes('财务') || row.description.includes('手动'))) {
      return '财务充值'
    }
    return '充值'
  }

  const map: Record<string, string> = {
    consumption: '消费',
    refund: '退款',
  }
  return map[type] || type
}

// 获取金额CSS类
const getAmountClass = (type: string) => {
  // 充值-绿色，消费-红色，退款-橙色
  if (type === 'recharge') return 'amount-recharge'
  if (type === 'consumption') return 'amount-consumption'
  if (type === 'refund') return 'amount-refund'
  return ''
}

// 获取金额显示
const getAmountDisplay = (type: string, amount: string) => {
  // 所有金额都是正数，不显示正负号
  const numAmount = parseFloat(amount)
  return `¥${numAmount.toFixed(2)}`
}

// 加载运营商列表
const loadOperators = async () => {
  try {
    const response = await http.get('/finance/operators', {
      params: {
        page: 1,
        page_size: 1000,
        status: 'active',
      },
    })
    operators.value = response.data.items || []
  } catch (error) {
    console.error('Load operators error:', error)
  }
}

// 加载交易记录
const loadTransactions = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.value.page,
      page_size: pagination.value.page_size,
    }

    if (filterForm.value.operator_id) {
      params.operator_id = filterForm.value.operator_id
    }

    if (filterForm.value.transaction_type) {
      params.transaction_type = filterForm.value.transaction_type
    }

    if (dateRange.value) {
      params.start_time = dateRange.value[0]
      params.end_time = dateRange.value[1]
    }

    const response = await http.get('/finance/transactions', { params })
    transactions.value = response.data.items || []
    pagination.value.total = response.data.total || 0
  } catch (error) {
    console.error('Load transactions error:', error)
    ElMessage.error('加载交易记录失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.value.page = 1
  loadTransactions()
}

// 重置
const handleReset = () => {
  dateRange.value = null
  filterForm.value = {
    operator_id: '',
    transaction_type: '',
  }
  pagination.value.page = 1
  loadTransactions()
}

// 页大小变化
const handlePageSizeChange = () => {
  pagination.value.page = 1
  loadTransactions()
}

onMounted(() => {
  loadOperators()
  loadTransactions()
})
</script>

<style scoped>
.transactions-page {
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

.filter-card :deep(.el-card__body) {
  padding: 20px;
}

.list-card :deep(.el-card__body) {
  padding: 20px;
}

.amount-recharge {
  color: #67C23A;
  font-weight: 600;
}

.amount-consumption {
  color: #F56C6C;
  font-weight: 600;
}

.amount-refund {
  color: #E6A23C;
  font-weight: 600;
}

.empty-state {
  padding: 40px 0;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.statistics {
  display: flex;
  gap: 40px;
  justify-content: center;
}

.stat-item {
  text-align: center;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.stat-value.recharge-total {
  color: #67C23A;
}

.stat-value.billing-total,
.stat-value.refund-total {
  color: #F56C6C;
}
</style>
