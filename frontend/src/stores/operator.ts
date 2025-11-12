import { defineStore } from 'pinia'
import { ref } from 'vue'
import type {
  Transaction,
  RechargeRequest,
  RechargeResponse,
  RefundRequest,
  Refund,
  InvoiceRequest,
  Invoice,
  OperationSite,
  SiteCreateRequest,
  AuthorizedApplication,
  ApplicationRequest,
  UsageRecord,
  SiteStatistics,
  ApplicationStatistics,
  ConsumptionStatistics,
  PlayerDistribution,
  PaginationParams,
  PaginationResponse,
} from '@/types'
import http from '@/utils/http'

export const useOperatorStore = defineStore('operator', () => {
  const isLoading = ref(false)

  // ========== 余额与交易 ==========
  async function getBalance(): Promise<{ balance: string; total_spent: string }> {
    const response = await http.get('/operators/me/balance')
    return response.data
  }

  async function getTransactions(params?: PaginationParams): Promise<PaginationResponse<Transaction>> {
    const response = await http.get('/operators/me/transactions', { params })
    return response.data
  }

  // ========== 充值 ==========
  async function recharge(data: RechargeRequest): Promise<RechargeResponse> {
    const response = await http.post('/operators/me/recharge', data)
    return response.data
  }

  // ========== 退款 ==========
  async function applyRefund(data: RefundRequest): Promise<Refund> {
    const response = await http.post('/operators/me/refunds', data)
    return response.data
  }

  async function getRefunds(params?: PaginationParams): Promise<PaginationResponse<Refund>> {
    const response = await http.get('/operators/me/refunds', { params })
    return response.data
  }

  // ========== 发票 ==========
  async function applyInvoice(data: InvoiceRequest): Promise<Invoice> {
    const response = await http.post('/operators/me/invoices', data)
    return response.data
  }

  async function getInvoices(params?: PaginationParams): Promise<PaginationResponse<Invoice>> {
    const response = await http.get('/operators/me/invoices', { params })
    return response.data.data || { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 }
  }

  async function cancelInvoice(invoiceId: string): Promise<void> {
    await http.delete(`/operators/me/invoices/${invoiceId}`)
  }

  // ========== 运营点管理 ==========
  async function createSite(data: SiteCreateRequest): Promise<OperationSite> {
    const response = await http.post('/operators/me/sites', data)
    return response.data
  }

  async function getSites(): Promise<OperationSite[]> {
    const response = await http.get('/operators/me/sites')
    return response.data.data?.sites || []
  }

  async function getSite(siteId: string): Promise<OperationSite> {
    const response = await http.get(`/operators/me/sites/${siteId}`)
    return response.data
  }

  async function updateSite(siteId: string, data: Partial<SiteCreateRequest>): Promise<OperationSite> {
    const response = await http.put(`/operators/me/sites/${siteId}`, data)
    return response.data
  }

  async function deleteSite(siteId: string): Promise<void> {
    await http.delete(`/operators/me/sites/${siteId}`)
  }

  // ========== 应用授权 ==========
  async function getAuthorizedApplications(): Promise<AuthorizedApplication[]> {
    const response = await http.get('/operators/me/applications')
    return response.data.data?.applications || []
  }

  async function createApplicationRequest(appId: string, reason: string): Promise<ApplicationRequest> {
    const response = await http.post('/operators/me/applications/requests', {
      app_id: appId,
      reason,
    })
    return response.data
  }

  async function getApplicationRequests(): Promise<ApplicationRequest[]> {
    const response = await http.get('/operators/me/applications/requests')
    return response.data.data?.items || []
  }

  // ========== 使用记录 ==========
  async function getUsageRecords(params?: {
    start_time?: string
    end_time?: string
    site_id?: string
    app_id?: string
    page?: number
    page_size?: number
  }): Promise<PaginationResponse<UsageRecord>> {
    const response = await http.get('/operators/me/usage-records', { params })
    return response.data.data  // API返回 { success: true, data: {...} }，需要提取data字段
  }

  async function getUsageRecord(recordId: string): Promise<UsageRecord> {
    const response = await http.get(`/operators/me/usage-records/${recordId}`)
    return response.data.data  // API返回 { success: true, data: {...} }，需要提取data字段
  }

  // ========== 统计数据 ==========
  async function getStatisticsBySite(params?: {
    start_time?: string
    end_time?: string
  }): Promise<{ sites: SiteStatistics[] }> {
    const response = await http.get('/operators/me/statistics/by-site', { params })
    return response.data.data  // API返回 { success: true, data: {...} }，需要提取data字段
  }

  async function getStatisticsByApplication(params?: {
    start_time?: string
    end_time?: string
  }): Promise<{ applications: ApplicationStatistics[] }> {
    const response = await http.get('/operators/me/statistics/by-app', { params })  // 后端路由是 by-app 不是 by-application
    return response.data.data  // API返回 { success: true, data: {...} }，需要提取data字段
  }

  async function getStatisticsByTime(params: {
    dimension: 'day' | 'week' | 'month'
    start_time?: string
    end_time?: string
  }): Promise<ConsumptionStatistics> {
    const response = await http.get('/operators/me/statistics/consumption', { params })  // 后端路由是 consumption 不是 by-time
    return response.data.data  // API返回 { success: true, data: {...} }，需要提取data字段
  }

  async function getPlayerDistribution(params?: {
    start_time?: string
    end_time?: string
  }): Promise<PlayerDistribution> {
    const response = await http.get('/operators/me/statistics/player-distribution', { params })
    return response.data.data  // API返回 { success: true, data: {...} }，需要提取data字段
  }

  // ========== 数据导出 ==========
  async function exportUsageRecords(params?: {
    format?: 'excel' | 'csv'
    start_time?: string
    end_time?: string
    site_id?: string
    app_id?: string
  }): Promise<{ download_url: string; filename: string }> {
    const response = await http.get('/operators/me/usage-records/export', { params })
    return response.data.data  // API返回 { success: true, data: {...} }，需要提取data字段
  }

  async function exportStatistics(params: {
    format?: 'excel' | 'csv'
    report_type: 'site' | 'application' | 'consumption' | 'player_distribution'
    start_time?: string
    end_time?: string
    dimension?: 'day' | 'week' | 'month'
  }): Promise<{ download_url: string; filename: string }> {
    const response = await http.get('/operators/me/statistics/export', { params })
    return response.data.data  // API返回 { success: true, data: {...} }，需要提取data字段
  }

  return {
    isLoading,
    // 余额与交易
    getBalance,
    getTransactions,
    // 充值
    recharge,
    // 退款
    applyRefund,
    getRefunds,
    // 发票
    applyInvoice,
    getInvoices,
    cancelInvoice,
    // 运营点
    createSite,
    getSites,
    getSite,
    updateSite,
    deleteSite,
    // 应用授权
    getAuthorizedApplications,
    createApplicationRequest,
    getApplicationRequests,
    // 使用记录
    getUsageRecords,
    getUsageRecord,
    // 统计
    getStatisticsBySite,
    getStatisticsByApplication,
    getStatisticsByTime,
    getPlayerDistribution,
    // 导出
    exportUsageRecords,
    exportStatistics,
  }
})
