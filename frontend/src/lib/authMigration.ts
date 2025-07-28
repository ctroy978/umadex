/**
 * Auth Migration Helper
 * This file helps manage the transition from legacy auth to Supabase auth
 */

import { auth as authLegacy } from './auth'
import { authSupabase } from './authSupabase'
import { api as apiLegacy } from './api'
import { apiSupabase } from './apiSupabase'
import { useAuth as useAuthLegacy } from '@/hooks/useAuth'
import { useAuthSupabase } from '@/hooks/useAuthSupabase'

// Feature flag - set via environment variable
const USE_SUPABASE_AUTH = process.env.NEXT_PUBLIC_USE_SUPABASE_AUTH === 'true'

// Export the appropriate implementations based on feature flag
export const auth = USE_SUPABASE_AUTH ? authSupabase : authLegacy
export const api = USE_SUPABASE_AUTH ? apiSupabase : apiLegacy
export const useAuth = USE_SUPABASE_AUTH ? useAuthSupabase : useAuthLegacy

// Helper to check which auth system is active
export const isUsingSupabaseAuth = () => USE_SUPABASE_AUTH

// Migration status helper
export const getAuthMigrationStatus = () => {
  return {
    usingSupabase: USE_SUPABASE_AUTH,
    legacyEndpoint: '/api/v1/auth',
    supabaseEndpoint: '/api/v1/auth-supabase',
    status: USE_SUPABASE_AUTH ? 'migrated' : 'legacy'
  }
}