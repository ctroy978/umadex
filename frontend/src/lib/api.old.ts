import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { tokenStorage } from './tokenStorage'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost/api'

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000, // 30 second timeout
  headers: {
    'Content-Type': 'application/json',
  },
})

// Queue to hold requests while refreshing token
let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

// Helper to add request to queue
function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

// Helper to process queued requests after refresh
function onTokenRefreshed(token: string) {
  refreshSubscribers.forEach(cb => cb(token))
  refreshSubscribers = []
}

// Request interceptor
api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    // Skip token for auth endpoints except /auth/me
    if (config.url?.includes('/auth/') && !config.url?.includes('/auth/me') && !config.url?.includes('/auth/sessions')) {
      return config
    }

    // Check if token needs refresh before sending request
    if (tokenStorage.isAccessTokenNearExpiry() && !isRefreshing) {
      isRefreshing = true
      
      try {
        const { authService } = await import('./auth')
        const newToken = await authService.refreshAccessToken()
        
        if (newToken) {
          onTokenRefreshed(newToken)
        } else {
          // Refresh failed, redirect to login
          window.location.href = '/login'
          return Promise.reject(new Error('Token refresh failed'))
        }
      } catch (error) {
        window.location.href = '/login'
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }

    // Add current token to request
    const token = tokenStorage.getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    
    // Skip retry for auth endpoints
    if (originalRequest?.url?.includes('/auth/')) {
      return Promise.reject(error)
    }
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      if (!isRefreshing) {
        isRefreshing = true
        
        try {
          const { authService } = await import('./auth')
          const newToken = await authService.refreshAccessToken()
          
          if (newToken) {
            onTokenRefreshed(newToken)
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            return api(originalRequest)
          }
        } catch (refreshError) {
          // Refresh failed
          tokenStorage.clearTokens()
          window.location.href = '/login'
          return Promise.reject(refreshError)
        } finally {
          isRefreshing = false
        }
      }
      
      // Token is being refreshed, queue this request
      return new Promise((resolve) => {
        subscribeTokenRefresh((token: string) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          resolve(api(originalRequest))
        })
      })
    }
    
    return Promise.reject(error)
  }
)

// Helper function for simpler API requests
export async function apiRequest<T = any>(url: string, options?: {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: string | FormData;
  headers?: Record<string, string>;
}): Promise<T> {
  const method = options?.method || 'GET';
  const config: any = {
    method: method.toLowerCase(),
    headers: options?.headers || {},
  };

  // Handle different body types
  if (options?.body) {
    if (options.body instanceof FormData) {
      config.data = options.body;
    } else {
      config.data = JSON.parse(options.body);
    }
  }

  // For FormData, we need to use a request without the default headers
  if (options?.body instanceof FormData) {
    const response = await api.request({
      url,
      method: config.method,
      data: config.data,
      headers: {
        ...options?.headers || {},
        // Let axios/browser set the Content-Type with boundary
      }
    });
    return response.data;
  }

  const response = await api({
    url,
    ...config,
  });

  return response.data;
}

export { api }
export default api