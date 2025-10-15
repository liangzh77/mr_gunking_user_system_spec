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

          <el-descriptions :column="1" border>
            <el-descriptions-item label="用户名">
              {{ authStore.profile?.username }}
            </el-descriptions-item>
            <el-descriptions-item label="邮箱">
              {{ authStore.profile?.email }}
            </el-descriptions-item>
            <el-descriptions-item label="手机号">
              {{ authStore.profile?.phone }}
            </el-descriptions-item>
            <el-descriptions-item label="公司名称">
              {{ authStore.profile?.company_name || '未填写' }}
            </el-descriptions-item>
            <el-descriptions-item label="客户等级">
              <el-tag :type="tierTagType" size="small">{{ tierLabel }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="注册时间">
              {{ formatDateTime(authStore.profile?.created_at || '') }}
            </el-descriptions-item>
          </el-descriptions>

          <div style="margin-top: 16px">
            <el-button type="primary" @click="dialogVisible = true">编辑信息</el-button>
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

          <el-descriptions :column="1" border>
            <el-descriptions-item label="当前余额">
              <span class="amount-value">¥{{ authStore.profile?.balance }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="累计消费">
              <span class="amount-value">¥{{ authStore.profile?.total_spent }}</span>
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
      @close="resetForm"
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
        <el-form-item label="公司名称" prop="company_name">
          <el-input v-model="profileForm.company_name" />
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
import dayjs from 'dayjs'

const authStore = useAuthStore()

const dialogVisible = ref(false)
const loading = ref(false)
const formRef = ref<FormInstance>()

const profileForm = reactive({
  email: '',
  phone: '',
  company_name: '',
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

const formatDateTime = (datetime: string) => {
  return dayjs(datetime).format('YYYY-MM-DD HH:mm:ss')
}

const resetForm = () => {
  if (authStore.profile) {
    profileForm.email = authStore.profile.email
    profileForm.phone = authStore.profile.phone
    profileForm.company_name = authStore.profile.company_name || ''
  }
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
</style>
