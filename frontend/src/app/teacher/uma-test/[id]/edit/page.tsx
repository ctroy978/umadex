'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'
import { useAuthSupabase } from '@/hooks/useAuthSupabase'
import { api } from '@/lib/api'
import { toast } from 'react-hot-toast'

interface TestDetail {
  id: string
  test_title: string
  test_description: string | null
  time_limit_minutes: number | null
  attempt_limit: number
  randomize_questions: boolean
  show_feedback_immediately: boolean
  status: 'draft' | 'published' | 'archived'
}

interface UpdateTestForm {
  test_title: string
  test_description: string
  time_limit_minutes: number | null
  attempt_limit: number
  randomize_questions: boolean
  show_feedback_immediately: boolean
}

export default function EditTestPage() {
  const params = useParams()
  const router = useRouter()
  const testId = params.id as string
  
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [test, setTest] = useState<TestDetail | null>(null)
  const [form, setForm] = useState<UpdateTestForm>({
    test_title: '',
    test_description: '',
    time_limit_minutes: null,
    attempt_limit: 1,
    randomize_questions: false,
    show_feedback_immediately: true
  })

  useEffect(() => {
    fetchTestDetail()
  }, [testId])

  const fetchTestDetail = async () => {
    try {
      setLoading(true)
      const response = await api.get<TestDetail>(`/v1/teacher/umatest/tests/${testId}`)
      const data = response.data
      
      setTest(data)
      setForm({
        test_title: data.test_title,
        test_description: data.test_description || '',
        time_limit_minutes: data.time_limit_minutes,
        attempt_limit: data.attempt_limit,
        randomize_questions: data.randomize_questions,
        show_feedback_immediately: data.show_feedback_immediately
      })
    } catch (error) {
      console.error('Error fetching test:', error)
      toast.error('Failed to load test details')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!form.test_title.trim()) {
      toast.error('Please enter a test title')
      return
    }

    try {
      setSaving(true)
      
      await api.put(`/v1/teacher/umatest/tests/${testId}`, {
        test_title: form.test_title,
        test_description: form.test_description || null,
        time_limit_minutes: form.time_limit_minutes || null,
        attempt_limit: form.attempt_limit,
        randomize_questions: form.randomize_questions,
        show_feedback_immediately: form.show_feedback_immediately
      })
      
      toast.success('Test settings updated successfully!')
      router.push(`/teacher/uma-test/${testId}`)
      
    } catch (error) {
      console.error('Error updating test:', error)
      toast.error('Failed to update test settings')
    } finally {
      setSaving(false)
    }
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
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href={`/teacher/uma-test/${testId}`}
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeftIcon className="mr-2 h-4 w-4" />
          Back to Test Details
        </Link>
        
        <h1 className="mt-4 text-2xl font-bold text-gray-900">Edit Test Settings</h1>
        <p className="mt-2 text-sm text-gray-600">
          Update the settings for your test. Note: You cannot change the selected lectures after creation.
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

        {/* Current Status */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Current Status</h2>
          <div className="text-sm text-gray-600">
            <p>
              Status: <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                test.status === 'published' ? 'bg-green-100 text-green-800' :
                test.status === 'archived' ? 'bg-yellow-100 text-yellow-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {test.status.charAt(0).toUpperCase() + test.status.slice(1)}
              </span>
            </p>
            <p className="mt-2 text-xs text-gray-500">
              To change the status, use the actions on the test detail page.
            </p>
          </div>
        </div>

        {/* Submit Buttons */}
        <div className="flex justify-end gap-4">
          <Link
            href={`/teacher/uma-test/${testId}`}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Saving...
              </>
            ) : (
              'Save Changes'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}