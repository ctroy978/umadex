'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthSupabase } from '@/hooks/useAuthSupabase'

/**
 * SECURITY COMPONENT: Teacher Route Guard
 * 
 * This component protects all teacher routes via layout-level implementation.
 * It ensures only authenticated users with 'teacher' role can access teacher pages.
 * 
 * SECURITY FEATURES:
 * 1. Prevents access before authentication completes (isLoading check)
 * 2. Redirects non-teachers to dashboard (default fallback)
 * 3. Works in conjunction with TeacherLayout for enhanced UX
 * 
 * IMPLEMENTATION PATTERN:
 * Used in /app/teacher/layout.tsx to protect ALL teacher routes.
 * Individual teacher pages should NOT include additional TeacherGuard wrappers.
 * 
 * ADDING NEW ROLES:
 * When adding roles above 'teacher' (like 'admin'), consider updating
 * the access logic to allow higher-privileged users access to teacher routes.
 */

interface TeacherGuardProps {
  children: React.ReactNode
}

export default function TeacherGuard({ children }: TeacherGuardProps) {
  const router = useRouter()
  const { user, isLoading, loadUser } = useAuthSupabase()

  useEffect(() => {
    loadUser()
  }, [loadUser])

  useEffect(() => {
    if (!isLoading && (!user || user.role !== 'teacher')) {
      router.push('/dashboard')
    }
  }, [user, isLoading, router])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!user || user.role !== 'teacher') {
    return null
  }

  return <>{children}</>
}