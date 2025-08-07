'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { studentApi, VocabularyTestStartResponse, VocabularyTestAttemptResponse } from '@/lib/studentApi'
import VocabularyTestInterface from '@/components/student/vocabulary-test/VocabularyTestInterface'
import VocabularyTestLockoutModal from '@/components/student/vocabulary-test/VocabularyTestLockoutModal'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { 
  BookOpen, 
  Clock, 
  CheckCircle, 
  XCircle, 
  Trophy, 
  AlertTriangle,
  ArrowLeft 
} from 'lucide-react'

type PageState = 'loading' | 'eligibility' | 'instructions' | 'test' | 'results' | 'error' | 'override_required' | 'locked'

interface TestResults {
  score_percentage: number
  questions_correct: number
  total_questions: number
  time_spent_seconds?: number
  detailed_results: Array<{
    question_id: string
    word: string
    example_sentence: string
    student_answer: string
    score: number
    is_correct: boolean
    feedback: string
    strengths: string[]
    areas_for_growth: string[]
    component_scores?: {
      core_meaning: number
      context_appropriateness: number
      completeness: number
      clarity: number
    }
  }>
}

export default function VocabularyTestPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const assignmentId = params.id as string
  const classroomId = searchParams.get('classroomId')

  const [pageState, setPageState] = useState<PageState>('loading')
  const [eligibilityData, setEligibilityData] = useState<any>(null)
  const [testData, setTestData] = useState<VocabularyTestStartResponse | null>(null)
  const [results, setResults] = useState<TestResults | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [overrideCode, setOverrideCode] = useState<string>('')

  useEffect(() => {
    // Check if there's an override code in the URL params
    const urlOverrideCode = searchParams.get('override')
    if (urlOverrideCode) {
      setOverrideCode(urlOverrideCode)
      // If there's an override code, go directly to test start
      startTest(urlOverrideCode)
    } else {
      checkEligibility()
    }
  }, [assignmentId, searchParams])

  const checkEligibility = async () => {
    try {
      const eligibility = await studentApi.checkVocabularyTestEligibility(assignmentId)
      setEligibilityData(eligibility)
      
      if (eligibility.eligible) {
        setPageState('instructions')
      } else {
        setPageState('eligibility')
      }
    } catch (error) {
      console.error('Error checking test eligibility:', error)
      setError('Failed to check test eligibility. Please try again.')
      setPageState('error')
    }
  }

  const startTest = async (overrideCode?: string) => {
    try {
      setPageState('loading')
      const testResponse = await studentApi.startVocabularyTest(assignmentId, overrideCode)
      setTestData(testResponse)
      setPageState('test')
    } catch (error: any) {
      console.error('Error starting test:', error)
      
      // Check if test is locked
      if (error.response?.status === 423) {
        const lockedAttemptId = error.response?.headers?.['x-locked-attempt-id']
        const message = error.response?.data?.detail || 'Your test is locked due to security violations.'
        
        setError(message)
        setPageState('locked')
        // Store the locked attempt ID if needed
        if (lockedAttemptId) {
          setTestData({ test_attempt_id: lockedAttemptId } as any)
        }
        return
      }
      
      // Check if it's a test schedule restriction error
      if (error.response?.status === 403 && error.response?.headers?.['x-override-required']) {
        const message = error.response?.data?.detail || 'Test not available at this time'
        const nextWindow = error.response?.headers?.['x-next-window']
        
        setError(message)
        // Show override code dialog
        setPageState('override_required')
        return
      }
      
      setError(error.response?.data?.detail || 'Failed to start test. Please try again.')
      setPageState('error')
    }
  }

  const handleTestComplete = (testResults: VocabularyTestAttemptResponse) => {
    setResults(testResults as any)
    setPageState('results')
  }

  const getScoreColor = (percentage: number) => {
    if (percentage >= 90) return 'text-green-600'
    if (percentage >= 80) return 'text-blue-600'
    if (percentage >= 70) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getScoreIcon = (percentage: number) => {
    if (percentage >= 80) return <Trophy className="w-6 h-6 text-yellow-500" />
    if (percentage >= 70) return <CheckCircle className="w-6 h-6 text-green-500" />
    return <XCircle className="w-6 h-6 text-red-500" />
  }

  // Loading state
  if (pageState === 'loading') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="p-6">
            <div className="flex items-center justify-center space-x-2">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span>Loading test...</span>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Error state
  if (pageState === 'error') {
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-2xl mx-auto pt-8">
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          
          <div className="mt-4">
            <Button onClick={() => {
              const query = classroomId ? `?classroomId=${classroomId}` : ''
              router.push(`/student/vocabulary/${assignmentId}/practice${query}`)
            }} variant="outline">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Go Back
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Override code required state
  if (pageState === 'override_required') {
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-2xl mx-auto pt-8">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-6 h-6 text-orange-500" />
                Test Schedule Restriction
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
              
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  Your teacher has set specific times when tests can be taken. 
                  If you have a bypass code from your teacher, you can enter it below to access the test.
                </p>
                
                <div className="space-y-2">
                  <label htmlFor="override-code" className="text-sm font-medium">
                    Bypass Code
                  </label>
                  <input
                    id="override-code"
                    type="text"
                    value={overrideCode}
                    onChange={(e) => setOverrideCode(e.target.value)}
                    placeholder="Enter bypass code"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              
              <div className="flex gap-2 justify-end">
                <Button onClick={() => {
                  const query = classroomId ? `?classroomId=${classroomId}` : ''
                  router.push(`/student/vocabulary/${assignmentId}/practice${query}`)
                }} variant="outline">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Go Back
                </Button>
                <Button 
                  onClick={() => startTest(overrideCode)}
                  disabled={!overrideCode.trim()}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  Submit Code
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  // Not eligible state
  if (pageState === 'eligibility') {
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-2xl mx-auto pt-8">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="w-6 h-6 text-blue-600" />
                Vocabulary Test Not Available
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  {eligibilityData?.reason || 'You need to complete more practice activities before taking the test.'}
                </AlertDescription>
              </Alert>

              <div className="space-y-3">
                <h3 className="font-medium">Progress Requirements:</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>Assignments Completed:</span>
                    <span className="font-medium">
                      {eligibilityData?.assignments_completed || 0} / {eligibilityData?.assignments_required || 3}
                    </span>
                  </div>
                  
                  <Progress 
                    value={((eligibilityData?.assignments_completed || 0) / (eligibilityData?.assignments_required || 3)) * 100} 
                    className="w-full" 
                  />
                </div>

                {eligibilityData?.attempts_used !== undefined && (
                  <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-amber-900">Test Attempts:</span>
                      <span className={`text-sm font-bold ${eligibilityData.attempts_remaining > 0 ? 'text-amber-900' : 'text-red-600'}`}>
                        {eligibilityData.attempts_used} / {eligibilityData.max_attempts} used
                        {eligibilityData.attempts_remaining > 0 && ` (${eligibilityData.attempts_remaining} remaining)`}
                      </span>
                    </div>
                  </div>
                )}

                {eligibilityData?.progress_details && (
                  <div className="grid grid-cols-2 gap-2 mt-4">
                    {Object.entries(eligibilityData.progress_details).map(([activity, completed]) => {
                      // Map activity names to user-friendly labels
                      const activityLabels: Record<string, string> = {
                        'story_builder_completed': 'Story Builder',
                        'concept_mapping_completed': 'Concept Mapping',
                        'puzzle_path_completed': 'Puzzle Path',
                        'fill_in_blank_completed': 'Fill in the Blank'
                      }
                      
                      return (
                        <div key={activity} className="flex items-center gap-2">
                          {completed ? 
                            <CheckCircle className="w-4 h-4 text-green-500" /> : 
                            <XCircle className="w-4 h-4 text-gray-400" />
                          }
                          <span className="text-sm">
                            {activityLabels[activity] || activity.replace('_', ' ')}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <Button onClick={() => {
              const query = classroomId ? `?classroomId=${classroomId}` : ''
              router.push(`/student/vocabulary/${assignmentId}/practice${query}`)
            }} variant="outline">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Practice
                </Button>
                <Button onClick={checkEligibility}>
                  Refresh Status
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  // Instructions state
  if (pageState === 'instructions') {
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-2xl mx-auto pt-8">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="w-6 h-6 text-blue-600" />
                Vocabulary Test Instructions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert>
                <CheckCircle className="h-4 w-4" />
                <AlertDescription>
                  You are eligible to take the vocabulary test!
                </AlertDescription>
              </Alert>

              <div className="space-y-3">
                <h3 className="font-medium">Test Guidelines:</h3>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li className="flex items-start gap-2">
                    <Clock className="w-4 h-4 mt-0.5 text-blue-500" />
                    <span>You have a time limit to complete all questions</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <BookOpen className="w-4 h-4 mt-0.5 text-blue-500" />
                    <span>Questions may include definitions, examples, and vocabulary usage</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 mt-0.5 text-yellow-500" />
                    <span>Once started, you cannot pause or restart the test</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 mt-0.5 text-green-500" />
                    <span>You can navigate between questions and change your answers</span>
                  </li>
                </ul>
              </div>

              <div className="bg-blue-50 p-4 rounded-lg">
                <h4 className="font-medium text-blue-900 mb-2">Important Notes:</h4>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>• Copy and paste functions are disabled during the test</li>
                  <li>• Right-clicking is disabled for security</li>
                  <li>• Navigate away from this page carefully - your progress will be lost</li>
                  <li>• Make sure you have a stable internet connection</li>
                </ul>
              </div>

              <div className="flex gap-2 justify-end">
                <Button onClick={() => {
              const query = classroomId ? `?classroomId=${classroomId}` : ''
              router.push(`/student/vocabulary/${assignmentId}/practice${query}`)
            }} variant="outline">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Cancel
                </Button>
                <Button onClick={() => startTest()} className="bg-green-600 hover:bg-green-700">
                  Start Test
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  // Test state
  if (pageState === 'test' && testData) {
    return (
      <VocabularyTestInterface
        assignmentId={assignmentId}
        testData={testData}
        onComplete={handleTestComplete}
      />
    )
  }

  // Results state
  if (pageState === 'results' && results) {
    const timeSpentMinutes = results.time_spent_seconds ? Math.round(results.time_spent_seconds / 60) : 0
    
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-4xl mx-auto pt-8">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {getScoreIcon(results.score_percentage)}
                Test Results
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Summary */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <div className={`text-3xl font-bold ${getScoreColor(results.score_percentage)}`}>
                    {Math.round(results.score_percentage)}%
                  </div>
                  <div className="text-sm text-gray-600">Final Score</div>
                </div>
                
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-3xl font-bold text-green-600">
                    {results.questions_correct}
                  </div>
                  <div className="text-sm text-gray-600">
                    Correct out of {results.total_questions}
                  </div>
                </div>
                
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="text-3xl font-bold text-purple-600">
                    {timeSpentMinutes}m
                  </div>
                  <div className="text-sm text-gray-600">Time Spent</div>
                </div>
              </div>

              {/* Performance Message */}
              <Alert className={results.score_percentage >= 80 ? 'border-green-200 bg-green-50' : 
                              results.score_percentage >= 70 ? 'border-yellow-200 bg-yellow-50' : 
                              'border-red-200 bg-red-50'}>
                <AlertDescription>
                  {results.score_percentage >= 90 ? 'Excellent work! You have mastered this vocabulary.' :
                   results.score_percentage >= 80 ? 'Great job! You have a strong understanding of this vocabulary.' :
                   results.score_percentage >= 70 ? 'Good work! Review the missed words to improve further.' :
                   'Keep practicing! Review the vocabulary words and try the practice activities again.'}
                </AlertDescription>
              </Alert>

              {/* Detailed Results */}
              <div>
                <h3 className="font-medium mb-3">Question by Question Results:</h3>
                <div className="space-y-4 max-h-[600px] overflow-y-auto">
                  {results.detailed_results.map((result, index) => (
                    <div key={result.question_id} 
                         className={`p-5 rounded-lg border ${result.is_correct ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'}`}>
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <span className="font-medium text-lg">Question {index + 1}: </span>
                          <span className="text-xl font-bold">{result.word}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          {result.is_correct ? 
                            <CheckCircle className="w-5 h-5 text-green-500" /> : 
                            <AlertTriangle className="w-5 h-5 text-yellow-600" />
                          }
                          <span className="text-lg font-bold">
                            {result.score}%
                          </span>
                        </div>
                      </div>
                      
                      <div className="space-y-3">
                        {/* Example Sentence */}
                        <div className="bg-white p-3 rounded border border-gray-200">
                          <p className="text-sm text-gray-600 mb-1"><strong>Context:</strong></p>
                          <p className="text-sm italic">{result.example_sentence}</p>
                        </div>

                        {/* Student's Definition */}
                        <div>
                          <p className="text-sm text-gray-600 mb-1"><strong>Your Definition:</strong></p>
                          <p className="text-sm">{result.student_answer || '(No answer provided)'}</p>
                        </div>

                        {/* AI Feedback */}
                        <div className="bg-blue-50 p-3 rounded">
                          <p className="text-sm font-medium text-blue-900 mb-1">Feedback:</p>
                          <p className="text-sm text-blue-800">{result.feedback}</p>
                        </div>

                        {/* Strengths and Areas for Growth */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {result.strengths && result.strengths.length > 0 && (
                            <div className="bg-green-100 p-3 rounded">
                              <p className="text-sm font-medium text-green-900 mb-1">Strengths:</p>
                              <ul className="text-sm text-green-800 space-y-1">
                                {result.strengths.map((strength, idx) => (
                                  <li key={idx} className="flex items-start">
                                    <CheckCircle className="w-3 h-3 mr-1 mt-0.5 flex-shrink-0" />
                                    {strength}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          
                          {result.areas_for_growth && result.areas_for_growth.length > 0 && (
                            <div className="bg-amber-100 p-3 rounded">
                              <p className="text-sm font-medium text-amber-900 mb-1">Areas for Growth:</p>
                              <ul className="text-sm text-amber-800 space-y-1">
                                {result.areas_for_growth.map((area, idx) => (
                                  <li key={idx} className="flex items-start">
                                    <AlertTriangle className="w-3 h-3 mr-1 mt-0.5 flex-shrink-0" />
                                    {area}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>

                        {/* Component Scores */}
                        {result.component_scores && (
                          <div className="bg-gray-100 p-3 rounded">
                            <p className="text-sm font-medium text-gray-700 mb-2">Score Breakdown:</p>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div className="flex justify-between">
                                <span>Core Meaning:</span>
                                <span className="font-medium">{result.component_scores.core_meaning}/40</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Context Understanding:</span>
                                <span className="font-medium">{result.component_scores.context_appropriateness}/30</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Completeness:</span>
                                <span className="font-medium">{result.component_scores.completeness}/20</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Clarity:</span>
                                <span className="font-medium">{result.component_scores.clarity}/10</span>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-2 justify-center">
                <Button onClick={() => {
                  const query = classroomId ? `?classroomId=${classroomId}` : ''
                  router.push(`/student/vocabulary/${assignmentId}/practice${query}`)
                }} className="bg-blue-600 hover:bg-blue-700">
                  Return to Assignment
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  // Locked state
  if (pageState === 'locked') {
    return (
      <VocabularyTestLockoutModal
        isOpen={true}
        testAttemptId={testData?.test_attempt_id}
        onUnlockSuccess={() => {
          // Refresh the page to restart the flow
          window.location.reload()
        }}
      />
    )
  }

  return null
}