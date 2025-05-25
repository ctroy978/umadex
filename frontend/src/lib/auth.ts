import api from './api'
import Cookies from 'js-cookie'
import { OTPRequestData, OTPVerifyData, AuthResponse, User } from '@/types/auth'

export const authService = {
  async requestOTP(data: OTPRequestData) {
    const response = await api.post('/v1/auth/request-otp', data)
    return response.data
  },

  async verifyOTP(data: OTPVerifyData): Promise<AuthResponse> {
    const response = await api.post('/v1/auth/verify-otp', data)
    const authData = response.data as AuthResponse
    
    // Store token in cookie
    Cookies.set('auth_token', authData.access_token, { 
      expires: 7, // 7 days
      sameSite: 'strict' 
    })
    
    return authData
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get('/v1/auth/me')
    return response.data
  },

  async logout() {
    await api.post('/v1/auth/logout')
    Cookies.remove('auth_token')
    window.location.href = '/login'
  },

  isAuthenticated(): boolean {
    return !!Cookies.get('auth_token')
  }
}