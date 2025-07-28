'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthSupabase } from '@/hooks/useAuthSupabase'

interface AuthGuardProps {
  children: React.ReactNode
  requireAuth?: boolean
  requireAdmin?: boolean
  requireTeacher?: boolean
}

export default function AuthGuard({ 
  children, 
  requireAuth = true,
  requireAdmin = false,
  requireTeacher = false
}: AuthGuardProps) {
  const router = useRouter()
  const { user, isLoading, loadUser } = useAuthSupabase()

  useEffect(() => {
    loadUser()
  }, [loadUser])

  useEffect(() => {
    if (!isLoading) {
      if (requireAuth && !user) {
        router.push('/login')
      } else if (requireAdmin && !user?.is_admin) {
        router.push('/dashboard')
      } else if (requireTeacher && user?.role === 'student') {
        router.push('/dashboard')
      }
    }
  }, [user, isLoading, requireAuth, requireAdmin, requireTeacher, router])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (requireAuth && !user) {
    return null
  }

  return <>{children}</>
}