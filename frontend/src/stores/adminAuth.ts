import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AdminLoginRequest, AdminLoginResponse, AdminProfile } from '@/types'
import http from '@/utils/http'

export const useAdminAuthStore = defineStore('adminAuth', () => {
  // 状态
  const accessToken = ref<string | null>(localStorage.getItem('admin_access_token'))
  const adminId = ref<string | null>(localStorage.getItem('admin_id'))
  const profile = ref<AdminProfile | null>(null)
  const isLoading = ref(false)

  // 计算属性
  const isAuthenticated = computed(() => !!accessToken.value)

  // 登录
  async function login(credentials: AdminLoginRequest): Promise<AdminLoginResponse> {
    isLoading.value = true
    try {
      const response = await http.post<AdminLoginResponse>('/admins/auth/login', credentials)
      const loginResponse = response.data

      // 直接提取数据（后端不包装在 data 字段中）
      const { access_token, user } = loginResponse

      // 保存token和admin_id
      accessToken.value = access_token
      adminId.value = user.id
      localStorage.setItem('admin_access_token', access_token)
      localStorage.setItem('admin_id', user.id)

      // 保存用户基本信息
      profile.value = {
        id: user.id,
        username: user.username,
        full_name: user.full_name,
        role: user.role,
        permissions: [],
        is_active: true,
        created_at: '',
        updated_at: '',
      }

      // 获取完整的用户信息
      await fetchProfile()

      return loginResponse
    } finally {
      isLoading.value = false
    }
  }

  // 登出
  async function logout(): Promise<void> {
    try {
      await http.post('/admins/auth/logout')
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      // 无论成功失败都清除本地状态
      accessToken.value = null
      adminId.value = null
      profile.value = null
      localStorage.removeItem('admin_access_token')
      localStorage.removeItem('admin_id')
    }
  }

  // 获取个人信息
  async function fetchProfile(): Promise<void> {
    if (!isAuthenticated.value) return

    try {
      const response = await http.get<AdminProfile>('/admins/auth/me')
      profile.value = response.data
    } catch (error: any) {
      console.error('Fetch profile error:', error)
      // 如果是401错误，清除本地状态（http拦截器会处理跳转）
      if (error?.response?.status === 401) {
        accessToken.value = null
        adminId.value = null
        profile.value = null
        localStorage.removeItem('admin_access_token')
        localStorage.removeItem('admin_id')
      }
      // 继续抛出错误，让http拦截器处理
      throw error
    }
  }

  // 修改密码
  async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await http.post('/admins/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
  }

  return {
    // 状态
    accessToken,
    adminId,
    profile,
    isLoading,
    // 计算属性
    isAuthenticated,
    // 方法
    login,
    logout,
    fetchProfile,
    changePassword,
  }
})
