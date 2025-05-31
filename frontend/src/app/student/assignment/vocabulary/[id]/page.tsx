'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { studentApi } from '@/lib/studentApi'
import StudentGuard from '@/components/StudentGuard'
import {
  ArrowLeftIcon,
  LanguageIcon,
  ExclamationCircleIcon,
  CheckCircleIcon,
  HomeIcon
} from '@heroicons/react/24/outline'

export default function VocabularyAssignmentPage() {
  const params = useParams()
  const router = useRouter()
  const { user } = useAuth()
  const assignmentId = params.id as string

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [assignmentInfo, setAssignmentInfo] = useState<{
    classroom_id: string
    classroom_name: string
  } | null>(null)

  useEffect(() => {
    validateAccess()
  }, [assignmentId])

  const validateAccess = async () => {
    try {
      setLoading(true)
      setError(null)

      const validation = await studentApi.validateAssignmentAccess('vocabulary', assignmentId)
      
      if (validation.access_granted) {
        setAssignmentInfo({
          classroom_id: validation.classroom_id,
          classroom_name: validation.classroom_name
        })
      }
    } catch (error: any) {
      console.error('Access validation failed:', error)
      
      // Handle specific error cases
      if (error.response?.status === 403) {
        setError(error.response.data.detail || 'You do not have access to this assignment')
      } else if (error.response?.status === 404) {
        setError('Assignment not found')
      } else {
        setError('Failed to validate access. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <StudentGuard>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-gray-500">Validating access...</p>
          </div>
        </div>
      </StudentGuard>
    )
  }

  if (error) {
    return (
      <StudentGuard>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
            <ExclamationCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Access Denied</h2>
            <p className="text-gray-600 mb-6">{error}</p>
            <button
              onClick={() => router.push('/student/dashboard')}
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </StudentGuard>
    )
  }

  return (
    <StudentGuard>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-4 flex items-center justify-between">
              <div className="flex items-center">
                <button
                  onClick={() => router.push(`/student/classrooms/${assignmentInfo?.classroom_id}`)}
                  className="mr-4 text-gray-500 hover:text-gray-700"
                >
                  <ArrowLeftIcon className="h-5 w-5" />
                </button>
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">Vocabulary Assignment</h1>
                  <p className="text-sm text-gray-500">{assignmentInfo?.classroom_name}</p>
                </div>
              </div>
              <nav className="flex items-center space-x-2 text-sm">
                <button
                  onClick={() => router.push('/student/dashboard')}
                  className="text-gray-500 hover:text-gray-700 flex items-center"
                >
                  <HomeIcon className="h-4 w-4 mr-1" />
                  Dashboard
                </button>
                <span className="text-gray-400">/</span>
                <button
                  onClick={() => router.push(`/student/classrooms/${assignmentInfo?.classroom_id}`)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  {assignmentInfo?.classroom_name}
                </button>
                <span className="text-gray-400">/</span>
                <span className="text-gray-700">Assignment</span>
              </nav>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="text-center">
              <div className="mx-auto h-16 w-16 bg-purple-100 rounded-full flex items-center justify-center mb-6">
                <LanguageIcon className="h-10 w-10 text-purple-600" />
              </div>
              
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Vocabulary Assignment Content
              </h2>
              
              <p className="text-gray-600 mb-8 max-w-2xl mx-auto">
                This is a placeholder page for the vocabulary assignment. 
                The actual UMAVocab content and interactive features will be implemented here.
              </p>

              <div className="bg-gray-50 rounded-lg p-6 mb-8">
                <h3 className="text-lg font-medium text-gray-900 mb-3">
                  Features to be implemented:
                </h3>
                <ul className="text-left text-gray-600 space-y-2 max-w-md mx-auto">
                  <li className="flex items-start">
                    <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                    <span>Interactive vocabulary flashcards</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                    <span>Word definitions and example sentences</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                    <span>Pronunciation guides and audio</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                    <span>Practice exercises and quizzes</span>
                  </li>
                  <li className="flex items-start">
                    <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                    <span>Progress tracking and mastery levels</span>
                  </li>
                </ul>
              </div>

              <div className="flex justify-center space-x-4">
                <button
                  onClick={() => router.push(`/student/classrooms/${assignmentInfo?.classroom_id}`)}
                  className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                >
                  Return to Classroom
                </button>
                <button
                  disabled
                  className="px-6 py-2 bg-primary-600 text-white rounded-lg opacity-50 cursor-not-allowed"
                >
                  Start Practice (Coming Soon)
                </button>
              </div>
            </div>
          </div>

          {/* Debug info for development */}
          <div className="mt-8 bg-gray-100 rounded-lg p-4 text-sm text-gray-600">
            <p className="font-medium mb-2">Debug Information:</p>
            <p>Assignment ID: {assignmentId}</p>
            <p>Assignment Type: Vocabulary</p>
            <p>Classroom ID: {assignmentInfo?.classroom_id}</p>
            <p>User ID: {user?.id}</p>
          </div>
        </main>
      </div>
    </StudentGuard>
  )
}