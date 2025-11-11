// 通用类型定义

export interface ApiResponse<T = any> {
  data?: T
  error_code?: string
  message?: string
}

export interface PaginationParams {
  page?: number
  page_size?: number
}

export interface PaginationResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// 运营商相关类型
export interface OperatorProfile {
  operator_id: string
  username: string
  email: string
  phone: string
  name: string  // 真实姓名或公司名
  customer_tier: 'trial' | 'regular' | 'vip'
  balance: string
  total_spent: string
  created_at: string
  updated_at: string
}

export interface LoginRequest {
  username: string
  password: string
  captcha_key: string
  captcha_code: string
}

export interface RegisterRequest {
  username: string
  password: string
  name: string  // 真实姓名或公司名
  email: string
  phone: string
}

export interface LoginResponse {
  success: boolean
  data: {
    access_token: string
    token_type: string
    expires_in: number
    operator: {
      operator_id: string
      username: string
      name: string
      category: string
    }
  }
}

// 运营点相关类型
export interface OperationSite {
  site_id: string
  name: string  // 运营点名称（后端返回name而非site_name）
  address: string
  contact_person?: string
  contact_phone?: string
  description?: string
  api_key?: string
  api_secret?: string
  is_active?: boolean
  is_deleted?: boolean
  created_at: string
  updated_at: string
}

export interface SiteCreateRequest {
  name: string  // 运营点名称（后端字段为name）
  address: string
  description?: string
  contact_person?: string
  contact_phone?: string
}

// 交易记录类型
export interface Transaction {
  transaction_id: string
  operator_id: string
  transaction_type: 'recharge' | 'billing' | 'refund'
  amount: string
  balance_before: string
  balance_after: string
  description: string
  created_at: string
}

// 充值相关类型
export interface RechargeRequest {
  amount: string
  payment_method: 'wechat' | 'alipay'
  payment_channel?: 'native' | 'h5' | 'jsapi'
}

export interface RechargeResponse {
  order_id: string
  amount: string
  payment_method: string
  payment_url: string
  qr_code?: string
  expires_at: string
  created_at: string
}

// 退款相关类型
export interface RefundRequest {
  amount?: string
  reason: string
}

export interface Refund {
  refund_id: string
  operator_id: string
  amount: string
  reason: string
  status: 'pending' | 'approved' | 'rejected' | 'completed'
  admin_note?: string
  created_at: string
  updated_at: string
}

// 发票相关类型
export interface InvoiceRequest {
  amount: string
  invoice_type: 'regular' | 'vat'
  invoice_title: string
  tax_number: string
}

export interface Invoice {
  invoice_id: string
  operator_id: string
  amount: string
  invoice_type: string
  invoice_title: string
  tax_number: string
  status: 'pending' | 'approved' | 'rejected' | 'issued'
  invoice_number?: string
  invoice_url?: string
  created_at: string
  updated_at: string
}

// 使用记录类型
export interface UsageRecord {
  record_id: string
  operator_id: string
  site_id: string
  site_name: string
  app_id: string
  app_name: string
  session_id: string
  player_count: number
  unit_price: string
  total_cost: string
  created_at: string
}

// 统计数据类型
export interface SiteStatistics {
  site_id: string
  site_name: string
  total_sessions: number
  total_players: number
  total_cost: string
}

export interface ApplicationStatistics {
  app_id: string
  app_name: string
  total_sessions: number
  total_players: number
  avg_players_per_session: number
  total_cost: string
}

export interface ChartDataPoint {
  date: string
  total_sessions: number
  total_players: number
  total_cost: string
}

export interface ConsumptionStatistics {
  dimension: 'day' | 'week' | 'month'
  chart_data: ChartDataPoint[]
  summary: {
    total_sessions: number
    total_players: number
    total_cost: string
    avg_players_per_session: number
  }
}

export interface PlayerDistributionItem {
  player_count: number
  session_count: number
  percentage: number
  total_cost: string
}

export interface PlayerDistribution {
  distribution: PlayerDistributionItem[]
  total_sessions: number
  most_common_player_count: number
}

// 应用相关类型
export interface AuthorizedApplication {
  app_id: string
  app_name: string
  description?: string
  unit_price: string
  min_players: number
  max_players: number
  authorized_at: string
}

export interface ApplicationRequest {
  request_id: string
  app_id: string
  app_name: string
  reason: string
  status: 'pending' | 'approved' | 'rejected'
  admin_note?: string
  created_at: string
  updated_at: string
}

// 管理员相关类型
export interface AdminLoginRequest {
  username: string
  password: string
}

export interface AdminLoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: {
    id: string
    username: string
    full_name: string
    role: 'super_admin' | 'admin' | 'finance'
  }
}

export interface AdminProfile {
  id: string
  username: string
  full_name: string
  email?: string
  phone?: string
  role: 'super_admin' | 'admin' | 'finance'
  permissions: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

// 运营点类型
export interface Site {
  site_id: string
  operator_id: string
  operator_name?: string  // 所属运营商名称（管理后台返回）
  name: string  // 运营点名称（后端返回name而非site_name）
  address: string
  contact_person: string
  contact_phone: string
  description?: string  // 运营点描述
  is_active: boolean
  created_at: string
  updated_at: string
}

// 运营商详细信息类型
export interface Operator {
  id: string
  operator_id: string
  username: string
  full_name: string
  email: string
  phone: string
  customer_tier: 'trial' | 'standard' | 'premium' | 'vip'
  balance: string
  total_spent: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// 运营点创建请求类型
export interface SiteCreateRequest {
  site_name: string
  contact_person: string
  contact_phone: string
  address: string
  description?: string
}
