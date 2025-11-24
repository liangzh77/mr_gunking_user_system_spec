<template>
  <div class="profile-page">
    <el-row :gutter="20">
      <!-- 基本信息 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span class="card-title">
              <el-icon><User /></el-icon>
              基本信息
            </span>
          </template>

          <el-descriptions :column="1" border class="copyable-descriptions">
            <el-descriptions-item label="用户名">
              <span class="copyable-value" @click="handleCopyValue(authStore.profile?.username || '')">
                {{ authStore.profile?.username }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="邮箱">
              <span class="copyable-value" @click="handleCopyValue(authStore.profile?.email || '')">
                {{ authStore.profile?.email }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="手机号">
              <span class="copyable-value" @click="handleCopyValue(authStore.profile?.phone || '')">
                {{ authStore.profile?.phone }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="公司名称">
              <span class="copyable-value" @click="handleCopyValue(authStore.profile?.name || '未填写')">
                {{ authStore.profile?.name || '未填写' }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="客户等级">
              <el-tag :type="tierTagType" size="small">{{ tierLabel }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="注册时间">
              <span class="copyable-value" @click="handleCopyValue(formatDateTime(authStore.profile?.created_at || ''))">
                {{ formatDateTime(authStore.profile?.created_at || '') }}
              </span>
            </el-descriptions-item>
          </el-descriptions>

          <div style="margin-top: 16px">
            <el-button type="primary" @click="handleEdit">编辑信息</el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 账户统计 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span class="card-title">
              <el-icon><DataAnalysis /></el-icon>
              账户统计
            </span>
          </template>

          <el-descriptions :column="1" border class="copyable-descriptions">
            <el-descriptions-item label="当前余额">
              <span class="amount-value copyable-value" @click="handleCopyValue(`¥${authStore.profile?.balance}`)">
                ¥{{ formatAmount(authStore.profile?.balance) }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="累计消费">
              <span class="amount-value copyable-value" @click="handleCopyValue(`¥${authStore.profile?.total_spent}`)">
                ¥{{ formatAmount(authStore.profile?.total_spent) }}
              </span>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <!-- 编辑信息对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="编辑个人信息"
      width="500px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="profileForm"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="profileForm.email" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="profileForm.phone" />
        </el-form-item>
        <el-form-item label="公司名称" prop="name">
          <el-input v-model="profileForm.name" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="handleUpdate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime, formatAmount} from '@/utils/format'
import { copyToClipboard } from '@/utils/clipboard'

const authStore = useAuthStore()

const dialogVisible = ref(false)
const loading = ref(false)
const formRef = ref<FormInstance>()

const profileForm = reactive({
  email: '',
  phone: '',
  name: '',
})

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号码', trigger: 'blur' },
  ],
}

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

const resetForm = () => {
  if (authStore.profile) {
    profileForm.email = authStore.profile.email
    profileForm.phone = authStore.profile.phone
    profileForm.name = authStore.profile.name || ''
  }
}

// 打开编辑对话框
const handleEdit = () => {
  resetForm()  // 先填充表单数据
  dialogVisible.value = true  // 再打开对话框
}

// 对话框关闭时重置表单
const handleDialogClose = () => {
  formRef.value?.resetFields()
}

const handleUpdate = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      await authStore.updateProfile(profileForm)
      ElMessage.success('更新成功')
      dialogVisible.value = false
    } catch (error) {
      console.error('Update error:', error)
    } finally {
      loading.value = false
    }
  })
}

// 复制值到剪贴板
const handleCopyValue = async (value: string) => {
  const success = await copyToClipboard(value)
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

</script>

<style scoped>
.profile-page {
  max-width: 1200px;
  margin: 0 auto;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
}

.amount-value {
  font-size: 18px;
  font-weight: 600;
  color: #409EFF;
}

.copyable-value {
  cursor: copy;
  padding: 2px 4px;
  border-radius: 2px;
  transition: background-color 0.2s;
}

.copyable-value:hover {
  background-color: #e6f7ff;
}
</style>
