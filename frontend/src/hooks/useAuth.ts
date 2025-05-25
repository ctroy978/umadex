import { create } from 'zustand'
import { User } from '@/types/auth'
import { authService } from '@/lib/auth'

interface AuthState {
  user: User | null
  isLoading: boolean
  setUser: (user: User | null) => void
  loadUser: () => Promise<void>
  logout: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  isLoading: true,

  setUser: (user) => set({ user }),

  loadUser: async () => {
    try {
      if (authService.isAuthenticated()) {
        const user = await authService.getCurrentUser()
        set({ user, isLoading: false })
      } else {
        set({ user: null, isLoading: false })
      }
    } catch (error) {
      set({ user: null, isLoading: false })
    }
  },

  logout: async () => {
    await authService.logout()
    set({ user: null })
  },
}))