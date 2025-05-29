'use client'

import { useAuth } from '@/hooks/useAuth'
import { authService } from '@/lib/auth'

export default function TokenExpiryWarning() {
  const { tokenExpirySeconds } = useAuth()
  
  // Only show in development
  if (process.env.NODE_ENV !== 'development') {
    return null
  }
  
  // Don't show if not authenticated
  if (!authService.isAuthenticated()) {
    return null
  }
  
  // Show warning when less than 5 minutes remaining
  if (tokenExpirySeconds > 300) {
    return null
  }
  
  const minutes = Math.floor(tokenExpirySeconds / 60)
  const seconds = tokenExpirySeconds % 60
  
  return (
    <div className="fixed bottom-4 right-4 bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-2 rounded-lg shadow-lg z-50">
      <div className="flex items-center space-x-2">
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
        <div>
          <p className="font-semibold">Token expires in {minutes}:{seconds.toString().padStart(2, '0')}</p>
          <p className="text-sm">Auto-refresh will occur before expiry</p>
        </div>
      </div>
    </div>
  )
}