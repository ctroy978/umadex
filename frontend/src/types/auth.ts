export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  username: string
  role: 'student' | 'teacher'
  is_admin: boolean
  created_at: string
}

export interface OTPRequestData {
  email: string
  first_name?: string
  last_name?: string
}

export interface OTPVerifyData {
  email: string
  otp_code: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}