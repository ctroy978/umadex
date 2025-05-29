import { parseJwt } from './utils'

interface TokenData {
  accessToken: string
  refreshToken: string
  expiresIn: number // seconds
  issuedAt: number // timestamp
}

class TokenStorage {
  private readonly ACCESS_TOKEN_KEY = 'access_token'
  private readonly REFRESH_TOKEN_KEY = 'refresh_token'
  private readonly TOKEN_DATA_KEY = 'token_data'
  
  // Buffer time before token expiry (1 minute)
  private readonly REFRESH_BUFFER_SECONDS = 60

  saveTokens(accessToken: string, refreshToken: string, expiresIn: number) {
    const tokenData: TokenData = {
      accessToken,
      refreshToken,
      expiresIn,
      issuedAt: Date.now()
    }
    
    // Store tokens in localStorage
    localStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken)
    localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken)
    localStorage.setItem(this.TOKEN_DATA_KEY, JSON.stringify(tokenData))
  }
  
  getAccessToken(): string | null {
    return localStorage.getItem(this.ACCESS_TOKEN_KEY)
  }
  
  getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY)
  }
  
  getTokenData(): TokenData | null {
    const data = localStorage.getItem(this.TOKEN_DATA_KEY)
    if (!data) return null
    
    try {
      return JSON.parse(data)
    } catch {
      return null
    }
  }
  
  isAccessTokenExpired(): boolean {
    const tokenData = this.getTokenData()
    if (!tokenData) return true
    
    const expiresAt = tokenData.issuedAt + (tokenData.expiresIn * 1000)
    const now = Date.now()
    
    return now >= expiresAt
  }
  
  isAccessTokenNearExpiry(): boolean {
    const tokenData = this.getTokenData()
    if (!tokenData) return true
    
    const expiresAt = tokenData.issuedAt + (tokenData.expiresIn * 1000)
    const bufferTime = this.REFRESH_BUFFER_SECONDS * 1000
    const now = Date.now()
    
    return now >= (expiresAt - bufferTime)
  }
  
  getTimeUntilExpiry(): number {
    const tokenData = this.getTokenData()
    if (!tokenData) return 0
    
    const expiresAt = tokenData.issuedAt + (tokenData.expiresIn * 1000)
    const now = Date.now()
    const timeLeft = expiresAt - now
    
    return Math.max(0, Math.floor(timeLeft / 1000)) // Return seconds
  }
  
  updateAccessToken(accessToken: string, expiresIn: number) {
    const tokenData = this.getTokenData()
    if (!tokenData) return
    
    tokenData.accessToken = accessToken
    tokenData.expiresIn = expiresIn
    tokenData.issuedAt = Date.now()
    
    localStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken)
    localStorage.setItem(this.TOKEN_DATA_KEY, JSON.stringify(tokenData))
  }
  
  clearTokens() {
    localStorage.removeItem(this.ACCESS_TOKEN_KEY)
    localStorage.removeItem(this.REFRESH_TOKEN_KEY)
    localStorage.removeItem(this.TOKEN_DATA_KEY)
  }
  
  hasTokens(): boolean {
    return !!(this.getAccessToken() && this.getRefreshToken())
  }
}

export const tokenStorage = new TokenStorage()