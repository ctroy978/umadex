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
  ExclamationCircleIcon,
  BookOpenIcon,
  PencilSquareIcon
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
  test_type: 'lecture_based' | 'hand_built'
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
    test_type: 'lecture_based',
    selected_lecture_ids: [],
    time_limit_minutes: null,
    attempt_limit: 1,
    randomize_questions: false,
    show_feedback_immediately: true
  })

  useEffect(() => {
    if (form.test_type === 'lecture_based') {
      fetchAvailableLectures()
    }
  }, [form.test_type])

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
    
    if (form.test_type === 'lecture_based' && form.selected_lecture_ids.length === 0) {
      toast.error('Please select at least one lecture')
      return
    }

    try {
      setLoading(true)
      
      // Create the test
      const createResponse = await api.post('/v1/teacher/umatest/tests', {
        ...form,
        selected_lecture_ids: form.test_type === 'lecture_based' ? form.selected_lecture_ids : null,
        time_limit_minutes: form.time_limit_minutes || null
      })
      
      const testId = createResponse.data.id
      toast.success('Test created successfully!')
      
      // For lecture-based tests, start generating questions
      if (form.test_type === 'lecture_based') {
        setGenerating(true)
        try {
          await api.post(`/v1/teacher/umatest/tests/${testId}/generate-questions`)
          toast.success('Question generation started!')
        } catch (error) {
          console.error('Error starting generation:', error)
          toast.error('Failed to start question generation')
        }
      }
      
      // Navigate to the appropriate page
      if (form.test_type === 'hand_built') {
        router.push(`/teacher/uma-test/${testId}/build`)
      } else {
        router.push(`/teacher/uma-test/${testId}`)
      }
      
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
          Choose between creating a test from UMALecture content or building your own custom questions.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Test Type Selection */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Test Type</h2>
          
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="relative cursor-pointer">
              <input
                type="radio"
                name="test_type"
                value="lecture_based"
                checked={form.test_type === 'lecture_based'}
                onChange={(e) => setForm(prev => ({ 
                  ...prev, 
                  test_type: 'lecture_based',
                  selected_lecture_ids: []
                }))}
                className="sr-only peer"
              />
              <div className="flex items-center p-4 border-2 rounded-lg peer-checked:border-primary-500 peer-checked:bg-primary-50">
                <BookOpenIcon className="h-8 w-8 text-gray-400 peer-checked:text-primary-600 mr-3" />
                <div>
                  <p className="font-medium">Lecture-Based Test</p>
                  <p className="text-sm text-gray-500">Generate questions from UMALecture content</p>
                </div>
              </div>
            </label>

            <label className="relative cursor-pointer">
              <input
                type="radio"
                name="test_type"
                value="hand_built"
                checked={form.test_type === 'hand_built'}
                onChange={(e) => setForm(prev => ({ 
                  ...prev, 
                  test_type: 'hand_built',
                  selected_lecture_ids: []
                }))}
                className="sr-only peer"
              />
              <div className="flex items-center p-4 border-2 rounded-lg peer-checked:border-primary-500 peer-checked:bg-primary-50">
                <PencilSquareIcon className="h-8 w-8 text-gray-400 peer-checked:text-primary-600 mr-3" />
                <div>
                  <p className="font-medium">Hand-Built Test</p>
                  <p className="text-sm text-gray-500">Create your own custom questions</p>
                </div>
              </div>
            </label>
          </div>
        </div>

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
                Maximum Attempts
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

            <div className="space-y-3">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={form.randomize_questions}
                  onChange={(e) => setForm(prev => ({ 
                    ...prev, 
                    randomize_questions: e.target.checked 
                  }))}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700">
                  Randomize question order
                </span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={form.show_feedback_immediately}
                  onChange={(e) => setForm(prev => ({ 
                    ...prev, 
                    show_feedback_immediately: e.target.checked 
                  }))}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700">
                  Show feedback immediately after submission
                </span>
              </label>
            </div>
          </div>
        </div>

        {/* Lecture Selection (only for lecture-based tests) */}
        {form.test_type === 'lecture_based' && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Select Lectures <span className="text-red-500">*</span>
            </h2>
            
            {loadingLectures ? (
              <div className="text-center py-8 text-gray-500">
                Loading available lectures...
              </div>
            ) : lectures.length === 0 ? (
              <div className="text-center py-8">
                <ExclamationCircleIcon className="mx-auto h-12 w-12 text-gray-400" />
                <p className="mt-2 text-sm text-gray-500">
                  No published UMALecture assignments found
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Create and publish UMALecture assignments first
                </p>
              </div>
            ) : (
              <>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {lectures.map((lecture) => (
                    <label
                      key={lecture.id}
                      className="flex items-start p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={form.selected_lecture_ids.includes(lecture.id)}
                        onChange={() => handleLectureToggle(lecture.id)}
                        className="h-4 w-4 mt-1 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      />
                      <div className="ml-3 flex-1">
                        <p className="text-sm font-medium text-gray-900">{lecture.title}</p>
                        <p className="text-xs text-gray-500">
                          {lecture.subject} • Grade {lecture.grade_level} • {lecture.topic_count} topics
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
                
                {form.selected_lecture_ids.length > 0 && (
                  <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                    <p className="text-sm text-blue-800">
                      <span className="font-medium">Selected:</span> {form.selected_lecture_ids.length} lecture(s)
                    </p>
                    <p className="text-xs text-blue-600 mt-1">
                      Estimated questions: ~{calculateTotalQuestions()}
                    </p>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Hand-Built Test Info (only for hand-built tests) */}
        {form.test_type === 'hand_built' && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex">
              <ExclamationCircleIcon className="h-5 w-5 text-blue-400 mt-0.5" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-blue-800">Hand-Built Test</h3>
                <p className="mt-1 text-sm text-blue-700">
                  After creating the test, you'll be able to add your own questions with:
                </p>
                <ul className="mt-2 text-sm text-blue-600 list-disc list-inside">
                  <li>Custom question text</li>
                  <li>Correct answer</li>
                  <li>Explanation for students</li>
                  <li>Evaluation rubric for grading</li>
                  <li>Difficulty level (Basic, Intermediate, Advanced, Expert)</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end space-x-3">
          <Link
            href="/teacher/uma-test"
            className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            Cancel
          </Link>
          
          <button
            type="submit"
            disabled={loading || generating}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading || generating ? (
              <>
                <ArrowPathIcon className="animate-spin -ml-1 mr-2 h-4 w-4" />
                {generating ? 'Generating Questions...' : 'Creating Test...'}
              </>
            ) : (
              <>
                <CheckCircleIcon className="-ml-1 mr-2 h-4 w-4" />
                {form.test_type === 'hand_built' ? 'Create & Build Questions' : 'Create Test'}
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}