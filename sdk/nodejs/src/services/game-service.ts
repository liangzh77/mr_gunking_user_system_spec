/**
 * 游戏服务
 */

import { HttpClient } from '../http-client';
import {
  GameAuthRequest,
  GameAuthResponse,
  EndSessionRequest,
  EndSessionResponse,
  Site,
  ApiResponse
} from '../types';
import {
  GameSessionError,
  DuplicateRequestError,
  ValidationError
} from '../utils';

export class GameService {
  // 活跃的游戏会话缓存
  private activeSessions: Map<string, GameAuthResponse> = new Map();

  constructor(private http: HttpClient) {}

  /**
   * 游戏授权
   */
  async authorizeGame(request: GameAuthRequest): Promise<GameAuthResponse> {
    // 验证请求数据
    this.validateGameAuthRequest(request);

    // 检查是否为重复请求
    if (this.activeSessions.has(request.session_id)) {
      throw new DuplicateRequestError(`游戏会话 ${request.session_id} 已存在`);
    }

    try {
      const response = await this.http.post<GameAuthResponse>('/v1/games/authorize', request);

      if (response.success && response.data) {
        // 缓存会话信息
        this.activeSessions.set(request.session_id, response.data);
        return response.data;
      }

      throw new GameSessionError(response.message || '游戏授权失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 结束游戏会话
   */
  async endSession(request: EndSessionRequest): Promise<EndSessionResponse> {
    // 验证请求数据
    this.validateEndSessionRequest(request);

    // 检查会话是否存在
    if (!this.activeSessions.has(request.session_id)) {
      throw new GameSessionError(`游戏会话 ${request.session_id} 不存在`);
    }

    try {
      const response = await this.http.post<EndSessionResponse>('/v1/games/end-session', request);

      if (response.success && response.data) {
        // 从缓存中移除会话
        this.activeSessions.delete(request.session_id);
        return response.data;
      }

      throw new GameSessionError(response.message || '结束游戏会话失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取游戏会话信息
   */
  async getSessionInfo(sessionId: string): Promise<GameAuthResponse | null> {
    // 先从缓存中查找
    const cachedSession = this.activeSessions.get(sessionId);
    if (cachedSession) {
      return cachedSession;
    }

    // 从服务器获取
    try {
      const response = await this.http.get<GameAuthResponse>(`/v1/games/sessions/${sessionId}`);

      if (response.success && response.data) {
        return response.data;
      }

      return null;
    } catch (error) {
      return null;
    }
  }

  /**
   * 强制结束游戏会话
   */
  async forceEndSession(sessionId: string): Promise<EndSessionResponse> {
    try {
      const response = await this.http.post<EndSessionResponse>(`/v1/games/sessions/${sessionId}/force-end`);

      if (response.success && response.data) {
        // 从缓存中移除会话
        this.activeSessions.delete(sessionId);
        return response.data;
      }

      throw new GameSessionError(response.message || '强制结束会话失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取活跃的游戏会话列表
   */
  async getActiveSessions(): Promise<GameAuthResponse[]> {
    try {
      const response = await this.http.get<GameAuthResponse[]>('/v1/games/active-sessions');

      if (response.success && response.data) {
        // 更新本地缓存
        response.data.forEach(session => {
          this.activeSessions.set(session.session_id, session);
        });
        return response.data;
      }

      return [];
    } catch (error) {
      throw error;
    }
  }

  /**
   * 创建运营点
   */
  async createSite(siteData: Omit<Site, 'site_id' | 'created_at' | 'updated_at' | 'is_active'>): Promise<Site> {
    this.validateSiteData(siteData);

    try {
      const response = await this.http.post<Site>('/v1/sites', siteData);

      if (response.success && response.data) {
        return response.data;
      }

      throw new GameSessionError(response.message || '创建运营点失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取运营点列表
   */
  async getSites(): Promise<Site[]> {
    try {
      const response = await this.http.get<Site[]>('/v1/sites');

      if (response.success && response.data) {
        return response.data;
      }

      return [];
    } catch (error) {
      throw error;
    }
  }

  /**
   * 更新运营点
   */
  async updateSite(siteId: string, siteData: Partial<Site>): Promise<Site> {
    // 移除不允许更新的字段
    const { site_id, operator_id, created_at, updated_at, is_active, ...updateData } = siteData;

    try {
      const response = await this.http.put<Site>(`/v1/sites/${siteId}`, updateData);

      if (response.success && response.data) {
        return response.data;
      }

      throw new GameSessionError(response.message || '更新运营点失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 删除运营点
   */
  async deleteSite(siteId: string): Promise<void> {
    try {
      const response = await this.http.delete(`/v1/sites/${siteId}`);

      if (!response.success) {
        throw new GameSessionError(response.message || '删除运营点失败');
      }
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取游戏应用列表
   */
  async getGameApps(): Promise<any[]> {
    try {
      const response = await this.http.get<any[]>('/v1/games/apps');

      if (response.success && response.data) {
        return response.data;
      }

      return [];
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取游戏统计信息
   */
  async getGameStats(startDate?: string, endDate?: string): Promise<any> {
    const params: any = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    try {
      const response = await this.http.get<any>('/v1/games/stats', params);

      if (response.success && response.data) {
        return response.data;
      }

      return null;
    } catch (error) {
      throw error;
    }
  }

  /**
   * 验证游戏授权请求
   */
  private validateGameAuthRequest(request: GameAuthRequest): void {
    const errors: string[] = [];

    if (!request.app_id || request.app_id <= 0) {
      errors.push('应用ID必须是正整数');
    }

    if (!request.player_count || request.player_count <= 0 || request.player_count > 100) {
      errors.push('玩家数量必须在1-100之间');
    }

    if (!request.session_id || request.session_id.length < 1 || request.session_id.length > 100) {
      errors.push('会话ID长度应在1-100个字符之间');
    }

    if (request.site_id && (request.site_id.length < 1 || request.site_id.length > 50)) {
      errors.push('运营点ID长度应在1-50个字符之间');
    }

    if (errors.length > 0) {
      throw new ValidationError('游戏授权请求验证失败：' + errors.join(', '));
    }
  }

  /**
   * 验证结束会话请求
   */
  private validateEndSessionRequest(request: EndSessionRequest): void {
    const errors: string[] = [];

    if (!request.app_id || request.app_id <= 0) {
      errors.push('应用ID必须是正整数');
    }

    if (!request.session_id || request.session_id.length < 1 || request.session_id.length > 100) {
      errors.push('会话ID长度应在1-100个字符之间');
    }

    if (!request.player_count || request.player_count <= 0 || request.player_count > 100) {
      errors.push('玩家数量必须在1-100之间');
    }

    if (errors.length > 0) {
      throw new ValidationError('结束会话请求验证失败：' + errors.join(', '));
    }
  }

  /**
   * 验证运营点数据
   */
  private validateSiteData(siteData: any): void {
    const errors: string[] = [];

    if (!siteData.site_name || siteData.site_name.length < 2 || siteData.site_name.length > 100) {
      errors.push('运营点名称长度应在2-100个字符之间');
    }

    if (!siteData.address || siteData.address.length < 5 || siteData.address.length > 200) {
      errors.push('地址长度应在5-200个字符之间');
    }

    if (!siteData.contact_person || siteData.contact_person.length < 2 || siteData.contact_person.length > 50) {
      errors.push('联系人姓名长度应在2-50个字符之间');
    }

    if (!siteData.contact_phone || siteData.contact_phone.length < 11 || siteData.contact_phone.length > 15) {
      errors.push('联系人电话长度应在11-15个字符之间');
    }

    if (errors.length > 0) {
      throw new ValidationError('运营点数据验证失败：' + errors.join(', '));
    }
  }

  /**
   * 清理本地会话缓存
   */
  clearSessionCache(): void {
    this.activeSessions.clear();
  }

  /**
   * 获取本地缓存的活跃会话数量
   */
  getActiveSessionCount(): number {
    return this.activeSessions.size;
  }
}