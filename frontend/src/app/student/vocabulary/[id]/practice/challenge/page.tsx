'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { studentApi } from '@/lib/studentApi'
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  XCircleIcon,
  LightBulbIcon,
  ClockIcon,
  ChartBarIcon,
  ArrowRightIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline'

interface Question {
  id: string
  question_type: string
  difficulty_level: string
  question_text: string
  question_number: number
}

interface GameSession {
  game_attempt_id: string
  total_questions: number
  passing_score: number
  max_possible_score: number
  current_question: number
  question: Question | null
}

export default function VocabularyChallengePage() {
  const params = useParams()
  const router = useRouter()
  const vocabularyId = params.id as string

  const [gameSession, setGameSession] = useState<GameSession | null>(null)
  const [currentAnswer, setCurrentAnswer] = useState('')
  const [currentScore, setCurrentScore] = useState(0)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedback, setFeedback] = useState<{
    correct: boolean
    points_earned: number
    correct_answer?: string
    is_complete?: boolean
    passed?: boolean
    percentage_score?: number
    next_question?: Question
  } | null>(null)
  const [isResuming, setIsResuming] = useState(false)
  const [timeSpent, setTimeSpent] = useState(0)
  const startTimeRef = useRef<number>(Date.now())
  const [showCompletionDialog, setShowCompletionDialog] = useState(false)
  const [confirmingCompletion, setConfirmingCompletion] = useState(false)

  useEffect(() => {
    startNewGame()
  }, [vocabularyId])

  useEffect(() => {
    // Reset timer when new question starts
    if (!showFeedback) {
      startTimeRef.current = Date.now()
    }
  }, [showFeedback])

  useEffect(() => {
    // Add navigation warning when game is in progress
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (gameSession && !showCompletionDialog && !feedback?.is_complete) {
        e.preventDefault()
        e.returnValue = 'You have an assignment in progress. If you leave now, your progress will be lost.'
        return 'You have an assignment in progress. If you leave now, your progress will be lost.'
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [gameSession, showCompletionDialog, feedback?.is_complete])

  const startNewGame = async () => {
    try {
      setLoading(true)
      const session = await studentApi.startVocabularyChallenge(vocabularyId)
      setGameSession(session)
      
      // Handle session resumption
      if (session.is_resuming) {
        setIsResuming(true)
        setCurrentScore(session.current_score || 0)
        setTimeout(() => setIsResuming(false), 3000) // Hide message after 3 seconds
      } else {
        setCurrentScore(session.current_score || 0)
      }
    } catch (err: any) {
      console.error('Failed to start game:', err)
      
      // Check if it's a completion error
      if (err.response?.data?.detail?.includes('already been completed')) {
        alert('This activity has already been completed and cannot be retaken.')
      } else {
        alert('Failed to start game. Please try again.')
      }
      router.back()
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitAnswer = async () => {
    if (!gameSession || !gameSession.question || !currentAnswer.trim()) return

    setSubmitting(true)
    const timeSpentSeconds = Math.floor((Date.now() - startTimeRef.current) / 1000)

    try {
      const result = await studentApi.submitVocabularyAnswer(
        gameSession.game_attempt_id,
        {
          question_id: gameSession.question.id,
          student_answer: currentAnswer.trim(),
          attempt_number: 1,  // Always 1 - no retries
          time_spent_seconds: timeSpentSeconds
        }
      )

      setFeedback(result)
      setShowFeedback(true)
      setCurrentScore(result.current_score)
      
      // Show completion dialog if needs confirmation
      if (result.is_complete && result.needs_confirmation) {
        setShowCompletionDialog(true)
      }
    } catch (err: any) {
      console.error('Failed to submit answer:', err)
      alert('Failed to submit answer. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleNextQuestion = async () => {
    if (!gameSession) return

    setShowFeedback(false)
    setFeedback(null)
    setCurrentAnswer('')

    // If there's a next question in the feedback, use it
    if (feedback?.next_question) {
      setGameSession({
        ...gameSession,
        current_question: gameSession.current_question + 1,
        question: feedback.next_question
      })
    } else if (feedback?.is_complete) {
      // Game is complete - don't redirect immediately, let user see the completion screen
      // The redirect will happen when user clicks the completion button
      return
    } else {
      // Fetch next question
      try {
        const nextData = await studentApi.getNextVocabularyQuestion(gameSession.game_attempt_id)
        if (nextData.question) {
          setGameSession({
            ...gameSession,
            current_question: nextData.current_question,
            question: nextData.question
          })
        } else {
          // No more questions
          router.push(`/student/vocabulary/${vocabularyId}/practice`)
        }
      } catch (err) {
        console.error('Failed to get next question:', err)
      }
    }
  }

  const handleConfirmCompletion = async () => {
    if (!gameSession) return
    
    setConfirmingCompletion(true)
    try {
      await studentApi.confirmChallengeCompletion(gameSession.game_attempt_id)
      router.push(`/student/vocabulary/${vocabularyId}/practice?completed=challenge`)
    } catch (err: any) {
      console.error('Failed to confirm completion:', err)
      alert('Failed to complete assignment. Please try again.')
      setConfirmingCompletion(false)
    }
  }

  const handleDeclineCompletion = async () => {
    if (!gameSession) return
    
    setConfirmingCompletion(true)
    try {
      await studentApi.declineChallengeCompletion(gameSession.game_attempt_id)
      router.push(`/student/vocabulary/${vocabularyId}/practice?retake=challenge`)
    } catch (err: any) {
      console.error('Failed to decline completion:', err)
      alert('Failed to process request. Please try again.')
      setConfirmingCompletion(false)
    }
  }

  const getQuestionTypeIcon = (type: string) => {
    switch (type) {
      case 'fill_in_blank': return '✏️'
      default: return '❓'
    }
  }

  const getDifficultyColor = (level: string) => {
    switch (level) {
      case 'easy': return 'text-green-600 bg-green-100'
      case 'medium': return 'text-yellow-600 bg-yellow-100'
      case 'hard': return 'text-red-600 bg-red-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Starting vocabulary challenge...</p>
        </div>
      </div>
    )
  }

  if (!gameSession || !gameSession.question) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <ExclamationCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-gray-600">Unable to load game. Please try again.</p>
          <button
            onClick={() => router.back()}
            className="mt-4 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
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
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4 flex items-center justify-between">
            <div className="flex items-center">
              <button
                onClick={() => router.back()}
                className="mr-4 text-gray-500 hover:text-gray-700"
              >
                <ArrowLeftIcon className="h-5 w-5" />
              </button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  Fill in the Blank
                </h1>
                <p className="text-sm text-gray-500">
                  Question {gameSession.current_question} of {gameSession.total_questions}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm">
                <span className="text-gray-500">Score: </span>
                <span className="font-semibold text-primary-600">
                  {currentScore} / {gameSession.max_possible_score}
                </span>
              </div>
              <div className="text-sm">
                <span className="text-gray-500">Pass: </span>
                <span className="font-semibold text-green-600">
                  {gameSession.passing_score} pts
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-primary-600 h-2 rounded-full transition-all duration-300"
              style={{
                width: `${((gameSession.current_question - 1) / gameSession.total_questions) * 100}%`
              }}
            />
          </div>
        </div>
      </div>

      {/* Resuming Session Indicator */}
      {isResuming && (
        <div className="bg-blue-50 border-b border-blue-200">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
            <div className="flex items-center">
              <ClockIcon className="h-5 w-5 text-blue-600 mr-2" />
              <p className="text-blue-800 text-sm font-medium">
                Continuing previous session...
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Question Card */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <span className="text-3xl">{getQuestionTypeIcon(gameSession.question.question_type)}</span>
              <div>
                <h2 className="text-lg font-medium text-gray-900 capitalize">
                  Fill in the Blank
                </h2>
                <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${getDifficultyColor(gameSession.question.difficulty_level)}`}>
                  {gameSession.question.difficulty_level}
                </span>
              </div>
            </div>
          </div>

          {/* Question Text */}
          <div className="mb-8">
            <p className="text-lg text-gray-800 leading-relaxed whitespace-pre-line">
              {gameSession.question.question_text}
            </p>
          </div>

          {/* Answer Input or Feedback */}
          {!showFeedback ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Your Answer:
              </label>
              <input
                type="text"
                value={currentAnswer}
                onChange={(e) => setCurrentAnswer(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSubmitAnswer()}
                placeholder="Type your answer here..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                autoFocus
                disabled={submitting}
              />
              <button
                onClick={handleSubmitAnswer}
                disabled={!currentAnswer.trim() || submitting}
                className={`mt-4 w-full px-6 py-3 rounded-lg font-medium transition-colors ${
                  !currentAnswer.trim() || submitting
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-primary-600 text-white hover:bg-primary-700'
                }`}
              >
                {submitting ? 'Checking...' : 'Submit Answer'}
              </button>
            </div>
          ) : (
            <div>
              {/* Feedback Display */}
              <div className={`p-6 rounded-lg mb-4 ${
                feedback?.correct ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
              }`}>
                <div className="flex items-start space-x-3">
                  {feedback?.correct ? (
                    <CheckCircleIcon className="h-6 w-6 text-green-600 mt-0.5" />
                  ) : (
                    <XCircleIcon className="h-6 w-6 text-red-600 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <h3 className={`font-semibold mb-2 ${
                      feedback?.correct ? 'text-green-800' : 'text-red-800'
                    }`}>
                      {feedback?.correct ? 'Correct!' : 'Incorrect'}
                    </h3>
                    <p className="text-gray-700">
                      You earned <span className="font-semibold">{feedback?.points_earned} points</span>
                    </p>
                    {feedback?.correct_answer && (
                      <p className="mt-2 text-gray-700">
                        The correct answer was: <span className="font-semibold">{feedback.correct_answer}</span>
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <button
                onClick={() => {
                  if (feedback?.is_complete) {
                    // Show completion dialog instead of redirecting
                    setShowCompletionDialog(true)
                  } else {
                    handleNextQuestion()
                  }
                }}
                className="w-full px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 flex items-center justify-center"
              >
                {feedback?.is_complete ? (
                  feedback.passed ? 'Continue to Practice Activities' : 'Try Again'
                ) : (
                  <>
                    Next Question
                    <ArrowRightIcon className="h-5 w-5 ml-2" />
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {/* Score Summary (shown only when dialog is not shown) */}
        {feedback?.is_complete && !showCompletionDialog && (
          <div className="bg-white rounded-lg shadow-lg border-2 border-primary-200 p-8">
            <div className="text-center mb-6">
              <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
                feedback.passed ? 'bg-green-100' : 'bg-red-100'
              }`}>
                {feedback.passed ? (
                  <CheckCircleIcon className="h-8 w-8 text-green-600" />
                ) : (
                  <XCircleIcon className="h-8 w-8 text-red-600" />
                )}
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                {feedback.passed ? 'Congratulations!' : 'Game Complete'}
              </h2>
              <p className={`text-lg font-semibold ${feedback.passed ? 'text-green-600' : 'text-red-600'}`}>
                {feedback.passed ? 'You PASSED the Fill in the Blank activity!' : 'You did not pass this time'}
              </p>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-6 mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 text-center">Your Results</h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-700 font-medium">Final Score:</span>
                  <span className="text-2xl font-bold text-primary-600">{currentScore} points</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-700 font-medium">Passing Score:</span>
                  <span className="text-lg font-semibold text-gray-900">{gameSession.passing_score} points</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-700 font-medium">Total Questions:</span>
                  <span className="text-lg font-semibold text-gray-900">{gameSession.total_questions}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-700 font-medium">Percentage:</span>
                  <span className="text-lg font-semibold text-gray-900">
                    {Math.round((currentScore / gameSession.max_possible_score) * 100)}%
                  </span>
                </div>
                <div className="border-t pt-4">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-700 font-medium">Result:</span>
                    <span className={`text-xl font-bold px-4 py-2 rounded-full ${
                      feedback.passed 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {feedback.passed ? 'PASSED' : 'FAILED'}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {feedback.passed && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                <p className="text-green-800 text-center">
                  <strong>Great job!</strong> You've completed 1 of 4 practice activities. 
                  Complete 2 more to unlock the final vocabulary test.
                </p>
              </div>
            )}

            {!feedback.passed && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
                <p className="text-amber-800 text-center">
                  <strong>Keep trying!</strong> You can retake this challenge as many times as needed. 
                  Review the vocabulary words and try again when you're ready.
                </p>
              </div>
            )}
          </div>
        )}

      </main>

      {/* Completion Confirmation Dialog */}
      {showCompletionDialog && feedback && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full shadow-xl">
            <div className="text-center mb-6">
              <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
                feedback.percentage_score >= 70 ? 'bg-green-100' : 'bg-amber-100'
              }`}>
                {feedback.percentage_score >= 70 ? (
                  <CheckCircleIcon className="h-8 w-8 text-green-600" />
                ) : (
                  <ExclamationCircleIcon className="h-8 w-8 text-amber-600" />
                )}
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-2">
                Fill in the Blank Complete!
              </h3>
              <p className="text-lg text-gray-700 mb-4">
                You scored <span className="font-bold text-primary-600">{Math.round(feedback.percentage_score)}%</span>
              </p>
              {feedback.percentage_score >= 70 ? (
                <p className="text-green-700">
                  Congratulations! You scored 70% or higher.
                  <br />
                  <span className="font-semibold">Assignment completed successfully!</span>
                </p>
              ) : (
                <p className="text-amber-700">
                  You scored below 70%.
                  <br />
                  <span className="font-semibold">You need 70% or higher to complete this assignment.</span>
                </p>
              )}
            </div>

            {feedback.percentage_score >= 70 ? (
              <button
                onClick={handleConfirmCompletion}
                disabled={confirmingCompletion}
                className="w-full px-6 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {confirmingCompletion ? 'Completing...' : 'Complete Assignment'}
              </button>
            ) : (
              <button
                onClick={handleDeclineCompletion}
                disabled={confirmingCompletion}
                className="w-full px-6 py-3 bg-amber-600 text-white rounded-lg font-medium hover:bg-amber-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {confirmingCompletion ? 'Processing...' : 'Retake Assignment Later'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}