'use client'

import { useState, useEffect, useCallback } from 'react'
import { TestStartResponse, ReadingContentResponse, TestQuestion } from '@/types/test'
import { testApi } from '@/lib/testApi'
import ReadingTabs from './ReadingTabs'
import QuestionDisplay from './QuestionDisplay'
import TestProgress from './TestProgress'
import TestNavigation from './TestNavigation'
import SubmissionModal from './SubmissionModal'
import SecurityWarningModal from './SecurityWarningModal'
import TestLockoutModal from './TestLockoutModal'
import { useTestSecurity } from '@/hooks/useTestSecurity'
import { useRouter } from 'next/navigation'

interface TestInterfaceProps {
  testData: TestStartResponse
  readingContent: ReadingContentResponse
  onComplete: () => void
}

export default function TestInterface({ testData, readingContent, onComplete }: TestInterfaceProps) {
  const router = useRouter()
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(testData.current_question - 1)
  const [answers, setAnswers] = useState<Record<string, string>>(testData.saved_answers || {})
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [lastSaveTime, setLastSaveTime] = useState<Date | null>(null)
  const [showSubmitModal, setShowSubmitModal] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [timeSpent, setTimeSpent] = useState(0)
  const [questionStartTime, setQuestionStartTime] = useState(Date.now())
  const [questions, setQuestions] = useState<TestQuestion[]>([])
  const [questionsLoading, setQuestionsLoading] = useState(true)
  const [isTestActive, setIsTestActive] = useState(testData.status === 'in_progress')
  
  // Use the security hook
  const { violationCount, isLocked, showWarning, acknowledgeWarning } = useTestSecurity({
    testId: testData.test_attempt_id,
    isActive: isTestActive && testData.status === 'in_progress',
    onWarning: () => {
      // Pause any timers if needed
      setIsTestActive(false)
    },
    onLock: () => {
      // Test is locked, disable everything
      setIsTestActive(false)
    }
  })

  // Check if test is already submitted
  useEffect(() => {
    if (testData.status === 'submitted' || testData.status === 'evaluated') {
      console.log('Test already submitted, redirecting...')
      onComplete()
    }
  }, [testData.status, onComplete])

  // Fetch actual test questions
  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        const response = await testApi.getTestQuestions(testData.test_id)
        const mappedQuestions = response.questions.map((q: any) => ({
          question: q.question,
          difficulty: q.difficulty || 5,
          answer_key: '',
          grading_context: ''
        }))
        setQuestions(mappedQuestions)
      } catch (error) {
        console.error('Failed to fetch questions:', error)
      } finally {
        setQuestionsLoading(false)
      }
    }
    fetchQuestions()
  }, [testData.test_id])

  // Disable copy/paste and right-click
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && ['c', 'v', 'a', 'x'].includes(e.key.toLowerCase())) {
        e.preventDefault()
      }
    }

    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault()
    }

    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('contextmenu', handleContextMenu)

    // Prevent navigation if there are unsaved changes
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (Object.keys(answers).length > 0) {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('contextmenu', handleContextMenu)
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [answers])

  // Auto-save functionality
  useEffect(() => {
    // Don't auto-save if test is not active or is being submitted
    if (!isTestActive || isSubmitting) {
      return
    }
    
    const timer = setTimeout(() => {
      const currentAnswer = answers[String(currentQuestionIndex)]
      if (currentAnswer && currentAnswer.trim() && !isSaving) {
        saveAnswer(currentQuestionIndex, currentAnswer)
      }
    }, 2000) // Save 2 seconds after typing stops

    return () => clearTimeout(timer)
  }, [answers, currentQuestionIndex, isSaving, isTestActive, isSubmitting])

  // Track time spent on current question
  useEffect(() => {
    setQuestionStartTime(Date.now())
  }, [currentQuestionIndex])

  const saveAnswer = async (questionIndex: number, answer: string) => {
    if (isSaving || !isTestActive || isSubmitting) return // Prevent saves if test is not active or being submitted
    
    setIsSaving(true)
    setSaveError(null)
    try {
      const timeOnQuestion = Math.floor((Date.now() - questionStartTime) / 1000)
      await testApi.saveAnswer(testData.test_attempt_id, {
        question_index: questionIndex,
        answer: answer,
        time_spent_seconds: timeOnQuestion
      })
      setTimeSpent(prev => prev + timeOnQuestion)
      setLastSaveTime(new Date())
    } catch (error: any) {
      console.error('Failed to save answer:', error)
      
      // Handle 404 errors (test already submitted)
      if (error.response?.status === 404) {
        console.warn('Test has been submitted. Cannot save additional answers.')
        setIsTestActive(false)
        return
      }
      
      // Handle 401 errors without redirecting
      if (error.response?.status === 401) {
        console.warn('Auth issue while saving answer. Answer may not be saved.')
        setSaveError('Session expired. Your answer may not be saved. Please complete the test quickly.')
      } else {
        const errorMessage = error.response?.data?.detail || error.message || 'Failed to save answer'
        setSaveError(errorMessage)
      }
    } finally {
      setIsSaving(false)
    }
  }

  const handleAnswerChange = (answer: string) => {
    setAnswers(prev => ({
      ...prev,
      [String(currentQuestionIndex)]: answer
    }))
  }

  const handleNavigate = (direction: 'prev' | 'next') => {
    // Save current answer before navigating
    const currentAnswer = answers[String(currentQuestionIndex)] || ''
    if (currentAnswer) {
      saveAnswer(currentQuestionIndex, currentAnswer)
    }

    if (direction === 'next' && currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1)
    } else if (direction === 'prev' && currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1)
    }
  }

  const handleQuestionSelect = (index: number) => {
    // Save current answer before navigating
    const currentAnswer = answers[String(currentQuestionIndex)] || ''
    if (currentAnswer) {
      saveAnswer(currentQuestionIndex, currentAnswer)
    }
    setCurrentQuestionIndex(index)
  }

  const handleSubmit = async () => {
    console.log('=== FRONTEND: handleSubmit called ===')
    console.log('Test Attempt ID:', testData.test_attempt_id)
    console.log('Answers:', answers)
    
    setShowSubmitModal(false)
    setIsSubmitting(true)
    setIsTestActive(false) // Stop all auto-save operations
    
    try {
      // Save current answer first if needed - don't let this fail the submission
      const currentAnswer = answers[String(currentQuestionIndex)] || ''
      if (currentAnswer) {
        console.log('=== FRONTEND: Saving current answer before submit ===')
        try {
          await saveAnswer(currentQuestionIndex, currentAnswer)
        } catch (saveError) {
          console.warn('Failed to save current answer, continuing with submission:', saveError)
        }
      }

      // Submit test
      console.log('=== FRONTEND: Calling testApi.submitTest ===')
      const result = await testApi.submitTest(testData.test_attempt_id)
      console.log('=== FRONTEND: Submit result:', result)
      
      // Always redirect after submission (whether evaluation succeeds or not)
      onComplete()
    } catch (error) {
      console.error('=== FRONTEND: Failed to submit test ===', error)
      console.error('Error details:', (error as any).response?.data)
      
      // Still redirect even if submission fails to avoid getting stuck
      // The test attempt is already marked as submitted on the backend
      if ((error as any).response?.data?.detail?.includes('already submitted')) {
        console.log('Test already submitted, redirecting...')
        onComplete()
      } else {
        // For other errors, show an alert but still redirect
        alert('Test submission encountered an error. Your answers have been saved. Please contact your teacher if you see any issues.')
        onComplete()
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const answeredQuestions = Object.keys(answers)
    .filter(key => answers[key]?.trim())
    .map(key => parseInt(key))

  // Show loading state while fetching questions
  if (questionsLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading test questions...</p>
        </div>
      </div>
    )
  }

  // Show error if no questions loaded
  if (questions.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Failed to load test questions</p>
          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
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
      <div className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">{testData.assignment_title}</h1>
              <p className="text-sm text-gray-600">Comprehension Test - Attempt #{testData.attempt_number}</p>
            </div>
            {testData.time_limit_minutes && (
              <div className="text-sm text-gray-600">
                Time Limit: {testData.time_limit_minutes} minutes
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <TestProgress
        currentQuestion={currentQuestionIndex + 1}
        totalQuestions={questions.length}
        answeredQuestions={answeredQuestions}
      />

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Reading Material */}
          <div className="bg-white rounded-lg shadow-sm">
            <ReadingTabs chunks={readingContent.chunks} />
          </div>

          {/* Right: Question and Answer */}
          <div className="bg-white rounded-lg shadow-sm">
            <QuestionDisplay
              question={questions[currentQuestionIndex]}
              questionNumber={currentQuestionIndex + 1}
              answer={answers[String(currentQuestionIndex)] || ''}
              onAnswerChange={handleAnswerChange}
              isDisabled={isLocked || !isTestActive}
            />
            
            <div className="px-6 pb-6">
              <TestNavigation
                currentQuestion={currentQuestionIndex + 1}
                totalQuestions={questions.length}
                answeredQuestions={answeredQuestions}
                onNavigate={handleNavigate}
                onQuestionSelect={handleQuestionSelect}
                onSubmit={() => setShowSubmitModal(true)}
                isSaving={isSaving}
                isSubmitting={isSubmitting}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Submit Modal */}
      {showSubmitModal && (
        <SubmissionModal
          answeredCount={answeredQuestions.length}
          totalQuestions={questions.length}
          answeredQuestions={answeredQuestions}
          onConfirm={handleSubmit}
          onCancel={() => setShowSubmitModal(false)}
          isSubmitting={isSubmitting}
        />
      )}

      {/* Save Status Indicator */}
      <div className="fixed bottom-4 right-4 space-y-2">
        {/* Save Status */}
        {isSaving && (
          <div className="bg-blue-600 text-white text-xs px-3 py-2 rounded-lg flex items-center space-x-2">
            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>
            <span>Saving...</span>
          </div>
        )}
        
        {/* Red box save error removed per request - students don't need to see save errors */}
        {/* {saveError && (
          <div className="bg-red-600 text-white text-xs px-3 py-2 rounded-lg max-w-xs">
            <div className="font-medium">Save Failed!</div>
            <div className="text-red-100 mt-1">{saveError}</div>
            <button
              onClick={() => {
                const currentAnswer = answers[String(currentQuestionIndex)]
                if (currentAnswer) {
                  saveAnswer(currentQuestionIndex, currentAnswer)
                }
              }}
              className="text-red-100 underline mt-1 text-xs hover:text-white"
            >
              Retry Save
            </button>
          </div>
        )} */}
        
        {!isSaving && !saveError && lastSaveTime && (
          <div className="bg-green-600 text-white text-xs px-3 py-2 rounded-lg">
            Saved {lastSaveTime.toLocaleTimeString()}
          </div>
        )}
        
        {/* Copy/Paste Disabled Indicator */}
        <div className="bg-gray-800 text-white text-xs px-3 py-2 rounded-lg opacity-75">
          Copy/Paste Disabled for Test Integrity
        </div>
      </div>

      {/* Security Warning Modal */}
      <SecurityWarningModal
        isOpen={showWarning}
        onAcknowledge={() => {
          acknowledgeWarning()
          setIsTestActive(true)
        }}
      />

      {/* Test Lockout Modal */}
      <TestLockoutModal
        isOpen={isLocked}
        testAttemptId={testData.test_attempt_id}
        onUnlockSuccess={() => {
          // Reload the page to restart the test
          window.location.reload()
        }}
      />

      {/* Submission Processing Overlay */}
      {isSubmitting && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Processing Your Test</h3>
            <p className="text-gray-600 mb-4">
              Please wait while we save your answers and evaluate your responses. This may take a moment.
            </p>
            <div className="text-sm text-gray-500">
              Do not close this window or navigate away.
            </div>
          </div>
        </div>
      )}
    </div>
  )
}