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
  // Load initial user
  useAuthSupabase.getState().loadUser()
  
  // Listen for auth state changes
  supabase.auth.onAuthStateChange((event, session) => {
    if (event === 'SIGNED_OUT') {
      useAuthSupabase.getState().setUser(null)
    } else if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
      // Reload user data when signed in or token refreshed
      useAuthSupabase.getState().loadUser()
    }
  })
}