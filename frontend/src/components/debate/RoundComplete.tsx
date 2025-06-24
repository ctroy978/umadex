'use client'

import { useState, useEffect } from 'react'
import { CheckCircleIcon, AcademicCapIcon, ArrowRightIcon } from '@heroicons/react/24/outline'
import { RoundFeedback } from '@/types/debate'

interface RoundCompleteProps {
  assignmentId: string
  debateNumber: number
  onContinue: () => void
}

export default function RoundComplete({ assignmentId, debateNumber, onContinue }: RoundCompleteProps) {
  const [feedback, setFeedback] = useState<RoundFeedback | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchFeedback()
  }, [assignmentId, debateNumber])

  const fetchFeedback = async () => {
    try {
      const response = await fetch(`/api/v1/student-debate/${assignmentId}/feedback/${debateNumber}`)
      if (!response.ok) throw new Error('Failed to fetch feedback')
      const data = await response.json()
      setFeedback(data)
    } catch (err) {
      setError('Could not load feedback')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-green-200 rounded w-3/4 mb-2"></div>
          <div className="h-4 bg-green-200 rounded w-1/2"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg shadow-lg">
      <div className="p-6">
        <div className="flex items-center mb-4">
          <CheckCircleIcon className="h-8 w-8 text-green-600 mr-3" />
          <h3 className="text-2xl font-bold text-gray-900">Round {debateNumber} Complete!</h3>
        </div>

        {feedback && (
          <div className="space-y-4">
            {/* Main Feedback */}
            <div className="bg-white rounded-lg p-4 border border-gray-200">
              <div className="flex items-start">
                <AcademicCapIcon className="h-5 w-5 text-blue-600 mr-2 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">AI Coach Feedback</h4>
                  <p className="text-gray-700">{feedback.coaching_feedback}</p>
                </div>
              </div>
            </div>

            {/* Strengths */}
            {feedback.strengths && (
              <div className="bg-green-50 rounded-lg p-4">
                <h4 className="font-semibold text-green-900 mb-2">Your Strengths:</h4>
                <p className="text-green-800">{feedback.strengths}</p>
              </div>
            )}

            {/* Areas for Improvement */}
            {feedback.improvement_areas && (
              <div className="bg-yellow-50 rounded-lg p-4">
                <h4 className="font-semibold text-yellow-900 mb-2">Areas to Improve:</h4>
                <p className="text-yellow-800">{feedback.improvement_areas}</p>
              </div>
            )}

            {/* Specific Suggestions */}
            {feedback.specific_suggestions && (
              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="font-semibold text-blue-900 mb-2">Try This Next Round:</h4>
                <p className="text-blue-800">{feedback.specific_suggestions}</p>
              </div>
            )}
          </div>
        )}

        {/* Continue Button */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={onContinue}
            className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
          >
            Continue to Round {debateNumber + 1}
            <ArrowRightIcon className="ml-2 h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  )
}