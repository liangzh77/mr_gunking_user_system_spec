import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 创建axios实例
// 统一使用 /api/v1，通过Vite代理转发到后端
// 无论是localhost还是FRP环境，都使用相对路径，避免CORS问题
const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 防止重复跳转的标志
let isRedirecting = false

// 请求拦截器
http.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 添加JWT token - 根据请求路径选择token
    let token: string | null = null

    if (config.url?.startsWith('/admin')) {
      // 管理员API使用admin token
      token = localStorage.getItem('admin_access_token')
    } else if (config.url?.startsWith('/finance')) {
      // 财务API使用finance token
      token = localStorage.getItem('finance_access_token')
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
          const currentPath = router.currentRoute.value.path

          // 判断是否在登录页面
          const isLoginPage = currentPath === '/operator/login' ||
                             currentPath === '/admin/login' ||
                             currentPath === '/finance/login'

          if (isLoginPage) {
            // 在登录页面的401错误 = 用户名或密码错误
            ElMessage.error({
              message: data?.message || data?.error?.message || data?.detail?.message || '用户名或密码错误',
              duration: 3000,
              showClose: true,
            })
          } else {
            // 在其他页面的401错误 = token过期，需要重新登录
            // 防止多个401请求导致重复跳转
            if (isRedirecting) {
              break
            }
            isRedirecting = true

            let loginPath = '/operator/login'
            let messageText = '登录已过期，请重新登录'

            if (currentPath.startsWith('/admin')) {
              localStorage.removeItem('admin_access_token')
              localStorage.removeItem('admin_user')
              loginPath = '/admin/login'
              messageText = '管理员登录已过期，请重新登录'
            } else if (currentPath.startsWith('/finance')) {
              localStorage.removeItem('finance_access_token')
              localStorage.removeItem('finance_user')
              loginPath = '/finance/login'
              messageText = '财务登录已过期，请重新登录'
            } else {
              localStorage.removeItem('access_token')
              localStorage.removeItem('operator_id')
            }

            // 显示友好的错误提示
            ElMessage.warning({
              message: messageText,
              duration: 2000,
              showClose: true,
            })

            // 延迟跳转，让用户看到提示消息
            setTimeout(() => {
              router.push(loginPath).finally(() => {
                // 重置跳转标志，允许下次跳转
                setTimeout(() => {
                  isRedirecting = false
                }, 1000)
              })
            }, 500)
          }
          break

        case 403:
          ElMessage.error(data?.message || data?.error?.message || '无权访问此资源')
          break

        case 404:
          ElMessage.error(data?.message || data?.error?.message || '请求的资源不存在')
          break

        case 422:
          // 验证错误
          const validationErrors = data?.detail || data?.details
          if (Array.isArray(validationErrors)) {
            const errorMessages = validationErrors
              .map((err: any) => `${err.loc?.join('.')} : ${err.msg}`)
              .join('; ')
            ElMessage.error(`验证错误: ${errorMessages}`)
          } else if (data?.message) {
            ElMessage.error(data.message)
          } else {
            ElMessage.error('请求参数验证失败')
          }
          break

        case 429:
          ElMessage.error('请求过于频繁，请稍后再试')
          break

        case 500:
          ElMessage.error(data?.message || data?.error?.message || '服务器内部错误')
          break

        default:
          ElMessage.error(data?.message || data?.error?.message || `请求失败 (${status})`)
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
