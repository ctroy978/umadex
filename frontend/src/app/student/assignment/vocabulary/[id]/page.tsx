'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { studentApi } from '@/lib/studentApi'
import {
  ArrowLeftIcon,
  BookOpenIcon,
  LanguageIcon,
  SpeakerWaveIcon,
  ArrowRightIcon,
  ArrowLeftIcon as ArrowLeftSmIcon,
  DocumentDuplicateIcon,
  AcademicCapIcon,
  ClockIcon,
  ExclamationCircleIcon,
  HomeIcon
} from '@heroicons/react/24/outline'

interface VocabularyWord {
  id: string
  word: string
  definition: string
  example_1?: string
  example_2?: string
  audio_url?: string
  phonetic_text?: string
  position: number
}

interface VocabularyAssignment {
  id: string
  title: string
  context_description: string
  grade_level: string
  subject_area: string
  classroom_name: string
  teacher_name: string
  start_date: string
  end_date: string
  total_words: number
  available_words: number
  words: VocabularyWord[]
  settings: {
    delivery_mode: string
    group_size: number
    groups_count: number
    released_groups: number[]
  }
}

export default function VocabularyAssignmentPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const assignmentId = params.id as string
  const classroomId = searchParams.get('classroomId')

  const [assignment, setAssignment] = useState<VocabularyAssignment | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAssignment()
  }, [assignmentId])

  const fetchAssignment = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await studentApi.getVocabularyAssignment(assignmentId)
      setAssignment(data)
    } catch (err: any) {
      console.error('Failed to fetch vocabulary assignment:', err)
      if (err.response?.status === 404) {
        setError('Assignment not found or you don\'t have access to it.')
      } else if (err.response?.status === 403) {
        setError('This assignment is not currently active.')
      } else {
        setError('Failed to load assignment. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleStartPresentation = () => {
    const query = classroomId ? `?classroomId=${classroomId}` : ''
    router.push(`/student/vocabulary/${assignmentId}/presentation${query}`)
  }

  const handleStartFlashCards = () => {
    const query = classroomId ? `?classroomId=${classroomId}` : ''
    router.push(`/student/vocabulary/${assignmentId}/flashcards${query}`)
  }

  const formatTimeRemaining = (endDate: string | null | undefined) => {
    if (!endDate) return 'Always available'
    
    const end = new Date(endDate)
    const now = new Date()
    const diff = end.getTime() - now.getTime()
    
    if (diff <= 0) return 'Assignment ended'
    
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    
    if (days > 0) {
      return `${days} day${days > 1 ? 's' : ''} remaining`
    } else if (hours > 0) {
      return `${hours} hour${hours > 1 ? 's' : ''} remaining`
    } else {
      return 'Less than 1 hour remaining'
    }
  }

  const getDeliveryModeText = (mode: string) => {
    switch (mode) {
      case 'all_at_once':
        return 'All words available'
      case 'in_groups':
        return 'Released in groups'
      case 'teacher_controlled':
        return 'Teacher controlled release'
      default:
        return 'Unknown mode'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading vocabulary assignment...</p>
        </div>
      </div>
    )
  }

  if (error || !assignment) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <ExclamationCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Access Denied</h2>
          <p className="text-gray-600 mb-6">{error || 'Assignment not found'}</p>
          <button
            onClick={() => router.push('/student/dashboard')}
            className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
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
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4 flex items-center justify-between">
            <div className="flex items-center">
              <button
                onClick={() => {
                  if (classroomId) {
                    router.push(`/student/classrooms/${classroomId}`)
                  } else {
                    router.push('/student/dashboard')
                  }
                }}
                className="mr-4 text-gray-500 hover:text-gray-700"
              >
                <ArrowLeftIcon className="h-5 w-5" />
              </button>
              <div className="flex items-center">
                <div className="p-2 bg-purple-100 rounded-lg mr-3">
                  <LanguageIcon className="h-6 w-6 text-purple-600" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">
                    {assignment.title}
                  </h1>
                  <p className="text-sm text-gray-500">
                    {assignment.classroom_name} • {assignment.teacher_name}
                  </p>
                </div>
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
            </nav>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Assignment Info */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Assignment Details</h3>
              <div className="space-y-3">
                <div>
                  <span className="text-sm font-medium text-gray-600">Context: </span>
                  <span className="text-sm text-gray-900">{assignment.context_description}</span>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-600">Grade Level: </span>
                  <span className="text-sm text-gray-900">{assignment.grade_level}</span>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-600">Subject: </span>
                  <span className="text-sm text-gray-900">{assignment.subject_area}</span>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-600">Delivery: </span>
                  <span className="text-sm text-gray-900">{getDeliveryModeText(assignment.settings.delivery_mode)}</span>
                </div>
              </div>
            </div>
            
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Progress & Timing</h3>
              <div className="space-y-3">
                <div className="flex items-center text-sm">
                  <ClockIcon className="h-4 w-4 mr-2 text-amber-600" />
                  <span className="font-medium text-amber-600">
                    {formatTimeRemaining(assignment.end_date)}
                  </span>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-600">Available Words: </span>
                  <span className="text-sm text-gray-900">
                    {assignment.available_words} of {assignment.total_words}
                  </span>
                </div>
                {assignment.settings.delivery_mode !== 'all_at_once' && (
                  <div>
                    <span className="text-sm font-medium text-gray-600">Groups: </span>
                    <span className="text-sm text-gray-900">
                      {assignment.settings.released_groups.length} of {assignment.settings.groups_count} released
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Study Options */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Study Words */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center mb-4">
              <div className="p-2 bg-blue-100 rounded-lg mr-3">
                <BookOpenIcon className="h-6 w-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-900">Study Words</h3>
            </div>
            <p className="text-gray-600 mb-4">
              Learn vocabulary words with definitions, examples, and pronunciation audio.
            </p>
            <ul className="text-sm text-gray-500 mb-6 space-y-1">
              <li>• Clear word definitions and examples</li>
              <li>• Audio pronunciation when available</li>
              <li>• Navigate between words easily</li>
              <li>• Always available for review</li>
            </ul>
            <button
              onClick={handleStartPresentation}
              disabled={assignment.available_words === 0}
              className={`w-full flex items-center justify-center px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                assignment.available_words > 0
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }`}
            >
              <BookOpenIcon className="h-4 w-4 mr-2" />
              Study Words
              <ArrowRightIcon className="h-4 w-4 ml-2" />
            </button>
          </div>

          {/* Flash Cards */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center mb-4">
              <div className="p-2 bg-green-100 rounded-lg mr-3">
                <DocumentDuplicateIcon className="h-6 w-6 text-green-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-900">Flash Cards</h3>
            </div>
            <p className="text-gray-600 mb-4">
              Practice vocabulary with interactive flash cards for memorization.
            </p>
            <ul className="text-sm text-gray-500 mb-6 space-y-1">
              <li>• Flip cards to reveal definitions</li>
              <li>• Shuffle for varied practice</li>
              <li>• Mark cards as known/unknown</li>
              <li>• Self-directed study sessions</li>
            </ul>
            <button
              onClick={handleStartFlashCards}
              disabled={assignment.available_words === 0}
              className={`w-full flex items-center justify-center px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                assignment.available_words > 0
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }`}
            >
              <DocumentDuplicateIcon className="h-4 w-4 mr-2" />
              Flash Cards
              <ArrowRightIcon className="h-4 w-4 ml-2" />
            </button>
          </div>
        </div>

        {/* Practice Activities */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center">
              <div className="p-2 bg-amber-100 rounded-lg mr-3">
                <AcademicCapIcon className="h-6 w-6 text-amber-600" />
              </div>
              <div>
                <h3 className="text-lg font-medium text-gray-900">Practice Activities</h3>
                <p className="text-sm text-gray-600">Complete 3 of 4 activities to unlock the test</p>
              </div>
            </div>
            <button
              onClick={() => {
                const query = classroomId ? `?classroomId=${classroomId}` : ''
                router.push(`/student/vocabulary/${assignmentId}/practice${query}`)
              }}
              disabled={assignment.available_words === 0}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                assignment.available_words > 0
                  ? 'bg-amber-600 text-white hover:bg-amber-700'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }`}
            >
              View Activities
              <ArrowRightIcon className="h-4 w-4 ml-2 inline" />
            </button>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl mb-1">📝</div>
              <p className="text-sm font-medium text-gray-700">Story Builder</p>
              <p className="text-xs text-gray-500 mt-1">Available</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl mb-1">🗺️</div>
              <p className="text-sm font-medium text-gray-700">Concept Map</p>
              <p className="text-xs text-gray-500 mt-1">Available</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl mb-1">🧩</div>
              <p className="text-sm font-medium text-gray-700">Word Puzzles</p>
              <p className="text-xs text-gray-500 mt-1">Available</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl mb-1">✏️</div>
              <p className="text-sm font-medium text-gray-700">Fill In The Blank</p>
              <p className="text-xs text-gray-500 mt-1">Available</p>
            </div>
          </div>
        </div>

        {/* No Words Available */}
        {assignment.available_words === 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 text-center mb-6">
            <ExclamationCircleIcon className="h-12 w-12 text-amber-600 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Words Available Yet</h3>
            <p className="text-gray-600">
              {assignment.settings.delivery_mode === 'teacher_controlled'
                ? 'Your teacher hasn\'t released any vocabulary groups yet. Check back later!'
                : 'There are no vocabulary words available for this assignment.'}
            </p>
          </div>
        )}
      </main>
    </div>
  )
}