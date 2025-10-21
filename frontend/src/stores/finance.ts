import { defineStore } from 'pinia'
import { ref } from 'vue'
import http from '@/utils/http'

// ==================== Dashboard数据看板 ====================

export interface DashboardOverview {
  today_recharge: string
  today_consumption: string
  today_refund: string
  today_net_income: string
  total_operators: number
  active_operators_today: number
}

export interface ChartDataPoint {
  date: string
  recharge: string
  consumption: string
  refund: string
  net_income: string
}

export interface DashboardTrends {
  month: string
  chart_data: ChartDataPoint[]
  summary: {
    total_recharge: string
    total_consumption: string
    total_refund: string
    total_net_income: string
  }
}

export interface TopCustomer {
  operator_id: string
  username: string
  full_name: string
  total_recharge: string
  total_consumption: string
  balance: string
}

export interface TopCustomersResponse {
  customers: TopCustomer[]
  total_count: number
}

export interface CustomerFinanceDetails {
  operator_id: string
  username: string
  full_name: string
  balance: string
  total_recharge: string
  total_consumption: string
  total_refund: string
  recent_transactions: Array<{
    transaction_id: string
    transaction_type: string
    amount: string
    created_at: string
    description: string
  }>
}

// ==================== 退款审核 ====================

export interface Refund {
  refund_id: string
  operator_id: string
  operator_name: string
  amount: string
  reason: string
  status: 'pending' | 'approved' | 'rejected'
  admin_note?: string
  reviewed_by?: string
  reviewed_at?: string
  requested_at: string
  created_at: string
  updated_at: string
}

export interface RefundListResponse {
  refunds: Refund[]
  total: number
  page: number
  page_size: number
}

export interface RefundApproveRequest {
  admin_note?: string
}

export interface RefundRejectRequest {
  reject_reason: string
}

// ==================== 开票审核 ====================

export interface Invoice {
  invoice_id: string
  operator_id: string
  operator_name: string
  invoice_type: 'regular' | 'vat'
  amount: string
  invoice_title: string
  tax_number: string
  bank_name?: string
  bank_account?: string
  address?: string
  phone?: string
  status: 'pending' | 'approved' | 'rejected' | 'issued'
  invoice_number?: string
  invoice_url?: string
  admin_note?: string
  reviewed_by?: string
  reviewed_at?: string
  requested_at: string
  created_at: string
  updated_at: string
}

export interface InvoiceListResponse {
  invoices: Invoice[]
  total: number
  page: number
  page_size: number
}

export interface InvoiceApproveRequest {
  invoice_number: string
  invoice_url?: string
  admin_note?: string
}

export const useFinanceStore = defineStore('finance', () => {
  const isLoading = ref(false)

  // ==================== Dashboard数据看板 ====================

  /**
   * 获取今日收入概览
   */
  async function getDashboardOverview(): Promise<DashboardOverview> {
    const response = await http.get('/finance/dashboard')
    return response.data
  }

  /**
   * 获取月度收入趋势
   * @param month 月份(YYYY-MM格式,可选,默认当前月)
   */
  async function getDashboardTrends(month?: string): Promise<DashboardTrends> {
    const response = await http.get('/finance/dashboard/trends', {
      params: { month },
    })
    return response.data
  }

  /**
   * 获取消费金额Top客户列表
   * @param limit 返回数量限制(默认10)
   */
  async function getTopCustomers(limit: number = 10): Promise<TopCustomersResponse> {
    const response = await http.get('/finance/top-customers', {
      params: { limit },
    })
    return response.data
  }

  /**
   * 获取客户详细财务信息
   * @param operatorId 运营商ID
   */
  async function getCustomerFinanceDetails(
    operatorId: string
  ): Promise<CustomerFinanceDetails> {
    const response = await http.get(`/finance/customers/${operatorId}/details`)
    return response.data
  }

  // ==================== 退款审核 ====================

  /**
   * 获取退款申请列表
   * @param params 查询参数
   */
  async function getRefunds(params?: {
    status?: string
    search?: string
    page?: number
    page_size?: number
  }): Promise<RefundListResponse> {
    const response = await http.get('/finance/refunds', { params })
    return response.data
  }

  /**
   * 获取退款申请详情
   * @param refundId 退款ID
   */
  async function getRefundDetails(refundId: string): Promise<Refund> {
    const response = await http.get(`/finance/refunds/${refundId}`)
    return response.data
  }

  /**
   * 批准退款
   * @param refundId 退款ID
   * @param adminNote 管理员备注(可选)
   */
  async function approveRefund(refundId: string, adminNote?: string): Promise<Refund> {
    const response = await http.post(`/finance/refunds/${refundId}/approve`, {
      admin_note: adminNote,
    })
    return response.data
  }

  /**
   * 拒绝退款
   * @param refundId 退款ID
   * @param rejectReason 拒绝原因
   */
  async function rejectRefund(refundId: string, rejectReason: string): Promise<Refund> {
    const response = await http.post(`/finance/refunds/${refundId}/reject`, {
      reject_reason: rejectReason,
    })
    return response.data
  }

  // ==================== 开票审核 ====================

  /**
   * 获取开票申请列表
   * @param params 查询参数
   */
  async function getInvoices(params?: {
    status?: string
    search?: string
    page?: number
    page_size?: number
  }): Promise<InvoiceListResponse> {
    const response = await http.get('/finance/invoices', { params })
    return response.data
  }

  /**
   * 批准开票
   * @param invoiceId 发票ID
   * @param data 审批数据
   */
  async function approveInvoice(
    invoiceId: string,
    data: InvoiceApproveRequest
  ): Promise<Invoice> {
    const response = await http.post(`/finance/invoices/${invoiceId}/approve`, data)
    return response.data
  }

  /**
   * 拒绝开票
   * @param invoiceId 发票ID
   * @param rejectReason 拒绝原因
   */
  async function rejectInvoice(invoiceId: string, rejectReason: string): Promise<Invoice> {
    const response = await http.post(`/finance/invoices/${invoiceId}/reject`, {
      reject_reason: rejectReason,
    })
    return response.data
  }

  return {
    isLoading,
    // Dashboard
    getDashboardOverview,
    getDashboardTrends,
    getTopCustomers,
    getCustomerFinanceDetails,
    // 退款
    getRefunds,
    getRefundDetails,
    approveRefund,
    rejectRefund,
    // 发票
    getInvoices,
    approveInvoice,
    rejectInvoice,
  }
})
