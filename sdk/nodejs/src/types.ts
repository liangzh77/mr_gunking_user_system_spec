/**
 * MR SDK 类型定义
 */

// 基础配置
export interface MRConfig {
  baseURL: string;
  timeout?: number;
  retryCount?: number;
  retryDelay?: number;
}

// 运营商认证相关
export interface OperatorRegisterRequest {
  username: string;
  password: string;
  name: string;
  email: string;
  phone: string;
  company_name?: string;
}

export interface OperatorLoginRequest {
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  operator_id: string;
  username: string;
  balance: number;
}

// 运营商信息
export interface Operator {
  operator_id: string;
  username: string;
  full_name: string;
  email: string;
  phone: string;
  company_name?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// 运营点
export interface Site {
  site_id: string;
  operator_id: string;
  site_name: string;
  address: string;
  contact_person: string;
  contact_phone: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// 游戏授权
export interface GameAuthRequest {
  app_id: number;
  player_count: number;
  session_id: string;
  site_id?: string;
}

export interface GameAuthResponse {
  success: boolean;
  session_id: string;
  auth_token: string;
  player_count: number;
  cost_per_player: number;
  expires_at: string;
}

export interface EndSessionRequest {
  app_id: number;
  session_id: string;
  player_count: number;
  site_id?: string;
}

export interface EndSessionResponse {
  success: boolean;
  session_id: string;
  total_cost: number;
  duration_minutes: number;
}

// 余额信息
export interface BalanceInfo {
  balance: number;
  available_balance: number;
  frozen_balance: number;
  currency: string;
  updated_at: string;
}

// 交易记录
export interface Transaction {
  transaction_id: string;
  operator_id: string;
  type: 'recharge' | 'consumption' | 'refund' | 'withdrawal';
  amount: number;
  balance_before: number;
  balance_after: number;
  description: string;
  created_at: string;
  status: 'pending' | 'completed' | 'failed';
}

export interface TransactionListRequest {
  page?: number;
  page_size?: number;
  type?: string;
  start_date?: string;
  end_date?: string;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// 充值
export interface RechargeRequest {
  amount: string;
  payment_method: 'alipay' | 'wechat' | 'bank_transfer';
  return_url?: string;
  notify_url?: string;
}

export interface RechargeOrder {
  order_id: string;
  amount: number;
  status: 'pending' | 'paid' | 'cancelled' | 'expired';
  payment_method: string;
  qr_code?: string;
  payment_url?: string;
  created_at: string;
  expires_at: string;
}

// 退款
export interface RefundRequest {
  reason: string;
  amount?: string;
  transaction_ids?: string[];
}

export interface RefundResponse {
  refund_request_id: string;
  status: 'pending' | 'approved' | 'rejected' | 'completed';
  amount: number;
  created_at: string;
}

// API 响应
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  code?: number;
}

// 错误类型
export interface ErrorDetail {
  code: string;
  message: string;
  field?: string;
}

// 统计数据
export interface ConsumptionStats {
  total_players: number;
  total_duration: number;
  total_cost: number;
  session_count: number;
  avg_session_duration: number;
  cost_per_hour: number;
}

// 游戏统计
export interface GameStats {
  app_id: number;
  app_name: string;
  total_sessions: number;
  total_players: number;
  total_revenue: number;
  avg_session_duration: number;
  revenue_per_session: number;
}