'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { 
  ArrowLeftIcon, 
  CheckCircleIcon, 
  XCircleIcon,
  ClockIcon,
  AcademicCapIcon
} from '@heroicons/react/24/outline'
import { studentApi } from '@/lib/studentApi'

interface FillInBlankSentence {
  id: string
  sentence_with_blank: string
  vocabulary_words: string[]
}

interface FillInBlankSession {
  fill_in_blank_attempt_id: string
  total_sentences: number
  passing_score: number
  current_sentence_index: number
  sentence: FillInBlankSentence | null
  is_complete: boolean
  needs_confirmation: boolean
  correct_answers: number
  score_percentage: number
}

interface SubmissionResult {
  valid: boolean
  errors?: Record<string, string>
  is_correct: boolean
  correct_answer: string
  correct_answers: number
  sentences_remaining: number
  is_complete: boolean
  passed?: boolean
  score_percentage: number
  needs_confirmation: boolean
  next_sentence?: FillInBlankSentence
  progress_percentage: number
}

export default function FillInBlankPracticePage() {
  const router = useRouter()
  const params = useParams()
  const assignmentId = params.id as string

  const [session, setSession] = useState<FillInBlankSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [selectedAnswer, setSelectedAnswer] = useState('')
  const [showFeedback, setShowFeedback] = useState(false)
  const [lastSubmissionResult, setLastSubmissionResult] = useState<SubmissionResult | null>(null)
  const [startTime, setStartTime] = useState<Date>(new Date())
  const [error, setError] = useState<string | null>(null)
  const [showConfirmation, setShowConfirmation] = useState(false)

  // Navigation protection
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (session && !session.is_complete) {
        const message = 'You have unsaved progress. Are you sure you want to leave?'
        e.returnValue = message
        return message
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [session])

  const initializeSession = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await studentApi.startFillInBlank(assignmentId)
      setSession(response)
      setStartTime(new Date())
      
      if (response.needs_confirmation) {
        setShowConfirmation(true)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start fill-in-the-blank activity')
      console.error('Failed to initialize fill-in-blank session:', err)
    } finally {
      setLoading(false)
    }
  }, [assignmentId])

  useEffect(() => {
    initializeSession()
  }, [initializeSession])

  const submitAnswer = async () => {
    if (!session || !selectedAnswer.trim() || submitting) return

    try {
      setSubmitting(true)
      const timeSpent = Math.floor((new Date().getTime() - startTime.getTime()) / 1000)
      
      const result = await studentApi.submitFillInBlankAnswer(
        session.fill_in_blank_attempt_id,
        {
          sentence_id: session.sentence!.id,
          student_answer: selectedAnswer.trim(),
          time_spent_seconds: timeSpent
        }
      )

      setLastSubmissionResult(result)
      setShowFeedback(true)
      
      if (result.needs_confirmation) {
        setShowConfirmation(true)
      }

      // Auto-advance after showing feedback
      setTimeout(() => {
        if (result.next_sentence) {
          setSession(prev => prev ? {
            ...prev,
            sentence: result.next_sentence!,
            current_sentence_index: prev.current_sentence_index + 1,
            correct_answers: result.correct_answers,
            score_percentage: result.score_percentage
          } : null)
          setSelectedAnswer('')
          setShowFeedback(false)
          setStartTime(new Date())
        } else if (result.is_complete) {
          setSession(prev => prev ? {
            ...prev,
            is_complete: true,
            needs_confirmation: result.needs_confirmation,
            correct_answers: result.correct_answers,
            score_percentage: result.score_percentage
          } : null)
        }
      }, 2000)

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit answer')
      console.error('Failed to submit answer:', err)
    } finally {
      setSubmitting(false)
    }
  }

  const confirmCompletion = async () => {
    if (!session) return

    try {
      await studentApi.confirmFillInBlankCompletion(session.fill_in_blank_attempt_id)
      router.push(`/student/vocabulary/${assignmentId}/practice`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to confirm completion')
      console.error('Failed to confirm completion:', err)
    }
  }

  const declineCompletion = async () => {
    if (!session) return

    try {
      await studentApi.declineFillInBlankCompletion(session.fill_in_blank_attempt_id)
      setShowConfirmation(false)
      // Allow retake
      initializeSession()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to decline completion')
      console.error('Failed to decline completion:', err)
    }
  }

  const goBack = () => {
    if (session && !session.is_complete) {
      const confirmLeave = window.confirm('You have unsaved progress. Are you sure you want to leave?')
      if (!confirmLeave) return
    }
    router.push(`/student/vocabulary/${assignmentId}/practice`)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading fill-in-the-blank activity...</p>
        </div>
      </div>
    )
  }

  if (error && !session) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <XCircleIcon className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Error</h1>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={goBack}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
          >
            Return to Practice
          </button>
        </div>
      </div>
    )
  }

  if (!session) {
    return null
  }

  const progressPercentage = (session.current_sentence_index / session.total_sentences) * 100
  const scorePercentage = session.score_percentage || 0

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center">
              <button
                onClick={goBack}
                className="flex items-center text-gray-600 hover:text-gray-900"
              >
                <ArrowLeftIcon className="h-5 w-5 mr-2" />
                Back to Practice
              </button>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center text-sm text-gray-600">
                <ClockIcon className="h-4 w-4 mr-1" />
                Question {session.current_sentence_index + 1} of {session.total_sentences}
              </div>
              <div className="flex items-center text-sm text-gray-600">
                <AcademicCapIcon className="h-4 w-4 mr-1" />
                Score: {session.correct_answers}/{session.total_sentences} ({scorePercentage.toFixed(0)}%)
              </div>
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progressPercentage}%` }}
            ></div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {session.is_complete && !showConfirmation ? (
          /* Completion Screen */
          <div className="text-center">
            <CheckCircleIcon className="h-16 w-16 text-green-500 mx-auto mb-4" />
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Fill-in-the-Blank Complete!</h1>
            <p className="text-lg text-gray-600 mb-4">
              You scored {session.correct_answers} out of {session.total_sentences} ({scorePercentage.toFixed(0)}%)
            </p>
            {scorePercentage >= session.passing_score ? (
              <p className="text-green-600 font-semibold">Congratulations! You passed!</p>
            ) : (
              <p className="text-red-600 font-semibold">
                You need {session.passing_score}% to pass. You can try again later.
              </p>
            )}
            <button
              onClick={goBack}
              className="mt-6 bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700"
            >
              Return to Practice
            </button>
          </div>
        ) : session.sentence ? (
          /* Main Practice Interface */
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="mb-8">
              <h1 className="text-2xl font-bold text-gray-900 mb-4">Fill in the Blank</h1>
              <p className="text-gray-600 mb-6">
                Select the correct vocabulary word to complete the sentence.
              </p>
              
              {/* Sentence Display */}
              <div className="bg-gray-50 rounded-lg p-6 mb-8">
                <p className="text-lg text-gray-900 leading-relaxed text-center">
                  {session.sentence.sentence_with_blank}
                </p>
              </div>

              {/* Answer Choices */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
                {session.sentence.vocabulary_words.map((word) => (
                  <button
                    key={word}
                    onClick={() => setSelectedAnswer(word)}
                    disabled={showFeedback || submitting}
                    className={`p-4 rounded-lg border-2 text-center transition-all ${
                      selectedAnswer === word
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    } ${
                      showFeedback || submitting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                    }`}
                  >
                    {word}
                  </button>
                ))}
              </div>

              {/* Feedback */}
              {showFeedback && lastSubmissionResult && (
                <div className={`rounded-lg p-4 mb-6 ${
                  lastSubmissionResult.is_correct ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                }`}>
                  <div className="flex items-center">
                    {lastSubmissionResult.is_correct ? (
                      <CheckCircleIcon className="h-6 w-6 text-green-500 mr-2" />
                    ) : (
                      <XCircleIcon className="h-6 w-6 text-red-500 mr-2" />
                    )}
                    <div>
                      <p className={`font-semibold ${
                        lastSubmissionResult.is_correct ? 'text-green-800' : 'text-red-800'
                      }`}>
                        {lastSubmissionResult.is_correct ? 'Correct!' : 'Incorrect'}
                      </p>
                      {!lastSubmissionResult.is_correct && (
                        <p className="text-red-700 text-sm">
                          The correct answer is: <span className="font-semibold">{lastSubmissionResult.correct_answer}</span>
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Submit Button */}
              <div className="flex justify-center">
                <button
                  onClick={submitAnswer}
                  disabled={!selectedAnswer || submitting || showFeedback}
                  className={`px-8 py-3 rounded-md font-semibold ${
                    !selectedAnswer || submitting || showFeedback
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  }`}
                >
                  {submitting ? 'Submitting...' : 'Submit Answer'}
                </button>
              </div>
            </div>
          </div>
        ) : null}

        {/* Confirmation Modal */}
        {showConfirmation && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-md w-full p-6">
              <div className="text-center">
                <CheckCircleIcon className="h-12 w-12 text-green-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Assignment Complete!</h3>
                <p className="text-gray-600 mb-4">
                  You scored {scorePercentage.toFixed(0)}% and passed the assignment.
                  Would you like to submit your completion?
                </p>
                <div className="flex space-x-3">
                  <button
                    onClick={confirmCompletion}
                    className="flex-1 bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700"
                  >
                    Yes, Complete
                  </button>
                  <button
                    onClick={declineCompletion}
                    className="flex-1 bg-gray-300 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-400"
                  >
                    Retake
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <XCircleIcon className="h-5 w-5 text-red-400 mr-2" />
              <p className="text-red-800">{error}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}