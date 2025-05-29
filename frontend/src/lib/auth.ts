import api from './api'
import { tokenStorage } from './tokenStorage'
import { OTPRequestData, OTPVerifyData, AuthResponse, User, RefreshTokenResponse } from '@/types/auth'
import Cookies from 'js-cookie'

export const authService = {
  async requestOTP(data: OTPRequestData) {
    const response = await api.post('/v1/auth/request-otp', data)
    return response.data
  },

  async verifyOTP(data: OTPVerifyData): Promise<AuthResponse> {
    const response = await api.post('/v1/auth/verify-otp', data)
    const authData = response.data as AuthResponse
    
    // Clear any old cookie-based tokens
    Cookies.remove('auth_token')
    
    // Store tokens using new token storage
    tokenStorage.saveTokens(
      authData.access_token,
      authData.refresh_token,
      authData.expires_in
    )
    
    return authData
  },

  async refreshAccessToken(): Promise<string | null> {
    const refreshToken = tokenStorage.getRefreshToken()
    if (!refreshToken) return null

    try {
      const response = await api.post('/v1/auth/refresh', {
        refresh_token: refreshToken
      })
      const data = response.data as RefreshTokenResponse
      
      // Update access token
      tokenStorage.updateAccessToken(data.access_token, data.expires_in)
      
      return data.access_token
    } catch (error) {
      // Refresh failed, clear tokens
      tokenStorage.clearTokens()
      return null
    }
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get('/v1/auth/me')
    return response.data
  },

  async logout() {
    const refreshToken = tokenStorage.getRefreshToken()
    
    try {
      // Send refresh token with logout request to revoke it
      await api.post('/v1/auth/logout', {
        refresh_token: refreshToken
      })
    } catch (error) {
      // Continue with logout even if request fails
    }
    
    tokenStorage.clearTokens()
    window.location.href = '/login'
  },

  async revokeAllSessions() {
    await api.delete('/v1/auth/sessions')
    tokenStorage.clearTokens()
    window.location.href = '/login'
  },

  isAuthenticated(): boolean {
    return tokenStorage.hasTokens() && !tokenStorage.isAccessTokenExpired()
  },
  
  isTokenNearExpiry(): boolean {
    return tokenStorage.isAccessTokenNearExpiry()
  },
  
  getTimeUntilExpiry(): number {
    return tokenStorage.getTimeUntilExpiry()
  }
}