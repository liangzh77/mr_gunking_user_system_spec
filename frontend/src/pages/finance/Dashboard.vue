<template>
  <div class="dashboard">
    <!-- 今日财务概览 -->
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #67c23a">
            <el-icon :size="32"><Money /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">今日充值</div>
            <div class="stat-value">¥{{ dashboard.today_recharge || '0.00' }}</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #e6a23c">
            <el-icon :size="32"><Wallet /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">今日消费</div>
            <div class="stat-value">¥{{ dashboard.today_consumption || '0.00' }}</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #f56c6c">
            <el-icon :size="32"><RefreshLeft /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">今日退款</div>
            <div class="stat-value">¥{{ dashboard.today_refund || '0.00' }}</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #409eff">
            <el-icon :size="32"><TrendCharts /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">今日净收入</div>
            <div class="stat-value">¥{{ dashboard.today_net_income || '0.00' }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 运营商统计 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card class="stat-card clickable-card" @click="showBalanceRankingDialog">
          <div class="stat-icon" style="background-color: #909399">
            <el-icon :size="32"><UserFilled /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">运营商总数</div>
            <div class="stat-value">{{ dashboard.total_operators || 0 }}</div>
            <div class="stat-hint">点击查看余额排行</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="stat-card">
          <div class="stat-icon" style="background-color: #5a3bbd">
            <el-icon :size="32"><Avatar /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">今日活跃运营商</div>
            <div class="stat-value">{{ dashboard.active_operators_today || 0 }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Top客户列表 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>消费Top客户</span>
              <el-button type="primary" size="small" @click="fetchTopCustomers">刷新</el-button>
            </div>
          </template>
          <el-table :data="topCustomers" stripe>
            <el-table-column prop="rank" label="排名" width="80" align="center" />
            <el-table-column prop="operator_name" label="运营商名称" />
            <el-table-column prop="total_consumption" label="累计消费" align="right">
              <template #default="scope">
                ¥{{ scope.row.total_consumption }}
              </template>
            </el-table-column>
            <el-table-column prop="total_recharge" label="累计充值" align="right">
              <template #default="scope">
                ¥{{ scope.row.total_recharge }}
              </template>
            </el-table-column>
            <el-table-column prop="current_balance" label="当前余额" align="right">
              <template #default="scope">
                ¥{{ scope.row.current_balance }}
              </template>
            </el-table-column>
            <el-table-column prop="customer_tier" label="客户分类" width="100" align="center">
              <template #default="scope">
                <el-tag :type="getTierType(scope.row.customer_tier)">
                  {{ getTierLabel(scope.row.customer_tier) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 待处理事项 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>待处理事项</span>
            </div>
          </template>
          <div class="pending-items">
            <div class="pending-item" @click="$router.push('/finance/refunds')">
              <el-icon :size="20" color="#f56c6c"><RefreshLeft /></el-icon>
              <span>待审核退款</span>
              <el-badge :value="pendingRefunds" class="badge" />
            </div>
            <div class="pending-item" @click="$router.push('/finance/invoices')">
              <el-icon :size="20" color="#409eff"><Tickets /></el-icon>
              <span>待审核发票</span>
              <el-badge :value="pendingInvoices" class="badge" />
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>快速操作</span>
            </div>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/finance/refunds')">
              <el-icon><RefreshLeft /></el-icon>
              退款审核
            </el-button>
            <el-button type="success" @click="$router.push('/finance/invoices')">
              <el-icon><Tickets /></el-icon>
              发票审核
            </el-button>
            <el-button type="warning" @click="showRechargeDialog = true">
              <el-icon><Money /></el-icon>
              手动充值
            </el-button>
            <el-button type="info" @click="$router.push('/finance/reports')">
              <el-icon><Document /></el-icon>
              财务报表
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

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

    <!-- 运营商余额排行对话框 -->
    <el-dialog
      v-model="balanceRankingDialogVisible"
      title="运营商余额排行"
      width="900px"
    >
      <el-table :data="balanceRanking" stripe v-loading="balanceLoading">
        <el-table-column label="排名" width="80" align="center">
          <template #default="scope">
            <el-tag
              :type="scope.$index === 0 ? 'danger' : scope.$index === 1 ? 'warning' : scope.$index === 2 ? 'success' : 'info'"
              effect="dark"
            >
              {{ scope.$index + 1 }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="full_name" label="运营商名称" min-width="200" />
        <el-table-column prop="balance" label="账户余额" width="150" align="right">
          <template #default="scope">
            <span style="color: #67c23a; font-weight: bold; font-size: 16px">
              ¥{{ scope.row.balance.toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="customer_tier" label="客户分类" width="120" align="center">
          <template #default="scope">
            <el-tag :type="getTierType(scope.row.customer_tier)">
              {{ getTierLabel(scope.row.customer_tier) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.is_active && !scope.row.is_locked ? 'success' : 'info'">
              {{ scope.row.is_active && !scope.row.is_locked ? '正常' : '异常' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="balanceRankingDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="fetchBalanceRanking">刷新</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type UploadFile } from 'element-plus'
import {
  Money,
  Wallet,
  RefreshLeft,
  TrendCharts,
  UserFilled,
  Avatar,
  Tickets,
  Document,
  Plus,
} from '@element-plus/icons-vue'
import http from '@/utils/http'

// 仪表盘数据
const dashboard = ref({
  today_recharge: '0.00',
  today_consumption: '0.00',
  today_refund: '0.00',
  today_net_income: '0.00',
  total_operators: 0,
  active_operators_today: 0,
})

// Top客户列表
const topCustomers = ref<any[]>([])

// 运营商余额排行
const balanceRanking = ref<any[]>([])
const balanceLoading = ref(false)
const balanceRankingDialogVisible = ref(false)

// 待处理数量
const pendingRefunds = ref(0)
const pendingInvoices = ref(0)

// 充值相关状态
const showRechargeDialog = ref(false)
const rechargeLoading = ref(false)
const rechargeFormRef = ref<FormInstance>()
const operators = ref<any[]>([])
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

// 获取仪表盘数据
const fetchDashboard = async () => {
  try {
    const response = await http.get('/finance/dashboard')
    dashboard.value = response.data
  } catch (error: any) {
    ElMessage.error('获取财务概览失败')
  }
}

// 获取Top客户
const fetchTopCustomers = async () => {
  try {
    const response = await http.get('/finance/top-customers', {
      params: { limit: 10 }
    })
    topCustomers.value = response.data.customers || []
  } catch (error: any) {
    ElMessage.error('获取Top客户失败')
  }
}

// 获取运营商余额排行
const fetchBalanceRanking = async () => {
  balanceLoading.value = true
  try {
    const response = await http.get('/finance/operators', {
      params: {
        page: 1,
        page_size: 10,
        status: 'active',
        sort_by: 'balance',
        sort_order: 'desc'
      }
    })
    // 获取运营商列表并按余额降序排序
    const operators = response.data.items || []
    balanceRanking.value = operators.sort((a: any, b: any) => b.balance - a.balance)
  } catch (error: any) {
    console.error('获取余额排行失败:', error)
    ElMessage.error('获取余额排行失败')
  } finally {
    balanceLoading.value = false
  }
}

// 打开余额排行对话框
const showBalanceRankingDialog = async () => {
  balanceRankingDialogVisible.value = true
  // 如果还没有数据,或者数据为空,则加载数据
  if (balanceRanking.value.length === 0) {
    await fetchBalanceRanking()
  }
}

// 客户分类标签
const getTierType = (tier: string) => {
  switch (tier) {
    case 'vip': return 'danger'
    case 'standard': return 'success'
    case 'trial': return 'info'
    default: return 'info'
  }
}

const getTierLabel = (tier: string) => {
  switch (tier) {
    case 'vip': return 'VIP'
    case 'standard': return '普通'
    case 'trial': return '试用'
    default: return '未知'
  }
}

// 获取运营商列表
const fetchOperators = async () => {
  try {
    const response = await http.get('/finance/operators', {
      params: {
        page: 1,
        page_size: 1000,
        status: 'active'  // 只获取激活状态的运营商
      }
    })
    operators.value = response.data.items || []
  } catch (error: any) {
    console.error('获取运营商列表失败:', error)
    ElMessage.error('获取运营商列表失败')
  }
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

      // 刷新数据
      fetchDashboard()
      fetchTopCustomers()

    } catch (error: any) {
      console.error('充值失败:', error)
      // 错误已在http拦截器中处理
    } finally {
      rechargeLoading.value = false
    }
  })
}

// 页面加载时获取数据
onMounted(() => {
  fetchDashboard()
  fetchTopCustomers()
  fetchOperators()
})
</script>

<style scoped>
.dashboard {
  width: 100%;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
}

.clickable-card {
  cursor: pointer;
  transition: all 0.3s ease;
}

.clickable-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.stat-content {
  flex: 1;
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

.stat-hint {
  font-size: 12px;
  color: #409eff;
  margin-top: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pending-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pending-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.pending-item:hover {
  background-color: #f5f7fa;
}

.pending-item span {
  flex: 1;
  font-size: 14px;
  color: #606266;
}

.badge {
  margin-left: auto;
}

.quick-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}
</style>
