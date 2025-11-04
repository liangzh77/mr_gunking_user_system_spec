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
        v-loading="loading"
        :data="transactions"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="transaction_id" label="交易ID" width="200" show-overflow-tooltip />
        <el-table-column prop="transaction_type" label="交易类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTransactionTypeTag(row.transaction_type)" size="small">
              {{ getTransactionTypeLabel(row.transaction_type) }}
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
          <div class="stat-value refund-total">+¥{{ pageRefundTotal }}</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useOperatorStore } from '@/stores/operator'
import type { Transaction } from '@/types'
import dayjs from 'dayjs'

const operatorStore = useOperatorStore()

const loading = ref(false)
const transactions = ref<Transaction[]>([])
const dateRange = ref<[string, string] | null>(null)

const filterForm = ref({
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
  // 消费金额后端返回负数，这里取绝对值用于显示
  return Math.abs(total).toFixed(2)
})

const pageRefundTotal = computed(() => {
  return transactions.value
    .filter(t => t.transaction_type === 'refund')
    .reduce((sum, t) => sum + parseFloat(t.amount), 0)
    .toFixed(2)
})

// 格式化日期时间
const formatDateTime = (datetime: string) => {
  return dayjs(datetime).format('YYYY-MM-DD HH:mm:ss')
}

// 获取交易类型标签
const getTransactionTypeTag = (type: string) => {
  const map: Record<string, any> = {
    recharge: 'success',
    consumption: 'warning',
    refund: 'info',
  }
  return map[type] || 'info'
}

// 获取交易类型标签文本
const getTransactionTypeLabel = (type: string) => {
  const map: Record<string, string> = {
    recharge: '充值',
    consumption: '消费',
    refund: '退款',
  }
  return map[type] || type
}

// 获取金额CSS类
const getAmountClass = (type: string) => {
  return type === 'recharge' || type === 'refund' ? 'amount-positive' : 'amount-negative'
}

// 获取金额显示
const getAmountDisplay = (type: string, amount: string) => {
  // 后端返回的amount已经带有正负号（消费为负数，充值/退款为正数）
  const numAmount = parseFloat(amount)
  const absAmount = Math.abs(numAmount).toFixed(2)
  const prefix = numAmount >= 0 ? '+' : '-'
  return `${prefix}¥${absAmount}`
}

// 加载交易记录
const loadTransactions = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.value.page,
      page_size: pagination.value.page_size,
    }

    if (filterForm.value.transaction_type) {
      params.transaction_type = filterForm.value.transaction_type
    }

    if (dateRange.value) {
      params.start_time = dateRange.value[0]
      params.end_time = dateRange.value[1]
    }

    const response = await operatorStore.getTransactions(params)
    transactions.value = response.items
    pagination.value.total = response.total
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

.amount-positive {
  color: #67C23A;
  font-weight: 600;
}

.amount-negative {
  color: #F56C6C;
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

.stat-value.recharge-total,
.stat-value.refund-total {
  color: #67C23A;
}

.stat-value.billing-total {
  color: #F56C6C;
}
</style>
