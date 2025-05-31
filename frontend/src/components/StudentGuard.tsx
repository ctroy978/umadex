'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'

interface StudentGuardProps {
  children: React.ReactNode
}

export default function StudentGuard({ children }: StudentGuardProps) {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading) {
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
  }, [user, loading, router])

  if (loading) {
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