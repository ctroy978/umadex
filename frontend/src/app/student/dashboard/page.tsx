'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { studentApi, type StudentClassroom } from '@/lib/studentApi'
import { useAuthSupabase } from '@/hooks/useAuthSupabase'
import { 
  PlusIcon, 
  BookOpenIcon, 
  AcademicCapIcon,
  UsersIcon,
  ClockIcon,
  ArrowRightIcon,
  ArrowRightOnRectangleIcon
} from '@heroicons/react/24/outline'

export default function StudentDashboard() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { logout, user } = useAuthSupabase()
  const [classrooms, setClassrooms] = useState<StudentClassroom[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchClassrooms()
  }, [])

  // Listen for refresh parameter from test completion
  useEffect(() => {
    const refresh = searchParams.get('refresh')
    if (refresh === 'true') {
      console.log('=== DASHBOARD: Refreshing data after test completion ===')
      // Remove the refresh parameter from URL
      router.replace('/student/dashboard')
      // Refetch data to show updated test status
      fetchClassrooms()
    }
  }, [searchParams, router])

  const fetchClassrooms = async () => {
    try {
      setLoading(true)
      const data = await studentApi.getClassrooms()
      setClassrooms(data)
    } catch (err) {
      console.error('Failed to fetch classrooms:', err)
      setError('Failed to load classrooms')
    } finally {
      setLoading(false)
    }
  }

  const handleJoinClassroom = () => {
    router.push('/student/join')
  }

  const handleViewClassroom = (classroomId: string) => {
    router.push(`/student/classrooms/${classroomId}`)
  }

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 17) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-6">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">
                    {getGreeting()}!
                  </h1>
                  <p className="text-gray-600 mt-1">
                    Access your classrooms and assignments
                  </p>
                </div>
                <div className="flex items-center space-x-3">
                  {user && (
                    <span className="text-gray-700 font-medium">
                      {user.first_name} {user.last_name}
                    </span>
                  )}
                  <button
                    onClick={handleJoinClassroom}
                    className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                  >
                    <PlusIcon className="h-5 w-5 mr-2" />
                    Join Class
                  </button>
                  <button
                    onClick={handleLogout}
                    className="flex items-center px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                  >
                    <ArrowRightOnRectangleIcon className="h-5 w-5 mr-2" />
                    Logout
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

          {/* Main Content */}
          {loading ? (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
              <p className="mt-4 text-gray-500">Loading your classrooms...</p>
            </div>
          ) : error ? (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <p className="text-red-600">{error}</p>
              <button
                onClick={fetchClassrooms}
                className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                Try Again
              </button>
            </div>
          ) : classrooms.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <AcademicCapIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No classes yet</h3>
              <p className="text-gray-600 mb-6">
                Get started by joining your first classroom using a class code from your teacher.
              </p>
              <button
                onClick={handleJoinClassroom}
                className="inline-flex items-center px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                <PlusIcon className="h-5 w-5 mr-2" />
                Join Your First Class
              </button>
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-gray-900">Your Classes</h2>
                <span className="text-sm text-gray-500">
                  {classrooms.length} {classrooms.length === 1 ? 'class' : 'classes'}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {classrooms.map((classroom) => (
                  <div
                    key={classroom.id}
                    className="bg-white rounded-lg shadow hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => handleViewClassroom(classroom.id)}
                  >
                    <div className="p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <h3 className="text-lg font-semibold text-gray-900 mb-1">
                            {classroom.name}
                          </h3>
                          <p className="text-sm text-gray-600 mb-2">
                            {classroom.teacher_name}
                          </p>
                          <p className="text-xs text-gray-500">
                            Class Code: {classroom.class_code}
                          </p>
                        </div>
                        <ArrowRightIcon className="h-5 w-5 text-gray-400" />
                      </div>

                      <div className="pt-4 border-t border-gray-200">
                        <p className="text-xs text-gray-500">
                          Joined {new Date(classroom.joined_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
  )
}