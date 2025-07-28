'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthSupabase } from '@/hooks/useAuthSupabase'
import { api } from '@/lib/api'
import { toast } from 'react-hot-toast'
import { 
  ArrowLeftIcon,
  DocumentCheckIcon,
  ClockIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline'
import Link from 'next/link'

interface LectureInfo {
  id: string
  title: string
  subject: string
  grade_level: string
  topic_count: number
}

interface CreateTestForm {
  test_title: string
  test_description: string
  selected_lecture_ids: string[]
  time_limit_minutes: number | null
  attempt_limit: number
  randomize_questions: boolean
  show_feedback_immediately: boolean
}

export default function NewTestPage() {
  const router = useRouter()
  const { user } = useAuthSupabase()
  const [loading, setLoading] = useState(false)
  const [lectures, setLectures] = useState<LectureInfo[]>([])
  const [loadingLectures, setLoadingLectures] = useState(true)
  const [generating, setGenerating] = useState(false)
  
  const [form, setForm] = useState<CreateTestForm>({
    test_title: '',
    test_description: '',
    selected_lecture_ids: [],
    time_limit_minutes: null,
    attempt_limit: 1,
    randomize_questions: false,
    show_feedback_immediately: true
  })

  useEffect(() => {
    fetchAvailableLectures()
  }, [])

  const fetchAvailableLectures = async () => {
    try {
      setLoadingLectures(true)
      const response = await api.get<LectureInfo[]>('/v1/teacher/umatest/lectures/available')
      setLectures(response.data)
    } catch (error) {
      console.error('Error fetching lectures:', error)
      toast.error('Failed to load available lectures')
    } finally {
      setLoadingLectures(false)
    }
  }

  const handleLectureToggle = (lectureId: string) => {
    setForm(prev => ({
      ...prev,
      selected_lecture_ids: prev.selected_lecture_ids.includes(lectureId)
        ? prev.selected_lecture_ids.filter(id => id !== lectureId)
        : [...prev.selected_lecture_ids, lectureId]
    }))
  }

  const calculateTotalQuestions = () => {
    const selectedLectures = lectures.filter(l => form.selected_lecture_ids.includes(l.id))
    const totalTopics = selectedLectures.reduce((sum, lecture) => sum + lecture.topic_count, 0)
    return totalTopics * 10 // 10 questions per topic
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!form.test_title.trim()) {
      toast.error('Please enter a test title')
      return
    }
    
    if (form.selected_lecture_ids.length === 0) {
      toast.error('Please select at least one lecture')
      return
    }

    try {
      setLoading(true)
      
      // Create the test
      const createResponse = await api.post('/v1/teacher/umatest/tests', {
        ...form,
        time_limit_minutes: form.time_limit_minutes || null
      })
      
      const testId = createResponse.data.id
      toast.success('Test created successfully!')
      
      // Start generating questions
      setGenerating(true)
      try {
        await api.post(`/v1/teacher/umatest/tests/${testId}/generate-questions`)
        toast.success('Question generation started!')
      } catch (error) {
        console.error('Error starting generation:', error)
        toast.error('Failed to start question generation')
      }
      
      // Navigate to the test detail page
      router.push(`/teacher/uma-test/${testId}`)
      
    } catch (error) {
      console.error('Error creating test:', error)
      toast.error('Failed to create test')
    } finally {
      setLoading(false)
      setGenerating(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/teacher/uma-test"
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeftIcon className="mr-2 h-4 w-4" />
          Back to Tests
        </Link>
        
        <h1 className="mt-4 text-2xl font-bold text-gray-900">Create New Test</h1>
        <p className="mt-2 text-sm text-gray-600">
          Select UMALecture assignments to generate a comprehensive test with AI-powered questions.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Test Information */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Test Information</h2>
          
          <div className="space-y-4">
            <div>
              <label htmlFor="title" className="block text-sm font-medium text-gray-700">
                Test Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="title"
                value={form.test_title}
                onChange={(e) => setForm(prev => ({ ...prev, test_title: e.target.value }))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                placeholder="e.g., Biology Unit 1 Test"
              />
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                Description
              </label>
              <textarea
                id="description"
                rows={3}
                value={form.test_description}
                onChange={(e) => setForm(prev => ({ ...prev, test_description: e.target.value }))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                placeholder="Optional description for the test..."
              />
            </div>
          </div>
        </div>

        {/* Test Configuration */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Test Configuration</h2>
          
          <div className="space-y-4">
            <div>
              <label htmlFor="time-limit" className="block text-sm font-medium text-gray-700">
                Time Limit (minutes)
              </label>
              <input
                type="number"
                id="time-limit"
                min="0"
                value={form.time_limit_minutes || ''}
                onChange={(e) => setForm(prev => ({ 
                  ...prev, 
                  time_limit_minutes: e.target.value ? parseInt(e.target.value) : null 
                }))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                placeholder="No time limit"
              />
              <p className="mt-1 text-xs text-gray-500">Leave empty for no time limit</p>
            </div>

            <div>
              <label htmlFor="attempts" className="block text-sm font-medium text-gray-700">
                Attempt Limit
              </label>
              <input
                type="number"
                id="attempts"
                min="1"
                value={form.attempt_limit}
                onChange={(e) => setForm(prev => ({ 
                  ...prev, 
                  attempt_limit: parseInt(e.target.value) || 1 
                }))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>

            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={form.randomize_questions}
                  onChange={(e) => setForm(prev => ({ ...prev, randomize_questions: e.target.checked }))}
                  className="rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                />
                <span className="ml-2 text-sm text-gray-700">Randomize question order</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={form.show_feedback_immediately}
                  onChange={(e) => setForm(prev => ({ ...prev, show_feedback_immediately: e.target.checked }))}
                  className="rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                />
                <span className="ml-2 text-sm text-gray-700">Show feedback immediately after each answer</span>
              </label>
            </div>
          </div>
        </div>

        {/* Lecture Selection */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Select Lectures <span className="text-red-500">*</span>
          </h2>
          
          {loadingLectures ? (
            <div className="text-center py-8">
              <div className="inline-flex items-center">
                <svg className="animate-spin h-5 w-5 mr-3 text-gray-500" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Loading available lectures...
              </div>
            </div>
          ) : lectures.length === 0 ? (
            <div className="text-center py-8">
              <ExclamationCircleIcon className="mx-auto h-12 w-12 text-gray-400" />
              <p className="mt-2 text-sm text-gray-500">
                No published UMALecture assignments found. Please create and publish some lectures first.
              </p>
            </div>
          ) : (
            <>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {lectures.map((lecture) => (
                  <label
                    key={lecture.id}
                    className={`flex items-start p-3 border rounded-lg cursor-pointer transition-colors ${
                      form.selected_lecture_ids.includes(lecture.id)
                        ? 'bg-primary-50 border-primary-300'
                        : 'bg-white border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={form.selected_lecture_ids.includes(lecture.id)}
                      onChange={() => handleLectureToggle(lecture.id)}
                      className="mt-1 rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                    />
                    <div className="ml-3 flex-1">
                      <div className="font-medium text-gray-900">{lecture.title}</div>
                      <div className="text-sm text-gray-500">
                        {lecture.subject} • {lecture.grade_level} • {lecture.topic_count} topics
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        Will generate {lecture.topic_count * 10} questions (10 per topic)
                      </div>
                    </div>
                  </label>
                ))}
              </div>

              {/* Question Summary */}
              {form.selected_lecture_ids.length > 0 && (
                <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                  <div className="flex items-center">
                    <DocumentCheckIcon className="h-5 w-5 text-blue-600 mr-2" />
                    <div className="text-sm">
                      <span className="font-medium text-blue-900">Total questions to be generated: </span>
                      <span className="text-blue-700">{calculateTotalQuestions()}</span>
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-blue-600">
                    Distribution per topic: 7 Basic/Intermediate (70%), 2 Advanced (20%), 1 Expert (10%)
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Submit Button */}
        <div className="flex justify-end gap-4">
          <Link
            href="/teacher/uma-test"
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={loading || generating || form.selected_lecture_ids.length === 0}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading || generating ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {generating ? 'Generating Questions...' : 'Creating Test...'}
              </>
            ) : (
              'Create Test & Generate Questions'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}