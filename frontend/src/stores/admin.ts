import { defineStore } from 'pinia'
import { ref } from 'vue'
import http from '@/utils/http'

export interface Operator {
  operator_id: string
  username: string
  full_name: string
  email: string
  phone: string
  company_name?: string
  customer_tier: 'trial' | 'regular' | 'vip'
  balance: string
  total_spent: string
  is_active: boolean
  is_locked: boolean
  locked_reason?: string
  locked_at?: string
  created_at: string
  updated_at: string
}

export interface Application {
  application_id: string
  app_code: string
  app_name: string
  description?: string
  price_per_player: string
  min_players: number
  max_players: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ApplicationRequest {
  request_id: string
  operator_id: string
  operator_name: string
  application_id: string
  app_name: string
  app_code: string
  reason: string
  status: 'pending' | 'approved' | 'rejected'
  admin_note?: string
  reviewed_by?: string
  reviewed_at?: string
  created_at: string
  updated_at: string
}

export interface PaginationParams {
  page?: number
  page_size?: number
  search?: string
  status?: string
}

export interface PaginationResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const useAdminStore = defineStore('admin', () => {
  const isLoading = ref(false)

  // ==================== 运营商管理 ====================

  /**
   * 获取运营商列表
   */
  async function getOperators(params?: PaginationParams): Promise<PaginationResponse<Operator>> {
    const response = await http.get('/admins/operators', { params })
    return response.data
  }

  /**
   * 获取运营商详情
   */
  async function getOperator(operatorId: string): Promise<Operator> {
    const response = await http.get(`/admins/operators/${operatorId}`)
    return response.data
  }

  /**
   * 锁定运营商账户
   */
  async function lockOperator(operatorId: string, reason: string): Promise<void> {
    await http.post(`/admins/operators/${operatorId}/lock`, { reason })
  }

  /**
   * 解锁运营商账户
   */
  async function unlockOperator(operatorId: string): Promise<void> {
    await http.post(`/admins/operators/${operatorId}/unlock`)
  }

  /**
   * 调整运营商余额
   */
  async function adjustBalance(
    operatorId: string,
    amount: string,
    description: string,
    type: 'add' | 'subtract'
  ): Promise<void> {
    await http.post(`/admins/operators/${operatorId}/balance/adjust`, {
      amount,
      description,
      type,
    })
  }

  // ==================== 应用管理 ====================

  /**
   * 获取应用列表
   */
  async function getApplications(params?: PaginationParams): Promise<PaginationResponse<Application>> {
    const response = await http.get('/admins/applications', { params })
    return response.data
  }

  /**
   * 创建新应用
   */
  async function createApplication(data: {
    app_code: string
    app_name: string
    description?: string
    price_per_player: string
    min_players: number
    max_players: number
  }): Promise<Application> {
    const response = await http.post('/admins/applications', data)
    return response.data
  }

  /**
   * 更新应用价格
   */
  async function updateApplicationPrice(
    appId: string,
    newPrice: string
  ): Promise<Application> {
    const response = await http.put(`/admins/applications/${appId}/price`, {
      new_price: newPrice,
    })
    return response.data
  }

  /**
   * 更新应用玩家数量范围
   */
  async function updatePlayerRange(
    appId: string,
    minPlayers: number,
    maxPlayers: number
  ): Promise<Application> {
    const response = await http.put(`/admins/applications/${appId}/player-range`, {
      min_players: minPlayers,
      max_players: maxPlayers,
    })
    return response.data
  }

  // ==================== 应用授权审核 ====================

  /**
   * 获取授权申请列表
   */
  async function getApplicationRequests(
    params?: PaginationParams
  ): Promise<PaginationResponse<ApplicationRequest>> {
    const response = await http.get('/admins/applications/requests', { params })
    return response.data
  }

  /**
   * 审核授权申请（批准/拒绝）
   */
  async function reviewApplicationRequest(
    requestId: string,
    action: 'approve' | 'reject',
    rejectReason?: string
  ): Promise<ApplicationRequest> {
    const response = await http.post(
      `/admins/applications/requests/${requestId}/review`,
      {
        action,
        reject_reason: rejectReason,
      }
    )
    return response.data
  }

  // ==================== 授权管理 ====================

  /**
   * 授权应用给运营商
   */
  async function authorizeApplication(
    operatorId: string,
    applicationId: string,
    expiresAt?: string
  ): Promise<void> {
    await http.post(`/admins/operators/${operatorId}/applications`, {
      application_id: applicationId,
      expires_at: expiresAt,
    })
  }

  /**
   * 撤销运营商的应用授权
   */
  async function revokeAuthorization(
    operatorId: string,
    appId: string
  ): Promise<void> {
    await http.delete(`/admins/operators/${operatorId}/applications/${appId}`)
  }

  // ==================== 统计数据 ====================

  /**
   * 获取仪表盘统计数据
   */
  async function getDashboardStats(): Promise<{
    operators_count: number
    applications_count: number
    pending_requests_count: number
    today_transactions_count: number
    today_revenue: string
  }> {
    const response = await http.get('/admins/dashboard/stats')
    return response.data
  }

  return {
    isLoading,
    // 运营商管理
    getOperators,
    getOperator,
    lockOperator,
    unlockOperator,
    adjustBalance,
    // 应用管理
    getApplications,
    createApplication,
    updateApplicationPrice,
    updatePlayerRange,
    // 授权审核
    getApplicationRequests,
    reviewApplicationRequest,
    // 授权管理
    authorizeApplication,
    revokeAuthorization,
    // 统计
    getDashboardStats,
  }
})
