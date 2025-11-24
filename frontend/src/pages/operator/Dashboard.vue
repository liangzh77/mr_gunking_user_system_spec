<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <!-- 账户余额卡片 -->
      <el-col :span="8">
        <el-card class="stat-card balance-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="24"><Wallet /></el-icon>
              <span>账户余额</span>
            </div>
          </template>
          <div class="stat-value copyable-stat" @click="handleCopyValue(`¥${formatAmount(balance)}`)">
            ¥{{ formatAmount(balance) }}
          </div>
          <div class="stat-footer">
            <el-button type="primary" size="small" @click="goToRecharge">立即充值</el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 累计消费卡片 -->
      <el-col :span="8">
        <el-card class="stat-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="24"><TrendCharts /></el-icon>
              <span>累计消费</span>
            </div>
          </template>
          <div class="stat-value copyable-stat" @click="handleCopyValue(`¥${formatAmount(totalSpent)}`)">
            ¥{{ formatAmount(totalSpent) }}
          </div>
          <div class="stat-footer">
            <span class="stat-label">客户等级:</span>
            <el-tag :type="tierTagType" size="small">{{ tierLabel }}</el-tag>
          </div>
        </el-card>
      </el-col>

      <!-- 运营点数量卡片 -->
      <el-col :span="8">
        <el-card class="stat-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="24"><OfficeBuilding /></el-icon>
              <span>运营点数量</span>
            </div>
          </template>
          <div class="stat-value copyable-stat" @click="handleCopyValue(sitesCount)">
            {{ sitesCount }}
          </div>
          <div class="stat-footer">
            <el-button type="primary" size="small" plain @click="goToSites">查看详情</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近交易记录 -->
    <el-card class="recent-card" style="margin-top: 20px">
      <template #header>
        <div class="card-header-row">
          <span class="card-title">
            <el-icon><List /></el-icon>
            最近交易记录
          </span>
          <el-button type="primary" text @click="goToTransactions">查看更多</el-button>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="recentTransactions"
        v-copyable
        stripe
        style="width: 100%"
      >
        <el-table-column prop="created_at" label="交易时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="transaction_type" label="交易类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTransactionTypeTag(row.transaction_type)" size="small">
              {{ getTransactionTypeLabel(row.transaction_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="150">
          <template #default="{ row }">
            <span :class="getAmountClass(row.transaction_type)">
              {{ getAmountDisplay(row.transaction_type, row.amount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="balance_after" label="余额" width="150" />
        <el-table-column prop="description" label="描述" min-width="200" />
      </el-table>

      <div v-if="!loading && recentTransactions.length === 0" class="empty-state">
        <el-empty description="暂无交易记录" />
      </div>
    </el-card>

    <!-- 快捷操作 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <span class="card-title">
          <el-icon><Grid /></el-icon>
          快捷操作
        </span>
      </template>
      <el-row :gutter="16">
        <el-col :span="6">
          <div class="quick-action" @click="goToRecharge">
            <el-icon :size="32" color="#409EFF"><CreditCard /></el-icon>
            <span>在线充值</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="quick-action" @click="goToSites">
            <el-icon :size="32" color="#67C23A"><MapLocation /></el-icon>
            <span>运营点管理</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="quick-action" @click="goToStatistics">
            <el-icon :size="32" color="#E6A23C"><DataAnalysis /></el-icon>
            <span>统计分析</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="quick-action" @click="goToRefunds">
            <el-icon :size="32" color="#F56C6C"><RefreshLeft /></el-icon>
            <span>申请退款</span>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useOperatorStore } from '@/stores/operator'
import type { Transaction } from '@/types'
import { formatDateTime, formatAmount } from '@/utils/format'
import { copyToClipboard } from '@/utils/clipboard'

const router = useRouter()
const authStore = useAuthStore()
const operatorStore = useOperatorStore()

const loading = ref(false)
const balance = ref('0.00')
const totalSpent = ref('0.00')
const sitesCount = ref(0)
const recentTransactions = ref<Transaction[]>([])

// 客户等级标签
const tierTagType = computed(() => {
  switch (authStore.profile?.customer_tier) {
    case 'vip':
      return 'danger'
    case 'regular':
      return 'success'
    case 'trial':
      return 'info'
    default:
      return 'info'
  }
})

const tierLabel = computed(() => {
  switch (authStore.profile?.customer_tier) {
    case 'vip':
      return 'VIP客户'
    case 'regular':
      return '普通客户'
    case 'trial':
      return '试用客户'
    default:
      return '未知'
  }
})

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
  // 充值是加钱（绿色），消费和退款都是减钱（红色）
  return type === 'recharge' ? 'amount-positive' : 'amount-negative'
}

// 获取金额显示
const getAmountDisplay = (type: string, amount: string) => {
  // 后端返回的amount已经带有正负号（充值为正数，消费和退款为负数）
  const numAmount = parseFloat(amount)
  const absAmount = Math.abs(numAmount).toFixed(2)
  const prefix = numAmount >= 0 ? '+' : '-'
  return `${prefix}¥${absAmount}`
}

// 复制值到剪贴板
const handleCopyValue = async (value: string | number) => {
  const text = String(value)
  const success = await copyToClipboard(text)
  if (success) {
    ElMessage.success({
      message: '已复制',
      duration: 1000,
      showClose: false,
    })
  } else {
    ElMessage.error('复制失败')
  }
}

// 页面跳转
const goToRecharge = () => router.push('/operator/recharge')
const goToSites = () => router.push('/operator/sites')
const goToStatistics = () => router.push('/operator/statistics')
const goToRefunds = () => router.push('/operator/refunds')
const goToTransactions = () => router.push('/operator/transactions')

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    // 并行加载余额、运营点、交易记录
    const [balanceData, sitesData, transactionsData] = await Promise.all([
      operatorStore.getBalance(),
      operatorStore.getSites(),
      operatorStore.getTransactions({ page: 1, page_size: 5 }),
    ])

    balance.value = balanceData.balance
    totalSpent.value = balanceData.total_spent || '0.00'
    sitesCount.value = sitesData.length
    recentTransactions.value = transactionsData.items
  } catch (error) {
    console.error('Load data error:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

.stat-card {
  height: 200px;
}

.stat-card .card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: #303133;
  margin: 20px 0;
}

.balance-card .stat-value {
  color: #409EFF;
}

.stat-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.recent-card :deep(.el-card__header) {
  padding: 16px 20px;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
}

.amount-positive {
  color: #67C23A;
  font-weight: 500;
}

.amount-negative {
  color: #F56C6C;
  font-weight: 500;
}

.empty-state {
  padding: 40px 0;
}

.quick-action {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px;
  border-radius: 8px;
  background-color: #f5f7fa;
  cursor: pointer;
  transition: all 0.3s;
}

.quick-action:hover {
  background-color: #e6e8eb;
  transform: translateY(-2px);
}

.quick-action span {
  font-size: 14px;
  color: #606266;
}

.copyable-stat {
  cursor: copy;
  border-radius: 4px;
  transition: all 0.2s;
}

.copyable-stat:hover {
  background-color: rgba(64, 158, 255, 0.1);
}
</style>
