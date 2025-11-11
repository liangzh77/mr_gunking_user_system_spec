<template>
  <div class="recharge-records-page">
    <!-- 页面标题和操作 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>充值记录</span>
          <el-button type="primary" :icon="RefreshIcon" @click="fetchRecords">刷新</el-button>
        </div>
      </template>

      <!-- 筛选条件 -->
      <el-form :model="queryForm" :inline="true" class="filter-form">
        <el-form-item label="运营商">
          <el-select
            v-model="queryForm.operator_id"
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

        <el-form-item label="充值时间">
          <el-date-picker
            v-model="queryForm.date_range"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 240px"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleQuery">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 充值记录表格 -->
      <el-table :data="records" v-loading="loading" border stripe>
        <el-table-column prop="transaction_id" label="交易ID" width="300" show-overflow-tooltip />
        <el-table-column prop="operator_name" label="运营商" width="180">
          <template #default="{ row }">
            <div>{{ row.operator_name }}</div>
            <div style="color: #909399; font-size: 12px">{{ row.operator_username }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="充值金额" width="120" align="right">
          <template #default="{ row }">
            <span style="color: #67c23a; font-weight: bold">+¥{{ row.amount }}</span>
          </template>
        </el-table-column>
        <el-table-column label="余额变动" width="200" align="right">
          <template #default="{ row }">
            <div style="font-size: 12px">
              <span>¥{{ row.balance_before }}</span>
              <el-icon style="margin: 0 4px"><Right /></el-icon>
              <span style="color: #67c23a; font-weight: bold">¥{{ row.balance_after }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="recharge_method" label="充值方式" width="120">
          <template #default="{ row }">
            <el-tag :type="row.recharge_method === '手动充值' ? 'warning' : 'success'">
              {{ row.recharge_method }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column prop="created_at" label="充值时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleViewDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchRecords"
          @current-change="fetchRecords"
        />
      </div>
    </el-card>

    <!-- 充值详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="充值记录详情" width="600px">
      <el-descriptions :column="1" border v-if="currentRecord">
        <el-descriptions-item label="交易ID">{{ currentRecord.transaction_id }}</el-descriptions-item>
        <el-descriptions-item label="运营商">
          {{ currentRecord.operator_name }} ({{ currentRecord.operator_username }})
        </el-descriptions-item>
        <el-descriptions-item label="充值金额">
          <span style="color: #67c23a; font-weight: bold; font-size: 18px">¥{{ currentRecord.amount }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="充值前余额">¥{{ currentRecord.balance_before }}</el-descriptions-item>
        <el-descriptions-item label="充值后余额">¥{{ currentRecord.balance_after }}</el-descriptions-item>
        <el-descriptions-item label="充值方式">
          <el-tag :type="currentRecord.recharge_method === '手动充值' ? 'warning' : 'success'">
            {{ currentRecord.recharge_method }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="支付信息" v-if="currentRecord.payment_info">
          <div>
            <div>支付渠道: {{ currentRecord.payment_info.channel === 'wechat' ? '微信支付' : '支付宝' }}</div>
            <div>订单号: {{ currentRecord.payment_info.order_no }}</div>
            <div>状态: {{ currentRecord.payment_info.status }}</div>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="备注">{{ currentRecord.description || '无' }}</el-descriptions-item>
        <el-descriptions-item label="充值时间">{{ formatDateTime(currentRecord.created_at) }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh as RefreshIcon, Right } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/format'
import http from '@/utils/http'

// 查询表单
const queryForm = reactive({
  operator_id: '',
  date_range: [] as string[],
})

// 分页信息
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

// 数据
const records = ref<any[]>([])
const operators = ref<any[]>([])
const loading = ref(false)

// 详情对话框
const detailDialogVisible = ref(false)
const currentRecord = ref<any>(null)

// 获取充值记录列表
const fetchRecords = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.page_size,
    }

    if (queryForm.operator_id) {
      params.operator_id = queryForm.operator_id
    }

    if (queryForm.date_range && queryForm.date_range.length === 2) {
      params.start_date = queryForm.date_range[0]
      params.end_date = queryForm.date_range[1]
    }

    const response = await http.get('/finance/recharge-records', { params })
    records.value = response.data.items || []
    pagination.total = response.data.total || 0
  } catch (error: any) {
    console.error('获取充值记录失败:', error)
    ElMessage.error('获取充值记录失败')
  } finally {
    loading.value = false
  }
}

// 获取运营商列表（用于筛选）
const fetchOperators = async () => {
  try {
    const response = await http.get('/finance/operators', {
      params: {
        page: 1,
        page_size: 1000,
        status: 'active',
      },
    })
    operators.value = response.data.items || []
  } catch (error: any) {
    console.error('获取运营商列表失败:', error)
  }
}

// 查询
const handleQuery = () => {
  pagination.page = 1
  fetchRecords()
}

// 重置
const handleReset = () => {
  queryForm.operator_id = ''
  queryForm.date_range = []
  pagination.page = 1
  fetchRecords()
}

// 查看详情
const handleViewDetail = (row: any) => {
  currentRecord.value = row
  detailDialogVisible.value = true
}

// 页面加载
onMounted(() => {
  fetchOperators()
  fetchRecords()
})
</script>

<style scoped>
.recharge-records-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-form {
  margin-bottom: 16px;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

pre {
  background-color: #f5f7fa;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
}
</style>
