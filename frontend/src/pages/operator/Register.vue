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
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="3-20个字符,支持字母数字下划线"
            clearable
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="8-32个字符,必须包含大小写字母和数字"
            show-password
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="registerForm.email"
            type="email"
            placeholder="请输入邮箱地址"
            clearable
          />
        </el-form-item>

        <el-form-item label="手机号" prop="phone">
          <el-input
            v-model="registerForm.phone"
            placeholder="请输入手机号码"
            clearable
          />
        </el-form-item>

        <el-form-item label="姓名/公司" prop="name">
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

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const registerForm = reactive<RegisterRequest & { confirmPassword: string }>({
  username: '',
  password: '',
  name: '',
  email: '',
  phone: '',
  confirmPassword: '',
})

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

const rules: FormRules = {
  username: [{ validator: validateUsername, trigger: 'blur' }],
  password: [{ validator: validatePassword, trigger: 'blur' }],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  phone: [{ validator: validatePhone, trigger: 'blur' }],
  name: [
    { required: true, message: '请输入姓名或公司名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在2-50个字符', trigger: 'blur' },
  ],
}

const handleRegister = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      // 提取注册所需字段,排除confirmPassword
      const { confirmPassword: _, ...registerData } = registerForm
      await authStore.register(registerData as RegisterRequest)
      ElMessage.success('注册成功,请登录')
      router.push('/operator/login')
    } catch (error) {
      console.error('Register error:', error)
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
