/**
 * 工具函数
 */

import CryptoJS from 'crypto-js';

/**
 * 延迟函数
 */
export const delay = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

/**
 * 重试函数
 */
export const retry = async <T>(
  fn: () => Promise<T>,
  maxAttempts: number = 3,
  delayMs: number = 1000
): Promise<T> => {
  let lastError: Error;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      if (attempt === maxAttempts) {
        throw lastError;
      }

      // 等待后重试
      if (delayMs > 0) {
        await delay(delayMs * attempt);
      }
    }
  }

  throw lastError!;
};

/**
 * 生成随机字符串
 */
export const generateRandomString = (length: number = 32): string => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';

  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }

  return result;
};

/**
 * 生成UUID
 */
export const generateUUID = (): string => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

/**
 * 时间戳转ISO字符串
 */
export const toISOString = (timestamp?: number): string => {
  return new Date(timestamp || Date.now()).toISOString();
};

/**
 * 解析日期字符串
 */
export const parseDate = (dateString: string): Date => {
  return new Date(dateString);
};

/**
 * 深度合并对象
 */
export const deepMerge = <T extends Record<string, any>>(target: T, source: Partial<T>): T => {
  const result = { ...target };

  for (const key in source) {
    if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
      result[key] = deepMerge(result[key] || {}, source[key] as any);
    } else {
      result[key] = source[key] as any;
    }
  }

  return result;
};

/**
 * 清理URL参数
 */
export const cleanParams = (params: Record<string, any>): Record<string, string> => {
  const cleaned: Record<string, string> = {};

  for (const key in params) {
    const value = params[key];
    if (value !== undefined && value !== null && value !== '') {
      cleaned[key] = String(value);
    }
  }

  return cleaned;
};

/**
 * 构建查询字符串
 */
export const buildQueryString = (params: Record<string, any>): string => {
  const cleanedParams = cleanParams(params);
  const queryString = new URLSearchParams(cleanedParams).toString();
  return queryString ? `?${queryString}` : '';
};

/**
 * 验证邮箱格式
 */
export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * 验证手机号格式（中国大陆）
 */
export const isValidPhone = (phone: string): boolean => {
  const phoneRegex = /^1[3-9]\d{9}$/;
  return phoneRegex.test(phone);
};

/**
 * 验证密码强度
 */
export const validatePassword = (password: string): {
  isValid: boolean;
  errors: string[];
} => {
  const errors: string[] = [];

  if (password.length < 8) {
    errors.push('密码长度不能少于8位');
  }

  if (!/[A-Z]/.test(password)) {
    errors.push('密码必须包含至少一个大写字母');
  }

  if (!/[a-z]/.test(password)) {
    errors.push('密码必须包含至少一个小写字母');
  }

  if (!/\d/.test(password)) {
    errors.push('密码必须包含至少一个数字');
  }

  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push('密码必须包含至少一个特殊字符');
  }

  // 检查常见弱密码模式
  const weakPatterns = [
    /123456/,
    /password/i,
    /qwerty/i,
    /admin/i,
    /(\w)\1{2,}/  // 连续重复字符
  ];

  for (const pattern of weakPatterns) {
    if (pattern.test(password)) {
      errors.push('密码过于简单，请使用更复杂的密码');
      break;
    }
  }

  return {
    isValid: errors.length === 0,
    errors
  };
};

/**
 * 格式化货币金额
 */
export const formatCurrency = (amount: number, currency: string = 'CNY'): string => {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2
  }).format(amount);
};

/**
 * 生成签名（用于API请求）
 */
export const generateSignature = (
  data: Record<string, any>,
  secret: string,
  timestamp?: number
): string => {
  const timestampValue = timestamp || Date.now();

  // 按字母顺序排序参数
  const sortedKeys = Object.keys(data).sort();

  // 构建签名字符串
  const signString = sortedKeys
    .map(key => `${key}=${data[key]}`)
    .join('&') + `&timestamp=${timestampValue}&secret=${secret}`;

  // 生成MD5哈希
  return CryptoJS.MD5(signString).toString();
};

/**
 * 验证响应数据结构
 */
export const validateResponse = <T>(
  response: any,
  expectedKeys: (keyof T)[]
): response is T => {
  if (!response || typeof response !== 'object') {
    return false;
  }

  return expectedKeys.every(key => key in response);
};