'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { studentApi, VocabularyTestStartResponse, VocabularyTestAttemptResponse } from '@/lib/studentApi'
import VocabularyTestInterface from '@/components/student/vocabulary-test/VocabularyTestInterface'
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

type PageState = 'loading' | 'eligibility' | 'instructions' | 'test' | 'results' | 'error'

interface TestResults {
  score_percentage: number
  questions_correct: number
  total_questions: number
  time_spent_seconds?: number
  detailed_results: Array<{
    question_id: string
    question_text: string
    correct_answer: string
    student_answer: string
    score: number
    is_correct: boolean
    explanation: string
  }>
}

export default function VocabularyTestPage() {
  const params = useParams()
  const router = useRouter()
  const assignmentId = params.id as string

  const [pageState, setPageState] = useState<PageState>('loading')
  const [eligibilityData, setEligibilityData] = useState<any>(null)
  const [testData, setTestData] = useState<VocabularyTestStartResponse | null>(null)
  const [results, setResults] = useState<TestResults | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    checkEligibility()
  }, [assignmentId])

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

  const startTest = async () => {
    try {
      setPageState('loading')
      const testResponse = await studentApi.startVocabularyTest(assignmentId)
      setTestData(testResponse)
      setPageState('test')
    } catch (error) {
      console.error('Error starting test:', error)
      setError('Failed to start test. Please try again.')
      setPageState('error')
    }
  }

  const handleTestComplete = (testResults: VocabularyTestAttemptResponse) => {
    setResults(testResults)
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
            <Button onClick={() => router.back()} variant="outline">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Go Back
            </Button>
          </div>
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

                {eligibilityData?.progress_details && (
                  <div className="grid grid-cols-2 gap-2 mt-4">
                    {Object.entries(eligibilityData.progress_details).map(([activity, completed]) => (
                      <div key={activity} className="flex items-center gap-2">
                        {completed ? 
                          <CheckCircle className="w-4 h-4 text-green-500" /> : 
                          <XCircle className="w-4 h-4 text-gray-400" />
                        }
                        <span className="text-sm capitalize">
                          {activity.replace('_', ' ')}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <Button onClick={() => router.back()} variant="outline">
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
                <Button onClick={() => router.back()} variant="outline">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Cancel
                </Button>
                <Button onClick={startTest} className="bg-green-600 hover:bg-green-700">
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
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {results.detailed_results.map((result, index) => (
                    <div key={result.question_id} 
                         className={`p-4 rounded-lg border ${result.is_correct ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                      <div className="flex items-start justify-between mb-2">
                        <span className="font-medium">Question {index + 1}</span>
                        <div className="flex items-center gap-2">
                          {result.is_correct ? 
                            <CheckCircle className="w-5 h-5 text-green-500" /> : 
                            <XCircle className="w-5 h-5 text-red-500" />
                          }
                          <span className="text-sm font-medium">
                            {result.score}%
                          </span>
                        </div>
                      </div>
                      
                      <div className="text-sm space-y-1">
                        <p><strong>Question:</strong> {result.question_text}</p>
                        <p><strong>Your Answer:</strong> {result.student_answer || '(No answer)'}</p>
                        <p><strong>Correct Answer:</strong> {result.correct_answer}</p>
                        {result.explanation && (
                          <p className="text-gray-600"><strong>Explanation:</strong> {result.explanation}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-2 justify-center">
                <Button onClick={() => router.back()} className="bg-blue-600 hover:bg-blue-700">
                  Return to Assignment
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return null
}