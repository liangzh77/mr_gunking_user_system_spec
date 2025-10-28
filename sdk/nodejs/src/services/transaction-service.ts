/**
 * 交易服务
 */

import { HttpClient } from '../http-client';
import {
  Transaction,
  TransactionListRequest,
  TransactionListResponse,
  ApiResponse
} from '../types';

export class TransactionService {
  constructor(private http: HttpClient) {}

  /**
   * 获取交易记录列表
   */
  async getTransactions(params: TransactionListRequest = {}): Promise<TransactionListResponse> {
    // 设置默认值
    const requestParams = {
      page: 1,
      page_size: 20,
      ...params
    };

    try {
      const response = await this.http.get<TransactionListResponse>('/v1/transactions', requestParams);

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
   * 获取交易详情
   */
  async getTransaction(transactionId: string): Promise<Transaction | null> {
    if (!transactionId || transactionId.trim().length === 0) {
      throw new Error('交易ID不能为空');
    }

    try {
      const response = await this.http.get<Transaction>(`/v1/transactions/${transactionId}`);

      if (response.success && response.data) {
        return response.data;
      }

      return null;
    } catch (error) {
      throw error;
    }
  }

  /**
   * 导出交易记录
   */
  async exportTransactions(params: TransactionListRequest & {
    format?: 'csv' | 'excel' | 'pdf';
  }): Promise<{
    download_url: string;
    file_id: string;
    expires_at: string;
  }> {
    const requestParams = {
      format: 'csv',
      ...params
    };

    try {
      const response = await this.http.post('/v1/transactions/export', requestParams);

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '导出交易记录失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取交易统计信息
   */
  async getTransactionStats(params?: {
    start_date?: string;
    end_date?: string;
    group_by?: 'day' | 'week' | 'month';
    type?: string;
  }): Promise<{
    total_amount: number;
    total_count: number;
    type_stats: Array<{
      type: string;
      amount: number;
      count: number;
    }>;
    period_stats: Array<{
      period: string;
      amount: number;
      count: number;
    }>;
    trend: 'increasing' | 'decreasing' | 'stable';
  }> {
    try {
      const response = await this.http.get('/v1/transactions/stats', params);

      if (response.success && response.data) {
        return response.data;
      }

      return {
        total_amount: 0,
        total_count: 0,
        type_stats: [],
        period_stats: [],
        trend: 'stable'
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * 搜索交易记录
   */
  async searchTransactions(query: {
    keyword?: string;
    amount_min?: number;
    amount_max?: number;
    date_from?: string;
    date_to?: string;
    type?: string;
    status?: string;
  }): Promise<TransactionListResponse> {
    try {
      const response = await this.http.post<TransactionListResponse>('/v1/transactions/search', query);

      if (response.success && response.data) {
        return response.data;
      }

      return {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取交易类型列表
   */
  async getTransactionTypes(): Promise<Array<{
    type: string;
    name: string;
    description: string;
    is_active: boolean;
  }>> {
    try {
      const response = await this.http.get('/v1/transactions/types');

      if (response.success && response.data) {
        return response.data;
      }

      return [];
    } catch (error) {
      throw error;
    }
  }

  /**
   * 重新计算交易统计
   */
  async recalculateTransactionStats(params?: {
    start_date?: string;
    end_date?: string;
    operator_id?: string;
  }): Promise<{
    task_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    estimated_time: number;
  }> {
    try {
      const response = await this.http.post('/v1/transactions/recalculate-stats', params);

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '重新计算统计失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取交易记录审核状态
   */
  async getTransactionReviewStatus(transactionId: string): Promise<{
    transaction_id: string;
    status: 'pending' | 'approved' | 'rejected';
    reviewer_id?: string;
    reviewer_name?: string;
    review_note?: string;
    reviewed_at?: string;
  }> {
    if (!transactionId || transactionId.trim().length === 0) {
      throw new Error('交易ID不能为空');
    }

    try {
      const response = await this.http.get(`/v1/transactions/${transactionId}/review-status`);

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '获取审核状态失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 批量标记交易记录
   */
  async batchMarkTransactions(transactionIds: string[], tags: string[]): Promise<{
    success_count: number;
    failed_count: number;
    errors: Array<{
      transaction_id: string;
      error: string;
    }>;
  }> {
    if (!transactionIds || transactionIds.length === 0) {
      throw new Error('交易ID列表不能为空');
    }

    if (!tags || tags.length === 0) {
      throw new Error('标签列表不能为空');
    }

    try {
      const response = await this.http.post('/v1/transactions/batch-mark', {
        transaction_ids: transactionIds,
        tags
      });

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '批量标记失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取交易记录标签
   */
  async getTransactionTags(): Promise<Array<{
    tag: string;
    name: string;
    color: string;
    count: number;
  }>> {
    try {
      const response = await this.http.get('/v1/transactions/tags');

      if (response.success && response.data) {
        return response.data;
      }

      return [];
    } catch (error) {
      throw error;
    }
  }
}