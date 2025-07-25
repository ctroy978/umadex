'use client'

import { useState, useEffect, useCallback } from 'react'
import { UMATestStartResponse, UMATestQuestion } from '@/lib/umatestApi'
import { umatestApi } from '@/lib/umatestApi'
import QuestionDisplay from './QuestionDisplay'
import TestProgress from '../test/TestProgress'
import TestNavigation from '../test/TestNavigation'
import SubmissionModal from '../test/SubmissionModal'
import SecurityWarningModal from '../test/SecurityWarningModal'
import UMATestLockoutModal from './UMATestLockoutModal'
import { useRouter } from 'next/navigation'
import { useUMATestSecurity } from '@/hooks/useUMATestSecurity'

interface UMATestInterfaceProps {
  testData: UMATestStartResponse
  onComplete: () => void
}

export default function UMATestInterface({ testData, onComplete }: UMATestInterfaceProps) {
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
  const [isTestActive, setIsTestActive] = useState(true)
  
  // Security features
  const { violationCount, isLocked, showWarning, acknowledgeWarning } = useUMATestSecurity({
    testAttemptId: testData.test_attempt_id,
    isActive: isTestActive,
    onWarning: () => {
      setIsTestActive(false)
    },
    onLock: () => {
      setIsTestActive(false)
    }
  })

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

  // Track if current answer has been saved
  const [unsavedChanges, setUnsavedChanges] = useState(false)

  // Track time spent on current question
  useEffect(() => {
    setQuestionStartTime(Date.now())
  }, [currentQuestionIndex])

  const saveAnswer = async (questionIndex: number, answer: string) => {
    if (isSaving || !answer.trim()) return
    
    setIsSaving(true)
    setSaveError(null)
    try {
      const timeOnQuestion = Math.floor((Date.now() - questionStartTime) / 1000)
      await umatestApi.saveAnswer(testData.test_attempt_id, {
        question_index: questionIndex,
        answer: answer,
        time_spent_seconds: timeOnQuestion
      })
      setTimeSpent(prev => prev + timeOnQuestion)
      setLastSaveTime(new Date())
      setUnsavedChanges(false)
    } catch (error: any) {
      console.error('Failed to save answer:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to save answer'
      setSaveError(errorMessage)
    } finally {
      setIsSaving(false)
    }
  }

  const handleAnswerChange = (answer: string) => {
    setAnswers(prev => ({
      ...prev,
      [String(currentQuestionIndex)]: answer
    }))
    setUnsavedChanges(true)
  }

  const handleNavigate = async (direction: 'prev' | 'next') => {
    // Save current answer before navigating if there are unsaved changes
    if (unsavedChanges) {
      const currentAnswer = answers[String(currentQuestionIndex)] || ''
      if (currentAnswer) {
        await saveAnswer(currentQuestionIndex, currentAnswer)
      }
    }

    if (direction === 'next' && currentQuestionIndex < testData.questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1)
    } else if (direction === 'prev' && currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1)
    }
  }

  const handleQuestionSelect = async (index: number) => {
    // Save current answer before navigating if there are unsaved changes
    if (unsavedChanges) {
      const currentAnswer = answers[String(currentQuestionIndex)] || ''
      if (currentAnswer) {
        await saveAnswer(currentQuestionIndex, currentAnswer)
      }
    }
    setCurrentQuestionIndex(index)
  }

  const handleSubmit = async () => {
    setShowSubmitModal(false)
    setIsSubmitting(true)
    
    try {
      // Save all unsaved answers before submission
      for (const [questionIndex, answer] of Object.entries(answers)) {
        if (answer && answer.trim()) {
          try {
            await saveAnswer(parseInt(questionIndex), answer)
          } catch (saveError) {
            console.warn(`Failed to save answer for question ${questionIndex}:`, saveError)
          }
        }
      }

      // Submit test
      const result = await umatestApi.submitTest(testData.test_attempt_id)
      
      // Redirect to results after successful submission
      onComplete()
    } catch (error) {
      console.error('Failed to submit test:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const answeredQuestions = Object.keys(answers)
    .filter(key => answers[key]?.trim())
    .map(key => parseInt(key))

  const currentQuestion = testData.questions[currentQuestionIndex]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">{testData.test_title}</h1>
              <p className="text-sm text-gray-600">
                {testData.test_description || 'Comprehensive Test'} - Attempt #{testData.attempt_number} of {testData.max_attempts}
              </p>
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
        totalQuestions={testData.questions.length}
        answeredQuestions={answeredQuestions}
      />

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 py-6">
        <div className="bg-white rounded-lg shadow-sm">
          {/* Question Context */}
          <div className="px-6 pt-6 pb-2">
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <span className="font-medium">Lecture: {currentQuestion.source_lecture_title}</span>
              <span>•</span>
              <span>Topic: {currentQuestion.topic_title}</span>
              <span>•</span>
              <span className="capitalize">Difficulty: {currentQuestion.difficulty_level}</span>
            </div>
          </div>

          {/* Question Display */}
          <QuestionDisplay
            question={currentQuestion}
            questionNumber={currentQuestionIndex + 1}
            answer={answers[String(currentQuestionIndex)] || ''}
            onAnswerChange={handleAnswerChange}
            isDisabled={isLocked || !isTestActive}
          />
          
          {/* Navigation */}
          <div className="px-6 pb-6">
            <TestNavigation
              currentQuestion={currentQuestionIndex + 1}
              totalQuestions={testData.questions.length}
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

      {/* Submit Modal */}
      {showSubmitModal && (
        <SubmissionModal
          answeredCount={answeredQuestions.length}
          totalQuestions={testData.questions.length}
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
      <UMATestLockoutModal
        isOpen={isLocked}
        testAttemptId={testData.test_attempt_id}
        onUnlockSuccess={() => {
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