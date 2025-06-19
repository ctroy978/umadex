'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { VocabularyTestStartResponse, VocabularyTestQuestion, studentApi } from '@/lib/studentApi'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Clock, CheckCircle, AlertTriangle, BookOpen } from 'lucide-react'

interface VocabularyTestInterfaceProps {
  assignmentId: string
  testData: VocabularyTestStartResponse
  onComplete: (results: any) => void
}

interface TestState {
  currentQuestionIndex: number
  answers: Record<string, string>
  timeRemaining: number
  isSubmitting: boolean
  showSubmitConfirm: boolean
  error: string | null
}

export default function VocabularyTestInterface({ 
  assignmentId, 
  testData, 
  onComplete 
}: VocabularyTestInterfaceProps) {
  const router = useRouter()
  const [state, setState] = useState<TestState>({
    currentQuestionIndex: 0,
    answers: {},
    timeRemaining: testData.time_limit_minutes * 60,
    isSubmitting: false,
    showSubmitConfirm: false,
    error: null
  })

  // Timer countdown
  useEffect(() => {
    if (state.timeRemaining <= 0) return

    const timer = setInterval(() => {
      setState(prev => {
        const newTimeRemaining = prev.timeRemaining - 1
        if (newTimeRemaining <= 0) {
          // Auto-submit when time runs out
          handleSubmitTest()
          return { ...prev, timeRemaining: 0 }
        }
        return { ...prev, timeRemaining: newTimeRemaining }
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [state.timeRemaining])

  // Prevent navigation away
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (Object.keys(state.answers).length > 0 && !state.isSubmitting) {
        e.preventDefault()
        e.returnValue = 'You have unsaved answers. Are you sure you want to leave?'
      }
    }

    // Disable copy/paste and right-click
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && ['c', 'v', 'a', 'x'].includes(e.key.toLowerCase())) {
        e.preventDefault()
      }
    }

    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault()
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('contextmenu', handleContextMenu)

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('contextmenu', handleContextMenu)
    }
  }, [state.answers, state.isSubmitting])

  const currentQuestion = testData.questions[state.currentQuestionIndex]
  const progress = ((state.currentQuestionIndex + 1) / testData.total_questions) * 100
  const answeredCount = Object.keys(state.answers).length

  const handleAnswerChange = (value: string) => {
    setState(prev => ({
      ...prev,
      answers: {
        ...prev.answers,
        [currentQuestion.id]: value
      },
      error: null
    }))
  }

  const goToQuestion = (index: number) => {
    setState(prev => ({ ...prev, currentQuestionIndex: index }))
  }

  const nextQuestion = () => {
    if (state.currentQuestionIndex < testData.questions.length - 1) {
      setState(prev => ({ ...prev, currentQuestionIndex: prev.currentQuestionIndex + 1 }))
    }
  }

  const previousQuestion = () => {
    if (state.currentQuestionIndex > 0) {
      setState(prev => ({ ...prev, currentQuestionIndex: prev.currentQuestionIndex - 1 }))
    }
  }

  const handleSubmitTest = async () => {
    setState(prev => ({ ...prev, isSubmitting: true, error: null }))

    try {
      const results = await studentApi.submitVocabularyTest(
        testData.test_attempt_id,
        state.answers
      )
      onComplete(results)
    } catch (error) {
      console.error('Error submitting test:', error)
      setState(prev => ({
        ...prev,
        isSubmitting: false,
        error: 'Failed to submit test. Please try again.'
      }))
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getQuestionStatusIcon = (index: number) => {
    const question = testData.questions[index]
    const hasAnswer = state.answers[question.id]?.trim()
    
    if (hasAnswer) {
      return <CheckCircle className="w-4 h-4 text-green-500" />
    }
    return <div className="w-4 h-4 rounded-full border-2 border-gray-300" />
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BookOpen className="w-6 h-6 text-blue-600" />
              <h1 className="text-2xl font-bold">Vocabulary Test</h1>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-orange-600">
                <Clock className="w-5 h-5" />
                <span className="font-mono text-lg">
                  {formatTime(state.timeRemaining)}
                </span>
              </div>
              
              {state.timeRemaining <= 300 && (
                <div className="flex items-center gap-2 text-red-600">
                  <AlertTriangle className="w-5 h-5" />
                  <span className="text-sm font-medium">5 minutes remaining!</span>
                </div>
              )}
            </div>
          </div>

          {/* Progress */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm text-gray-600">
              <span>Question {state.currentQuestionIndex + 1} of {testData.total_questions}</span>
              <span>{answeredCount} of {testData.total_questions} answered</span>
            </div>
            <Progress value={progress} className="w-full" />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Question Navigation Sidebar */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Questions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-5 lg:grid-cols-1 gap-2">
                  {testData.questions.map((_, index) => (
                    <Button
                      key={index}
                      variant={index === state.currentQuestionIndex ? "default" : "outline"}
                      size="sm"
                      onClick={() => goToQuestion(index)}
                      className="flex items-center justify-between p-2"
                    >
                      <span>{index + 1}</span>
                      {getQuestionStatusIcon(index)}
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Main Question Area */}
          <div className="lg:col-span-3">
            <Card>
              <CardHeader>
                <CardTitle>
                  Question {state.currentQuestionIndex + 1} of {testData.total_questions}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Word Display */}
                <div className="text-center">
                  <h2 className="text-3xl font-bold text-gray-800">
                    {currentQuestion.word}
                  </h2>
                </div>

                {/* Example Sentence */}
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
                    <BookOpen className="h-4 w-4 mr-2" />
                    Example:
                  </h3>
                  <p className="text-lg leading-relaxed">
                    {currentQuestion.example_sentence}
                  </p>
                </div>

                {/* Definition Input */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Define this word based on how it's used in the sentence:
                  </label>
                  <Textarea
                    value={state.answers[currentQuestion.id] || ''}
                    onChange={(e) => handleAnswerChange(e.target.value)}
                    placeholder="Write your definition here..."
                    rows={4}
                    className="w-full"
                    minLength={10}
                  />
                  <p className="mt-2 text-sm text-gray-500">
                    {state.answers[currentQuestion.id]?.length || 0} characters
                    {state.answers[currentQuestion.id]?.length < 10 && (
                      <span className="text-amber-600 ml-2">
                        (minimum 10 characters required)
                      </span>
                    )}
                  </p>
                </div>

                {/* Error Message */}
                {state.error && (
                  <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>{state.error}</AlertDescription>
                  </Alert>
                )}

                {/* Navigation */}
                <div className="flex justify-between items-center pt-4">
                  <Button
                    variant="outline"
                    onClick={previousQuestion}
                    disabled={state.currentQuestionIndex === 0}
                  >
                    Previous
                  </Button>

                  <div className="flex gap-2">
                    {state.currentQuestionIndex === testData.questions.length - 1 ? (
                      <Button
                        onClick={() => setState(prev => ({ ...prev, showSubmitConfirm: true }))}
                        disabled={state.isSubmitting}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        Submit Test
                      </Button>
                    ) : (
                      <Button onClick={nextQuestion}>
                        Next
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Submit Confirmation Modal */}
        {state.showSubmitConfirm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="w-full max-w-md">
              <CardHeader>
                <CardTitle>Submit Test</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p>
                  Are you sure you want to submit your test? You have answered{' '}
                  <strong>{answeredCount} out of {testData.total_questions}</strong> questions.
                </p>
                
                {answeredCount < testData.total_questions && (
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      You have {testData.total_questions - answeredCount} unanswered questions.
                      These will be marked as incorrect.
                    </AlertDescription>
                  </Alert>
                )}

                <div className="flex gap-2 justify-end">
                  <Button
                    variant="outline"
                    onClick={() => setState(prev => ({ ...prev, showSubmitConfirm: false }))}
                    disabled={state.isSubmitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSubmitTest}
                    disabled={state.isSubmitting}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {state.isSubmitting ? 'Submitting...' : 'Submit Test'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}