/**
 * 运营商认证服务
 */

import { HttpClient } from '../http-client';
import {
  OperatorRegisterRequest,
  OperatorLoginRequest,
  AuthResponse,
  Operator,
  ApiResponse
} from '../types';
import {
  AuthError,
  ValidationError,
  validateEmail,
  isValidPhone,
  validatePassword
} from '../utils';

export class OperatorAuth {
  constructor(private http: HttpClient) {}

  /**
   * 运营商注册
   */
  async register(data: OperatorRegisterRequest): Promise<AuthResponse> {
    // 验证输入数据
    this.validateRegisterData(data);

    try {
      const response = await this.http.post<AuthResponse>('/v1/auth/operators/register', data);

      if (response.success && response.data) {
        // 自动设置认证token
        this.http.setAuthToken(response.data.access_token);
        return response.data;
      }

      throw new AuthError(response.message || '注册失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 运营商登录
   */
  async login(username: string, password: string): Promise<AuthResponse> {
    // 验证输入
    if (!username || !password) {
      throw new ValidationError('用户名和密码不能为空');
    }

    try {
      const response = await this.http.post<AuthResponse>('/v1/auth/operators/login', {
        username,
        password
      });

      if (response.success && response.data) {
        // 自动设置认证token
        this.http.setAuthToken(response.data.access_token);
        return response.data;
      }

      throw new AuthError(response.message || '登录失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 运营商登出
   */
  async logout(): Promise<void> {
    try {
      await this.http.post('/v1/auth/operators/logout');
      this.http.clearAuthToken();
    } catch (error) {
      // 即使登出失败，也清除本地token
      this.http.clearAuthToken();
      throw error;
    }
  }

  /**
   * 刷新token
   */
  async refreshToken(): Promise<AuthResponse> {
    try {
      const response = await this.http.post<AuthResponse>('/v1/auth/operators/refresh');

      if (response.success && response.data) {
        this.http.setAuthToken(response.data.access_token);
        return response.data;
      }

      throw new AuthError(response.message || '刷新token失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 修改密码
   */
  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    // 验证新密码
    const passwordValidation = validatePassword(newPassword);
    if (!passwordValidation.isValid) {
      throw new ValidationError('新密码不符合安全要求：' + passwordValidation.errors.join(', '));
    }

    try {
      const response = await this.http.post('/v1/auth/operators/change-password', {
        old_password: oldPassword,
        new_password: newPassword
      });

      if (!response.success) {
        throw new AuthError(response.message || '修改密码失败');
      }
    } catch (error) {
      throw error;
    }
  }

  /**
   * 获取当前运营商信息
   */
  async getCurrentOperator(): Promise<Operator> {
    try {
      const response = await this.http.get<Operator>('/v1/auth/operators/me');

      if (response.success && response.data) {
        return response.data;
      }

      throw new AuthError(response.message || '获取运营商信息失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 更新运营商信息
   */
  async updateOperator(data: Partial<Operator>): Promise<Operator> {
    // 移除不允许更新的字段
    const { operator_id, username, created_at, updated_at, is_active, ...updateData } = data;

    // 验证邮箱和手机号格式
    if (updateData.email && !validateEmail(updateData.email)) {
      throw new ValidationError('邮箱格式不正确');
    }

    if (updateData.phone && !isValidPhone(updateData.phone)) {
      throw new ValidationError('手机号格式不正确');
    }

    try {
      const response = await this.http.put<Operator>('/v1/auth/operators/me', updateData);

      if (response.success && response.data) {
        return response.data;
      }

      throw new AuthError(response.message || '更新运营商信息失败');
    } catch (error) {
      throw error;
    }
  }

  /**
   * 验证注册数据
   */
  private validateRegisterData(data: OperatorRegisterRequest): void {
    const errors: string[] = [];

    // 用户名验证
    if (!data.username || data.username.length < 3 || data.username.length > 50) {
      errors.push('用户名长度应在3-50个字符之间');
    }

    if (!/^[a-zA-Z0-9_]+$/.test(data.username)) {
      errors.push('用户名只能包含字母、数字和下划线');
    }

    // 密码验证
    const passwordValidation = validatePassword(data.password);
    if (!passwordValidation.isValid) {
      errors.push(...passwordValidation.errors);
    }

    // 姓名验证
    if (!data.name || data.name.length < 2 || data.name.length > 100) {
      errors.push('姓名长度应在2-100个字符之间');
    }

    // 邮箱验证
    if (!validateEmail(data.email)) {
      errors.push('邮箱格式不正确');
    }

    // 手机号验证
    if (!isValidPhone(data.phone)) {
      errors.push('手机号格式不正确');
    }

    // 公司名称验证（可选）
    if (data.company_name && data.company_name.length > 200) {
      errors.push('公司名称长度不能超过200个字符');
    }

    if (errors.length > 0) {
      throw new ValidationError('数据验证失败：' + errors.join(', '));
    }
  }

  /**
   * 验证token是否有效
   */
  async validateToken(): Promise<boolean> {
    try {
      await this.getCurrentOperator();
      return true;
    } catch (error) {
      return false;
    }
  }
}