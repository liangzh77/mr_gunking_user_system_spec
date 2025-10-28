/**
 * HTTP客户端
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import { ApiError, NetworkError } from './errors';
import { retry, delay } from './utils';
import { ApiResponse } from './types';

export interface HttpClientConfig {
  baseURL: string;
  timeout?: number;
  retryCount?: number;
  retryDelay?: number;
  headers?: Record<string, string>;
}

export class HttpClient {
  private axios: AxiosInstance;
  private retryCount: number;
  private retryDelay: number;

  constructor(config: HttpClientConfig) {
    this.retryCount = config.retryCount || 3;
    this.retryDelay = config.retryDelay || 1000;

    this.axios = axios.create({
      baseURL: config.baseURL,
      timeout: config.timeout || 30000,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': '@mr-gaming/sdk-nodejs/1.0.0',
        ...config.headers
      }
    });

    this.setupInterceptors();
  }

  /**
   * 设置请求和响应拦截器
   */
  private setupInterceptors(): void {
    // 请求拦截器
    this.axios.interceptors.request.use(
      (config) => {
        // 添加请求时间戳
        config.metadata = { startTime: Date.now() };

        console.log(`[HTTP Request] ${config.method?.toUpperCase()} ${config.url}`, {
          params: config.params,
      data: config.data
    });

    return config;
  },
  (error) => {
    console.error('[HTTP Request Error]', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
this.axios.interceptors.response.use(
  (response) => {
    const duration = Date.now() - (response.config.metadata?.startTime || 0);

    console.log(`[HTTP Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, {
      status: response.status,
      duration: `${duration}ms`,
      data: response.data
    });

    return response;
  },
  async (error: AxiosError) => {
    const config = error.config as any;
    const duration = Date.now() - (config?.metadata?.startTime || 0);

    console.error(`[HTTP Error] ${config?.method?.toUpperCase()} ${config?.url}`, {
      status: error.response?.status,
      duration: `${duration}ms`,
      message: error.message,
      data: error.response?.data
    });

    // 如果是网络错误并且设置了重试
    if (this.shouldRetry(error) && (!config._retryCount || config._retryCount < this.retryCount)) {
      config._retryCount = (config._retryCount || 0) + 1;

      console.log(`[HTTP Retry] Attempt ${config._retryCount}/${this.retryCount} for ${config?.method?.toUpperCase()} ${config?.url}`);

      // 指数退避策略
      const retryDelay = this.retryDelay * Math.pow(2, config._retryCount - 1);
      await delay(retryDelay);

      return this.axios(config);
    }

    return Promise.reject(this.handleError(error));
  }
);
}

/**
 * 判断是否应该重试
 */
private shouldRetry(error: AxiosError): boolean {
  // 网络错误
  if (!error.response) {
    return true;
  }

  const status = error.response.status;

  // 可重试的HTTP状态码
  const retryableStatuses = [
    408, // Request Timeout
    429, // Too Many Requests
    500, // Internal Server Error
    502, // Bad Gateway
    503, // Service Unavailable
    504, // Gateway Timeout
    520, // Unknown Error
    521, // Web Server Is Down
    522, // Connection Timed Out
    523, // Origin Is Unreachable
    524  // A Timeout Occurred
  ];

  return retryableStatuses.includes(status);
}

/**
 * 处理错误
 */
private handleError(error: AxiosError): Error {
  if (!error.response) {
    // 网络错误
    return new NetworkError(
      error.message || '网络连接失败',
      {
        code: error.code,
        message: error.message,
        config: error.config
      }
    );
  }

  const response = error.response;
  const data = response.data as any;

  // 构建错误消息
  let message = '请求失败';
  if (data?.message) {
    message = data.message;
  } else if (data?.error) {
    message = data.error;
  } else {
    message = `HTTP ${response.status}: ${response.statusText}`;
  }

  const apiError = new ApiError(
    message,
    response.status,
    data
  );

  // 添加额外的错误信息
  if (data?.code) {
    (apiError as any).errorCode = data.code;
  }

  if (data?.details) {
    (apiError as any).errorDetails = data.details;
  }

  return apiError;
}

/**
 * 设置认证token
 */
setAuthToken(token: string): void {
  this.axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
}

/**
 * 清除认证token
 */
clearAuthToken(): void {
  delete this.axios.defaults.headers.common['Authorization'];
}

/**
 * 设置自定义请求头
 */
setHeader(key: string, value: string): void {
  this.axios.defaults.headers.common[key] = value;
}

/**
 * GET请求
 */
async get<T = any>(
  url: string,
  params?: Record<string, any>,
  config?: AxiosRequestConfig
): Promise<ApiResponse<T>> {
  try {
    const response = await this.axios.get<ApiResponse<T>>(url, {
      ...config,
      params
    });

    return response.data;
  } catch (error) {
    throw error;
  }
}

/**
 * POST请求
 */
async post<T = any>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig
): Promise<ApiResponse<T>> {
  try {
    const response = await this.axios.post<ApiResponse<T>>(url, data, config);
    return response.data;
  } catch (error) {
    throw error;
  }
}

/**
 * PUT请求
 */
async put<T = any>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig
): Promise<ApiResponse<T>> {
  try {
    const response = await this.axios.put<ApiResponse<T>>(url, data, config);
    return response.data;
  } catch (error) {
    throw error;
  }
}

/**
 * PATCH请求
 */
async patch<T = any>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig
): Promise<ApiResponse<T>> {
  try {
    const response = await this.axios.patch<ApiResponse<T>>(url, data, config);
    return response.data;
  } catch (error) {
    throw error;
  }
}

/**
 * DELETE请求
 */
async delete<T = any>(
  url: string,
  config?: AxiosRequestConfig
): Promise<ApiResponse<T>> {
  try {
    const response = await this.axios.delete<ApiResponse<T>>(url, config);
    return response.data;
  } catch (error) {
    throw error;
  }
}

/**
 * 文件上传
 */
async upload<T = any>(
  url: string,
  file: Buffer | Blob,
  fileName: string,
  additionalData?: Record<string, any>,
  config?: AxiosRequestConfig
): Promise<ApiResponse<T>> {
  const formData = new FormData();

  // 添加文件
  if (file instanceof Buffer) {
    formData.append('file', new Blob([file]), fileName);
  } else {
    formData.append('file', file, fileName);
  }

  // 添加额外数据
  if (additionalData) {
    for (const [key, value] of Object.entries(additionalData)) {
      formData.append(key, String(value));
    }
  }

  try {
    const response = await this.axios.post<ApiResponse<T>>(url, formData, {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...config?.headers
      }
    });

    return response.data;
  } catch (error) {
    throw error;
  }
}
}