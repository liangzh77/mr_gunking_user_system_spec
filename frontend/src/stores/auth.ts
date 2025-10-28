import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { LoginRequest, RegisterRequest, LoginResponse, OperatorProfile } from '@/types'
import http from '@/utils/http'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const operatorId = ref<string | null>(localStorage.getItem('operator_id'))
  const profile = ref<OperatorProfile | null>(null)
  const isLoading = ref(false)

  // 计算属性
  const isAuthenticated = computed(() => !!accessToken.value)

  // 登录
  async function login(credentials: LoginRequest): Promise<LoginResponse> {
    isLoading.value = true
    try {
      const response = await http.post<LoginResponse>('/auth/operators/login', credentials)
      const loginResponse = response.data

      // 提取嵌套的数据
      const { access_token, operator } = loginResponse.data

      // 保存token和operator_id
      accessToken.value = access_token
      operatorId.value = operator.operator_id
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('operator_id', operator.operator_id)

      // 获取用户信息
      await fetchProfile()

      return loginResponse
    } finally {
      isLoading.value = false
    }
  }

  // 注册
  async function register(data: RegisterRequest): Promise<void> {
    isLoading.value = true
    try {
      await http.post('/auth/operators/register', data)
    } finally {
      isLoading.value = false
    }
  }

  // 登出
  async function logout(): Promise<void> {
    try {
      await http.post('/auth/operators/logout')
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      // 无论成功失败都清除本地状态
      accessToken.value = null
      operatorId.value = null
      profile.value = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('operator_id')
    }
  }

  // 获取个人信息
  async function fetchProfile(): Promise<void> {
    if (!isAuthenticated.value) return

    try {
      const response = await http.get<OperatorProfile>('/operators/me')
      profile.value = response.data
    } catch (error) {
      console.error('Fetch profile error:', error)
    }
  }

  // 更新个人信息
  async function updateProfile(data: Partial<OperatorProfile>): Promise<void> {
    const response = await http.put<OperatorProfile>('/operators/me', data)
    profile.value = response.data
  }

  // 重置API Key
  async function regenerateApiKey(): Promise<void> {
    await http.post('/operators/me/api-key/regenerate')
    await fetchProfile()
  }

  return {
    // 状态
    accessToken,
    operatorId,
    profile,
    isLoading,
    // 计算属性
    isAuthenticated,
    // 方法
    login,
    register,
    logout,
    fetchProfile,
    updateProfile,
    regenerateApiKey,
  }
})
