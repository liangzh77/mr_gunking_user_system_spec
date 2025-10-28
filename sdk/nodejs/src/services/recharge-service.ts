/**
 * 充值服务
 */

import { HttpClient } from '../http-client';
import {
  RechargeRequest,
  RechargeOrder,
  ApiResponse
} from '../types';
import { ValidationError } from '../utils';

export class RechargeService {
  constructor(private http: HttpClient) {}

  /**
   * 创建充值订单
   */
  async createRechargeOrder(request: RechargeRequest): Promise<RechargeOrder> {
    this.validateRechargeRequest(request);

    try {
      const response = await this.http.post<RechargeOrder>('/v1/recharge/orders', request);

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '创建充值订单失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取充值订单详情
   */
  async getRechargeOrder(orderId: string): Promise<RechargeOrder | null> {
    if (!orderId || orderId.trim().length === 0) {
      throw new Error('订单ID不能为空');
    }

    try {
      const response = await this.http.get<RechargeOrder>(`/v1/recharge/orders/${orderId}`);

      if (response.success && response.data) {
        return response.data;
      }

      return null;
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取充值订单列表
   */
  async getRechargeOrders(params?: {
    page?: number;
    page_size?: number;
    status?: 'pending' | 'paid' | 'cancelled' | 'expired';
    start_date?: string;
    end_date?: string;
    payment_method?: string;
  }): Promise<{
    items: RechargeOrder[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }> {
    const requestParams = {
      page: 1,
      page_size: 20,
      ...params
    };

    try {
      const response = await this.http.get('/v1/recharge/orders', requestParams);

      if (response.success && response.data) {
        return response.data;
      }

      return {
        items: [],
        total: 0,
        page: requestParams.page || 1,
        page_size: requestParams.page_size || 20,
        total_pages: 0
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * 取消充值订单
   */
  async cancelRechargeOrder(orderId: string, reason?: string): Promise<void> {
    if (!orderId || orderId.trim().length === 0) {
      throw new Error('订单ID不能为空');
    }

    try {
      const requestData: any = {};
      if (reason && reason.trim().length > 0) {
        requestData.reason = reason.trim();
      }

      const response = await this.http.post(`/v1/recharge/orders/${orderId}/cancel`, requestData);

      if (!response.success) {
        throw new Error(response.message || '取消充值订单失败');
      }
    } catch (error) {
      throw error;
    }
  }

  /**
   * 重新发起支付
   */
  async retryPayment(orderId: string): Promise<{
    payment_url?: string;
    qr_code?: string;
    expires_at: string;
  }> {
    if (!orderId || orderId.trim().length === 0) {
      throw new Error('订单ID不能为空');
    }

    try {
      const response = await this.http.post(`/v1/recharge/orders/${orderId}/retry`);

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '重新发起支付失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取支付方式列表
   */
  async getPaymentMethods(): Promise<Array<{
    method: string;
    name: string;
    icon: string;
    is_active: boolean;
    min_amount: number;
    max_amount: number;
    fee_rate: number;
  }>> {
    try {
      const response = await this.http.get('/v1/recharge/payment-methods');

      if (response.success && response.data) {
        return response.data;
      }

      return [];
    } catch (error) {
      throw error;
    }
  }

  /**
   * 模拟支付回调（仅用于测试）
   */
  async simulatePaymentCallback(orderId: string, status: 'success' | 'failed'): Promise<void> {
    if (!orderId || orderId.trim().length === 0) {
      throw new Error('订单ID不能为空');
    }

    if (process.env.NODE_ENV === 'production') {
      throw new Error('生产环境不支持模拟支付');
    }

    try {
      const response = await this.http.post('/v1/recharge/callback', {
        order_id: orderId,
        status,
        trade_no: `TEST_${Date.now()}`,
        amount: 0 // 将在服务端获取实际金额
      });

      if (!response.success) {
        throw new Error(response.message || '模拟支付回调失败');
      }
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取充值统计
   */
  async getRechargeStats(params?: {
    start_date?: string;
    end_date?: string;
    group_by?: 'day' | 'week' | 'month';
    payment_method?: string;
  }): Promise<{
    total_amount: number;
    total_count: number;
    success_rate: number;
    method_stats: Array<{
      method: string;
      amount: number;
      count: number;
      success_rate: number;
    }>;
    period_stats: Array<{
      period: string;
      amount: number;
      count: number;
    }>;
    trend: 'increasing' | 'decreasing' | 'stable';
  }> {
    try {
      const response = await this.http.get('/v1/recharge/stats', params);

      if (response.success && response.data) {
        return response.data;
      }

      return {
        total_amount: 0,
        total_count: 0,
        success_rate: 0,
        method_stats: [],
        period_stats: [],
        trend: 'stable'
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * 验证充值请求
   */
  private validateRechargeRequest(request: RechargeRequest): void {
    const errors: string[] = [];

    // 验证金额
    if (!request.amount) {
      errors.push('充值金额不能为空');
    } else {
      const amount = parseFloat(request.amount);
      if (isNaN(amount) || amount <= 0) {
        errors.push('充值金额必须大于0');
      }
      if (amount < 1) {
        errors.push('最小充值金额为1元');
      }
      if (amount > 50000) {
        errors.push('单笔充值金额不能超过50000元');
      }
    }

    // 验证支付方式
    const validMethods = ['alipay', 'wechat', 'bank_transfer'];
    if (!request.payment_method || !validMethods.includes(request.payment_method)) {
      errors.push('支付方式无效，支持：' + validMethods.join('、'));
    }

    // 验证回调URL（可选）
    if (request.return_url && request.return_url.length > 500) {
      errors.push('返回URL长度不能超过500个字符');
    }

    if (request.notify_url && request.notify_url.length > 500) {
      errors.push('通知URL长度不能超过500个字符');
    }

    if (errors.length > 0) {
      throw new ValidationError('充值请求验证失败：' + errors.join(', '));
    }
  }

  /**
   * 获取充值优惠活动
   */
  async getRechargePromotions(): Promise<Array<{
    id: string;
    title: string;
    description: string;
    min_amount: number;
    bonus_amount: number;
    bonus_rate: number;
    start_time: string;
    end_time: string;
    is_active: boolean;
  }>> {
    try {
      const response = await this.http.get('/v1/recharge/promotions');

      if (response.success && response.data) {
        return response.data;
      }

      return [];
    } catch (error) {
      throw error;
    }
  }

  /**
   * 应用充值优惠
   */
  async applyRechargePromotion(orderId: string, promotionId: string): Promise<{
    bonus_amount: number;
    final_amount: number;
  }> {
    if (!orderId || orderId.trim().length === 0) {
      throw new Error('订单ID不能为空');
    }

    if (!promotionId || promotionId.trim().length === 0) {
      throw new Error('优惠活动ID不能为空');
    }

    try {
      const response = await this.http.post(`/v1/recharge/orders/${orderId}/apply-promotion`, {
        promotion_id: promotionId
      });

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '应用优惠失败');
    } catch (error) {
      throw error;
    }
  }
}