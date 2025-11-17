<template>
  <div class="recharge-records-page">
    <!-- 页面标题和操作 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>充值记录</span>
          <div class="header-actions">
            <el-button type="warning" :icon="Money" @click="showRechargeDialog = true">手动充值</el-button>
            <el-button type="primary" :icon="RefreshIcon" @click="fetchRecords">刷新</el-button>
          </div>
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

    <!-- 手动充值对话框 -->
    <el-dialog
      v-model="showRechargeDialog"
      title="手动充值"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="rechargeFormRef"
        :model="rechargeForm"
        :rules="rechargeRules"
        label-width="100px"
      >
        <el-form-item label="运营商" prop="operator_id">
          <el-select
            v-model="rechargeForm.operator_id"
            placeholder="请选择运营商"
            filterable
            clearable
            style="width: 100%"
            @change="handleOperatorChange"
          >
            <el-option
              v-for="operator in operators"
              :key="operator.id"
              :label="`${operator.username} (${operator.full_name})`"
              :value="operator.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="当前余额">
          <el-input
            v-model="currentOperatorBalance"
            placeholder="请先选择运营商"
            readonly
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="充值金额" prop="amount">
          <el-input-number
            v-model="rechargeForm.amount"
            :min="0.01"
            :max="999999.99"
            :precision="2"
            :step="100"
            controls-position="right"
            placeholder="请输入充值金额"
            style="width: 100%"
          />
          <div class="form-tip">充值金额必须大于0</div>
        </el-form-item>

        <el-form-item label="备注" prop="description">
          <el-input
            v-model="rechargeForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入充值备注（可选）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="付款凭证">
          <el-upload
            v-model:file-list="paymentFiles"
            :auto-upload="false"
            :limit="1"
            :on-exceed="handleExceed"
            :before-upload="beforeUpload"
            accept=".jpg,.jpeg,.png,.pdf"
            list-type="picture-card"
          >
            <el-icon><Plus /></el-icon>
            <div class="el-upload__text">上传凭证</div>
          </el-upload>
          <div class="form-tip">支持 JPG、PNG、PDF 格式，最大 5MB</div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showRechargeDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="rechargeLoading"
          @click="handleRechargeSubmit"
        >
          确认充值
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type UploadFile } from 'element-plus'
import { Refresh as RefreshIcon, Right, Money, Plus } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/format'
import http from '@/utils/http'

const route = useRoute()

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

// 手动充值相关状态
const showRechargeDialog = ref(false)
const rechargeLoading = ref(false)
const rechargeFormRef = ref<FormInstance>()
const currentOperatorBalance = ref('')
const paymentFiles = ref<UploadFile[]>([])

// 充值表单数据
const rechargeForm = reactive({
  operator_id: '',
  amount: 0,
  description: '',
})

// 充值表单验证规则
const rechargeRules = {
  operator_id: [
    { required: true, message: '请选择运营商', trigger: 'change' }
  ],
  amount: [
    { required: true, message: '请输入充值金额', trigger: 'blur' },
    { type: 'number', min: 0.01, message: '充值金额必须大于0', trigger: 'blur' }
  ]
}

// 运营商选择变化
const handleOperatorChange = (operatorId: string) => {
  if (operatorId) {
    const operator = operators.value.find(op => op.id === operatorId)
    if (operator) {
      currentOperatorBalance.value = `¥${operator.balance.toFixed(2)}`
    }
  } else {
    currentOperatorBalance.value = ''
  }
}

// 文件上传前检查
const beforeUpload = (file: File) => {
  const isLt5M = file.size / 1024 / 1024 < 5
  if (!isLt5M) {
    ElMessage.error('文件大小不能超过 5MB!')
    return false
  }
  return true
}

// 文件超出限制
const handleExceed = () => {
  ElMessage.warning('最多只能上传一个文件')
}

// 提交充值
const handleRechargeSubmit = async () => {
  if (!rechargeFormRef.value) return

  await rechargeFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      rechargeLoading.value = true

      // 构建表单数据
      const formData = new FormData()
      formData.append('operator_id', rechargeForm.operator_id)
      formData.append('amount', rechargeForm.amount.toString())
      formData.append('description', rechargeForm.description)

      // 添加付款凭证文件
      if (paymentFiles.value.length > 0 && paymentFiles.value[0].raw) {
        formData.append('payment_proof', paymentFiles.value[0].raw)
      }

      // 调用后端API
      await http.post('/finance/recharge', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      ElMessage.success('充值成功')

      // 重置表单
      rechargeFormRef.value.resetFields()
      paymentFiles.value = []
      currentOperatorBalance.value = ''
      showRechargeDialog.value = false

      // 刷新充值记录列表
      fetchRecords()

    } catch (error: any) {
      console.error('充值失败:', error)
      // 错误已在http拦截器中处理
    } finally {
      rechargeLoading.value = false
    }
  })
}

// 页面加载
onMounted(() => {
  fetchOperators()
  fetchRecords()

  // 检查URL查询参数，如果有action=recharge则自动打开充值对话框
  if (route.query.action === 'recharge') {
    showRechargeDialog.value = true
  }
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

.header-actions {
  display: flex;
  gap: 12px;
}

.filter-form {
  margin-bottom: 16px;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}

pre {
  background-color: #f5f7fa;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
}
</style>
