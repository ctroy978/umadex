'use client'

import AuthGuard from '@/components/AuthGuard'
import { useAuthSupabase } from '@/hooks/useAuthSupabase'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { studentClassroomApi } from '@/lib/classroomApi'
import { AcademicCapIcon, PlusIcon, ClipboardDocumentListIcon, ArrowRightOnRectangleIcon } from '@heroicons/react/24/outline'
import type { Classroom } from '@/types/classroom'

export default function DashboardPage() {
  const { user, logout } = useAuthSupabase()
  const router = useRouter()
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [loadingClassrooms, setLoadingClassrooms] = useState(true)

  useEffect(() => {
    if (user?.is_admin) {
      router.push('/admin/dashboard')
    } else if (user?.role === 'teacher') {
      router.push('/teacher/dashboard')
    } else if (user?.role === 'student') {
      fetchClassrooms()
    }
  }, [user, router])

  const fetchClassrooms = async () => {
    try {
      const data = await studentClassroomApi.listMyClassrooms()
      setClassrooms(data)
    } catch (error) {
      console.error('Failed to fetch classrooms:', error)
    } finally {
      setLoadingClassrooms(false)
    }
  }

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  // Prevent flash by not rendering content for teachers
  if (user?.role === 'teacher') {
    return (
      <AuthGuard>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-gray-500">Redirecting...</div>
        </div>
      </AuthGuard>
    )
  }

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <h1 className="text-xl font-semibold text-gray-900">uMaDex</h1>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-500">
                  {user?.email}
                </span>
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
        </nav>

        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">
                  Welcome, {user?.first_name} {user?.last_name}!
                </h2>
                
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <dt className="text-sm font-medium text-gray-500">Username</dt>
                    <dd className="mt-1 text-sm text-gray-900">{user?.username}</dd>
                  </div>
                  
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <dt className="text-sm font-medium text-gray-500">Role</dt>
                    <dd className="mt-1">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        (user?.role as string) === 'teacher' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
                      }`}>
                        {user?.role}
                      </span>
                    </dd>
                  </div>
                  
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <dt className="text-sm font-medium text-gray-500">Admin Access</dt>
                    <dd className="mt-1">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        user?.is_admin ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {user?.is_admin ? 'Yes' : 'No'}
                      </span>
                    </dd>
                  </div>
                </div>

                {user?.role === 'student' && (
                  <>
                    <div className="mt-8">
                      <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-medium text-gray-900">My Classrooms</h3>
                        <button
                          onClick={() => router.push('/student/join')}
                          className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
                        >
                          <PlusIcon className="h-4 w-4 mr-1" />
                          Join Class
                        </button>
                      </div>

                      {loadingClassrooms ? (
                        <div className="flex justify-center py-8">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                        </div>
                      ) : classrooms.length === 0 ? (
                        <div className="text-center py-8 bg-gray-50 rounded-lg">
                          <AcademicCapIcon className="h-12 w-12 mx-auto mb-3 text-gray-400" />
                          <p className="text-gray-500 mb-2">No classrooms yet</p>
                          <p className="text-sm text-gray-400">Join a classroom using the code from your teacher</p>
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                          {classrooms.map((classroom) => (
                            <div
                              key={classroom.id}
                              className="bg-gray-50 p-4 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
                              onClick={() => router.push(`/student/classrooms/${classroom.id}`)}
                            >
                              <h4 className="font-medium text-gray-900">{classroom.name}</h4>
                              <p className="text-sm text-gray-500 mt-1">Code: {classroom.class_code}</p>
                              <div className="mt-3 flex items-center text-sm text-gray-600">
                                <ClipboardDocumentListIcon className="h-4 w-4 mr-1" />
                                <span>{classroom.assignment_count} assignments</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="mt-6 pt-6 border-t">
                      <h3 className="text-sm font-medium text-gray-900 mb-2">Quick Actions</h3>
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <button 
                          onClick={() => router.push('/student/join')}
                          className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                        >
                          Join New Classroom
                        </button>
                        <button className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
                          Profile Settings
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    </AuthGuard>
  )
}