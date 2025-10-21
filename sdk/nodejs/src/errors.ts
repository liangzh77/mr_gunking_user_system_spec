/**
 * SDK 错误类定义
 */

// 基础错误类
export class MRSdkError extends Error {
  public readonly code: string;
  public readonly details?: any;

  constructor(message: string, code: string, details?: any) {
    super(message);
    this.name = 'MRSdkError';
    this.code = code;
    this.details = details;
  }
}

// 认证错误
export class AuthError extends MRSdkError {
  constructor(message: string = '认证失败', details?: any) {
    super(message, 'AUTH_ERROR', details);
    this.name = 'AuthError';
  }
}

// API 错误
export class ApiError extends MRSdkError {
  public readonly statusCode?: number;
  public readonly response?: any;

  constructor(message: string, statusCode?: number, response?: any) {
    super(message, 'API_ERROR', response);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.response = response;
  }
}

// 验证错误
export class ValidationError extends MRSdkError {
  constructor(message: string = '数据验证失败', details?: any) {
    super(message, 'VALIDATION_ERROR', details);
    this.name = 'ValidationError';
  }
}

// 网络错误
export class NetworkError extends MRSdkError {
  constructor(message: string = '网络连接失败', details?: any) {
    super(message, 'NETWORK_ERROR', details);
    this.name = 'NetworkError';
  }
}

// 权限错误
export class PermissionError extends MRSdkError {
  constructor(message: string = '权限不足', details?: any) {
    super(message, 'PERMISSION_ERROR', details);
    this.name = 'PermissionError';
  }
}

// 业务逻辑错误
export class BusinessError extends MRSdkError {
  constructor(message: string, code: string, details?: any) {
    super(message, code, details);
    this.name = 'BusinessError';
  }
}

// 余额不足错误
export class InsufficientBalanceError extends BusinessError {
  constructor(message: string = '余额不足', details?: any) {
    super(message, 'INSUFFICIENT_BALANCE', details);
    this.name = 'InsufficientBalanceError';
  }
}

// 游戏会话错误
export class GameSessionError extends BusinessError {
  constructor(message: string, details?: any) {
    super(message, 'GAME_SESSION_ERROR', details);
    this.name = 'GameSessionError';
  }
}

// 重复请求错误
export class DuplicateRequestError extends BusinessError {
  constructor(message: string = '重复的请求', details?: any) {
    super(message, 'DUPLICATE_REQUEST', details);
    this.name = 'DuplicateRequestError';
  }
}