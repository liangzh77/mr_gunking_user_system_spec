<template>
  <div class="recharge-records-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>转账记录</span>
          <div class="header-actions">
            <el-button type="success" size="small" @click="showRechargeDialog = true">
              <el-icon><Money /></el-icon>
              财务充值
            </el-button>
            <el-button type="danger" size="small" @click="showDeductDialog = true">
              <el-icon><Remove /></el-icon>
              财务扣费
            </el-button>
            <el-button type="primary" size="small" @click="fetchRecords">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选条件 -->
      <div class="filter-container">
        <el-form :inline="true">
          <el-form-item label="搜索">
            <el-input
              v-model="searchQuery"
              placeholder="搜索交易ID或备注..."
              clearable
              @keyup.enter="handleQuery"
              @clear="handleQuery"
              style="width: 280px"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item label="运营商">
            <el-select
              v-model="queryForm.operator_id"
              placeholder="全部运营商"
              clearable
              filterable
              @change="handleQuery"
              style="width: 220px"
            >
              <el-option
                v-for="op in operators"
                :key="op.id"
                :label="`${op.full_name} (${op.username})`"
                :value="op.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="交易方式">
            <el-select
              v-model="queryForm.recharge_method"
              placeholder="全部方式"
              clearable
              @change="handleQuery"
              style="width: 150px"
            >
              <el-option label="财务充值" value="manual" />
              <el-option label="财务扣费" value="deduct" />
              <el-option label="在线充值" value="online" />
              <el-option label="银行转账" value="bank_transfer" />
            </el-select>
          </el-form-item>

          <el-form-item label="交易时间">
            <el-date-picker
              v-model="queryForm.date_range"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              @change="handleQuery"
              style="width: 280px"
              value-format="YYYY-MM-DD"
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="handleQuery">
              <el-icon><Search /></el-icon>
              查询
            </el-button>
            <el-button @click="handleReset">
              <el-icon><RefreshLeft /></el-icon>
              重置
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 充值记录表格 -->
      <el-table v-copyable :data="records" v-loading="loading" stripe>
        <el-table-column prop="transaction_id" label="交易ID" width="220" show-overflow-tooltip />
        <el-table-column prop="operator_name" label="运营商" width="150" show-overflow-tooltip />
        <el-table-column prop="recharge_method" label="转账类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getRechargeMethodTagType(row.recharge_method)" size="small">
              {{ row.recharge_method }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="转账金额" width="120" align="right">
          <template #default="{ row }">
            <span :style="{ color: row.recharge_method === '财务扣费' ? '#f56c6c' : '#67c23a', fontWeight: 'bold' }">
              ¥{{ row.amount }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="balance_after" label="余额" width="120" align="right">
          <template #default="{ row }">
            ¥{{ row.balance_after }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column prop="created_at" label="充值时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button type="info" size="small" @click="handleViewDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchRecords"
          @current-change="fetchRecords"
        />
      </div>
    </el-card>

    <!-- 充值详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="转账记录详情" width="700px">
      <el-descriptions :column="2" border v-if="currentRecord">
        <el-descriptions-item label="交易ID">{{ currentRecord.transaction_id }}</el-descriptions-item>
        <el-descriptions-item label="运营商">{{ currentRecord.operator_name }}</el-descriptions-item>
        <el-descriptions-item label="交易方式">
          <el-tag :type="getRechargeMethodTagType(currentRecord.recharge_method)" size="small">
            {{ currentRecord.recharge_method }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="交易金额">
          <span :style="{ color: currentRecord.recharge_method === '财务扣费' ? '#f56c6c' : '#67c23a', fontWeight: 'bold' }">
            {{ currentRecord.recharge_method === '财务扣费' ? '-' : '+' }}¥{{ currentRecord.amount }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="交易前余额">¥{{ currentRecord.balance_before }}</el-descriptions-item>
        <el-descriptions-item label="交易后余额">¥{{ currentRecord.balance_after }}</el-descriptions-item>
        <el-descriptions-item label="交易时间" :span="2">{{ formatDateTime(currentRecord.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ currentRecord.description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="支付信息" :span="2" v-if="currentRecord.payment_info">
          <div>
            <div>支付渠道: {{ currentRecord.payment_info.channel === 'wechat' ? '微信转账' : '支付宝' }}</div>
            <div>订单号: {{ currentRecord.payment_info.order_no }}</div>
            <div>状态: {{ currentRecord.payment_info.status }}</div>
          </div>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 财务充值对话框 -->
    <el-dialog
      v-model="showRechargeDialog"
      title="财务充值"
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

    <!-- 财务扣费对话框 -->
    <el-dialog
      v-model="showDeductDialog"
      title="财务扣费"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="deductFormRef"
        :model="deductForm"
        :rules="deductRules"
        label-width="100px"
      >
        <el-form-item label="运营商" prop="operator_id">
          <el-select
            v-model="deductForm.operator_id"
            placeholder="请选择运营商"
            filterable
            clearable
            style="width: 100%"
            @change="handleDeductOperatorChange"
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
            v-model="deductOperatorBalance"
            placeholder="请先选择运营商"
            readonly
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="扣费金额" prop="amount">
          <el-input-number
            v-model="deductForm.amount"
            :min="0.01"
            :max="999999.99"
            :precision="2"
            :step="100"
            controls-position="right"
            placeholder="请输入扣费金额"
            style="width: 100%"
          />
          <div class="form-tip">扣费金额必须大于0且不能超过运营商当前余额</div>
        </el-form-item>

        <el-form-item label="扣费原因" prop="description">
          <el-input
            v-model="deductForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入扣费原因（必填）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showDeductDialog = false">取消</el-button>
        <el-button
          type="danger"
          :loading="deductLoading"
          @click="handleDeductSubmit"
        >
          确认扣费
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type UploadFile } from 'element-plus'
import { Refresh as RefreshIcon, RefreshLeft, Right, Money, Plus, Remove, Search } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/format'
import http from '@/utils/http'

const route = useRoute()

// 查询表单
const queryForm = reactive({
  operator_id: '',
  date_range: [] as string[],
  recharge_method: '', // 充值方式: manual(手动), online(在线), bank_transfer(银行转账)
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
const searchQuery = ref('')

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

    if (searchQuery.value) {
      params.search = searchQuery.value
    }

    if (queryForm.operator_id) {
      params.operator_id = queryForm.operator_id
    }

    if (queryForm.date_range && queryForm.date_range.length === 2) {
      params.start_date = queryForm.date_range[0]
      params.end_date = queryForm.date_range[1]
    }

    if (queryForm.recharge_method) {
      params.recharge_method = queryForm.recharge_method
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
  searchQuery.value = ''
  queryForm.operator_id = ''
  queryForm.date_range = []
  queryForm.recharge_method = ''
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

// 财务扣费相关状态
const showDeductDialog = ref(false)
const deductLoading = ref(false)
const deductFormRef = ref<FormInstance>()
const deductOperatorBalance = ref('')

// 扣费表单数据
const deductForm = reactive({
  operator_id: '',
  amount: 0,
  description: '',
})

// 扣费表单验证规则
const deductRules = {
  operator_id: [
    { required: true, message: '请选择运营商', trigger: 'change' }
  ],
  amount: [
    { required: true, message: '请输入扣费金额', trigger: 'blur' },
    { type: 'number', min: 0.01, message: '扣费金额必须大于0', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请输入扣费原因', trigger: 'blur' },
    { min: 1, message: '扣费原因至少1个字符', trigger: 'blur' }
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

// 扣费运营商选择变化
const handleDeductOperatorChange = (operatorId: string) => {
  if (operatorId) {
    const operator = operators.value.find(op => op.id === operatorId)
    if (operator) {
      deductOperatorBalance.value = `¥${operator.balance.toFixed(2)}`
      // 设置最大扣费金额为当前余额
      if (deductFormRef.value) {
        deductRules.amount.push({
          type: 'number',
          max: operator.balance,
          message: `扣费金额不能超过当前余额¥${operator.balance.toFixed(2)}`,
          trigger: 'blur'
        })
      }
    }
  } else {
    deductOperatorBalance.value = ''
  }
}

// 提交扣费
const handleDeductSubmit = async () => {
  if (!deductFormRef.value) return

  await deductFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      deductLoading.value = true

      // 构造FormData (后端使用Form参数)
      const formData = new FormData()
      formData.append('operator_id', deductForm.operator_id)
      formData.append('amount', deductForm.amount.toString())
      formData.append('description', deductForm.description)

      // 调用后端API
      await http.post('/finance/deduct', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      ElMessage.success('扣费成功')

      // 重置表单
      deductFormRef.value.resetFields()
      deductOperatorBalance.value = ''
      showDeductDialog.value = false

      // 刷新充值记录列表和运营商列表
      fetchRecords()
      fetchOperators()

    } catch (error: any) {
      console.error('扣费失败:', error)
      // 错误已在http拦截器中处理
    } finally {
      deductLoading.value = false
    }
  })
}

// 获取充值方式标签颜色
const getRechargeMethodTagType = (method: string) => {
  if (method === '财务扣费') return 'danger'
  if (method === '财务充值') return 'warning'
  if (method === '银行转账') return 'primary'
  if (method === '微信转账') return 'success'
  return 'success'
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
  width: 100%;
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

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}
</style>
