<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <h2>MR游戏运营管理系统</h2>
          <p>财务人员登录</p>
        </div>
      </template>

      <el-form :model="loginForm" :rules="rules" ref="loginFormRef" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input
            ref="usernameInputRef"
            v-model="loginForm.username"
            placeholder="请输入用户名"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item prop="captcha_code">
          <Captcha
            size="large"
            api-base-url="/finance"
            @update:captcha-key="loginForm.captcha_key = $event"
            @update:captcha-code="loginForm.captcha_code = $event"
            ref="captchaRef"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="financeAuthStore.isLoading"
            @click="handleLogin"
            class="login-button"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <el-divider />
        <div class="other-logins">
          <router-link to="/operator/login" class="link">运营商登录</router-link>
          <el-divider direction="vertical" />
          <router-link to="/admin/login" class="link">管理员登录</router-link>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useFinanceAuthStore } from '@/stores/financeAuth'
import Captcha from '@/components/Captcha.vue'

const router = useRouter()
const route = useRoute()
const financeAuthStore = useFinanceAuthStore()

// 表单引用
const loginFormRef = ref<FormInstance>()
const usernameInputRef = ref()
const captchaRef = ref()

// 登录表单
const loginForm = reactive({
  username: '',
  password: '',
  captcha_key: '',
  captcha_code: '',
})

// 页面加载时自动聚焦到用户名输入框
onMounted(() => {
  usernameInputRef.value?.focus()
})

// 验证规则
const rules = reactive<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 64, message: '用户名长度为3-64个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 32, message: '密码长度为8-32个字符', trigger: 'blur' },
  ],
  captcha_code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 4, message: '验证码长度为4位', trigger: 'blur' },
  ],
})

// 处理登录
const handleLogin = async () => {
  if (!loginFormRef.value) return

  try {
    await loginFormRef.value.validate()

    await financeAuthStore.login({
      username: loginForm.username,
      password: loginForm.password,
      captcha_key: loginForm.captcha_key,
      captcha_code: loginForm.captcha_code,
    })

    ElMessage.success('登录成功')

    // 跳转到目标页面或财务仪表盘
    const redirect = route.query.redirect as string
    router.push(redirect || '/finance/dashboard')
  } catch (error: any) {
    // 登录失败后刷新验证码
    captchaRef.value?.refresh()

    if (error.response?.status === 401) {
      ElMessage.error('用户名或密码错误')
    } else if (error.errors) {
      // 验证错误，不显示消息
    } else {
      ElMessage.error(error.message || '登录失败，请稍后重试')
    }
  }
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

.login-button {
  width: 100%;
}

.login-footer {
  margin-top: 10px;
}

.other-logins {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}

.link {
  color: #409eff;
  text-decoration: none;
  font-size: 14px;
}

.link:hover {
  text-decoration: underline;
}
</style>
