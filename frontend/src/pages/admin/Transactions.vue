<template>
  <div class="transactions-page">
    <!-- 页面标题 -->
    <el-card class="header-card">
      <div class="header-content">
        <div class="title-section">
          <el-icon :size="24"><Coin /></el-icon>
          <h2>充值记录管理</h2>
        </div>
      </div>
    </el-card>

    <!-- 筛选条件 -->
    <el-card class="filter-card" style="margin-top: 20px">
      <el-form :model="filterForm" label-width="80px" :inline="true">
        <el-form-item label="搜索">
          <el-input
            v-model="searchQuery"
            placeholder="搜索交易ID或描述..."
            clearable
            @keyup.enter="handleSearch"
            @clear="handleSearch"
            style="width: 300px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="运营商">
          <el-select
            v-model="filterForm.operator_id"
            placeholder="全部运营商"
            clearable
            filterable
            style="width: 200px"
          >
            <el-option
              v-for="operator in operators"
              :key="operator.id"
              :label="operator.username"
              :value="operator.id"
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
            <el-option label="财务扣费" value="deduct" />
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

    <!-- 数据表格 -->
    <el-card class="list-card" style="margin-top: 20px">
      <el-table
        v-copyable
        :data="tableData"
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="交易ID" width="220" show-overflow-tooltip />
        <el-table-column prop="operator_name" label="运营商" width="150" />
        <el-table-column prop="transaction_type" label="交易类型" width="120">
          <template #default="{ row }">
            <el-tag
              :type="getTransactionTypeTag(row)"
              size="small"
            >
              {{ getTransactionTypeText(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="交易金额" width="120" align="right">
          <template #default="{ row }">
            <span :class="getAmountClass(row.transaction_type)">
              {{ formatAmount(row.amount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="balance_after" label="余额" width="120" align="right">
          <template #default="{ row }">
            {{ formatAmount(row.balance_after) }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="created_at" label="交易时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Coin, Search, RefreshLeft } from '@element-plus/icons-vue'
import http from '@/utils/http'
import { formatDateTime } from '@/utils/format'

interface Transaction {
  id: string
  operator_id: string
  operator_name: string
  transaction_type: string
  amount: string
  balance_after: string
  description: string
  created_at: string
  status: string
}

interface Operator {
  id: string
  username: string
  full_name: string
}

interface FilterForm {
  operator_id: string
  transaction_type: string
  start_time: string
  end_time: string
}

// 响应式数据
const loading = ref(false)
const tableData = ref<Transaction[]>([])
const operators = ref<Operator[]>([])
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dateRange = ref<string[]>([])

const filterForm = reactive<FilterForm>({
  operator_id: '',
  transaction_type: '',
  start_time: '',
  end_time: '',
})

// 获取运营商列表
const fetchOperators = async () => {
  try {
    const response = await http.get('/admins/operators', {
      params: {
        page: 1,
        page_size: 100,  // 修改为100，符合后端最大限制
      },
    })
    operators.value = response.data.items || []
  } catch (error) {
    console.error('获取运营商列表失败:', error)
  }
}

// 获取交易记录
const fetchTransactions = async () => {
  try {
    loading.value = true

    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value,
    }

    if (searchQuery.value) {
      params.search = searchQuery.value
    }

    if (filterForm.operator_id) {
      params.operator_id = filterForm.operator_id
    }

    if (filterForm.transaction_type) {
      params.transaction_type = filterForm.transaction_type
    }

    if (dateRange.value && dateRange.value.length === 2) {
      params.start_time = dateRange.value[0]
      params.end_time = dateRange.value[1]
    }

    const response = await http.get('/admins/transactions', { params })
    tableData.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error: any) {
    console.error('获取交易记录失败:', error)
    ElMessage.error('获取交易记录失败')
  } finally {
    loading.value = false
  }
}

// 查询
const handleSearch = () => {
  currentPage.value = 1
  fetchTransactions()
}

// 重置
const handleReset = () => {
  searchQuery.value = ''
  filterForm.operator_id = ''
  filterForm.transaction_type = ''
  dateRange.value = []
  filterForm.start_time = ''
  filterForm.end_time = ''
  currentPage.value = 1
  fetchTransactions()
}

// 分页大小变化
const handleSizeChange = (size: number) => {
  pageSize.value = size
  fetchTransactions()
}

// 页码变化
const handleCurrentChange = (page: number) => {
  currentPage.value = page
  fetchTransactions()
}

// 工具函数
const getTransactionTypeTag = (row: any) => {
  const type = row.transaction_type

  // 如果是充值类型，根据payment_channel区分
  if (type === 'recharge') {
    if (row.payment_channel === 'bank_transfer') {
      return 'primary'  // 银行充值 - 蓝色
    } else if (row.payment_channel === 'wechat') {
      return 'success'  // 微信充值 - 绿色
    } else if (row.payment_channel) {
      return 'success'  // 在线充值 - 绿色
    }
    return 'warning'  // 财务充值 - 橙色
  }

  const typeMap: Record<string, string> = {
    consumption: 'danger',
    refund: 'warning',
    deduct: 'danger',  // 财务扣费 - 红色
  }
  return typeMap[type] || 'info'
}

const getTransactionTypeText = (row: any) => {
  const type = row.transaction_type

  // 如果是充值类型，根据payment_channel区分
  if (type === 'recharge') {
    if (row.payment_channel === 'wechat') {
      return '微信充值'
    } else if (row.payment_channel === 'bank_transfer') {
      return '银行充值'
    } else if (row.payment_channel) {
      return '在线充值'
    }
    // payment_channel为空表示手动充值
    return '财务充值'
  }

  const typeMap: Record<string, string> = {
    consumption: '消费',
    refund: '退款',
    deduct: '财务扣费',
  }
  return typeMap[type] || type
}

const formatAmount = (amount: string) => {
  const num = parseFloat(amount)
  return `¥${num.toFixed(2)}`
}

// 获取金额CSS类
const getAmountClass = (type: string) => {
  // 充值-绿色，消费-红色，退款-橙色
  if (type === 'recharge') return 'amount-recharge'
  if (type === 'consumption') return 'amount-consumption'
  if (type === 'refund') return 'amount-refund'
  return ''
}

// 生命周期
onMounted(() => {
  fetchOperators()
  fetchTransactions()
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

.list-card :deep(.el-card__body) {
  padding: 20px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
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
</style>