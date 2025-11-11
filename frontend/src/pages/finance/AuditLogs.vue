<template>
  <div class="audit-logs-page">
    <!-- 页面标题和操作 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>审计日志</span>
          <el-button type="primary" :icon="RefreshIcon" @click="fetchLogs">刷新</el-button>
        </div>
      </template>

      <!-- 筛选条件 -->
      <el-form :model="queryForm" :inline="true" class="filter-form">
        <el-form-item label="操作类型">
          <el-select v-model="queryForm.operation_type" placeholder="全部" clearable style="width: 150px">
            <el-option label="登录" value="login" />
            <el-option label="登出" value="logout" />
            <el-option label="审核" value="review" />
            <el-option label="导出" value="export" />
            <el-option label="查询" value="query" />
          </el-select>
        </el-form-item>

        <el-form-item label="操作人">
          <el-input v-model="queryForm.operator_name" placeholder="输入操作人用户名" clearable style="width: 200px" />
        </el-form-item>

        <el-form-item label="操作时间">
          <el-date-picker
            v-model="queryForm.date_range"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 240px"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleQuery">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 审计日志表格 -->
      <el-table :data="logs" v-loading="loading" border stripe>
        <el-table-column prop="log_id" label="日志ID" width="180" />
        <el-table-column prop="operator_name" label="操作人" width="120" />
        <el-table-column prop="operation_type" label="操作类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getOperationTypeTagType(row.operation_type)">
              {{ getOperationTypeText(row.operation_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operation_desc" label="操作描述" min-width="200" />
        <el-table-column prop="ip_address" label="IP地址" width="140" />
        <el-table-column prop="created_at" label="操作时间" width="180">
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
          :page-sizes="[20, 50, 100, 200]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchLogs"
          @current-change="fetchLogs"
        />
      </div>
    </el-card>

    <!-- 日志详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="审计日志详情" width="600px">
      <el-descriptions :column="1" border v-if="currentLog">
        <el-descriptions-item label="日志ID">{{ currentLog.log_id }}</el-descriptions-item>
        <el-descriptions-item label="操作人">{{ currentLog.operator_name }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">
          <el-tag :type="getOperationTypeTagType(currentLog.operation_type)">
            {{ getOperationTypeText(currentLog.operation_type) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="操作描述">{{ currentLog.operation_desc }}</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ currentLog.ip_address }}</el-descriptions-item>
        <el-descriptions-item label="User Agent">{{ currentLog.user_agent || '未记录' }}</el-descriptions-item>
        <el-descriptions-item label="操作时间">{{ currentLog.created_at }}</el-descriptions-item>
        <el-descriptions-item label="请求详情">
          <pre>{{ currentLog.request_data || '无' }}</pre>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Refresh as RefreshIcon } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import http from '@/utils/http'
import { formatDateTime } from '@/utils/format'

// 筛选表单
const queryForm = reactive({
  operation_type: '',
  operator_name: '',
  date_range: [] as Date[],
})

// 审计日志列表
const logs = ref<any[]>([])
const loading = ref(false)

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

// 详情对话框
const detailDialogVisible = ref(false)
const currentLog = ref<any>(null)

// 获取审计日志列表
const fetchLogs = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.page_size,
    }

    if (queryForm.operation_type) {
      params.operation_type = queryForm.operation_type
    }
    if (queryForm.operator_name) {
      params.operator_name = queryForm.operator_name
    }
    if (queryForm.date_range && queryForm.date_range.length === 2) {
      params.start_date = queryForm.date_range[0].toISOString().split('T')[0]
      params.end_date = queryForm.date_range[1].toISOString().split('T')[0]
    }

    const response = await http.get('/finance/audit-logs', { params })
    logs.value = response.data.items || []
    pagination.total = response.data.total || 0
  } catch (error: any) {
    console.error('Failed to fetch audit logs:', error)
    // 如果是404，不显示错误消息（后端未实现）
    if (error.response?.status !== 404) {
      ElMessage.error('获取审计日志失败')
    }
  } finally {
    loading.value = false
  }
}

// 查询
const handleQuery = () => {
  pagination.page = 1
  fetchLogs()
}

// 重置
const handleReset = () => {
  queryForm.operation_type = ''
  queryForm.operator_name = ''
  queryForm.date_range = []
  pagination.page = 1
  fetchLogs()
}

// 查看详情
const handleViewDetail = (log: any) => {
  currentLog.value = log
  detailDialogVisible.value = true
}

// 获取操作类型标签类型
const getOperationTypeTagType = (type: string): string => {
  const typeMap: Record<string, string> = {
    login: 'success',
    logout: 'info',
    review: 'warning',
    export: 'primary',
    query: '',
  }
  return typeMap[type] || ''
}

// 获取操作类型文本
const getOperationTypeText = (type: string): string => {
  const textMap: Record<string, string> = {
    login: '登录',
    logout: '登出',
    review: '审核',
    export: '导出',
    query: '查询',
  }
  return textMap[type] || type
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.audit-logs-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-form {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

pre {
  max-height: 300px;
  overflow: auto;
  background: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
}
</style>
