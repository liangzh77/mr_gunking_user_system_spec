<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <h2>MR游戏运营管理系统</h2>
          <p>管理员登录</p>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="loginForm"
        :rules="rules"
        label-width="80px"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入管理员用户名"
            prefix-icon="User"
            clearable
            autocomplete="username"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
            autocomplete="current-password"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="adminAuthStore.isLoading"
            style="width: 100%"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>

        <el-form-item>
          <div class="footer-links">
            <el-link type="info" href="/operator/login">切换到运营商登录</el-link>
          </div>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAdminAuthStore } from '@/stores/adminAuth'
import type { AdminLoginRequest } from '@/types'

const router = useRouter()
const route = useRoute()
const adminAuthStore = useAdminAuthStore()

const formRef = ref<FormInstance>()
const loginForm = reactive<AdminLoginRequest>({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 32, message: '用户名长度在3-32个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码长度在6-64个字符', trigger: 'blur' },
  ],
}

const handleLogin = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      await adminAuthStore.login(loginForm)
      ElMessage.success('登录成功')

      // 跳转到原页面或管理后台首页
      const redirect = route.query.redirect as string
      router.push(redirect || '/admin/dashboard')
    } catch (error) {
      console.error('Login error:', error)
      // 错误已在http拦截器中处理，这里不需要再显示
    }
  })
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 450px;
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
