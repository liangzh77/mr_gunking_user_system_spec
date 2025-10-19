import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 创建axios实例
const http: AxiosInstance = axios.create({
  baseURL: '/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
http.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 添加JWT token - 根据请求路径选择token
    let token: string | null = null

    if (config.url?.startsWith('/admin')) {
      // 管理员API使用admin token
      token = localStorage.getItem('admin_access_token')
    } else {
      // 其他API使用运营商token
      token = localStorage.getItem('access_token')
    }

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
http.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error: AxiosError<any>) => {
    // 处理HTTP错误
    if (error.response) {
      const { status, data } = error.response

      switch (status) {
        case 401:
          // 未授权，清除token并跳转到登录页
          localStorage.removeItem('access_token')
          localStorage.removeItem('operator_id')
          router.push('/operator/login')
          ElMessage.error(data?.detail?.message || '未授权，请重新登录')
          break

        case 403:
          ElMessage.error(data?.detail?.message || '无权访问此资源')
          break

        case 404:
          ElMessage.error(data?.detail?.message || '请求的资源不存在')
          break

        case 422:
          // 验证错误
          const validationErrors = data?.detail
          if (Array.isArray(validationErrors)) {
            const errorMessages = validationErrors
              .map((err: any) => `${err.loc?.join('.')} : ${err.msg}`)
              .join('; ')
            ElMessage.error(`验证错误: ${errorMessages}`)
          } else if (validationErrors?.message) {
            ElMessage.error(validationErrors.message)
          } else {
            ElMessage.error('请求参数验证失败')
          }
          break

        case 429:
          ElMessage.error('请求过于频繁，请稍后再试')
          break

        case 500:
          ElMessage.error(data?.detail?.message || '服务器内部错误')
          break

        default:
          ElMessage.error(data?.detail?.message || `请求失败 (${status})`)
      }
    } else if (error.request) {
      // 请求已发送但未收到响应
      ElMessage.error('网络错误，请检查网络连接')
    } else {
      // 其他错误
      ElMessage.error(error.message || '请求失败')
    }

    return Promise.reject(error)
  }
)

export default http
