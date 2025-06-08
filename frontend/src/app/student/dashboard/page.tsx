'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { studentApi, type StudentClassroom } from '@/lib/studentApi'
import { useAuth } from '@/hooks/useAuth'
import { tokenStorage } from '@/lib/tokenStorage'
import { 
  PlusIcon, 
  BookOpenIcon, 
  AcademicCapIcon,
  UsersIcon,
  ClockIcon,
  ArrowRightIcon,
  ArrowRightOnRectangleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline'

interface AvailableTest {
  test_id: string;
  assignment_id: string;
  assignment_title: string;
  time_limit_minutes: number;
  attempts_remaining: number;
  expires_at: string;
  classroom_assignment_id: string;
}

export default function StudentDashboard() {
  const router = useRouter()
  const { logout } = useAuth()
  const [classrooms, setClassrooms] = useState<StudentClassroom[]>([])
  const [availableTests, setAvailableTests] = useState<AvailableTest[]>([])
  const [loading, setLoading] = useState(true)
  const [testsLoading, setTestsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchClassrooms()
    fetchAvailableTests()
  }, [])

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

  const fetchAvailableTests = async () => {
    try {
      setTestsLoading(true)
      const token = tokenStorage.getAccessToken()
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/tests/available`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setAvailableTests(data)
      }
    } catch (err) {
      console.error('Failed to fetch available tests:', err)
    } finally {
      setTestsLoading(false)
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
                    {getGreeting()}! Ready to learn?
                  </h1>
                  <p className="text-gray-600 mt-1">
                    Access your assignments and track your progress
                  </p>
                </div>
                <div className="flex items-center space-x-3">
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
          {/* Stats Overview */}
          {classrooms.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <AcademicCapIcon className="h-6 w-6 text-blue-600" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Classes Enrolled</p>
                    <p className="text-2xl font-bold text-gray-900">{classrooms.length}</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <BookOpenIcon className="h-6 w-6 text-green-600" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Total Assignments</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {classrooms.reduce((sum, c) => sum + c.assignment_count, 0)}
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <div className="p-2 bg-amber-100 rounded-lg">
                    <ClockIcon className="h-6 w-6 text-amber-600" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Available Now</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {classrooms.reduce((sum, c) => sum + c.available_assignment_count, 0)}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Available Tests Section */}
          {!testsLoading && availableTests.length > 0 && (
            <div className="mb-8">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Available Tests</h2>
                <span className="text-sm text-gray-500">
                  {availableTests.length} {availableTests.length === 1 ? 'test' : 'tests'} available
                </span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {availableTests.map((test) => (
                  <div
                    key={test.test_id}
                    className="bg-white rounded-lg shadow hover:shadow-md transition-shadow border border-green-200"
                  >
                    <div className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <h3 className="font-medium text-gray-900 mb-1">
                            {test.assignment_title}
                          </h3>
                          <div className="space-y-1 text-sm text-gray-600">
                            <p>Time limit: {test.time_limit_minutes} minutes</p>
                            <p>Attempts remaining: {test.attempts_remaining}</p>
                            <p>Expires: {new Date(test.expires_at).toLocaleDateString()}</p>
                          </div>
                        </div>
                        <CheckCircleIcon className="h-5 w-5 text-green-500" />
                      </div>
                      
                      <button
                        onClick={() => router.push(`/student/test/${test.assignment_id}`)}
                        className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors text-sm font-medium"
                      >
                        Start Test
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

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

                      <div className="space-y-3">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-600">Total Assignments</span>
                          <span className="font-medium text-gray-900">
                            {classroom.assignment_count}
                          </span>
                        </div>
                        
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-600">Available Now</span>
                          <span className="font-medium text-green-600">
                            {classroom.available_assignment_count}
                          </span>
                        </div>

                        <div className="pt-2 border-t border-gray-200">
                          <p className="text-xs text-gray-500">
                            Joined {new Date(classroom.joined_at).toLocaleDateString()}
                          </p>
                        </div>
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