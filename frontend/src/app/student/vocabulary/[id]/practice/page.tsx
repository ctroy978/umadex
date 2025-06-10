'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { studentApi } from '@/lib/studentApi'
import {
  ArrowLeftIcon,
  AcademicCapIcon,
  CheckCircleIcon,
  LockClosedIcon,
  ClockIcon,
  ExclamationCircleIcon,
  ChartBarIcon,
  DocumentCheckIcon
} from '@heroicons/react/24/outline'

interface PracticeAssignment {
  type: string
  display_name: string
  status: 'not_started' | 'in_progress' | 'completed' | 'failed'
  attempts: number
  best_score: number
  completed_at?: string
  available: boolean
  can_start: boolean
  is_completed: boolean
}

interface PracticeStatus {
  assignments: PracticeAssignment[]
  completed_count: number
  required_count: number
  test_unlocked: boolean
  test_unlock_date?: string
}

export default function VocabularyPracticePage() {
  const params = useParams()
  const router = useRouter()
  const vocabularyId = params.id as string

  const [practiceStatus, setPracticeStatus] = useState<PracticeStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchPracticeStatus()
  }, [vocabularyId])

  const fetchPracticeStatus = async () => {
    try {
      setLoading(true)
      setError(null)
      const status = await studentApi.getVocabularyPracticeStatus(vocabularyId)
      setPracticeStatus(status)
    } catch (err: any) {
      console.error('Failed to fetch practice status:', err)
      setError('Failed to load practice activities. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const getAssignmentIcon = (type: string) => {
    switch (type) {
      case 'vocabulary_challenge':
        return '🎯'
      case 'definition_match':
        return '🔗'
      case 'context_clues':
        return '📖'
      case 'word_builder':
        return '🔤'
      default:
        return '📝'
    }
  }

  const getStatusBadge = (assignment: PracticeAssignment) => {
    if (assignment.status === 'completed') {
      return (
        <div className="flex items-center space-x-1 px-3 py-1 rounded-full text-sm bg-green-100 text-green-800">
          <CheckCircleIcon className="h-4 w-4" />
          <span>Completed</span>
        </div>
      )
    } else if (assignment.status === 'failed') {
      return (
        <div className="flex items-center space-x-1 px-3 py-1 rounded-full text-sm bg-red-100 text-red-800">
          <ExclamationCircleIcon className="h-4 w-4" />
          <span>Try Again</span>
        </div>
      )
    } else if (assignment.status === 'in_progress') {
      return (
        <div className="flex items-center space-x-1 px-3 py-1 rounded-full text-sm bg-yellow-100 text-yellow-800">
          <ClockIcon className="h-4 w-4" />
          <span>In Progress</span>
        </div>
      )
    } else if (!assignment.available) {
      return (
        <div className="flex items-center space-x-1 px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-500">
          <LockClosedIcon className="h-4 w-4" />
          <span>Coming Soon</span>
        </div>
      )
    }
    return null
  }

  const handleStartActivity = (assignment: PracticeAssignment) => {
    // Prevent starting if completed
    if (assignment.is_completed) {
      return
    }
    
    if (assignment.type === 'vocabulary_challenge' && assignment.can_start) {
      router.push(`/student/vocabulary/${vocabularyId}/practice/challenge`)
    }
    // Other assignment types will be added in Phase 2B
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading practice activities...</p>
        </div>
      </div>
    )
  }

  if (error || !practiceStatus) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <ExclamationCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Error Loading Activities</h2>
          <p className="text-gray-600 mb-6">{error || 'Unable to load practice activities'}</p>
          <button
            onClick={() => router.back()}
            className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4 flex items-center justify-between">
            <div className="flex items-center">
              <button
                onClick={() => router.back()}
                className="mr-4 text-gray-500 hover:text-gray-700"
              >
                <ArrowLeftIcon className="h-5 w-5" />
              </button>
              <div className="flex items-center">
                <div className="p-2 bg-amber-100 rounded-lg mr-3">
                  <AcademicCapIcon className="h-6 w-6 text-amber-600" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">
                    Practice Activities
                  </h1>
                  <p className="text-sm text-gray-500">
                    Complete {practiceStatus.required_count} of {practiceStatus.assignments.length} to unlock the test
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Progress Overview */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900">Your Progress</h2>
            <div className="flex items-center space-x-2">
              <ChartBarIcon className="h-5 w-5 text-gray-400" />
              <span className="text-sm text-gray-600">
                {practiceStatus.completed_count} / {practiceStatus.required_count} completed
              </span>
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
            <div
              className="bg-amber-600 h-3 rounded-full transition-all duration-300"
              style={{
                width: `${(practiceStatus.completed_count / practiceStatus.required_count) * 100}%`
              }}
            />
          </div>
          
          {/* Test Unlock Status */}
          {practiceStatus.test_unlocked ? (
            <div className="flex items-center justify-center p-4 bg-green-50 border border-green-200 rounded-lg">
              <CheckCircleIcon className="h-5 w-5 text-green-600 mr-2" />
              <span className="text-green-800 font-medium">Test Unlocked!</span>
            </div>
          ) : (
            <div className="flex items-center justify-center p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <LockClosedIcon className="h-5 w-5 text-amber-600 mr-2" />
              <span className="text-amber-800">
                Complete {practiceStatus.required_count - practiceStatus.completed_count} more {
                  practiceStatus.required_count - practiceStatus.completed_count === 1 ? 'activity' : 'activities'
                } to unlock the test
              </span>
            </div>
          )}
        </div>

        {/* Assignment Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {practiceStatus.assignments.map((assignment) => (
            <div
              key={assignment.type}
              className={`bg-white rounded-lg shadow hover:shadow-md transition-shadow ${
                !assignment.available ? 'opacity-60' : ''
              }`}
            >
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center">
                    <div className="text-4xl mr-4">{getAssignmentIcon(assignment.type)}</div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {assignment.display_name}
                      </h3>
                      {assignment.attempts > 0 && (
                        <p className="text-sm text-gray-600 mt-1">
                          {assignment.attempts} attempt{assignment.attempts !== 1 ? 's' : ''}
                          {assignment.best_score > 0 && ` • Best score: ${assignment.best_score}%`}
                        </p>
                      )}
                    </div>
                  </div>
                  {getStatusBadge(assignment)}
                </div>

                <p className="text-gray-600 mb-4">
                  {assignment.type === 'vocabulary_challenge' && 
                    'Test your vocabulary knowledge through riddles, poems, and word puzzles.'}
                  {assignment.type === 'definition_match' && 
                    'Match vocabulary words with their correct definitions.'}
                  {assignment.type === 'context_clues' && 
                    'Use context clues to identify the correct vocabulary words.'}
                  {assignment.type === 'word_builder' && 
                    'Build and spell vocabulary words correctly.'}
                </p>

                <button
                  onClick={() => handleStartActivity(assignment)}
                  disabled={!assignment.can_start}
                  className={`w-full px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    assignment.is_completed
                      ? 'bg-green-100 text-green-800 cursor-default'
                      : assignment.can_start
                      ? assignment.status === 'failed'
                        ? 'bg-red-600 text-white hover:bg-red-700'
                        : 'bg-primary-600 text-white hover:bg-primary-700'
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  {assignment.is_completed 
                    ? '✓ Completed'
                    : assignment.status === 'failed'
                    ? 'Try Again'
                    : assignment.status === 'in_progress'
                    ? 'Continue'
                    : assignment.can_start
                    ? 'Start Activity'
                    : 'Coming Soon'}
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Final Test Card */}
        <div className="mt-6 bg-white rounded-lg shadow">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="p-3 bg-blue-100 rounded-lg mr-4">
                  <DocumentCheckIcon className="h-8 w-8 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Final Vocabulary Test</h3>
                  <p className="text-gray-600">
                    {practiceStatus.test_unlocked
                      ? 'Ready to test your vocabulary mastery!'
                      : `Complete ${practiceStatus.required_count - practiceStatus.completed_count} more activities to unlock`}
                  </p>
                </div>
              </div>
              <button
                disabled={!practiceStatus.test_unlocked}
                className={`px-6 py-3 rounded-lg text-sm font-medium transition-colors ${
                  practiceStatus.test_unlocked
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
              >
                {practiceStatus.test_unlocked ? 'Take Test' : 'Locked'}
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}