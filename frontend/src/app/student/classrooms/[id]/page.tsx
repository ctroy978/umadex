'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { studentApi, type StudentClassroomDetail } from '@/lib/studentApi'
import AssignmentCard from '@/components/student/AssignmentCard'
import LeaveClassroomDialog from '@/components/student/LeaveClassroomDialog'
import {
  ArrowLeftIcon,
  ClockIcon,
  ExclamationCircleIcon,
  ArrowRightOnRectangleIcon,
  BookOpenIcon,
  AcademicCapIcon,
  CheckCircleIcon,
  EllipsisVerticalIcon,
  ArrowRightStartOnRectangleIcon
} from '@heroicons/react/24/outline'

export default function StudentClassroomPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const { user, logout } = useAuth()
  const classroomId = params.id as string

  const [classroom, setClassroom] = useState<StudentClassroomDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showLeaveDialog, setShowLeaveDialog] = useState(false)
  const [showMoreMenu, setShowMoreMenu] = useState(false)

  useEffect(() => {
    fetchClassroomData()
  }, [classroomId])

  // Listen for refresh parameter from test completion
  useEffect(() => {
    const refresh = searchParams.get('refresh')
    if (refresh === 'true') {
      console.log('=== CLASSROOM: Refreshing data after test completion ===')
      // Remove the refresh parameter from URL
      router.replace(`/student/classrooms/${classroomId}`)
      // Refetch data to show updated test status
      fetchClassroomData()
    }
  }, [searchParams, router, classroomId])

  const fetchClassroomData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch classroom details with assignments
      const classroomData = await studentApi.getClassroomDetail(classroomId)
      setClassroom(classroomData)
    } catch (error) {
      console.error('Failed to fetch classroom data:', error)
      setError('Failed to load classroom data. You may not be enrolled in this classroom.')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  const handleLeaveClassroom = async () => {
    try {
      await studentApi.leaveClassroom(classroomId)
      router.push('/student/dashboard')
    } catch (error) {
      console.error('Failed to leave classroom:', error)
      alert('Failed to leave classroom. Please try again.')
    }
  }

  // Group assignments by status
  const groupedAssignments = {
    active: classroom?.assignments.filter(a => a.status === 'active') || [],
    upcoming: classroom?.assignments.filter(a => a.status === 'not_started') || [],
    expired: classroom?.assignments.filter(a => a.status === 'expired') || []
  }

  if (loading) {
    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-gray-500">Loading classroom...</p>
          </div>
        </div>
    )
  }

  if (error || !classroom) {
    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <ExclamationCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <p className="text-red-600">{error || 'Classroom not found'}</p>
            <button
              onClick={() => router.push('/student/dashboard')}
              className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
    )
  }

  return (
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-4 flex items-center justify-between">
              <div className="flex items-center">
                <button
                  onClick={() => router.push('/student/dashboard')}
                  className="mr-4 text-gray-500 hover:text-gray-700"
                >
                  <ArrowLeftIcon className="h-5 w-5" />
                </button>
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">
                    {classroom.name}
                  </h1>
                  <p className="text-sm text-gray-500">
                    {classroom.teacher_name} • Class Code: {classroom.class_code}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                {user && (
                  <span className="text-gray-700 font-medium">
                    {user.first_name} {user.last_name}
                  </span>
                )}
                <button
                  onClick={handleLogout}
                  className="flex items-center px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  <ArrowRightOnRectangleIcon className="h-5 w-5 mr-2" />
                  Logout
                </button>
                <div className="relative">
                  <button
                    onClick={() => setShowMoreMenu(!showMoreMenu)}
                    className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                    title="More options"
                  >
                    <EllipsisVerticalIcon className="h-5 w-5" />
                  </button>
                  {showMoreMenu && (
                    <>
                      <div 
                        className="fixed inset-0 z-10" 
                        onClick={() => setShowMoreMenu(false)}
                      />
                      <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-20 py-1">
                        <button
                          onClick={() => {
                            setShowMoreMenu(false)
                            setShowLeaveDialog(true)
                          }}
                          className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center"
                        >
                          <ArrowRightStartOnRectangleIcon className="h-4 w-4 mr-2" />
                          Leave Classroom
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="p-2 bg-green-100 rounded-lg">
                  <CheckCircleIcon className="h-6 w-6 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Active Assignments</p>
                  <p className="text-2xl font-bold text-gray-900">{groupedAssignments.active.length}</p>
                </div>
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="p-2 bg-amber-100 rounded-lg">
                  <ClockIcon className="h-6 w-6 text-amber-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Upcoming</p>
                  <p className="text-2xl font-bold text-gray-900">{groupedAssignments.upcoming.length}</p>
                </div>
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <BookOpenIcon className="h-6 w-6 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Total Assignments</p>
                  <p className="text-2xl font-bold text-gray-900">{classroom.assignments.length}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Active Assignments */}
          {groupedAssignments.active.length > 0 && (
            <section className="mb-8">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Available Now</h2>
              <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
                {groupedAssignments.active.map((assignment) => (
                  <AssignmentCard
                    key={`${assignment.item_type}-${assignment.id}`}
                    assignment={assignment}
                    classroomId={classroomId}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Upcoming Assignments */}
          {groupedAssignments.upcoming.length > 0 && (
            <section className="mb-8">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Coming Soon</h2>
              <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
                {groupedAssignments.upcoming.map((assignment) => (
                  <AssignmentCard
                    key={`${assignment.item_type}-${assignment.id}`}
                    assignment={assignment}
                    classroomId={classroomId}
                  />
                ))}
              </div>
            </section>
          )}

          {/* No assignments */}
          {classroom.assignments.length === 0 && (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <AcademicCapIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No assignments yet</h3>
              <p className="text-gray-600">
                Your teacher hasn't added any assignments to this classroom yet.
              </p>
              <p className="text-sm text-gray-500 mt-2">
                Check back later or contact your teacher for more information.
              </p>
            </div>
          )}

          {/* Only expired assignments */}
          {classroom.assignments.length > 0 && 
           groupedAssignments.active.length === 0 && 
           groupedAssignments.upcoming.length === 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 text-center">
              <ExclamationCircleIcon className="h-12 w-12 text-amber-600 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No active assignments</h3>
              <p className="text-gray-600">
                All assignments in this classroom have ended or haven't started yet.
              </p>
            </div>
          )}

          {/* Expired Assignments */}
          {groupedAssignments.expired.length > 0 && (
            <section className="mt-8">
              <details className="group">
                <summary className="cursor-pointer list-none">
                  <div className="flex items-center justify-between p-4 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors">
                    <h3 className="text-lg font-medium text-gray-700">Past Assignments</h3>
                    <span className="text-sm text-gray-500">
                      {groupedAssignments.expired.length} ended assignment{groupedAssignments.expired.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                </summary>
                <div className="mt-4 grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
                  {groupedAssignments.expired.map((assignment) => (
                    <div key={`${assignment.item_type}-${assignment.id}`} className="opacity-60">
                      <AssignmentCard
                        assignment={assignment}
                        classroomId={classroomId}
                      />
                    </div>
                  ))}
                </div>
              </details>
            </section>
          )}
        </main>

        {/* Leave Classroom Confirmation Dialog */}
        <LeaveClassroomDialog
          isOpen={showLeaveDialog}
          onClose={() => setShowLeaveDialog(false)}
          onConfirm={handleLeaveClassroom}
          classroomName={classroom.name}
          teacherName={classroom.teacher_name}
          assignmentCount={classroom.assignments.length}
        />
      </div>
  )
}