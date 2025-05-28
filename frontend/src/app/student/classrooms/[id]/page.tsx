'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { studentClassroomApi } from '@/lib/classroomApi'
import { format, isAfter, isBefore } from 'date-fns'
import AuthGuard from '@/components/AuthGuard'
import {
  ArrowLeftIcon,
  ClockIcon,
  CalendarDaysIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline'
import type { Classroom, AssignmentInClassroom } from '@/types/classroom'

export default function StudentClassroomPage() {
  const params = useParams()
  const router = useRouter()
  const { user } = useAuth()
  const classroomId = params.id as string

  const [classroom, setClassroom] = useState<Classroom | null>(null)
  const [assignments, setAssignments] = useState<AssignmentInClassroom[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (user?.role !== 'student') {
      router.push('/dashboard')
      return
    }
    fetchClassroomData()
  }, [classroomId, user])

  const fetchClassroomData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch classroom details
      const classrooms = await studentClassroomApi.listMyClassrooms()
      const currentClassroom = classrooms.find(c => c.id === classroomId)
      
      if (!currentClassroom) {
        setError('Classroom not found or you are not enrolled')
        return
      }
      
      setClassroom(currentClassroom)

      // Fetch assignments
      const assignmentData = await studentClassroomApi.getClassroomAssignments(classroomId)
      setAssignments(assignmentData)
    } catch (error) {
      console.error('Failed to fetch classroom data:', error)
      setError('Failed to load classroom data')
    } finally {
      setLoading(false)
    }
  }

  const getAssignmentStatus = (assignment: AssignmentInClassroom) => {
    const now = new Date()
    const startDate = assignment.start_date ? new Date(assignment.start_date) : null
    const endDate = assignment.end_date ? new Date(assignment.end_date) : null

    if (startDate && isBefore(now, startDate)) {
      return { 
        status: 'upcoming', 
        message: `Available ${format(startDate, 'MMM d, yyyy h:mm a')}`,
        color: 'text-amber-600 bg-amber-50'
      }
    }
    
    if (endDate && isAfter(now, endDate)) {
      return { 
        status: 'expired', 
        message: `Ended ${format(endDate, 'MMM d, yyyy h:mm a')}`,
        color: 'text-red-600 bg-red-50'
      }
    }

    if (endDate) {
      return { 
        status: 'active', 
        message: `Due ${format(endDate, 'MMM d, yyyy h:mm a')}`,
        color: 'text-blue-600 bg-blue-50'
      }
    }

    return { 
      status: 'active', 
      message: 'Available',
      color: 'text-green-600 bg-green-50'
    }
  }

  const visibleAssignments = assignments.filter(assignment => {
    const status = getAssignmentStatus(assignment)
    return status.status !== 'expired'
  })

  const handleAssignmentClick = (assignment: AssignmentInClassroom) => {
    const status = getAssignmentStatus(assignment)
    if (status.status === 'upcoming') {
      alert('This assignment is not available yet.')
      return
    }
    if (status.status === 'expired') {
      alert('This assignment has ended.')
      return
    }
    
    // Navigate to assignment based on type
    const typeRoutes: Record<string, string> = {
      'UMARead': '/assignments/reading',
      'UMAVocab': '/assignments/vocabulary',
      'UMADebate': '/assignments/debate',
      'UMAWrite': '/assignments/writing',
      'UMALecture': '/assignments/lecture'
    }
    
    const route = typeRoutes[assignment.assignment_type] || '/assignments/reading'
    router.push(`${route}/${assignment.assignment_id}`)
  }

  if (loading) {
    return (
      <AuthGuard>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-gray-500">Loading classroom...</p>
          </div>
        </div>
      </AuthGuard>
    )
  }

  if (error) {
    return (
      <AuthGuard>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <ExclamationCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <p className="text-red-600">{error}</p>
            <button
              onClick={() => router.push('/dashboard')}
              className="mt-4 text-primary-600 hover:text-primary-700"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </AuthGuard>
    )
  }

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-4 flex items-center">
              <button
                onClick={() => router.push('/dashboard')}
                className="mr-4 text-gray-500 hover:text-gray-700"
              >
                <ArrowLeftIcon className="h-5 w-5" />
              </button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  {classroom?.name}
                </h1>
                <p className="text-sm text-gray-500">
                  Class Code: {classroom?.class_code}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <h2 className="text-lg font-medium text-gray-900 mb-6">Assignments</h2>

          {visibleAssignments.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <ClockIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No assignments available</p>
              <p className="text-sm text-gray-400 mt-2">
                Check back later for new assignments from your teacher
              </p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {visibleAssignments.map((assignment) => {
                const status = getAssignmentStatus(assignment)
                const isClickable = status.status === 'active'

                return (
                  <div
                    key={assignment.assignment_id}
                    onClick={() => isClickable && handleAssignmentClick(assignment)}
                    className={`
                      bg-white rounded-lg shadow p-6 
                      ${isClickable ? 'hover:shadow-lg cursor-pointer' : 'opacity-75 cursor-not-allowed'}
                      transition-shadow
                    `}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <h3 className="text-lg font-medium text-gray-900">
                        {assignment.title}
                      </h3>
                      <span className={`
                        inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                        ${status.color}
                      `}>
                        {assignment.assignment_type.replace('UMA', '')}
                      </span>
                    </div>

                    <div className="space-y-2">
                      {assignment.start_date && (
                        <div className="flex items-center text-sm text-gray-600">
                          <CalendarDaysIcon className="h-4 w-4 mr-2 text-gray-400" />
                          <span>
                            Start: {format(new Date(assignment.start_date), 'MMM d, h:mm a')}
                          </span>
                        </div>
                      )}
                      
                      {assignment.end_date && (
                        <div className="flex items-center text-sm text-gray-600">
                          <ClockIcon className="h-4 w-4 mr-2 text-gray-400" />
                          <span>
                            Due: {format(new Date(assignment.end_date), 'MMM d, h:mm a')}
                          </span>
                        </div>
                      )}

                      <div className="pt-2">
                        <span className={`text-sm font-medium ${
                          status.status === 'active' ? 'text-green-600' : 'text-gray-500'
                        }`}>
                          {status.message}
                        </span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Show expired assignments separately */}
          {assignments.some(a => getAssignmentStatus(a).status === 'expired') && (
            <div className="mt-8">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Past Assignments</h3>
              <div className="bg-gray-100 rounded-lg p-4">
                <p className="text-sm text-gray-600">
                  {assignments.filter(a => getAssignmentStatus(a).status === 'expired').length} assignment(s) 
                  are no longer available
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </AuthGuard>
  )
}