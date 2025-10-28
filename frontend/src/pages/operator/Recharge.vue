<template>
  <div class="recharge-page">
    <!-- 页面标题 -->
    <el-card class="header-card">
      <div class="header-content">
        <div class="title-section">
          <el-icon :size="24"><CreditCard /></el-icon>
          <h2>在线充值</h2>
        </div>
      </div>
    </el-card>

    <!-- 充值表单 -->
    <el-card v-if="!paymentInfo" class="form-card" style="margin-top: 20px">
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        style="max-width: 600px"
      >
        <el-form-item label="充值金额" prop="amount">
          <el-input
            v-model="formData.amount"
            placeholder="请输入充值金额"
            type="number"
            min="0"
            step="0.01"
          >
            <template #prefix>¥</template>
          </el-input>
          <div class="amount-presets">
            <el-tag
              v-for="preset in amountPresets"
              :key="preset"
              class="preset-tag"
              @click="selectPreset(preset)"
            >
              ¥{{ preset }}
            </el-tag>
          </div>
        </el-form-item>

        <el-form-item label="支付方式" prop="payment_method">
          <el-radio-group v-model="formData.payment_method">
            <el-radio value="wechat">
              <div class="payment-method">
                <el-icon :size="20" color="#07C160"><ChatDotRound /></el-icon>
                <span>微信支付</span>
              </div>
            </el-radio>
            <el-radio value="alipay">
              <div class="payment-method">
                <el-icon :size="20" color="#1677FF"><WalletFilled /></el-icon>
                <span>支付宝</span>
              </div>
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            立即充值
          </el-button>
          <el-button @click="handleCancel">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 支付信息展示 -->
    <el-card v-else class="payment-card" style="margin-top: 20px">
      <div class="payment-container">
        <div class="payment-header">
          <h3>请使用{{ paymentMethodLabel }}扫码支付</h3>
          <div class="payment-amount">¥{{ paymentInfo.amount }}</div>
        </div>

        <div v-if="paymentInfo.qr_code" class="qr-code-container">
          <el-image :src="paymentInfo.qr_code" fit="contain" style="width: 250px; height: 250px">
            <template #error>
              <div class="qr-code-error">
                <el-icon :size="40"><Warning /></el-icon>
                <div>二维码加载失败</div>
              </div>
            </template>
          </el-image>
        </div>

        <div v-else class="payment-link">
          <el-alert
            title="请点击下方链接完成支付"
            type="info"
            :closable="false"
          />
          <el-button type="primary" @click="openPaymentUrl">
            打开支付页面
          </el-button>
        </div>

        <div class="payment-info">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="订单号">
              {{ paymentInfo.order_id }}
            </el-descriptions-item>
            <el-descriptions-item label="充值金额">
              ¥{{ paymentInfo.amount }}
            </el-descriptions-item>
            <el-descriptions-item label="支付方式">
              {{ paymentMethodLabel }}
            </el-descriptions-item>
            <el-descriptions-item label="过期时间">
              {{ formatDateTime(paymentInfo.expires_at) }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="payment-actions">
          <el-button type="success" @click="checkPaymentStatus">
            <el-icon><Refresh /></el-icon>
            检查支付状态
          </el-button>
          <el-button @click="resetForm">
            <el-icon><Close /></el-icon>
            取消支付
          </el-button>
        </div>

        <el-alert
          title="提示"
          description="支付成功后，余额将自动更新。如长时间未到账，请联系客服。"
          type="info"
          :closable="false"
          style="margin-top: 20px"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useOperatorStore } from '@/stores/operator'
import type { RechargeResponse } from '@/types'
import dayjs from 'dayjs'

const router = useRouter()
const operatorStore = useOperatorStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const paymentInfo = ref<RechargeResponse | null>(null)

const formData = ref({
  amount: '',
  payment_method: 'wechat' as 'wechat' | 'alipay',
})

const amountPresets = [100, 200, 500, 1000, 2000, 5000]

const formRules: FormRules = {
  amount: [
    { required: true, message: '请输入充值金额', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        const amount = parseFloat(value)
        if (isNaN(amount)) {
          callback(new Error('请输入有效的金额'))
        } else if (amount <= 0) {
          callback(new Error('充值金额必须大于0'))
        } else if (amount > 100000) {
          callback(new Error('单次充值金额不能超过100000元'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  payment_method: [
    { required: true, message: '请选择支付方式', trigger: 'change' },
  ],
}

const paymentMethodLabel = computed(() => {
  return formData.value.payment_method === 'wechat' ? '微信支付' : '支付宝'
})

// 格式化日期时间
const formatDateTime = (datetime: string) => {
  return dayjs(datetime).format('YYYY-MM-DD HH:mm:ss')
}

// 选择预设金额
const selectPreset = (amount: number) => {
  formData.value.amount = amount.toString()
}

// 提交充值请求
const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    const response = await operatorStore.recharge({
      amount: formData.value.amount,
      payment_method: formData.value.payment_method,
    })

    paymentInfo.value = response
    ElMessage.success('充值订单已创建，请完成支付')
  } catch (error) {
    console.error('Recharge error:', error)
    ElMessage.error('创建充值订单失败')
  } finally {
    submitting.value = false
  }
}

// 取消
const handleCancel = () => {
  router.push('/operator/dashboard')
}

// 打开支付链接
const openPaymentUrl = () => {
  if (paymentInfo.value?.payment_url) {
    window.open(paymentInfo.value.payment_url, '_blank')
  }
}

// 检查支付状态
const checkPaymentStatus = async () => {
  try {
    const balance = await operatorStore.getBalance()
    ElMessage.success('余额已更新')
    router.push('/operator/dashboard')
  } catch (error) {
    ElMessage.warning('支付可能尚未完成，请稍后再试')
  }
}

// 重置表单
const resetForm = () => {
  paymentInfo.value = null
  formData.value = {
    amount: '',
    payment_method: 'wechat',
  }
  formRef.value?.resetFields()
}
</script>

<style scoped>
.recharge-page {
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

.form-card :deep(.el-card__body),
.payment-card :deep(.el-card__body) {
  padding: 30px;
}

.amount-presets {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.preset-tag {
  cursor: pointer;
  user-select: none;
}

.preset-tag:hover {
  background-color: #409EFF;
  color: white;
}

.payment-method {
  display: flex;
  align-items: center;
  gap: 8px;
}

.payment-container {
  max-width: 600px;
  margin: 0 auto;
}

.payment-header {
  text-align: center;
  margin-bottom: 30px;
}

.payment-header h3 {
  margin: 0 0 10px 0;
  font-size: 18px;
  color: #303133;
}

.payment-amount {
  font-size: 36px;
  font-weight: 600;
  color: #409EFF;
}

.qr-code-container {
  display: flex;
  justify-content: center;
  margin: 30px 0;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.qr-code-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #909399;
}

.payment-link {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin: 30px 0;
}

.payment-info {
  margin: 30px 0;
}

.payment-actions {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-top: 30px;
}
</style>
