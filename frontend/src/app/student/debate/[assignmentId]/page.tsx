'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { studentDebateApi } from '@/lib/studentDebateApi'
import { DebateAssignmentCard, DebateProgress } from '@/types/debate'
import { 
  ArrowLeftIcon,
  PlayIcon,
  ClockIcon,
  UserGroupIcon,
  ChatBubbleLeftRightIcon,
  ExclamationCircleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline'
import AntiCheatWrapper from '@/components/debate/AntiCheatWrapper'

export default function DebateAssignmentPage() {
  const params = useParams()
  const router = useRouter()
  const assignmentId = params.assignmentId as string

  const [assignment, setAssignment] = useState<DebateAssignmentCard | null>(null)
  const [progress, setProgress] = useState<DebateProgress | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    fetchAssignment()
  }, [assignmentId])

  const fetchAssignment = async () => {
    try {
      setLoading(true)
      setError(null)

      const assignmentData = await studentDebateApi.getAssignment(assignmentId)
      setAssignment(assignmentData)

      // If already started, get progress
      if (assignmentData.status !== 'not_started') {
        const progressData = await studentDebateApi.getCurrentDebate(assignmentId)
        setProgress(progressData)
      }
    } catch (err) {
      setError('Failed to load assignment details')
    } finally {
      setLoading(false)
    }
  }

  const handleStartAssignment = async () => {
    try {
      setStarting(true)
      await studentDebateApi.startAssignment(assignmentId)
      // Navigate to debate interface
      router.push(`/student/debate/${assignmentId}/debate`)
    } catch (err) {
      setError('Failed to start assignment. Please try again.')
      setStarting(false)
    }
  }

  const handleContinueDebate = () => {
    router.push(`/student/debate/${assignmentId}/debate`)
  }

  const handleViewResults = () => {
    router.push(`/student/debate/${assignmentId}/results`)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading debate assignment...</p>
        </div>
      </div>
    )
  }

  if (error || !assignment) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <ExclamationCircleIcon className="h-5 w-5 text-red-400" />
              <p className="ml-3 text-sm text-red-800">
                {error || 'Assignment not found'}
              </p>
            </div>
          </div>
          <button
            onClick={() => router.push('/student/dashboard')}
            className="mt-4 flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            <ArrowLeftIcon className="mr-2 h-4 w-4" />
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <AntiCheatWrapper>
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto p-6">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.push('/student/dashboard')}
            className="mb-4 flex items-center text-gray-600 hover:text-gray-900"
          >
            <ArrowLeftIcon className="mr-2 h-4 w-4" />
            Back to Dashboard
          </button>
          
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">{assignment.title}</h1>
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
              assignment.status === 'completed' 
                ? 'bg-green-100 text-green-800' 
                : (assignment.status === 'debate_1' || assignment.status === 'debate_2' || assignment.status === 'debate_3')
                ? 'bg-blue-100 text-blue-800'
                : 'bg-gray-100 text-gray-800'
            }`}>
              {studentDebateApi.getStatusText(assignment.status)}
            </span>
          </div>
        </div>

        {/* Assignment Overview */}
        <div className="bg-white shadow rounded-lg mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Debate Topic</h2>
          </div>
          <div className="p-6">
            <p className="text-lg text-gray-700 mb-4">{assignment.topic}</p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
              <div className="flex items-center">
                <ChatBubbleLeftRightIcon className="h-5 w-5 text-gray-400 mr-2" />
                <div>
                  <p className="text-sm text-gray-500">Debates</p>
                  <p className="font-medium">{assignment.debateFormat.debateCount} debates</p>
                </div>
              </div>
              
              <div className="flex items-center">
                <ClockIcon className="h-5 w-5 text-gray-400 mr-2" />
                <div>
                  <p className="text-sm text-gray-500">Time Limit</p>
                  <p className="font-medium">{assignment.debateFormat.timeLimitHours} hours per debate</p>
                </div>
              </div>
              
              <div className="flex items-center">
                <UserGroupIcon className="h-5 w-5 text-gray-400 mr-2" />
                <div>
                  <p className="text-sm text-gray-500">Rounds</p>
                  <p className="font-medium">{assignment.debateFormat.roundsPerDebate} rounds per debate</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Progress Overview */}
        {assignment.status !== 'not_started' && progress && (
          <div className="bg-white shadow rounded-lg mb-6">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Your Progress</h2>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                {/* Current Debate Status */}
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">
                      {assignment.status === 'completed' ? 'Assignment Status' : 'Current Debate'}
                    </p>
                    <p className="font-medium">
                      {assignment.status === 'completed' 
                        ? 'All debates completed' 
                        : `Debate ${progress?.studentDebate?.currentDebate || 1} of ${assignment.debateFormat.debateCount}`}
                    </p>
                  </div>
                  {assignment.status !== 'completed' && (
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Position</p>
                      <p className="font-medium capitalize">
                        {(() => {
                          const currentDebate = progress?.studentDebate?.currentDebate
                          if (!currentDebate || !progress?.studentDebate) return 'Not set'
                          
                          let position = null
                          if (currentDebate === 1) {
                            position = progress.studentDebate.debate_1Position
                          } else if (currentDebate === 2) {
                            position = progress.studentDebate.debate_2Position
                          } else if (currentDebate === 3) {
                            position = progress.studentDebate.debate_3Position
                          }
                          
                          return position ? position.toUpperCase() : 'Not set'
                        })()}
                      </p>
                    </div>
                  )}
                </div>

                {/* Debate Progress Bars */}
                <div className="space-y-3">
                  {[1, 2, 3].map((debateNum) => (
                    <div key={debateNum}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600">Debate {debateNum}</span>
                        {progress?.studentDebate?.[`debate_${debateNum}Percentage` as keyof typeof progress.studentDebate] !== null && (
                          <span className="text-gray-900 font-medium">
                            {progress?.studentDebate?.[`debate_${debateNum}Percentage` as keyof typeof progress.studentDebate]}%
                          </span>
                        )}
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full ${
                            debateNum < (progress?.studentDebate?.currentDebate || 1) ? 'bg-green-600' :
                            debateNum === (progress?.studentDebate?.currentDebate || 1) ? 'bg-blue-600' :
                            'bg-gray-300'
                          }`}
                          style={{
                            width: debateNum < (progress?.studentDebate?.currentDebate || 1) ? '100%' :
                                   debateNum === (progress?.studentDebate?.currentDebate || 1) ? 
                                     // Check if debate is complete by looking at nextAction
                                     (progress?.nextAction === 'debate_complete' || progress?.nextAction === 'assignment_complete') ? '100%' :
                                     // Otherwise calculate based on posts in current debate (5 posts = 100%)
                                     `${Math.min(100, ((progress?.currentPosts?.length || 0) / 5) * 100)}%` :
                                   '0%'
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                {/* Time Remaining */}
                {progress.timeRemaining && (
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                    <div className="flex items-center">
                      <ClockIcon className="h-5 w-5 text-amber-600 mr-2" />
                      <p className="text-sm text-amber-800">
                        Time remaining for current debate: {Math.floor(progress.timeRemaining / 3600)} hours {Math.floor((progress.timeRemaining % 3600) / 60)} minutes
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Instructions */}
        <div className="bg-white shadow rounded-lg mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Instructions</h2>
          </div>
          <div className="p-6">
            <ul className="space-y-2 text-gray-700">
              <li className="flex">
                <span className="text-green-500 mr-2">•</span>
                You will participate in {assignment.debateFormat.debateCount} debates on this topic
              </li>
              <li className="flex">
                <span className="text-green-500 mr-2">•</span>
                Each debate consists of {assignment.debateFormat.roundsPerDebate} rounds of exchanges
              </li>
              <li className="flex">
                <span className="text-green-500 mr-2">•</span>
                You have {assignment.debateFormat.timeLimitHours} hours to complete each debate
              </li>
              <li className="flex">
                <span className="text-green-500 mr-2">•</span>
                For debates 1 & 2, your position (pro/con) will be assigned
              </li>
              <li className="flex">
                <span className="text-green-500 mr-2">•</span>
                For debate 3, you can choose your position
              </li>
              <li className="flex">
                <span className="text-green-500 mr-2">•</span>
                Look for opportunities to challenge fallacies for bonus points!
              </li>
            </ul>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex justify-center">
          {assignment.status === 'not_started' && (
            <button
              onClick={handleStartAssignment}
              disabled={starting}
              className={`flex items-center px-6 py-3 text-white font-medium rounded-lg transition-colors ${
                starting 
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'bg-green-600 hover:bg-green-700'
              }`}
            >
              <PlayIcon className="mr-2 h-5 w-5" />
              {starting ? 'Starting...' : 'Start First Debate'}
            </button>
          )}

          {(assignment.status === 'debate_1' || assignment.status === 'debate_2' || assignment.status === 'debate_3') && (
            <button
              onClick={handleContinueDebate}
              className="flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              <PlayIcon className="mr-2 h-5 w-5" />
              Continue Debate
            </button>
          )}

          {assignment.status === 'completed' && (
            <button
              onClick={handleViewResults}
              className="flex items-center px-6 py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors"
            >
              <CheckCircleIcon className="mr-2 h-5 w-5" />
              View Results
            </button>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <ExclamationCircleIcon className="h-5 w-5 text-red-400" />
              <p className="ml-3 text-sm text-red-800">{error}</p>
            </div>
          </div>
        )}
        </div>
      </div>
    </AntiCheatWrapper>
  )
}