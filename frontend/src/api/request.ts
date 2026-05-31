import axios from 'axios'
import type { InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

/**
 * Axios instance — relies on Vite proxy ('/api' → backend).
 * Token is read on every request from localStorage so the
 * pinia store and direct logout both stay in sync.
 */
const request = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request — attach Bearer token
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Response — unwrap data, normalize errors, hard-redirect on 401
request.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      const detail = (data && (data.detail || data.message)) || ''
      switch (status) {
        case 401:
          ElMessage.error('登录已过期，请重新登录')
          localStorage.removeItem('token')
          if (location.pathname !== '/login') {
            location.href = '/login'
          }
          break
        case 403:
          ElMessage.error(detail || '没有权限访问该资源')
          break
        case 404:
          ElMessage.error(detail || '请求资源不存在')
          break
        case 422:
          ElMessage.error(detail || '请求参数有误')
          break
        case 500:
          ElMessage.error(detail || '服务器内部错误')
          break
        default:
          ElMessage.error(detail || `请求失败 (${status})`)
      }
    } else {
      ElMessage.error('网络连接失败，请检查后端服务')
    }
    return Promise.reject(error)
  },
)

export default request
