'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { 
  ArrowLeftIcon,
  ClockIcon,
  DocumentCheckIcon,
  PencilIcon,
  TrashIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ChevronDownIcon,
  ChevronRightIcon
} from '@heroicons/react/24/outline'
import { useAuth } from '@/hooks/useAuth'
import { api } from '@/lib/api'
import { toast } from 'react-hot-toast'
import { format } from 'date-fns'

interface AnswerKey {
  correct_answer: string
  explanation: string
  evaluation_rubric: string
}

interface TestQuestion {
  id: string
  question_text: string
  difficulty_level: string
  source_content: string
  answer_key: AnswerKey
}

interface TopicQuestions {
  topic_title: string
  source_lecture_id: string
  source_lecture_title: string
  questions: TestQuestion[]
}

interface TestStructure {
  total_questions: number
  topics: Record<string, TopicQuestions>
  generation_metadata: {
    generated_at: string
    ai_model: string
    distribution: {
      basic_intermediate: number
      advanced: number
      expert: number
    }
  }
}

interface LectureInfo {
  id: string
  title: string
  subject: string
  grade_level: string
  topic_count: number
}

interface TestDetail {
  id: string
  test_title: string
  test_description: string | null
  selected_lecture_ids: string[]
  time_limit_minutes: number | null
  attempt_limit: number
  randomize_questions: boolean
  show_feedback_immediately: boolean
  status: 'draft' | 'published' | 'archived'
  test_structure: TestStructure | null
  created_at: string
  updated_at: string
  selected_lectures?: LectureInfo[]
}

interface GenerationStatus {
  status: 'processing' | 'completed' | 'failed'
  error_message?: string
  total_topics_processed: number
  total_questions_generated: number
}

export default function TestDetailPage() {
  const params = useParams()
  const router = useRouter()
  const testId = params.id as string
  
  const [test, setTest] = useState<TestDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus | null>(null)
  const [expandedTopics, setExpandedTopics] = useState<Set<string>>(new Set())
  const [regenerating, setRegenerating] = useState(false)

  useEffect(() => {
    fetchTestDetail()
  }, [testId])

  useEffect(() => {
    if (test && !test.test_structure) {
      // Check generation status if no questions yet
      checkGenerationStatus()
      const interval = setInterval(checkGenerationStatus, 3000)
      return () => clearInterval(interval)
    }
  }, [test])

  const fetchTestDetail = async () => {
    try {
      setLoading(true)
      const response = await api.get<TestDetail>(`/v1/teacher/umatest/tests/${testId}`)
      setTest(response.data)
    } catch (error) {
      console.error('Error fetching test:', error)
      toast.error('Failed to load test details')
    } finally {
      setLoading(false)
    }
  }

  const checkGenerationStatus = async () => {
    try {
      const response = await api.get<GenerationStatus>(`/v1/teacher/umatest/tests/${testId}/generation-status`)
      setGenerationStatus(response.data)
      
      // Update regenerating state based on actual status
      if (response.data.status === 'processing') {
        setRegenerating(true)
      } else {
        setRegenerating(false)
      }
      
      if (response.data.status === 'completed') {
        // Refresh test data to get generated questions
        fetchTestDetail()
      } else if (response.data.status === 'failed') {
        toast.error('Question generation failed. Please try again.')
      }
    } catch (error) {
      // Ignore 404 errors (no generation log yet)
      if ((error as any)?.response?.status !== 404) {
        console.error('Error checking generation status:', error)
      }
      setRegenerating(false)
    }
  }

  const handleRegenerate = async () => {
    if (!confirm('This will regenerate all questions for this test. Continue?')) return

    try {
      setRegenerating(true)
      await api.post(`/v1/teacher/umatest/tests/${testId}/generate-questions?regenerate=true`)
      toast.success('Question regeneration started!')
      
      // Start checking generation status immediately and set up polling
      checkGenerationStatus()
      const interval = setInterval(checkGenerationStatus, 3000)
      
      // Store interval ID to clear it when generation completes
      const checkInterval = setInterval(() => {
        if (generationStatus?.status === 'completed' || generationStatus?.status === 'failed') {
          clearInterval(interval)
          clearInterval(checkInterval)
        }
      }, 1000)
    } catch (error) {
      console.error('Error regenerating questions:', error)
      toast.error('Failed to regenerate questions')
      setRegenerating(false)
    }
  }

  const handlePublish = async () => {
    try {
      await api.put(`/v1/teacher/umatest/tests/${testId}`, { status: 'published' })
      toast.success('Test published successfully!')
      fetchTestDetail()
    } catch (error) {
      console.error('Error publishing test:', error)
      toast.error('Failed to publish test')
    }
  }

  const handleArchive = async () => {
    if (!confirm('Archive this test? It will no longer be available to students.')) return

    try {
      await api.put(`/v1/teacher/umatest/tests/${testId}`, { status: 'archived' })
      toast.success('Test archived successfully!')
      fetchTestDetail()
    } catch (error) {
      console.error('Error archiving test:', error)
      toast.error('Failed to archive test')
    }
  }

  const toggleTopic = (topicId: string) => {
    setExpandedTopics(prev => {
      const newSet = new Set(prev)
      if (newSet.has(topicId)) {
        newSet.delete(topicId)
      } else {
        newSet.add(topicId)
      }
      return newSet
    })
  }

  const getDifficultyBadge = (level: string) => {
    const styles = {
      basic: 'bg-green-100 text-green-800',
      intermediate: 'bg-blue-100 text-blue-800',
      advanced: 'bg-purple-100 text-purple-800',
      expert: 'bg-red-100 text-red-800'
    }
    
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${styles[level as keyof typeof styles] || 'bg-gray-100 text-gray-800'}`}>
        {level.charAt(0).toUpperCase() + level.slice(1)}
      </span>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="inline-flex items-center">
          <svg className="animate-spin h-8 w-8 mr-3 text-gray-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Loading test details...
        </div>
      </div>
    )
  }

  if (!test) {
    return (
      <div className="text-center py-12">
        <ExclamationCircleIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">Test not found</h3>
        <div className="mt-6">
          <Link
            href="/teacher/uma-test"
            className="text-primary-600 hover:text-primary-900"
          >
            Back to tests
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/teacher/uma-test"
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeftIcon className="mr-2 h-4 w-4" />
          Back to Tests
        </Link>
        
        <div className="mt-4 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{test.test_title}</h1>
            {test.test_description && (
              <p className="mt-2 text-sm text-gray-600">{test.test_description}</p>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            {test.status === 'draft' && test.test_structure && (
              <button
                onClick={handlePublish}
                className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
              >
                Publish Test
              </button>
            )}
            
            {test.status === 'published' && (
              <button
                onClick={handleArchive}
                className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-yellow-600 hover:bg-yellow-700"
              >
                Archive Test
              </button>
            )}
            
            <Link
              href={`/teacher/uma-test/${testId}/edit`}
              className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <PencilIcon className="mr-2 h-4 w-4" />
              Edit Settings
            </Link>
          </div>
        </div>
      </div>

      {/* Test Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Status</div>
          <div className="mt-1 font-medium">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              test.status === 'published' ? 'bg-green-100 text-green-800' :
              test.status === 'archived' ? 'bg-yellow-100 text-yellow-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {test.status.charAt(0).toUpperCase() + test.status.slice(1)}
            </span>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Total Questions</div>
          <div className="mt-1 text-2xl font-semibold">
            {test.test_structure?.total_questions || 0}
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Time Limit</div>
          <div className="mt-1 font-medium">
            {test.time_limit_minutes ? `${test.time_limit_minutes} minutes` : 'No limit'}
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Attempt Limit</div>
          <div className="mt-1 font-medium">
            {test.attempt_limit} {test.attempt_limit === 1 ? 'attempt' : 'attempts'}
          </div>
        </div>
      </div>

      {/* Generation Status */}
      {generationStatus && generationStatus.status === 'processing' && (
        <div className="mb-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center">
            <svg className="animate-spin h-5 w-5 mr-3 text-blue-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <div>
              <p className="text-sm font-medium text-blue-900">Generating questions...</p>
              <p className="text-xs text-blue-700 mt-1">
                Processing topic {generationStatus.total_topics_processed + 1}...
              </p>
            </div>
          </div>
        </div>
      )}

      {generationStatus && generationStatus.status === 'failed' && (
        <div className="mb-8 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <ExclamationCircleIcon className="h-5 w-5 mr-3 text-red-600" />
            <div>
              <p className="text-sm font-medium text-red-900">Question generation failed</p>
              <p className="text-xs text-red-700 mt-1">
                {generationStatus.error_message || 'An error occurred during generation'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Selected Lectures */}
      {test.selected_lectures && test.selected_lectures.length > 0 && (
        <div className="mb-8 bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Selected Lectures</h2>
          <div className="space-y-2">
            {test.selected_lectures.map((lecture) => (
              <div key={lecture.id} className="flex items-center justify-between py-2 border-b last:border-0">
                <div>
                  <div className="font-medium text-gray-900">{lecture.title}</div>
                  <div className="text-sm text-gray-500">
                    {lecture.subject} • {lecture.grade_level} • {lecture.topic_count} topics
                  </div>
                </div>
                <div className="text-sm text-gray-500">
                  {lecture.topic_count * 10} questions
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Questions */}
      {test.test_structure && test.test_structure.topics && Object.keys(test.test_structure.topics).length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">Generated Questions</h2>
              <button
                onClick={handleRegenerate}
                disabled={regenerating}
                className="inline-flex items-center px-3 py-1 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                <ArrowPathIcon className={`mr-2 h-4 w-4 ${regenerating ? 'animate-spin' : ''}`} />
                Regenerate All
              </button>
            </div>
          </div>
          
          <div className="divide-y divide-gray-200">
            {Object.entries(test.test_structure.topics).map(([topicId, topic]) => (
              <div key={topicId} className="p-6">
                <button
                  onClick={() => toggleTopic(topicId)}
                  className="w-full flex items-center justify-between text-left"
                >
                  <div>
                    <h3 className="text-base font-medium text-gray-900">{topic.topic_title}</h3>
                    <p className="text-sm text-gray-500 mt-1">
                      From: {topic.source_lecture_title} • {topic.questions.length} questions
                    </p>
                  </div>
                  {expandedTopics.has(topicId) ? (
                    <ChevronDownIcon className="h-5 w-5 text-gray-400" />
                  ) : (
                    <ChevronRightIcon className="h-5 w-5 text-gray-400" />
                  )}
                </button>
                
                {expandedTopics.has(topicId) && (
                  <div className="mt-4 space-y-4">
                    {topic.questions.map((question, index) => (
                      <div key={question.id} className="border rounded-lg p-4 bg-gray-50">
                        <div className="flex items-start justify-between mb-2">
                          <span className="text-sm font-medium text-gray-700">Question {index + 1}</span>
                          {getDifficultyBadge(question.difficulty_level)}
                        </div>
                        
                        <p className="text-gray-900 mb-3">{question.question_text}</p>
                        
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="font-medium text-gray-700">Correct Answer:</span>
                            <p className="text-gray-600 mt-1">{question.answer_key.correct_answer}</p>
                          </div>
                          
                          <div>
                            <span className="font-medium text-gray-700">Explanation:</span>
                            <p className="text-gray-600 mt-1">{question.answer_key.explanation}</p>
                          </div>
                          
                          <div>
                            <span className="font-medium text-gray-700">Evaluation Rubric:</span>
                            <p className="text-gray-600 mt-1">{question.answer_key.evaluation_rubric}</p>
                          </div>
                          
                          <details className="mt-2">
                            <summary className="cursor-pointer text-gray-500 hover:text-gray-700">
                              View source excerpt
                            </summary>
                            <p className="mt-2 text-gray-600 bg-white p-2 rounded border border-gray-200">
                              {question.source_content}
                            </p>
                          </details>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* No questions yet */}
      {(!test.test_structure || !test.test_structure.topics || Object.keys(test.test_structure.topics).length === 0) && !generationStatus && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <DocumentCheckIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No questions generated yet</h3>
          <p className="mt-1 text-sm text-gray-500">
            Click the button below to generate questions for this test.
          </p>
          <div className="mt-6">
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50"
            >
              <ArrowPathIcon className={`mr-2 h-5 w-5 ${regenerating ? 'animate-spin' : ''}`} />
              Generate Questions
            </button>
          </div>
        </div>
      )}
    </div>
  )
}