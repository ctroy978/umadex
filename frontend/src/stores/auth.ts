import { defineStore } from 'pinia'
import { supabase } from '../services/supabase'
import { ref, computed } from 'vue'
import type { User, Session } from '@supabase/supabase-js'
import type { UserProfile } from '../types' // Import the interface

export const useAuthStore = defineStore('auth', () => {
  // Use proper types for user and session
  const user = ref<User | null>(null)
  const userProfile = ref<UserProfile | null>(null)
  const session = ref<Session | null>(null)
  const loading = ref<boolean>(false)
  const error = ref<string | null>(null)
  
  const isAuthenticated = computed(() => !!user.value)


  // Add role-related computed properties and methods
const isAdmin = computed(() => userProfile.value?.role_name === 'ADMIN')
const isTeacher = computed(() => userProfile.value?.role_name === 'TEACHER')
const isStudent = computed(() => userProfile.value?.role_name === 'STUDENT' || !userProfile.value?.role_name)

  
  // Fetch user profile from the profiles table
  async function fetchUserProfile(userId: string) {
    try {
      const { data, error: profileError } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', userId)
        .single()
      
      if (profileError) {
        console.error('Error fetching profile:', profileError)
        return null
      }
      
      userProfile.value = data
      return data
    } catch (err) {
      console.error('Error fetching profile:', err)
      return null
    }
  }
  
//signInWithOTP function in your auth store
async function signInWithOTP(email: string) {
  loading.value = true
  error.value = null
  
  try {
    const { error: signInError } = await supabase.auth.signInWithOtp({
      email,
    })
    
    if (signInError) {
      console.error('Supabase Auth Error:', signInError)
      
      // Transform the technical error into a user-friendly message
      let errorMessage = signInError.message || 'Failed to send verification code';
      
      // Check for the database error that happens with non-whitelisted emails
      if (signInError.message.includes('Database error saving new user')) {
        errorMessage = 'This email is not authorized to register. Please use an approved email address or contact an administrator.';
      }
      
      return { 
        success: false, 
        error: { 
          ...signInError, 
          message: errorMessage 
        } 
      };
    }
    
    return { success: true }
  } catch (err: any) {
    console.error('Error signing in:', err)
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
    console.log(`Attempting to verify OTP for email: ${email}`)
    
    const { data, error: verifyError } = await supabase.auth.verifyOtp({
      email,
      token,
      type: 'email',
    })
    
    if (verifyError) {
      console.error('OTP verification error:', verifyError)
      throw verifyError
    }
    
    console.log('OTP verification successful:', data)
    
    if (!data.user) {
      console.error('No user returned from OTP verification')
      throw new Error('Authentication succeeded but no user was returned')
    }
    
    session.value = data.session
    user.value = data.user
    
    console.log('User authenticated:', data.user)
    
    // Fetch user profile after successful authentication
    if (data.user) {
      const profile = await fetchUserProfile(data.user.id)
      console.log('User profile fetched:', profile)
    }
    
    return { success: true }
  } catch (err: any) {
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
      userProfile.value = null // Clear profile data
      
      return { success: true }
    } catch (err: any) { // Use 'any' as the error type
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
        
        // Fetch profile for existing user
        if (existingSession.user) {
          await fetchUserProfile(existingSession.user.id)
        }
        
        // Set up auth state change listener
        supabase.auth.onAuthStateChange(async (event, newSession) => {
          session.value = newSession
          user.value = newSession?.user || null
          
          // Update profile data when auth state changes
          if (newSession?.user) {
            await fetchUserProfile(newSession.user.id)
          } else {
            userProfile.value = null
          }
        })
      }
    } catch (err: any) { // Use 'any' as the error type
      console.error('Error initializing auth:', err)
      error.value = err.message || 'Error initializing authentication'
    } finally {
      loading.value = false
    }
  }

  // Add method to fetch all users (admin only)
async function fetchAllUsers() {
  if (!isAdmin.value) {
    return { success: false, error: 'Admin access required' }
  }
  
  try {
    const response = await fetch('/api/users', {
      headers: {
        'Authorization': `Bearer ${session.value?.access_token}`
      }
    })
    
    if (!response.ok) {
      throw new Error(`Error: ${response.status}`)
    }
    
    const data = await response.json()
    return { success: true, data }
  } catch (err: any) {
    console.error('Error fetching users:', err)
    return { success: false, error: err.message }
  }
}

// Add method to promote user (admin only)
async function promoteUser(userId: string, newRole: string) {
  if (!isAdmin.value) {
    return { success: false, error: 'Admin access required' }
  }
  
  try {
    const response = await fetch('/api/users/promote', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.value?.access_token}`
      },
      body: JSON.stringify({ user_id: userId, new_role: newRole })
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || `Error: ${response.status}`)
    }
    
    return { success: true }
  } catch (err: any) {
    console.error('Error promoting user:', err)
    return { success: false, error: err.message }
  }
}
  
  return {
    user,
    userProfile,
    session,
    loading,
    error,
    isAuthenticated,
    signInWithOTP,
    verifyOTP,
    logout,
    initialize,
    fetchUserProfile,
    isAdmin,
    isTeacher,
    isStudent,
    fetchAllUsers,
    promoteUser
  }
})