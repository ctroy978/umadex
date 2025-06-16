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
  ExclamationCircleIcon,
  EyeIcon
} from '@heroicons/react/24/outline'

interface StoryPrompt {
  id: string
  prompt_text: string
  required_words: string[]
  setting: string
  tone: string
  max_score: number
  prompt_order: number
}

interface StorySession {
  story_attempt_id: string
  total_prompts: number
  passing_score: number
  max_possible_score: number
  current_prompt: number
  prompt: StoryPrompt | null
}

interface Evaluation {
  total_score: number
  breakdown: {
    vocabulary_usage: {
      score: number
      max: number
      feedback: string
    }
    story_coherence: {
      score: number
      max: number
      feedback: string
    }
    tone_adherence: {
      score: number
      max: number
      feedback: string
    }
    creativity: {
      score: number
      max: number
      feedback: string
    }
  }
  overall_feedback: string
  revision_suggestion: string
}

const MAX_WORDS = 500

export default function StoryBuilderPage() {
  const params = useParams()
  const router = useRouter()
  const vocabularyId = params.id as string

  const [storySession, setStorySession] = useState<StorySession | null>(null)
  const [currentStory, setCurrentStory] = useState('')
  const [currentScore, setCurrentScore] = useState(0)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [showEvaluation, setShowEvaluation] = useState(false)
  const [evaluation, setEvaluation] = useState<{
    evaluation: Evaluation
    current_score: number
    prompts_remaining: number
    is_complete: boolean
    passed?: boolean
    percentage_score?: number
    needs_confirmation: boolean
    next_prompt?: StoryPrompt
    can_revise: boolean
  } | null>(null)
  const [showCompletionDialog, setShowCompletionDialog] = useState(false)
  const [confirmingCompletion, setConfirmingCompletion] = useState(false)
  const [timeSpent, setTimeSpent] = useState(0)
  const startTimeRef = useRef<number>(Date.now())
  const [wordCount, setWordCount] = useState(0)

  useEffect(() => {
    startNewChallenge()
  }, [vocabularyId])

  useEffect(() => {
    // Reset timer when new prompt starts
    if (!showEvaluation) {
      startTimeRef.current = Date.now()
    }
  }, [showEvaluation])

  // Navigation protection
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      // Only show warning if there's an active session and not showing completion dialog
      if (storySession && !showCompletionDialog && !evaluation?.is_complete) {
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
  }, [storySession, showCompletionDialog, evaluation?.is_complete])

  useEffect(() => {
    // Update word count
    setWordCount(currentStory.trim().split(/\s+/).filter(word => word.length > 0).length)
  }, [currentStory])

  const startNewChallenge = async () => {
    try {
      setLoading(true)
      const session = await studentApi.startStoryBuilder(vocabularyId)
      setStorySession(session)
      setCurrentScore(0)
    } catch (err: any) {
      console.error('Failed to start story builder:', err)
      
      // Check if it's a completion error
      if (err.response?.data?.detail?.includes('already been completed')) {
        alert('This activity has already been completed and cannot be retaken.')
      } else {
        alert('Failed to start story builder. Please try again.')
      }
      router.back()
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitStory = async () => {
    if (!storySession || !storySession.prompt || !currentStory.trim()) return

    setSubmitting(true)
    const timeSpentSeconds = Math.floor((Date.now() - startTimeRef.current) / 1000)

    try {
      const result = await studentApi.submitStory(
        storySession.story_attempt_id,
        {
          prompt_id: storySession.prompt.id,
          story_text: currentStory.trim(),
          attempt_number: 1
        }
      )

      setEvaluation(result)
      setShowEvaluation(true)
      setCurrentScore(result.current_score)
      
      // Show completion dialog if assignment is complete
      if (result.is_complete && result.needs_confirmation) {
        setShowCompletionDialog(true)
      }

    } catch (err: any) {
      console.error('Failed to submit story:', err)
      alert('Failed to submit story. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleNextPrompt = async () => {
    if (!storySession) return

    setShowEvaluation(false)
    setEvaluation(null)
    setCurrentStory('')

    // If there's a next prompt in the evaluation, use it
    if (evaluation?.next_prompt) {
      setStorySession({
        ...storySession,
        current_prompt: storySession.current_prompt + 1,
        prompt: evaluation.next_prompt
      })
    } else if (evaluation?.is_complete) {
      // Challenge is complete - don't redirect immediately, let user see the completion screen
      return
    } else {
      // Fetch next prompt
      try {
        const nextData = await studentApi.getNextStoryPrompt(storySession.story_attempt_id)
        if (nextData.prompt) {
          setStorySession({
            ...storySession,
            current_prompt: nextData.current_prompt,
            prompt: nextData.prompt
          })
        } else {
          // No more prompts
          router.push(`/student/vocabulary/${vocabularyId}/practice`)
        }
      } catch (err) {
        console.error('Failed to get next prompt:', err)
      }
    }
  }


  const handleConfirmCompletion = async () => {
    if (!storySession) return
    
    setConfirmingCompletion(true)
    try {
      const result = await studentApi.confirmStoryCompletion(storySession.story_attempt_id)
      // Redirect to practice page with success message
      router.push(`/student/vocabulary/${vocabularyId}/practice?completed=story-builder`)
    } catch (err: any) {
      console.error('Failed to confirm completion:', err)
      alert('Failed to complete assignment. Please try again.')
    } finally {
      setConfirmingCompletion(false)
    }
  }

  const handleDeclineCompletion = async () => {
    if (!storySession) return
    
    setConfirmingCompletion(true)
    try {
      const result = await studentApi.declineStoryCompletion(storySession.story_attempt_id)
      // Redirect to practice page
      router.push(`/student/vocabulary/${vocabularyId}/practice`)
    } catch (err: any) {
      console.error('Failed to decline completion:', err)
      alert('Failed to process request. Please try again.')
    } finally {
      setConfirmingCompletion(false)
    }
  }

  const checkWordUsage = (word: string) => {
    return currentStory.toLowerCase().includes(word.toLowerCase())
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Starting story builder challenge...</p>
        </div>
      </div>
    )
  }

  if (!storySession || !storySession.prompt) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <ExclamationCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-gray-600">Unable to load story challenge. Please try again.</p>
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
                  Story Builder Challenge
                </h1>
                <p className="text-sm text-gray-500">
                  Story {storySession.current_prompt} of {storySession.total_prompts}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm">
                <span className="text-gray-500">Score: </span>
                <span className="font-semibold text-primary-600">
                  {currentScore} / {storySession.max_possible_score}
                </span>
              </div>
              <div className="text-sm">
                <span className="text-gray-500">Pass: </span>
                <span className="font-semibold text-green-600">
                  {storySession.passing_score} pts
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
                width: `${((storySession.current_prompt - 1) / storySession.total_prompts) * 100}%`
              }}
            />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Prompt Card */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <span className="text-3xl">📝</span>
              <div>
                <h2 className="text-lg font-medium text-gray-900">
                  Creative Writing Prompt
                </h2>
                <span className="inline-block px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {storySession.prompt.tone} tone • {storySession.prompt.setting}
                </span>
              </div>
            </div>
            {!showEvaluation && (
              <div className="text-sm text-gray-600">
                Story 1 of 2
              </div>
            )}
          </div>

          {/* Prompt Text */}
          <div className="mb-6">
            <p className="text-lg text-gray-800 leading-relaxed">
              {storySession.prompt.prompt_text}
            </p>
          </div>

          {/* Required Words */}
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Required Words:</h3>
            <div className="flex flex-wrap gap-2">
              {storySession.prompt.required_words.map((word, index) => (
                <span
                  key={index}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    checkWordUsage(word)
                      ? 'bg-green-100 text-green-800 border border-green-200'
                      : 'bg-gray-100 text-gray-700 border border-gray-200'
                  }`}
                >
                  {checkWordUsage(word) && '✓ '}{word}
                </span>
              ))}
            </div>
          </div>

          {/* Story Writing or Evaluation */}
          {!showEvaluation ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Your Story (3-5 sentences, max 500 words):
              </label>
              <textarea
                value={currentStory}
                onChange={(e) => setCurrentStory(e.target.value)}
                placeholder="Write your creative story here using all the required words..."
                className="w-full h-40 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
                autoFocus
                disabled={submitting}
              />
              <div className="flex justify-between items-center mt-2">
                <span className={`text-sm font-medium ${
                  wordCount > MAX_WORDS ? 'text-red-600' : 
                  wordCount > MAX_WORDS * 0.9 ? 'text-amber-600' : 'text-gray-600'
                }`}>
                  {wordCount} / {MAX_WORDS} words
                  {wordCount > MAX_WORDS && ' (exceeds limit)'}
                </span>
                <span className="text-xs text-gray-500">
                  Include all required words naturally in your story
                </span>
              </div>
              <button
                onClick={handleSubmitStory}
                disabled={!currentStory.trim() || submitting || wordCount > MAX_WORDS}
                className={`mt-4 w-full px-6 py-3 rounded-lg font-medium transition-colors ${
                  !currentStory.trim() || submitting || wordCount > MAX_WORDS
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-primary-600 text-white hover:bg-primary-700'
                }`}
              >
                {submitting ? 'Evaluating...' : 
                 wordCount > MAX_WORDS ? `Reduce story by ${wordCount - MAX_WORDS} words` : 
                 'Submit Story'}
              </button>
            </div>
          ) : (
            <div>
              {/* Evaluation Display */}
              <div className={`p-6 rounded-lg mb-4 ${
                evaluation?.evaluation.total_score >= 70 ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'
              }`}>
                <div className="flex items-start space-x-3">
                  {evaluation?.evaluation.total_score >= 70 ? (
                    <CheckCircleIcon className="h-6 w-6 text-green-600 mt-0.5" />
                  ) : (
                    <ExclamationCircleIcon className="h-6 w-6 text-amber-600 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <h3 className={`font-semibold mb-2 ${
                      evaluation?.evaluation.total_score >= 70 ? 'text-green-800' : 'text-amber-800'
                    }`}>
                      Story Score: {evaluation?.evaluation.total_score}/100
                    </h3>
                    <p className="text-gray-700">
                      {evaluation?.evaluation.overall_feedback}
                    </p>
                  </div>
                </div>
              </div>

              {/* Detailed Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                {Object.entries(evaluation?.evaluation.breakdown || {}).map(([category, data]) => (
                  <div key={category} className="bg-gray-50 rounded-lg p-4">
                    <div className="flex justify-between items-center mb-2">
                      <h4 className="font-medium text-gray-900 capitalize">
                        {category.replace('_', ' ')}
                      </h4>
                      <span className="text-sm font-semibold text-primary-600">
                        {data.score}/{data.max}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">{data.feedback}</p>
                  </div>
                ))}
              </div>

              {/* Revision Suggestion */}
              {evaluation?.evaluation.revision_suggestion && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                  <div className="flex items-start space-x-3">
                    <LightBulbIcon className="h-5 w-5 text-blue-600 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-blue-900 mb-1">Suggestion for Improvement</h4>
                      <p className="text-blue-800">{evaluation.evaluation.revision_suggestion}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Action Button */}
              <button
                onClick={() => {
                  if (evaluation?.is_complete) {
                    // Don't automatically redirect - let the dialog handle it
                    setShowCompletionDialog(true)
                  } else {
                    handleNextPrompt()
                  }
                }}
                className="w-full px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 flex items-center justify-center"
              >
                {evaluation?.is_complete ? (
                  'View Results'
                ) : (
                  <>
                    Next Story
                    <ArrowRightIcon className="h-5 w-5 ml-2" />
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {/* Completion Summary (if challenge complete) */}
        {evaluation?.is_complete && (
          <div className="bg-white rounded-lg shadow-lg border-2 border-primary-200 p-8">
            <div className="text-center mb-6">
              <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
                evaluation.passed ? 'bg-green-100' : 'bg-red-100'
              }`}>
                {evaluation.passed ? (
                  <CheckCircleIcon className="h-8 w-8 text-green-600" />
                ) : (
                  <XCircleIcon className="h-8 w-8 text-red-600" />
                )}
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                {evaluation.passed ? 'Congratulations!' : 'Challenge Complete'}
              </h2>
              <p className={`text-lg font-semibold ${evaluation.passed ? 'text-green-600' : 'text-red-600'}`}>
                {evaluation.passed ? 'You PASSED the Story Builder Challenge!' : 'You did not pass this time'}
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
                  <span className="text-lg font-semibold text-gray-900">{storySession.passing_score} points</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-700 font-medium">Stories Completed:</span>
                  <span className="text-lg font-semibold text-gray-900">{storySession.total_prompts}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-700 font-medium">Percentage:</span>
                  <span className="text-lg font-semibold text-gray-900">
                    {Math.round((currentScore / storySession.max_possible_score) * 100)}%
                  </span>
                </div>
                <div className="border-t pt-4">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-700 font-medium">Result:</span>
                    <span className={`text-xl font-bold px-4 py-2 rounded-full ${
                      evaluation.passed 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {evaluation.passed ? 'PASSED' : 'FAILED'}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {evaluation.passed && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                <p className="text-green-800 text-center">
                  <strong>Great job!</strong> You've completed another practice activity. 
                  Complete more activities to unlock the final vocabulary test.
                </p>
              </div>
            )}

            {!evaluation.passed && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
                <p className="text-amber-800 text-center">
                  <strong>Keep trying!</strong> You can retake this challenge as many times as needed. 
                  Practice writing creative stories and try again when you're ready.
                </p>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Completion Confirmation Dialog */}
      {showCompletionDialog && evaluation && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full shadow-xl">
            <div className="text-center mb-6">
              <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
                evaluation.percentage_score >= 70 ? 'bg-green-100' : 'bg-amber-100'
              }`}>
                {evaluation.percentage_score >= 70 ? (
                  <CheckCircleIcon className="h-8 w-8 text-green-600" />
                ) : (
                  <ExclamationCircleIcon className="h-8 w-8 text-amber-600" />
                )}
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-2">
                Story Builder Complete!
              </h3>
              <p className="text-lg text-gray-700 mb-4">
                You scored <span className="font-bold text-primary-600">{Math.round(evaluation.percentage_score)}%</span>
              </p>
              {evaluation.percentage_score >= 70 ? (
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

            {evaluation.percentage_score >= 70 ? (
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