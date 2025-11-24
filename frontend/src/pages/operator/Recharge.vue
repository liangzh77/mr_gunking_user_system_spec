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
        style="max-width: 800px"
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
            <el-radio value="bank_transfer">
              <div class="payment-method">
                <el-icon :size="20" color="#F56C6C"><Money /></el-icon>
                <span>银行充值</span>
              </div>
            </el-radio>
            <el-radio value="wechat">
              <div class="payment-method">
                <el-icon :size="20" color="#07C160"><ChatDotRound /></el-icon>
                <span>微信充值</span>
              </div>
            </el-radio>
            <el-radio value="alipay" disabled>
              <div class="payment-method disabled">
                <el-icon :size="20" color="#909399"><WalletFilled /></el-icon>
                <span>支付宝(即将上线)</span>
              </div>
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 银行充值信息 -->
        <template v-if="formData.payment_method === 'bank_transfer'">
          <el-alert
            title="银行充值说明"
            type="info"
            :closable="false"
            style="margin-bottom: 20px"
          >
            <template #default>
              <div class="bank-transfer-notice">
                <p>1. 请将款项充值至以下公司银行账户</p>
                <p>2. 充值完成后,上传充值凭证截图</p>
                <p>3. 提交申请后,财务人员将在1-2个工作日内审核</p>
                <p>4. 审核通过后,款项将自动充值到您的账户</p>
              </div>
            </template>
          </el-alert>

          <el-card class="bank-info-card" shadow="never">
            <template #header>
              <div class="bank-info-header">
                <el-icon><Wallet /></el-icon>
                <span>收款账户信息</span>
              </div>
            </template>
            <el-descriptions :column="1" border v-loading="loadingBankInfo">
              <el-descriptions-item label="户名">
                <div class="account-number">
                  <span>{{ bankAccountInfo.account_name }}</span>
                  <el-button
                    link
                    type="primary"
                    @click="copyAccountName"
                    style="margin-left: 10px"
                  >
                    <el-icon><DocumentCopy /></el-icon>
                    复制
                  </el-button>
                </div>
              </el-descriptions-item>
              <el-descriptions-item label="账号">
                <div class="account-number">
                  <span>{{ bankAccountInfo.account_number }}</span>
                  <el-button
                    link
                    type="primary"
                    @click="copyAccountNumber"
                    style="margin-left: 10px"
                  >
                    <el-icon><DocumentCopy /></el-icon>
                    复制
                  </el-button>
                </div>
              </el-descriptions-item>
              <el-descriptions-item label="开户行">
                <div class="account-number">
                  <span>{{ bankAccountInfo.bank_name }}</span>
                  <el-button
                    link
                    type="primary"
                    @click="copyBankName"
                    style="margin-left: 10px"
                  >
                    <el-icon><DocumentCopy /></el-icon>
                    复制
                  </el-button>
                </div>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-form-item label="充值凭证" prop="voucher_image" style="margin-top: 20px">
            <!-- 隐藏的上传组件 -->
            <el-upload
              ref="voucherUploadRef"
              class="voucher-uploader-hidden"
              :auto-upload="false"
              :on-change="handleVoucherChange"
              :show-file-list="false"
              accept="image/jpeg,image/jpg,image/png"
              :limit="1"
              v-show="false"
            >
            </el-upload>

            <!-- 自定义上传区域 -->
            <div v-if="voucherImageUrl" class="voucher-preview" @click="handleReuploadVoucher">
              <el-image
                :src="voucherImageUrl"
                fit="contain"
                style="width: 200px; height: 200px; border: 1px dashed #d9d9d9; border-radius: 6px; cursor: pointer"
              >
                <template #error>
                  <div class="image-error">
                    <el-icon><Picture /></el-icon>
                    <span>加载失败</span>
                  </div>
                </template>
              </el-image>
            </div>
            <div v-else class="upload-trigger" @click="triggerUpload">
              <el-icon class="upload-icon"><Plus /></el-icon>
              <div class="upload-text">点击上传充值凭证</div>
              <div class="upload-hint">支持 JPG、PNG 格式,不超过 5MB</div>
            </div>
          </el-form-item>

          <el-form-item label="备注" prop="remark">
            <el-input
              v-model="formData.remark"
              type="textarea"
              :rows="3"
              placeholder="选填,可注明充值时间等信息"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
        </template>

        <!-- 微信支付信息 -->
        <template v-if="formData.payment_method === 'wechat'">
          <el-alert
            title="微信扫码支付说明"
            type="info"
            :closable="false"
            style="margin-bottom: 20px"
          >
            <template #default>
              <div class="wechat-notice">
                <p>1. 请使用微信扫描下方二维码</p>
                <p>2. 输入充值金额完成支付</p>
                <p>3. 支付完成后,上传支付凭证截图</p>
                <p>4. 提交申请后,财务人员将在1-2个工作日内审核</p>
                <p>5. 审核通过后,款项将自动充值到您的账户</p>
              </div>
            </template>
          </el-alert>

          <el-card class="wechat-info-card" shadow="never">
            <template #header>
              <div class="wechat-info-header">
                <el-icon><Wallet /></el-icon>
                <span>收款信息</span>
              </div>
            </template>
            <div class="wechat-content">
              <div class="qr-code-section">
                <div class="qr-code-wrapper">
                  <el-image
                    :src="wechatQRCode"
                    fit="contain"
                    style="width: 200px; height: 200px"
                  >
                    <template #error>
                      <div class="image-error">
                        <el-icon><Picture /></el-icon>
                        <span>二维码加载失败</span>
                      </div>
                    </template>
                  </el-image>
                </div>
                <div class="qr-code-hint">请使用微信扫描二维码支付</div>
              </div>
              <el-descriptions :column="1" border class="company-info">
                <el-descriptions-item label="收款方">
                  <span class="copyable-text" @click="copyCompanyName">北京触角科技有限公司</span>
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </el-card>

          <el-form-item label="支付凭证" prop="voucher_image" style="margin-top: 20px">
            <!-- 隐藏的上传组件 -->
            <el-upload
              ref="voucherUploadRef"
              class="voucher-uploader-hidden"
              :auto-upload="false"
              :on-change="handleVoucherChange"
              :show-file-list="false"
              accept="image/jpeg,image/jpg,image/png"
              :limit="1"
              v-show="false"
            >
            </el-upload>

            <!-- 自定义上传区域 -->
            <div v-if="voucherImageUrl" class="voucher-preview" @click="handleReuploadVoucher">
              <el-image
                :src="voucherImageUrl"
                fit="contain"
                style="width: 200px; height: 200px; border: 1px dashed #d9d9d9; border-radius: 6px; cursor: pointer"
              >
                <template #error>
                  <div class="image-error">
                    <el-icon><Picture /></el-icon>
                    <span>加载失败</span>
                  </div>
                </template>
              </el-image>
            </div>
            <div v-else class="upload-trigger" @click="triggerUpload">
              <el-icon class="upload-icon"><Plus /></el-icon>
              <div class="upload-text">点击上传支付凭证</div>
              <div class="upload-hint">支持 JPG、PNG 格式,不超过 5MB</div>
            </div>
          </el-form-item>

          <el-form-item label="备注" prop="remark">
            <el-input
              v-model="formData.remark"
              type="textarea"
              :rows="3"
              placeholder="选填,可注明支付时间等信息"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
        </template>

        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            {{ formData.payment_method === 'bank_transfer' || formData.payment_method === 'wechat' ? '提交申请' : '立即充值' }}
          </el-button>
          <el-button @click="handleCancel">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 支付信息展示 (微信/支付宝) -->
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
          description="支付成功后,余额将自动更新。如长时间未到账,请联系客服。"
          type="info"
          :closable="false"
          style="margin-top: 20px"
        />
      </div>
    </el-card>

    <!-- 充值申请列表 -->
    <el-card class="applications-card" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>充值申请记录</span>
        </div>
      </template>

      <!-- 搜索栏 -->
      <div class="filter-container" style="margin-bottom: 16px">
        <el-form :inline="true">
          <el-form-item label="搜索">
            <el-input
              v-model="searchQuery"
              placeholder="搜索申请ID、备注、拒绝原因..."
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
          <el-form-item label="状态">
            <el-select
              v-model="filterStatus"
              placeholder="全部状态"
              clearable
              @change="handleSearch"
              style="width: 130px"
            >
              <el-option label="待审核" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已拒绝" value="rejected" />
            </el-select>
          </el-form-item>
          <el-form-item label="申请时间">
            <el-date-picker
              v-model="filterDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              @change="handleSearch"
              style="width: 280px"
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
      </div>

      <el-table
        :data="bankTransfers"
        v-loading="loadingTransfers"
        v-copyable
        stripe
        style="width: 100%"
      >
        <el-table-column prop="application_id" label="申请ID" width="200" show-overflow-tooltip />
        <el-table-column label="充值类型" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="getPaymentMethodType(row.payment_method)" size="small">
              {{ getPaymentMethodLabel(row.payment_method) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="充值金额" width="120" align="right">
          <template #default="{ row }">
            <span class="amount-text">¥{{ row.amount }}</span>
          </template>
        </el-table-column>
        <el-table-column label="充值凭证" width="100" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewVoucher(row)">
              查看
            </el-button>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.remark">{{ row.remark }}</span>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reject_reason" label="拒绝原因" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.reject_reason" class="reject-reason">{{ row.reject_reason }}</span>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending'"
              type="danger"
              size="small"
              text
              @click="cancelTransfer(row)"
            >
              取消
            </el-button>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loadingTransfers && bankTransfers.length === 0" class="empty-state">
        <el-empty description="暂无充值申请记录" />
      </div>

      <div v-if="transferPagination.total > 0" class="pagination-container">
        <el-pagination
          v-model:current-page="transferPagination.page"
          v-model:page-size="transferPagination.page_size"
          :total="transferPagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="loadBankTransfers"
          @size-change="handlePageSizeChange"
        />
      </div>
    </el-card>

    <!-- 凭证查看对话框 -->
    <el-dialog v-model="voucherDialogVisible" title="充值凭证" width="600px">
      <div class="voucher-view">
        <el-image
          :src="currentVoucher"
          fit="contain"
          style="width: 100%"
          :preview-src-list="[currentVoucher]"
        >
          <template #error>
            <div class="image-error">
              <el-icon :size="60"><Picture /></el-icon>
              <div>图片加载失败</div>
            </div>
          </template>
        </el-image>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type UploadFile } from 'element-plus'
import { Search, Refresh, RefreshLeft } from '@element-plus/icons-vue'
import { useOperatorStore } from '@/stores/operator'
import type { RechargeResponse } from '@/types'
import dayjs from 'dayjs'
import http from '@/utils/http'

// 微信收款码图片
const wechatQRCode = new URL('@/assets/payment/wechat-qr.png', import.meta.url).href

const router = useRouter()
const operatorStore = useOperatorStore()

const formRef = ref<FormInstance>()
const voucherUploadRef = ref()
const submitting = ref(false)
const paymentInfo = ref<RechargeResponse | null>(null)
const loadingBankInfo = ref(false)
const loadingTransfers = ref(false)
const searchQuery = ref('')
const filterStatus = ref('')
const filterDateRange = ref<[Date, Date] | null>(null)
const voucherImageUrl = ref('')
const voucherFile = ref<File | null>(null)
const voucherDialogVisible = ref(false)
const currentVoucher = ref('')

const formData = ref({
  amount: '',
  payment_method: 'bank_transfer' as 'wechat' | 'alipay' | 'bank_transfer',
  voucher_image: '',
  remark: '',
})

const bankAccountInfo = ref({
  account_name: '',
  account_number: '',
  bank_name: '',
})

const bankTransfers = ref<any[]>([])
const transferPagination = ref({
  page: 1,
  page_size: 20,
  total: 0,
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
  voucher_image: [
    { required: true, message: '请上传充值凭证', trigger: 'change' },
  ],
}

const paymentMethodLabel = computed(() => {
  const labels = {
    wechat: '微信充值',
    alipay: '支付宝',
    bank_transfer: '银行充值'
  }
  return labels[formData.value.payment_method] || ''
})

// 格式化日期时间
const formatDateTime = (datetime: string) => {
  return dayjs(datetime).format('YYYY-MM-DD HH:mm:ss')
}

// 选择预设金额
const selectPreset = (amount: number) => {
  formData.value.amount = amount.toString()
}

// 加载银行账户信息
const loadBankAccountInfo = async () => {
  loadingBankInfo.value = true
  try {
    const response = await http.get('/operators/bank-account')
    bankAccountInfo.value = response.data
  } catch (error) {
    console.error('Load bank account error:', error)
    ElMessage.error('加载银行账户信息失败')
  } finally {
    loadingBankInfo.value = false
  }
}

// 复制银行账号
const copyAccountNumber = async () => {
  try {
    await navigator.clipboard.writeText(bankAccountInfo.value.account_number)
    ElMessage.success('账号已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

// 复制户名
const copyAccountName = async () => {
  try {
    await navigator.clipboard.writeText(bankAccountInfo.value.account_name)
    ElMessage.success('户名已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

// 复制开户行
const copyBankName = async () => {
  try {
    await navigator.clipboard.writeText(bankAccountInfo.value.bank_name)
    ElMessage.success('开户行已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

// 复制公司名
const copyCompanyName = async () => {
  try {
    await navigator.clipboard.writeText('北京触角科技有限公司')
    ElMessage.success('已复制')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

// 触发文件选择
const triggerUpload = () => {
  const uploadElement = voucherUploadRef.value?.$el.querySelector('input[type="file"]')
  if (uploadElement) {
    uploadElement.click()
  }
}

// 处理凭证图片上传
const handleVoucherChange = (file: UploadFile) => {
  if (!file.raw) return

  // 验证文件类型
  const isImage = file.raw.type.startsWith('image/')
  if (!isImage) {
    ElMessage.error('只能上传图片文件!')
    return
  }

  // 验证文件大小 (5MB)
  const isLt5M = file.raw.size / 1024 / 1024 < 5
  if (!isLt5M) {
    ElMessage.error('图片大小不能超过 5MB!')
    return
  }

  // 释放旧的 ObjectURL 以避免内存泄漏
  if (voucherImageUrl.value) {
    URL.revokeObjectURL(voucherImageUrl.value)
  }

  // 创建预览URL
  voucherImageUrl.value = URL.createObjectURL(file.raw)
  voucherFile.value = file.raw
  formData.value.voucher_image = file.name
}

// 重新上传凭证
const handleReuploadVoucher = () => {
  // 清除 el-upload 组件的内部状态，允许重新选择相同文件
  if (voucherUploadRef.value) {
    voucherUploadRef.value.clearFiles()
  }

  // 触发文件选择
  triggerUpload()
}

// 提交充值请求
const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  // 银行充值或微信充值提交
  if (formData.value.payment_method === 'bank_transfer' || formData.value.payment_method === 'wechat') {
    if (!voucherFile.value) {
      ElMessage.error(formData.value.payment_method === 'wechat' ? '请上传支付凭证' : '请上传充值凭证')
      return
    }

    submitting.value = true
    try {
      // 上传凭证图片
      const formDataUpload = new FormData()
      formDataUpload.append('file', voucherFile.value)

      const uploadResponse = await http.post('/operators/upload/bank-transfer-voucher', formDataUpload, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      const voucherUrl = uploadResponse.data.url

      // 提交申请
      const response = await http.post('/operators/me/bank-transfers', {
        amount: formData.value.amount,
        voucher_image_url: voucherUrl,
        remark: formData.value.remark || null,
        payment_method: formData.value.payment_method,  // 传递支付方式
      })

      const successMessage = formData.value.payment_method === 'wechat'
        ? '微信充值申请已提交,请等待财务审核'
        : '银行充值申请已提交,请等待财务审核'
      ElMessage.success(successMessage)
      resetForm()
      await loadBankTransfers()
    } catch (error: any) {
      console.error('Submit payment error:', error)
      ElMessage.error(error.response?.data?.detail?.message || '提交申请失败')
    } finally {
      submitting.value = false
    }
  } else {
    // 微信/支付宝支付
    submitting.value = true
    try {
      const response = await operatorStore.recharge({
        amount: formData.value.amount,
        payment_method: formData.value.payment_method,
      })

      paymentInfo.value = response
      ElMessage.success('充值订单已创建,请完成支付')
    } catch (error) {
      console.error('Recharge error:', error)
      ElMessage.error('创建充值订单失败')
    } finally {
      submitting.value = false
    }
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
    ElMessage.warning('支付可能尚未完成,请稍后再试')
  }
}

// 重置表单
const resetForm = () => {
  paymentInfo.value = null
  formData.value = {
    amount: '',
    payment_method: 'bank_transfer',
    voucher_image: '',
    remark: '',
  }

  // 释放 ObjectURL 以避免内存泄漏
  if (voucherImageUrl.value) {
    URL.revokeObjectURL(voucherImageUrl.value)
  }

  voucherImageUrl.value = ''
  voucherFile.value = null

  // 清除 el-upload 组件的内部状态
  if (voucherUploadRef.value) {
    voucherUploadRef.value.clearFiles()
  }

  formRef.value?.resetFields()
}

// 加载充值申请列表
const loadBankTransfers = async () => {
  loadingTransfers.value = true
  try {
    const params: any = {
      page: transferPagination.value.page,
      page_size: transferPagination.value.page_size,
    }

    if (searchQuery.value) {
      params.search = searchQuery.value
    }

    if (filterStatus.value) {
      params.status = filterStatus.value
    }

    const response = await http.get('/operators/me/bank-transfers', {
      params
    })

    // 前端筛选日期（后端不支持日期筛选）
    let items = response.data.items || []
    let total = response.data.total || 0

    if (filterDateRange.value && filterDateRange.value.length === 2) {
      const [start, end] = filterDateRange.value
      const startTime = new Date(start).setHours(0, 0, 0, 0)
      const endTime = new Date(end).setHours(23, 59, 59, 999)
      items = items.filter((item: any) => {
        const itemTime = new Date(item.created_at).getTime()
        return itemTime >= startTime && itemTime <= endTime
      })
      total = items.length
    }

    bankTransfers.value = items
    transferPagination.value.total = total
  } catch (error) {
    console.error('Load bank transfers error:', error)
    ElMessage.error('加载申请列表失败')
  } finally {
    loadingTransfers.value = false
  }
}

// 查看凭证
const viewVoucher = (row: any) => {
  // 确保URL是绝对路径，如果是相对路径则添加根路径
  const url = row.voucher_image_url
  currentVoucher.value = url.startsWith('http') || url.startsWith('/') ? url : `/${url}`
  voucherDialogVisible.value = true
}

// 取消申请
const cancelTransfer = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要取消这个充值申请吗?充值金额: ¥${row.amount}`,
      '取消申请',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 使用id字段(UUID)进行删除
    await http.delete(`/operators/me/bank-transfers/${row.id}`)
    ElMessage.success('申请已取消')
    await loadBankTransfers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Cancel transfer error:', error)
      ElMessage.error('取消申请失败')
    }
  }
}

// 搜索处理
const handleSearch = () => {
  transferPagination.value.page = 1
  loadBankTransfers()
}

// 重置搜索条件
const handleReset = () => {
  searchQuery.value = ''
  filterStatus.value = ''
  filterDateRange.value = null
  transferPagination.value.page = 1
  loadBankTransfers()
}

// 页大小变化
const handlePageSizeChange = () => {
  transferPagination.value.page = 1
  loadBankTransfers()
}

// 获取状态类型
const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
  }
  return types[status] || 'info'
}

// 获取状态标签
const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝',
  }
  return labels[status] || status
}

// 付款类型标签
const getPaymentMethodType = (method: string) => {
  const types: Record<string, any> = {
    wechat: 'success',
    bank_transfer: 'primary',
  }
  return types[method] || 'info'
}

const getPaymentMethodLabel = (method: string) => {
  const labels: Record<string, string> = {
    wechat: '微信充值',
    bank_transfer: '银行充值',
  }
  return labels[method] || method || '银行充值'
}

onMounted(() => {
  loadBankAccountInfo()
  loadBankTransfers()
})
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

.payment-method.disabled {
  opacity: 0.5;
}

.bank-transfer-notice p {
  margin: 5px 0;
  line-height: 1.6;
}

.bank-info-card {
  margin-top: 15px;
  background-color: #f5f7fa;
}

.bank-info-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.wechat-notice p {
  margin: 5px 0;
  line-height: 1.6;
}

.wechat-info-card {
  margin-top: 15px;
  background-color: #f5f7fa;
}

.wechat-info-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.wechat-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.qr-code-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}

.qr-code-wrapper {
  padding: 15px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.qr-code-hint {
  margin-top: 15px;
  font-size: 14px;
  color: #606266;
  text-align: center;
}

.company-info {
  margin-top: 10px;
}

.copyable-text {
  cursor: pointer;
  user-select: none;
  transition: color 0.2s;
}

.copyable-text:hover {
  color: #409EFF;
}

.account-number {
  display: flex;
  align-items: center;
}

.voucher-uploader-hidden {
  display: none;
}

.voucher-preview {
  width: 200px;
  height: 200px;
  cursor: pointer;
}

.upload-trigger {
  width: 200px;
  height: 200px;
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-trigger:hover {
  border-color: #409EFF;
}

.upload-icon {
  font-size: 40px;
  color: #8c939d;
  margin-bottom: 10px;
}

.upload-text {
  font-size: 14px;
  color: #606266;
  margin-bottom: 5px;
}

.upload-hint {
  font-size: 12px;
  color: #909399;
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #909399;
  width: 100%;
  height: 100%;
  justify-content: center;
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.amount-text {
  color: #67C23A;
  font-weight: 600;
}

.empty-text {
  color: #909399;
}

.reject-reason {
  color: #F56C6C;
}

.empty-state {
  padding: 40px 0;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.voucher-view {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  max-height: 70vh;
  overflow-y: auto;
}
</style>
