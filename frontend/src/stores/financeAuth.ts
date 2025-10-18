import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import http from '@/utils/http'

// 财务人员信息接口
export interface FinanceProfile {
  finance_id: string
  username: string
  full_name: string
  role: string
  email: string
}

// 财务登录请求接口
export interface FinanceLoginRequest {
  username: string
  password: string
}

// 财务登录响应接口
export interface FinanceLoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  finance: FinanceProfile
}

export const useFinanceAuthStore = defineStore('financeAuth', () => {
  // 状态
  const accessToken = ref<string | null>(localStorage.getItem('finance_access_token'))
  const financeId = ref<string | null>(localStorage.getItem('finance_id'))
  const profile = ref<FinanceProfile | null>(null)
  const isLoading = ref(false)

  // 计算属性
  const isAuthenticated = computed(() => !!accessToken.value)

  // 登录
  async function login(credentials: FinanceLoginRequest): Promise<FinanceLoginResponse> {
    isLoading.value = true
    try {
      const response = await http.post<FinanceLoginResponse>('/v1/auth/finance/login', credentials)
      const loginResponse = response.data

      // 提取数据
      const { access_token, finance } = loginResponse

      // 保存token和finance_id
      accessToken.value = access_token
      financeId.value = finance.finance_id
      localStorage.setItem('finance_access_token', access_token)
      localStorage.setItem('finance_id', finance.finance_id)

      // 保存用户基本信息
      profile.value = finance

      return loginResponse
    } finally {
      isLoading.value = false
    }
  }

  // 登出
  async function logout(): Promise<void> {
    try {
      // 暂时不调用后端登出接口，因为可能还未实现
      // await http.post('/v1/auth/finance/logout')
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      // 无论成功失败都清除本地状态
      accessToken.value = null
      financeId.value = null
      profile.value = null
      localStorage.removeItem('finance_access_token')
      localStorage.removeItem('finance_id')
    }
  }

  // 获取个人信息（如果后端有相应接口）
  async function fetchProfile(): Promise<void> {
    if (!isAuthenticated.value) return

    try {
      // const response = await http.get<FinanceProfile>('/v1/finance/me')
      // profile.value = response.data
    } catch (error) {
      console.error('Fetch profile error:', error)
    }
  }

  return {
    // 状态
    accessToken,
    financeId,
    profile,
    isLoading,
    // 计算属性
    isAuthenticated,
    // 方法
    login,
    logout,
    fetchProfile,
  }
})
