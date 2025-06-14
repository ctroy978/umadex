'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { studentApi } from '@/lib/studentApi'
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowRightIcon,
  ExclamationCircleIcon,
  PuzzlePieceIcon,
  ChartBarIcon,
  ClockIcon,
  StarIcon,
  LightBulbIcon
} from '@heroicons/react/24/outline'

interface PuzzleOption {
  text: string
  correct: boolean
}

interface PuzzleData {
  scrambled_letters?: string
  hint?: string
  letter_count?: number
  clue?: string
  first_letter?: string
  sentence?: string
  word_length?: number
  context_hint?: string
  target_word?: string
  options?: PuzzleOption[]
}

interface Puzzle {
  id: string
  puzzle_type: 'scrambled' | 'crossword_clue' | 'fill_blank' | 'word_match'
  puzzle_data: PuzzleData
  puzzle_order: number
  word?: string
}

interface PuzzleSession {
  puzzle_attempt_id: string
  total_puzzles: number
  passing_score: number
  max_possible_score: number
  current_puzzle_index: number
  puzzle: Puzzle | null
  is_complete?: boolean
  needs_confirmation?: boolean
  current_score?: number
  percentage_score?: number
}

interface PuzzleEvaluation {
  score: number
  accuracy: string
  feedback: string
  areas_checked: string[]
}

interface PuzzleSubmissionResult {
  valid: boolean
  evaluation?: PuzzleEvaluation
  current_score: number
  puzzles_remaining: number
  is_complete: boolean
  passed?: boolean
  percentage_score?: number
  needs_confirmation: boolean
  next_puzzle?: Puzzle
  progress_percentage: number
  errors?: any
}

export default function PuzzlePathPage() {
  const params = useParams()
  const router = useRouter()
  const vocabularyId = params.id as string

  const [session, setSession] = useState<PuzzleSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentAnswer, setCurrentAnswer] = useState('')
  const [selectedOption, setSelectedOption] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<PuzzleSubmissionResult | null>(null)
  const [startTime, setStartTime] = useState<Date>(new Date())
  const [showCompletionDialog, setShowCompletionDialog] = useState(false)
  const [confirmingCompletion, setConfirmingCompletion] = useState(false)

  useEffect(() => {
    initializeSession()
  }, [vocabularyId])

  // Navigation protection
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (session && !showCompletionDialog && !lastResult?.is_complete) {
        const message = 'You have an assignment in progress. If you leave now, your progress will be lost.'
        e.preventDefault()
        e.returnValue = message
        return message
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [session, showCompletionDialog, lastResult?.is_complete])

  const initializeSession = async () => {
    try {
      setLoading(true)
      setError(null)
      const sessionData = await studentApi.startPuzzlePath(vocabularyId)
      setSession(sessionData)
      
      // Check if this is a pending confirmation attempt
      if (sessionData.is_complete && sessionData.needs_confirmation) {
        setLastResult({
          valid: true,
          current_score: sessionData.current_score,
          puzzles_remaining: 0,
          is_complete: true,
          passed: sessionData.percentage_score >= 70,
          percentage_score: sessionData.percentage_score,
          needs_confirmation: true,
          progress_percentage: 100
        })
        setShowCompletionDialog(true)
      } else {
        setStartTime(new Date())
      }
    } catch (err: any) {
      console.error('Failed to start puzzle path:', err)
      setError('Failed to start puzzle path. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const submitAnswer = async () => {
    if (!session || !session.puzzle) return
    
    let answer = currentAnswer.trim()
    if (session.puzzle.puzzle_type === 'word_match' && selectedOption) {
      answer = selectedOption
    }

    if (!answer) {
      setError('Please provide an answer.')
      return
    }

    try {
      setSubmitting(true)
      setError(null)

      const timeSpent = Math.floor((new Date().getTime() - startTime.getTime()) / 1000)
      
      const result = await studentApi.submitPuzzleAnswer(session.puzzle_attempt_id, {
        puzzle_id: session.puzzle.id,
        student_answer: answer,
        time_spent_seconds: timeSpent
      })

      setLastResult(result)
      

      if (result.is_complete && result.needs_confirmation) {
        setShowCompletionDialog(true)
      } else if (result.is_complete) {
        // Puzzle path complete - show final result
      } else {
        // Not complete, fetch updated session to get next puzzle
        try {
          const updatedSession = await studentApi.getPuzzlePathProgress(session.puzzle_attempt_id)
          
          // Map the progress response to match the session structure
          const mappedSession = {
            ...updatedSession,
            puzzle: updatedSession.current_puzzle
          }
          
          setSession(mappedSession)
          setCurrentAnswer('')
          setSelectedOption(null)
          setStartTime(new Date())
        } catch (progressErr) {
          console.error('Failed to get puzzle progress:', progressErr)
          // Fallback: reload the entire session
          await initializeSession()
        }
      }
    } catch (err: any) {
      console.error('Failed to submit answer:', err)
      setError('Failed to submit answer. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const getPuzzleTypeIcon = (type: string) => {
    switch (type) {
      case 'scrambled':
        return '🔤'
      case 'crossword_clue':
        return '🧩'
      case 'fill_blank':
        return '📝'
      case 'word_match':
        return '🎯'
      default:
        return '🧩'
    }
  }

  const getPuzzleTypeTitle = (type: string) => {
    switch (type) {
      case 'scrambled':
        return 'Unscramble the Word'
      case 'crossword_clue':
        return 'Crossword Clue'
      case 'fill_blank':
        return 'Fill in the Blank'
      case 'word_match':
        return 'Match the Definition'
      default:
        return 'Word Puzzle'
    }
  }

  const renderPuzzleContent = () => {
    if (!session?.puzzle) return null

    const { puzzle_type, puzzle_data } = session.puzzle

    switch (puzzle_type) {
      case 'scrambled':
        return (
          <div className="space-y-4">
            <div className="text-center">
              <div className="text-2xl font-mono tracking-widest bg-gray-100 p-4 rounded-lg">
                {puzzle_data.scrambled_letters}
              </div>
              <p className="text-sm text-gray-600 mt-2">
                Unscramble these letters to form a {puzzle_data.letter_count}-letter word
              </p>
            </div>
            {puzzle_data.hint && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <div className="flex items-center">
                  <LightBulbIcon className="h-5 w-5 text-blue-600 mr-2" />
                  <span className="text-blue-800 font-medium">Hint:</span>
                </div>
                <p className="text-blue-700 mt-1">{puzzle_data.hint}</p>
              </div>
            )}
            <input
              type="text"
              value={currentAnswer}
              onChange={(e) => setCurrentAnswer(e.target.value)}
              placeholder="Enter the unscrambled word"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              maxLength={puzzle_data.letter_count}
            />
          </div>
        )

      case 'crossword_clue':
        return (
          <div className="space-y-4">
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <h4 className="font-medium text-purple-900 mb-2">Clue:</h4>
              <p className="text-lg text-purple-800">{puzzle_data.clue}</p>
            </div>
            <div className="text-center text-sm text-gray-600">
              {puzzle_data.letter_count} letters, starts with "{puzzle_data.first_letter?.toUpperCase()}"
            </div>
            <input
              type="text"
              value={currentAnswer}
              onChange={(e) => setCurrentAnswer(e.target.value)}
              placeholder="Enter your answer"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              maxLength={puzzle_data.letter_count}
            />
          </div>
        )

      case 'fill_blank':
        return (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h4 className="font-medium text-green-900 mb-2">Complete the sentence:</h4>
              <p className="text-lg text-green-800">
                {puzzle_data.sentence?.replace('___', '______')}
              </p>
            </div>
            {puzzle_data.context_hint && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <div className="flex items-center">
                  <LightBulbIcon className="h-5 w-5 text-yellow-600 mr-2" />
                  <span className="text-yellow-800 font-medium">Context Hint:</span>
                </div>
                <p className="text-yellow-700 mt-1">{puzzle_data.context_hint}</p>
              </div>
            )}
            <input
              type="text"
              value={currentAnswer}
              onChange={(e) => setCurrentAnswer(e.target.value)}
              placeholder="Enter the missing word"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              maxLength={puzzle_data.word_length}
            />
          </div>
        )

      case 'word_match':
        return (
          <div className="space-y-4">
            <div className="text-center">
              <h4 className="text-xl font-semibold text-gray-900 mb-2">
                What does "{puzzle_data.target_word}" mean?
              </h4>
              <p className="text-gray-600">Select the best definition:</p>
            </div>
            <div className="space-y-2">
              {puzzle_data.options?.map((option, index) => (
                <button
                  key={index}
                  onClick={() => setSelectedOption(option.text)}
                  className={`w-full text-left px-4 py-3 border rounded-lg transition-colors ${
                    selectedOption === option.text
                      ? 'border-primary-500 bg-primary-50 text-primary-900'
                      : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
                  }`}
                >
                  {option.text}
                </button>
              ))}
            </div>
          </div>
        )

      default:
        return <p>Unknown puzzle type</p>
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading puzzle path...</p>
        </div>
      </div>
    )
  }

  if (error && !session) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <ExclamationCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Error</h2>
          <p className="text-gray-600 mb-6">{error}</p>
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

  const handleConfirmCompletion = async () => {
    if (!session) return
    
    setConfirmingCompletion(true)
    try {
      const result = await studentApi.confirmPuzzleCompletion(session.puzzle_attempt_id)
      router.push(`/student/vocabulary/${vocabularyId}/practice?completed=puzzle-path`)
    } catch (err: any) {
      console.error('Failed to confirm completion:', err)
      
      // Show more specific error message
      const errorMessage = err.response?.data?.message || err.message || 'Unknown error occurred'
      alert(`Failed to complete assignment: ${errorMessage}. Please try again or contact support.`)
    } finally {
      setConfirmingCompletion(false)
    }
  }

  const handleDeclineCompletion = async () => {
    if (!session) return
    
    setConfirmingCompletion(true)
    try {
      const result = await studentApi.declinePuzzleCompletion(session.puzzle_attempt_id)
      router.push(`/student/vocabulary/${vocabularyId}/practice`)
    } catch (err: any) {
      console.error('Failed to decline completion:', err)
      alert('Failed to process request. Please try again.')
    } finally {
      setConfirmingCompletion(false)
    }
  }

  if (lastResult?.is_complete && !lastResult.needs_confirmation) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-md mx-auto text-center">
          <div className={`p-4 rounded-full mx-auto mb-4 w-16 h-16 flex items-center justify-center ${
            lastResult.passed ? 'bg-green-100' : 'bg-red-100'
          }`}>
            {lastResult.passed ? (
              <CheckCircleIcon className="h-8 w-8 text-green-600" />
            ) : (
              <XCircleIcon className="h-8 w-8 text-red-600" />
            )}
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Puzzle Path {lastResult.passed ? 'Complete!' : 'Finished'}
          </h2>
          <p className="text-gray-600 mb-4">
            You scored {lastResult.current_score} out of {session?.max_possible_score} points
            ({Math.round(lastResult.progress_percentage)}%)
          </p>
          <div className="space-y-3">
            <button
              onClick={() => router.push(`/student/vocabulary/${vocabularyId}/practice`)}
              className="w-full px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Back to Practice Activities
            </button>
          </div>
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
              <div className="flex items-center">
                <div className="p-2 bg-purple-100 rounded-lg mr-3">
                  <PuzzlePieceIcon className="h-6 w-6 text-purple-600" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">
                    Word Puzzle Path
                  </h1>
                  <p className="text-sm text-gray-500">
                    Puzzle {(session?.current_puzzle_index || 0) + 1} of {session?.total_puzzles || 0}
                  </p>
                </div>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium text-gray-900">
                Score: {lastResult?.current_score || 0} / {session?.max_possible_score || 0}
              </p>
              <p className="text-xs text-gray-500">
                Need {session?.passing_score || 0} to pass
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      {session && (
        <div className="bg-white border-b">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                style={{
                  width: `${((session.current_puzzle_index) / session.total_puzzles) * 100}%`
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {session?.puzzle && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            {/* Puzzle Header */}
            <div className="text-center mb-6">
              <div className="text-4xl mb-2">
                {getPuzzleTypeIcon(session.puzzle.puzzle_type)}
              </div>
              <h2 className="text-2xl font-bold text-gray-900">
                {getPuzzleTypeTitle(session.puzzle.puzzle_type)}
              </h2>
            </div>

            {/* Puzzle Content */}
            <div className="mb-6">
              {renderPuzzleContent()}
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-800">{error}</p>
              </div>
            )}

            {/* Last Result */}
            {lastResult?.evaluation && (
              <div className={`mb-4 p-4 rounded-lg border ${
                lastResult.evaluation.score >= 3 
                  ? 'bg-green-50 border-green-200' 
                  : 'bg-yellow-50 border-yellow-200'
              }`}>
                <div className="flex items-center mb-2">
                  <div className="flex items-center">
                    {[1, 2, 3, 4].map((star) => (
                      <StarIcon
                        key={star}
                        className={`h-5 w-5 ${
                          star <= lastResult.evaluation!.score
                            ? 'text-yellow-400 fill-current'
                            : 'text-gray-300'
                        }`}
                      />
                    ))}
                  </div>
                  <span className="ml-2 text-sm font-medium">
                    {lastResult.evaluation.accuracy}
                  </span>
                </div>
                <p className="text-sm text-gray-700">{lastResult.evaluation.feedback}</p>
              </div>
            )}

            {/* Submit Button */}
            <button
              onClick={submitAnswer}
              disabled={submitting || (!currentAnswer && !selectedOption)}
              className={`w-full px-6 py-3 rounded-lg font-medium transition-colors ${
                submitting || (!currentAnswer && !selectedOption)
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-purple-600 text-white hover:bg-purple-700'
              }`}
            >
              {submitting ? 'Submitting...' : 'Submit Answer'}
            </button>
          </div>
        )}
      </main>

      {/* Completion Confirmation Dialog */}
      {showCompletionDialog && lastResult && lastResult.percentage_score !== undefined && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full shadow-xl">
            <div className="text-center mb-6">
              <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
                lastResult.percentage_score >= 70 ? 'bg-green-100' : 'bg-amber-100'
              }`}>
                {lastResult.percentage_score >= 70 ? (
                  <CheckCircleIcon className="h-8 w-8 text-green-600" />
                ) : (
                  <ExclamationCircleIcon className="h-8 w-8 text-amber-600" />
                )}
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-2">
                Puzzle Path Complete!
              </h3>
              <p className="text-lg text-gray-700 mb-4">
                You scored <span className="font-bold text-primary-600">{Math.round(lastResult.percentage_score || 0)}%</span>
              </p>
              {lastResult.percentage_score >= 70 ? (
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

            {lastResult.percentage_score >= 70 ? (
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