import { create } from 'zustand'
import { authSupabase, User } from '@/lib/authSupabase'
import { supabase } from '@/lib/supabase'

interface AuthState {
  user: User | null
  isLoading: boolean
  setUser: (user: User | null) => void
  loadUser: () => Promise<void>
  logout: () => Promise<void>
}

export const useAuthSupabase = create<AuthState>((set) => ({
  user: null,
  isLoading: true,

  setUser: (user) => set({ user }),

  loadUser: async () => {
    set({ isLoading: true })
    try {
      const user = await authSupabase.getCurrentUser()
      set({ user, isLoading: false })
    } catch (error) {
      console.error('Failed to load user:', error)
      set({ user: null, isLoading: false })
    }
  },

  logout: async () => {
    set({ isLoading: true })
    try {
      await authSupabase.logout()
      set({ user: null, isLoading: false })
    } catch (error) {
      console.error('Failed to logout:', error)
      set({ isLoading: false })
    }
  },
}))

// Initialize auth state and listen for changes
if (typeof window !== 'undefined') {
  // Add a flag to prevent multiple initializations
  let isInitialized = false
  
  const initAuth = async () => {
    if (isInitialized) return
    isInitialized = true
    
    // Load initial user
    await useAuthSupabase.getState().loadUser()
    
    // Listen for auth state changes
    supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT') {
        useAuthSupabase.getState().setUser(null)
      } else if (event === 'SIGNED_IN') {
        // Only reload on sign in, not on token refresh to prevent loops
        useAuthSupabase.getState().loadUser()
      }
    })
  }
  
  initAuth()
}