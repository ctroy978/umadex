import { defineStore } from 'pinia'
import { supabase } from '../services/supabase'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const session = ref(null)
  const loading = ref(false)
  const error = ref(null)
  
  const isAuthenticated = computed(() => !!user.value)
  
  // Sign in with OTP (One-Time Password via email)
  async function signInWithOTP(email: string) {
    loading.value = true
    error.value = null
    
    try {
      const { error: signInError } = await supabase.auth.signInWithOtp({
        email,
      })
      
      if (signInError) throw signInError
      
      return { success: true }
    } catch (err) {
      console.error('Error signing in:', err)
      error.value = err.message || 'Error during sign in'
      return { success: false, error: err }
    } finally {
      loading.value = false
    }
  }
  
  // Verify OTP token
  async function verifyOTP(email: string, token: string) {
    loading.value = true
    error.value = null
    
    try {
      const { data, error: verifyError } = await supabase.auth.verifyOtp({
        email,
        token,
        type: 'email',
      })
      
      if (verifyError) throw verifyError
      
      session.value = data.session
      user.value = data.user
      
      return { success: true }
    } catch (err) {
      console.error('Error verifying OTP:', err)
      error.value = err.message || 'Error verifying code'
      return { success: false, error: err }
    } finally {
      loading.value = false
    }
  }
  
  // Log out
  async function logout() {
    loading.value = true
    error.value = null
    
    try {
      const { error: signOutError } = await supabase.auth.signOut()
      
      if (signOutError) throw signOutError
      
      user.value = null
      session.value = null
      
      return { success: true }
    } catch (err) {
      console.error('Error logging out:', err)
      error.value = err.message || 'Error during logout'
      return { success: false, error: err }
    } finally {
      loading.value = false
    }
  }
  
  // Check if user is already logged in
  async function initialize() {
    loading.value = true
    
    try {
      // Check for existing session
      const { data: { session: existingSession } } = await supabase.auth.getSession()
      
      if (existingSession) {
        session.value = existingSession
        user.value = existingSession.user
        
        // Set up auth state change listener
        supabase.auth.onAuthStateChange((event, newSession) => {
          session.value = newSession
          user.value = newSession?.user || null
        })
      }
    } catch (err) {
      console.error('Error initializing auth:', err)
      error.value = err.message || 'Error initializing authentication'
    } finally {
      loading.value = false
    }
  }
  
  return {
    user,
    session,
    loading,
    error,
    isAuthenticated,
    signInWithOTP,
    verifyOTP,
    logout,
    initialize
  }
})