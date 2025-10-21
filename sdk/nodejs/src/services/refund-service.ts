/**
 * 退款服务
 */

import { HttpClient } from '../http-client';
import {
  RefundRequest,
  RefundResponse,
  ApiResponse
} from '../types';
import { ValidationError } from '../utils';

export class RefundService {
  constructor(private http: HttpClient) {}

  /**
   * 申请退款
   */
  async requestRefund(request: RefundRequest): Promise<RefundResponse> {
    this.validateRefundRequest(request);

    try {
      const response = await this.http.post<RefundResponse>('/v1/refunds', request);

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '申请退款失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取退款申请详情
   */
  async getRefundRequest(refundRequestId: string): Promise<RefundResponse | null> {
    if (!refundRequestId || refundRequestId.trim().length === 0) {
      throw new Error('退款申请ID不能为空');
    }

    try {
      const response = await this.http.get<RefundResponse>(`/v1/refunds/${refundRequestId}`);

      if (response.success && response.data) {
        return response.data;
      }

      return null;
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取退款申请列表
   */
  async getRefundRequests(params?: {
    page?: number;
    page_size?: number;
    status?: 'pending' | 'approved' | 'rejected' | 'completed';
    start_date?: string;
    end_date?: string;
  }): Promise<{
    items: RefundResponse[];
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
      const response = await this.http.get('/v1/refunds', requestParams);

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
   * 取消退款申请
   */
  async cancelRefundRequest(refundRequestId: string, reason?: string): Promise<void> {
    if (!refundRequestId || refundRequestId.trim().length === 0) {
      throw new Error('退款申请ID不能为空');
    }

    try {
      const requestData: any = {};
      if (reason && reason.trim().length > 0) {
        requestData.reason = reason.trim();
      }

      const response = await this.http.post(`/v1/refunds/${refundRequestId}/cancel`, requestData);

      if (!response.success) {
        throw new Error(response.message || '取消退款申请失败');
      }
    } catch (error) {
      throw error;
    }
  }

  /**
   * 更新退款申请
   */
  async updateRefundRequest(refundRequestId: string, updates: {
    reason?: string;
    amount?: string;
    transaction_ids?: string[];
  }): Promise<RefundResponse> {
    if (!refundRequestId || refundRequestId.trim().length === 0) {
      throw new Error('退款申请ID不能为空');
    }

    if (!updates || Object.keys(updates).length === 0) {
      throw new Error('更新内容不能为空');
    }

    try {
      const response = await this.http.put<RefundResponse>(`/v1/refunds/${refundRequestId}`, updates);

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '更新退款申请失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取可退款的交易记录
   */
  async getRefundableTransactions(params?: {
    page?: number;
    page_size?: number;
    start_date?: string;
    end_date?: string;
    min_amount?: number;
  }): Promise<{
    items: Array<{
      transaction_id: string;
      amount: number;
      description: string;
      created_at: string;
      refundable_amount: number;
      refund_status: 'available' | 'partial' | 'none';
    }>;
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
      const response = await this.http.get('/v1/refunds/refundable-transactions', requestParams);

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
   * 获取退款统计
   */
  async getRefundStats(params?: {
    start_date?: string;
    end_date?: string;
    group_by?: 'day' | 'week' | 'month';
  }): Promise<{
    total_amount: number;
    total_count: number;
    success_rate: number;
    average_processing_time: number;
    status_stats: Array<{
      status: string;
      count: number;
      amount: number;
    }>;
    period_stats: Array<{
      period: string;
      amount: number;
      count: number;
    }>;
    trend: 'increasing' | 'decreasing' | 'stable';
  }> {
    try {
      const response = await this.http.get('/v1/refunds/stats', params);

      if (response.success && response.data) {
        return response.data;
      }

      return {
        total_amount: 0,
        total_count: 0,
        success_rate: 0,
        average_processing_time: 0,
        status_stats: [],
        period_stats: [],
        trend: 'stable'
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取退款申请进度
   */
  async getRefundProgress(refundRequestId: string): Promise<{
    refund_request_id: string;
    status: 'pending' | 'processing' | 'approved' | 'rejected' | 'completed' | 'failed';
    current_step: string;
    total_steps: number;
    completed_steps: number;
    estimated_completion_time?: string;
    progress_percentage: number;
    timeline: Array<{
      step: string;
      status: 'pending' | 'completed' | 'failed';
      timestamp?: string;
      note?: string;
    }>;
  }> {
    if (!refundRequestId || refundRequestId.trim().length === 0) {
      throw new Error('退款申请ID不能为空');
    }

    try {
      const response = await this.http.get(`/v1/refunds/${refundRequestId}/progress`);

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '获取退款进度失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 验证退款请求
   */
  private validateRefundRequest(request: RefundRequest): void {
    const errors: string[] = [];

    // 验证退款原因
    if (!request.reason || request.reason.trim().length === 0) {
      errors.push('退款原因不能为空');
    } else if (request.reason.trim().length < 10) {
      errors.push('退款原因至少需要10个字符');
    } else if (request.reason.trim().length > 500) {
      errors.push('退款原因不能超过500个字符');
    }

    // 验证退款金额（可选）
    if (request.amount) {
      const amount = parseFloat(request.amount);
      if (isNaN(amount) || amount <= 0) {
        errors.push('退款金额必须大于0');
      }
      if (amount < 1) {
        errors.push('最小退款金额为1元');
      }
      if (amount > 10000) {
        errors.push('单笔退款金额不能超过10000元');
      }
    }

    // 验证交易ID列表（可选）
    if (request.transaction_ids && Array.isArray(request.transaction_ids)) {
      if (request.transaction_ids.length === 0) {
        errors.push('交易ID列表不能为空');
      } else if (request.transaction_ids.length > 50) {
        errors.push('单次退款最多支持50笔交易');
      }

      // 验证每个交易ID格式
      for (const transactionId of request.transaction_ids) {
        if (!transactionId || typeof transactionId !== 'string' || transactionId.trim().length === 0) {
          errors.push('交易ID格式无效');
          break;
        }
      }
    }

    if (errors.length > 0) {
      throw new ValidationError('退款请求验证失败：' + errors.join(', '));
    }
  }

  /**
   * 获取退款原因模板
   */
  async getRefundReasonTemplates(): Promise<Array<{
    id: string;
    category: string;
    reason: string;
    description: string;
    is_popular: boolean;
  }>> {
    try {
      const response = await this.http.get('/v1/refunds/reason-templates');

      if (response.success && response.data) {
        return response.data;
      }

      return [];
    } catch (error) {
      throw error;
    }
  }

  /**
   * 批量提交退款申请
   */
  async batchRequestRefunds(requests: Array<{
    reason: string;
    amount?: string;
    transaction_ids?: string[];
  }>): Promise<{
    success_count: number;
    failed_count: number;
    results: Array<{
      request: any;
      refund_request_id?: string;
      success: boolean;
      error?: string;
    }>;
  }> {
    if (!requests || requests.length === 0) {
      throw new Error('退款申请列表不能为空');
    }

    if (requests.length > 10) {
      throw new Error('批量提交最多支持10个退款申请');
    }

    try {
      const response = await this.http.post('/v1/refunds/batch', {
        requests
      });

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '批量提交退款申请失败');
    } catch (error) {
      throw error;
    }
  }
}