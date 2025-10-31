<template>
  <div class="transactions-page">
    <!-- 页面标题 -->
    <el-card class="header-card">
      <div class="header-content">
        <div class="title-section">
          <el-icon :size="24"><Coin /></el-icon>
          <h2>交易记录管理</h2>
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
    <el-card style="margin-top: 20px">
      <el-table
        :data="tableData"
        v-loading="loading"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="交易ID" width="100" />
        <el-table-column prop="operator_name" label="运营商" width="150" />
        <el-table-column prop="transaction_type" label="交易类型" width="120">
          <template #default="{ row }">
            <el-tag
              :type="getTransactionTypeTag(row.transaction_type)"
              size="small"
            >
              {{ getTransactionTypeText(row.transaction_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="120" align="right">
          <template #default="{ row }">
            {{ formatAmount(row.amount) }}
          </template>
        </el-table-column>
        <el-table-column prop="balance_after" label="余额" width="120" align="right">
          <template #default="{ row }">
            {{ formatAmount(row.balance_after) }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="created_at" label="交易时间" width="180" />
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
const getTransactionTypeTag = (type: string) => {
  const typeMap: Record<string, string> = {
    recharge: 'success',
    consumption: 'danger',
    refund: 'warning',
  }
  return typeMap[type] || 'info'
}

const getTransactionTypeText = (type: string) => {
  const typeMap: Record<string, string> = {
    recharge: '充值',
    consumption: '消费',
    refund: '退款',
  }
  return typeMap[type] || type
}

const formatAmount = (amount: string) => {
  const num = parseFloat(amount)
  return `¥${num.toFixed(2)}`
}

// 生命周期
onMounted(() => {
  fetchOperators()
  fetchTransactions()
})
</script>

<style scoped>
.transactions-page {
  width: 100%;
}

.header-card {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-section h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>