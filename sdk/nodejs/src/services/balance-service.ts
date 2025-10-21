/**
 * 余额服务
 */

import { HttpClient } from '../http-client';
import {
  BalanceInfo,
  ApiResponse
} from '../types';

export class BalanceService {
  constructor(private http: HttpClient) {}

  /**
   * 获取余额信息
   */
  async getBalance(): Promise<BalanceInfo> {
    try {
      const response = await this.http.get<BalanceInfo>('/v1/balance');

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '获取余额信息失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取详细余额信息（包含冻结余额明细）
   */
  async getDetailedBalance(): Promise<BalanceInfo & { frozen_details: any[] }> {
    try {
      const response = await this.http.get<BalanceInfo & { frozen_details: any[] }>('/v1/balance/detailed');

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '获取详细余额信息失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 冻结余额
   */
  async freezeBalance(amount: number, reason: string): Promise<any> {
    if (amount <= 0) {
      throw new Error('冻结金额必须大于0');
    }

    if (!reason || reason.trim().length === 0) {
      throw new Error('冻结原因不能为空');
    }

    try {
      const response = await this.http.post('/v1/balance/freeze', {
        amount,
        reason: reason.trim()
      });

      if (response.success) {
        return response.data;
      }

      throw new Error(response.message || '冻结余额失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 解冻余额
   */
  async unfreezeBalance(freezeId: string, amount?: number): Promise<any> {
    if (!freezeId || freezeId.trim().length === 0) {
      throw new Error('冻结记录ID不能为空');
    }

    try {
      const requestData: any = { freeze_id: freezeId };
      if (amount && amount > 0) {
        requestData.amount = amount;
      }

      const response = await this.http.post('/v1/balance/unfreeze', requestData);

      if (response.success) {
        return response.data;
      }

      throw new Error(response.message || '解冻余额失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取余额变更记录
   */
  async getBalanceHistory(params?: {
    page?: number;
    page_size?: number;
    start_date?: string;
    end_date?: string;
    type?: string;
  }): Promise<{
    items: any[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }> {
    try {
      const response = await this.http.get('/v1/balance/history', params);

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
   * 验证余额是否充足
   */
  async checkSufficientBalance(requiredAmount: number): Promise<boolean> {
    if (requiredAmount <= 0) {
      return true;
    }

    try {
      const balance = await this.getBalance();
      return balance.available_balance >= requiredAmount;
    } catch (error) {
      return false;
    }
  }

  /**
   * 获取余额预警设置
   */
  async getBalanceAlertSettings(): Promise<{
    low_balance_threshold: number;
    alert_enabled: boolean;
    alert_methods: string[];
  }> {
    try {
      const response = await this.http.get('/v1/balance/alert-settings');

      if (response.success && response.data) {
        return response.data;
      }

      // 返回默认设置
      return {
        low_balance_threshold: 100,
        alert_enabled: false,
        alert_methods: []
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * 更新余额预警设置
   */
  async updateBalanceAlertSettings(settings: {
    low_balance_threshold?: number;
    alert_enabled?: boolean;
    alert_methods?: string[];
  }): Promise<void> {
    try {
      const response = await this.http.put('/v1/balance/alert-settings', settings);

      if (!response.success) {
        throw new Error(response.message || '更新余额预警设置失败');
      }
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取余额使用统计
   */
  async getBalanceStats(params?: {
    start_date?: string;
    end_date?: string;
    granularity?: 'day' | 'week' | 'month';
  }): Promise<{
    total_consumption: number;
    total_recharge: number;
    net_change: number;
    daily_stats: any[];
    trend: 'increasing' | 'decreasing' | 'stable';
  }> {
    try {
      const response = await this.http.get('/v1/balance/stats', params);

      if (response.success && response.data) {
        return response.data;
      }

      return {
        total_consumption: 0,
        total_recharge: 0,
        net_change: 0,
        daily_stats: [],
        trend: 'stable'
      };
    } catch (error) {
      throw error;
    }
  }
}