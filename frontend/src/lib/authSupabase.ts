import { supabase } from './supabase'
import { api } from './api'

export interface LoginData {
  email: string
  first_name?: string
  last_name?: string
  role?: 'student' | 'teacher'
}

export interface VerifyOTPData {
  email: string
  otp: string
}

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  username: string
  role: 'student' | 'teacher'
  is_admin: boolean
  created_at: string
  updated_at: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

class AuthSupabaseService {
  async requestOTP(data: LoginData) {
    // For new users, we need to go through our backend to check whitelist
    const response = await api.post('/auth/request-otp', data)
    return response.data
  }

  async verifyOTP(data: VerifyOTPData): Promise<AuthResponse> {
    // Verify OTP through our backend which will create/update user
    const response = await api.post<AuthResponse>('/auth/verify-otp', data)
    
    // Store tokens in Supabase client
    const { access_token, refresh_token } = response.data
    await supabase.auth.setSession({
      access_token,
      refresh_token,
    })
    
    return response.data
  }

  async refreshAccessToken(): Promise<AuthResponse> {
    // Use Supabase client to refresh
    const { data, error } = await supabase.auth.refreshSession()
    
    if (error || !data.session) {
      throw new Error('Failed to refresh token')
    }
    
    // Get user data from our backend
    const userResponse = await api.get<User>('/auth/me')
    
    return {
      access_token: data.session.access_token,
      refresh_token: data.session.refresh_token,
      token_type: 'bearer',
      user: userResponse.data
    }
  }

  async getCurrentUser(): Promise<User | null> {
    // Check if we have a session
    const { data: { session } } = await supabase.auth.getSession()
    
    if (!session) {
      return null
    }
    
    try {
      // Get user data from our backend
      const response = await api.get<User>('/auth/me')
      return response.data
    } catch (error) {
      // If backend fails, session might be invalid
      await this.logout()
      return null
    }
  }

  async logout() {
    // Sign out from Supabase
    await supabase.auth.signOut()
    
    // Clear any local storage
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
  }

  async revokeAllSessions() {
    // Call backend to revoke all sessions
    await api.delete('/auth/sessions')
    
    // Then logout locally
    await this.logout()
  }

  // Helper to get current session
  async getSession() {
    const { data: { session } } = await supabase.auth.getSession()
    return session
  }

  // Helper to subscribe to auth state changes
  onAuthStateChange(callback: (event: string, session: any) => void) {
    return supabase.auth.onAuthStateChange(callback)
  }
}

export const authSupabase = new AuthSupabaseService()