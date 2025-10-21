/**
 * 统计服务
 */

import { HttpClient } from '../http-client';
import {
  ConsumptionStats,
  GameStats,
  ApiResponse
} from '../types';

export class StatisticsService {
  constructor(private http: HttpClient) {}

  /**
   * 获取消费统计
   */
  async getConsumptionStats(params?: {
    start_date?: string;
    end_date?: string;
    site_id?: string;
    app_id?: number;
    group_by?: 'hour' | 'day' | 'week' | 'month';
  }): Promise<{
    total_stats: ConsumptionStats;
    time_series: Array<{
      period: string;
      players: number;
      duration: number;
      cost: number;
      sessions: number;
    }>;
    site_stats: Array<{
      site_id: string;
      site_name: string;
      total_players: number;
      total_cost: number;
      session_count: number;
    }>;
    app_stats: GameStats[];
  }> {
    try {
      const response = await this.http.get('/v1/statistics/consumption', params);

      if (response.success && response.data) {
        return response.data;
      }

      return {
        total_stats: {
          total_players: 0,
          total_duration: 0,
          total_cost: 0,
          session_count: 0,
          avg_session_duration: 0,
          cost_per_hour: 0
        },
        time_series: [],
        site_stats: [],
        app_stats: []
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取游戏统计
   */
  async getGameStats(params?: {
    start_date?: string;
    end_date?: string;
    app_id?: number;
    site_id?: string;
    sort_by?: 'revenue' | 'sessions' | 'players' | 'duration';
    sort_order?: 'asc' | 'desc';
    limit?: number;
  }): Promise<{
    summary: {
      total_apps: number;
      total_sessions: number;
      total_players: number;
      total_revenue: number;
    };
    apps: GameStats[];
    trends: Array<{
      app_id: number;
      app_name: string;
      trend: 'up' | 'down' | 'stable';
      change_percentage: number;
    }>;
  }> {
    try {
      const response = await this.http.get('/v1/statistics/games', params);

      if (response.success && response.data) {
        return response.data;
      }

      return {
        summary: {
          total_apps: 0,
          total_sessions: 0,
          total_players: 0,
          total_revenue: 0
        },
        apps: [],
        trends: []
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取运营点统计
   */
  async getSiteStats(params?: {
    start_date?: string;
    end_date?: string;
    site_id?: string;
    group_by?: 'day' | 'week' | 'month';
  }): Promise<{
    total_stats: {
      total_sites: number;
      active_sites: number;
      total_sessions: number;
      total_revenue: number;
      avg_revenue_per_site: number;
    };
    site_rankings: Array<{
      site_id: string;
      site_name: string;
      total_sessions: number;
      total_players: number;
      total_revenue: number;
      avg_session_duration: number;
      rank: number;
    }>;
    time_series: Array<{
      period: string;
      active_sites: number;
      total_sessions: number;
      total_revenue: number;
    }>;
  }> {
    try {
      const response = await this.http.get('/v1/statistics/sites', params);

      if (response.success && response.data) {
        return response.data;
      }

      return {
        total_stats: {
          total_sites: 0,
          active_sites: 0,
          total_sessions: 0,
          total_revenue: 0,
          avg_revenue_per_site: 0
        },
        site_rankings: [],
        time_series: []
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取用户行为统计
   */
  async getUserBehaviorStats(params?: {
    start_date?: string;
    end_date?: string;
    site_id?: string;
    app_id?: number;
    segment?: 'new' | 'returning' | 'vip' | 'all';
  }): Promise<{
    user_segments: Array<{
      segment: string;
      user_count: number;
      session_count: number;
      total_revenue: number;
      avg_revenue_per_user: number;
      retention_rate: number;
    }>;
    usage_patterns: Array<{
      pattern: string;
      count: number;
      percentage: number;
    }>;
    peak_hours: Array<{
      hour: number;
      session_count: number;
      player_count: number;
      revenue: number;
    }>;
  }> {
    try {
      const response = await this.http.get('/v1/statistics/user-behavior', params);

      if (response.success && response.data) {
        return response.data;
      }

      return {
        user_segments: [],
        usage_patterns: [],
        peak_hours: []
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取财务报表数据
   */
  async getFinancialReports(params?: {
    start_date?: string;
    end_date?: string;
    report_type?: 'daily' | 'weekly' | 'monthly' | 'custom';
    format?: 'json' | 'excel' | 'pdf';
  }): Promise<{
    revenue_report: {
      total_revenue: number;
      gross_revenue: number;
      net_revenue: number;
      growth_rate: number;
      breakdown: Array<{
        category: string;
        amount: number;
        percentage: number;
      }>;
    };
    cost_report: {
      total_cost: number;
      fixed_cost: number;
      variable_cost: number;
      breakdown: Array<{
        category: string;
        amount: number;
        percentage: number;
      }>;
    };
    profit_report: {
      gross_profit: number;
      net_profit: number;
      profit_margin: number;
      roi: number;
    };
    cash_flow: Array<{
      date: string;
      inflow: number;
      outflow: number;
      net_flow: number;
      balance: number;
    }>;
  }> {
    try {
      const response = await this.http.get('/v1/statistics/financial-reports', params);

      if (response.success && response.data) {
        return response.data;
      }

      return {
        revenue_report: {
          total_revenue: 0,
          gross_revenue: 0,
          net_revenue: 0,
          growth_rate: 0,
          breakdown: []
        },
        cost_report: {
          total_cost: 0,
          fixed_cost: 0,
          variable_cost: 0,
          breakdown: []
        },
        profit_report: {
          gross_profit: 0,
          net_profit: 0,
          profit_margin: 0,
          roi: 0
        },
        cash_flow: []
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取实时统计数据
   */
  async getRealTimeStats(): Promise<{
    current_sessions: number;
    active_players: number;
    current_revenue: number;
    top_apps: Array<{
      app_id: number;
      app_name: string;
      active_sessions: number;
      active_players: number;
    }>;
    top_sites: Array<{
      site_id: string;
      site_name: string;
      active_sessions: number;
      active_players: number;
    }>;
    hourly_stats: Array<{
      hour: number;
      sessions: number;
      players: number;
      revenue: number;
    }>;
  }> {
    try {
      const response = await this.http.get('/v1/statistics/realtime');

      if (response.success && response.data) {
        return response.data;
      }

      return {
        current_sessions: 0,
        active_players: 0,
        current_revenue: 0,
        top_apps: [],
        top_sites: [],
        hourly_stats: []
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取预测数据
   */
  async getForecastData(params?: {
    metric: 'revenue' | 'sessions' | 'players';
    period: 'week' | 'month' | 'quarter';
    forecast_days?: number;
  }): Promise<{
    forecast: Array<{
      date: string;
      predicted_value: number;
      confidence_interval: {
        lower: number;
        upper: number;
      };
    }>;
    accuracy: {
      mape: number; // Mean Absolute Percentage Error
      rmse: number; // Root Mean Square Error
      r2: number;   // R-squared
    };
    trends: {
      direction: 'increasing' | 'decreasing' | 'stable';
      strength: number; // 0-1
    };
  }> {
    try {
      const response = await this.http.get('/v1/statistics/forecast', params);

      if (response.success && response.data) {
        return response.data;
      }

      return {
        forecast: [],
        accuracy: {
          mape: 0,
          rmse: 0,
          r2: 0
        },
        trends: {
          direction: 'stable',
          strength: 0
        }
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * 导出统计数据
   */
  async exportStats(params: {
    report_type: 'consumption' | 'games' | 'sites' | 'financial';
    start_date?: string;
    end_date?: string;
    format?: 'csv' | 'excel' | 'pdf';
    filters?: Record<string, any>;
  }): Promise<{
    file_id: string;
    download_url: string;
    expires_at: string;
    file_size: number;
  }> {
    try {
      const response = await this.http.post('/v1/statistics/export', params);

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '导出统计数据失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取自定义报表
   */
  async getCustomReport(config: {
    metrics: string[];
    dimensions: string[];
    filters?: Record<string, any>;
    start_date?: string;
    end_date?: string;
    sort?: Array<{
      field: string;
      order: 'asc' | 'desc';
    }>;
  }): Promise<{
    columns: Array<{
      name: string;
      type: string;
      label: string;
    }>;
    rows: Array<Record<string, any>>;
    total_rows: number;
    page: number;
    page_size: number;
  }> {
    try {
      const response = await this.http.post('/v1/statistics/custom-report', config);

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '获取自定义报表失败');
    } catch (error) {
      throw error;
    }
  }
}