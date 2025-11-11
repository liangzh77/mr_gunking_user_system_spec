<template>
  <div class="register-container">
    <el-card class="register-card">
      <template #header>
        <div class="card-header">
          <h2>MR游戏运营管理系统</h2>
          <p>运营商注册</p>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="registerForm"
        :rules="rules"
        label-width="100px"
        @submit.prevent="handleRegister"
      >
        <el-form-item label="用户名" prop="username" required>
          <el-input
            v-model="registerForm.username"
            placeholder="3-20个字符,支持字母数字下划线"
            clearable
          />
        </el-form-item>

        <el-form-item label="密码" prop="password" required>
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="8-32个字符,必须包含大小写字母和数字"
            show-password
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword" required>
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="邮箱" prop="email" required>
          <el-input
            v-model="registerForm.email"
            type="email"
            placeholder="请输入邮箱地址"
            clearable
          />
        </el-form-item>

        <el-form-item label="手机号" prop="phone" required>
          <el-input
            v-model="registerForm.phone"
            placeholder="请输入手机号码"
            clearable
          />
        </el-form-item>

        <el-form-item label="短信验证码" prop="smsCode" required>
          <div style="display: flex; gap: 10px">
            <el-input
              v-model="registerForm.smsCode"
              placeholder="请输入6位验证码"
              maxlength="6"
              style="flex: 1"
            />
            <el-button
              type="primary"
              :disabled="sendingSMS || countdown > 0"
              @click="sendSMSCode"
            >
              {{ countdown > 0 ? `${countdown}秒后重试` : '发送验证码' }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="姓名/公司" prop="name" required>
          <el-input
            v-model="registerForm.name"
            placeholder="真实姓名或公司名称"
            clearable
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="authStore.isLoading"
            style="width: 100%"
            @click="handleRegister"
          >
            注册
          </el-button>
        </el-form-item>

        <el-form-item>
          <div class="footer-links">
            <span>已有账号?</span>
            <el-link type="primary" @click="goToLogin">立即登录</el-link>
          </div>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import type { RegisterRequest } from '@/types'
import axios from 'axios'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const registerForm = reactive<RegisterRequest & { confirmPassword: string; smsCode: string }>({
  username: '',
  password: '',
  name: '',
  email: '',
  phone: '',
  confirmPassword: '',
  smsCode: '',
})

// 短信验证码相关
const smsKey = ref('')
const sendingSMS = ref(false)
const countdown = ref(0)
let countdownTimer: ReturnType<typeof setInterval> | null = null

// 自定义验证规则
const validateUsername = (_rule: any, value: any, callback: any) => {
  if (!value) {
    return callback(new Error('请输入用户名'))
  }
  if (value.length < 3 || value.length > 20) {
    return callback(new Error('用户名长度在3-20个字符'))
  }
  if (!/^[a-zA-Z0-9_]+$/.test(value)) {
    return callback(new Error('用户名只能包含字母、数字和下划线'))
  }
  callback()
}

const validatePassword = (_rule: any, value: any, callback: any) => {
  if (!value) {
    return callback(new Error('请输入密码'))
  }
  if (value.length < 8 || value.length > 32) {
    return callback(new Error('密码长度在8-32个字符'))
  }
  if (!(/[A-Z]/.test(value) && /[a-z]/.test(value) && /\d/.test(value))) {
    return callback(new Error('密码必须包含大小写字母和数字'))
  }
  callback()
}

const validateConfirmPassword = (_rule: any, value: any, callback: any) => {
  if (!value) {
    return callback(new Error('请再次输入密码'))
  }
  if (value !== registerForm.password) {
    return callback(new Error('两次输入的密码不一致'))
  }
  callback()
}

const validatePhone = (_rule: any, value: any, callback: any) => {
  if (!value) {
    return callback(new Error('请输入手机号'))
  }
  if (!/^1[3-9]\d{9}$/.test(value)) {
    return callback(new Error('请输入有效的手机号码'))
  }
  callback()
}

const validateSmsCode = (_rule: any, value: any, callback: any) => {
  if (!value) {
    return callback(new Error('请输入短信验证码'))
  }
  if (!/^\d{6}$/.test(value)) {
    return callback(new Error('请输入6位数字验证码'))
  }
  callback()
}

const rules: FormRules = {
  username: [{ validator: validateUsername, trigger: 'blur' }],
  password: [{ validator: validatePassword, trigger: 'blur' }],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  phone: [{ validator: validatePhone, trigger: 'blur' }],
  smsCode: [{ validator: validateSmsCode, trigger: 'blur' }],
  name: [
    { required: true, message: '请输入姓名或公司名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在2-50个字符', trigger: 'blur' },
  ],
}

// 发送短信验证码
const sendSMSCode = async () => {
  // 先验证手机号
  if (!registerForm.phone) {
    ElMessage.error('请先输入手机号')
    return
  }

  if (!/^1[3-9]\d{9}$/.test(registerForm.phone)) {
    ElMessage.error('请输入有效的手机号码')
    return
  }

  sendingSMS.value = true

  try {
    const response = await axios.post('/api/v1/common/sms/send', {
      phone: registerForm.phone,
    })

    smsKey.value = response.data.sms_key
    ElMessage.success(response.data.message || '验证码已发送')

    // 开始倒计时(60秒)
    countdown.value = 60
    countdownTimer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0 && countdownTimer) {
        clearInterval(countdownTimer)
        countdownTimer = null
      }
    }, 1000)
  } catch (error: any) {
    console.error('Send SMS error:', error)
    const errorMessage = error.response?.data?.detail?.message || '发送失败,请稍后重试'
    ElMessage.error(errorMessage)
  } finally {
    sendingSMS.value = false
  }
}

const handleRegister = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    if (!smsKey.value) {
      ElMessage.error('请先获取短信验证码')
      return
    }

    try {
      // 提取注册所需字段,排除confirmPassword,添加短信验证码字段
      const { confirmPassword: _, smsCode, ...registerData } = registerForm
      const requestData = {
        ...registerData,
        sms_key: smsKey.value,
        sms_code: smsCode,
      }
      await authStore.register(requestData as any)
      ElMessage.success('注册成功,请登录')
      router.push('/operator/login')
    } catch (error: any) {
      console.error('Register error:', error)
      // 显示详细错误信息
      const errorMessage = error.response?.data?.detail?.message || error.message || '注册失败,请稍后重试'
      ElMessage.error(errorMessage)
      return  // 失败时不跳转,停止执行
    }
  })
}

const goToLogin = () => {
  router.push('/operator/login')
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-card {
  width: 500px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: #303133;
}

.card-header p {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

.footer-links {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #909399;
}
</style>
