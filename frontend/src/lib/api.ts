import axios from 'axios'
import { supabase } from './supabase'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost/api'

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  async (config) => {
    // Skip token for auth endpoints except /auth/me
    if (config.url?.includes('/auth/') && 
        !config.url?.includes('/auth/me') && 
        !config.url?.includes('/auth/sessions')) {
      return config
    }

    // Get the current session from Supabase
    const { data: { session } } = await supabase.auth.getSession()
    
    if (session?.access_token) {
      // Check if token is about to expire (within 5 minutes)
      const tokenPayload = JSON.parse(atob(session.access_token.split('.')[1]))
      const expiryTime = tokenPayload.exp * 1000 // Convert to milliseconds
      const currentTime = Date.now()
      const timeUntilExpiry = expiryTime - currentTime
      
      // If token expires in less than 5 minutes, try to refresh it
      if (timeUntilExpiry < 5 * 60 * 1000) {
        try {
          const { data, error } = await supabase.auth.refreshSession()
          if (!error && data.session) {
            config.headers.Authorization = `Bearer ${data.session.access_token}`
          } else {
            config.headers.Authorization = `Bearer ${session.access_token}`
          }
        } catch (refreshError) {
          // If refresh fails, use existing token
          config.headers.Authorization = `Bearer ${session.access_token}`
        }
      } else {
        config.headers.Authorization = `Bearer ${session.access_token}`
      }
    }
    
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor to handle 401s
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    
    // Skip retry for auth endpoints to prevent loops
    if (originalRequest?.url?.includes('/auth/')) {
      return Promise.reject(error)
    }
    
    // Special handling for test-related endpoints - don't redirect on 401
    if (originalRequest?.url?.includes('/security-incident') || 
        originalRequest?.url?.includes('/save-answer') ||
        originalRequest?.url?.includes('/tests/')) {
      return Promise.reject(error)
    }
    
    // If we get a 401 and haven't already tried to refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      try {
        // Check if we have a valid session first
        const { data: { session } } = await supabase.auth.getSession()
        
        if (!session) {
          // No session, redirect to login
          window.location.href = '/login'
          return Promise.reject(new Error('No session'))
        }
        
        // Try to refresh the session
        const { data, error: refreshError } = await supabase.auth.refreshSession()
        
        if (refreshError || !data.session) {
          // Refresh failed, redirect to login
          await supabase.auth.signOut()
          window.location.href = '/login'
          return Promise.reject(refreshError || new Error('Session refresh failed'))
        }
        
        // Retry the original request with new token
        originalRequest.headers.Authorization = `Bearer ${data.session.access_token}`
        return api(originalRequest)
      } catch (refreshError) {
        // Don't sign out on error - just reject
        return Promise.reject(refreshError)
      }
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