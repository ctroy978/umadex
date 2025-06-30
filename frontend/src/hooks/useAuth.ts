import { create } from 'zustand'
import { User } from '@/types/auth'
import { authService } from '@/lib/auth'

/**
 * SECURITY ARCHITECTURE: Authentication State Management
 * 
 * This is the central authentication store for the application. All auth-related
 * state should flow through this hook to ensure consistency.
 * 
 * SECURITY PRINCIPLES:
 * 1. Single source of truth for auth state
 * 2. Automatic token validation and refresh
 * 3. Secure logout that clears all user data
 * 4. Loading states prevent unauthorized access during auth checks
 * 
 * USAGE PATTERNS:
 * - Guards: Use isLoading to prevent premature redirects
 * - Components: Use user.role for permission checks
 * - API calls: Token management is handled automatically
 * 
 * When adding new user roles, update the User type in /types/auth.ts
 * and ensure all guards handle the new role appropriately.
 */

interface AuthState {
  user: User | null
  isLoading: boolean
  tokenExpirySeconds: number
  setUser: (user: User | null) => void
  loadUser: () => Promise<void>
  logout: () => Promise<void>
  checkTokenExpiry: () => void
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  isLoading: true,
  tokenExpirySeconds: 0,

  setUser: (user) => set({ user }),

  loadUser: async () => {
    console.log('useAuth.loadUser called');
    set({ isLoading: true })
    try {
      const isAuth = authService.isAuthenticated();
      console.log('Is authenticated:', isAuth);
      
      if (isAuth) {
        console.log('Fetching current user...');
        const user = await authService.getCurrentUser()
        console.log('User loaded:', user);
        set({ user, isLoading: false })
        
        // Start checking token expiry
        get().checkTokenExpiry()
      } else {
        console.log('Not authenticated, setting user to null');
        set({ user: null, isLoading: false })
      }
    } catch (error) {
      console.error('Failed to load user:', error)
      set({ user: null, isLoading: false })
    }
  },

  logout: async () => {
    await authService.logout()
    set({ user: null, tokenExpirySeconds: 0 })
  },
  
  checkTokenExpiry: () => {
    // Update token expiry time every second
    const interval = setInterval(() => {
      const seconds = authService.getTimeUntilExpiry()
      set({ tokenExpirySeconds: seconds })
      
      // Stop checking if logged out or token expired
      if (!authService.isAuthenticated()) {
        clearInterval(interval)
      }
    }, 1000)
    
    // Initial check
    set({ tokenExpirySeconds: authService.getTimeUntilExpiry() })
  }
}))