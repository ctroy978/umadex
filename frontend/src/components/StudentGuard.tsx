'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'

/**
 * SECURITY COMPONENT: Student Route Guard
 * 
 * This component protects all student routes via layout-level implementation.
 * It ensures only authenticated users with 'student' role can access student pages.
 * 
 * SECURITY FEATURES:
 * 1. Prevents access before authentication completes (isLoading check)
 * 2. Redirects non-students to appropriate dashboards based on role
 * 3. Graceful handling of unauthenticated users
 * 
 * IMPLEMENTATION PATTERN:
 * Used in /app/student/layout.tsx to protect ALL student routes.
 * Do NOT use this component on individual pages - use layout-level protection.
 * 
 * ADDING NEW ROLES:
 * When adding new roles, update the redirect logic in the useEffect
 * to route new roles to their appropriate dashboard.
 */

interface StudentGuardProps {
  children: React.ReactNode
}

export default function StudentGuard({ children }: StudentGuardProps) {
  const { user, isLoading, loadUser } = useAuth()
  const router = useRouter()

  useEffect(() => {
    loadUser()
  }, [loadUser])

  useEffect(() => {
    if (!isLoading) {
      if (!user) {
        router.push('/login')
        return
      }
      
      if (user.role !== 'student') {
        // Redirect non-students to their appropriate dashboard
        if (user.role === 'teacher') {
          router.push('/teacher/dashboard')
        } else if (user.role === 'admin') {
          router.push('/dashboard') // Admin dashboard
        } else {
          router.push('/login')
        }
        return
      }
    }
  }, [user, isLoading, router])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!user || user.role !== 'student') {
    return null
  }

  return <>{children}</>
}