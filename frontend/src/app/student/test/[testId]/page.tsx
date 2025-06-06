'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { testApi } from '@/lib/testApi'
import StudentGuard from '@/components/StudentGuard'
import TestInterface from '@/components/student/test/TestInterface'
import { TestStartResponse, ReadingContentResponse } from '@/types/test'
import { Loader2 } from 'lucide-react'

export default function TestPage({ params }: { params: { testId: string } }) {
  const router = useRouter()
  const { testId: assignmentId } = params // testId is actually the assignment ID
  
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [testData, setTestData] = useState<TestStartResponse | null>(null)
  const [readingContent, setReadingContent] = useState<ReadingContentResponse | null>(null)
  const [showOverrideDialog, setShowOverrideDialog] = useState(false)
  const [overrideCode, setOverrideCode] = useState('')

  useEffect(() => {
    loadTestData()
  }, [assignmentId])

  const loadTestData = async (retryWithOverride?: string) => {
    try {
      setLoading(true)
      setError(null)
      
      // Start/resume test and get reading content in parallel
      const testPromise = retryWithOverride 
        ? testApi.startTestWithOverride(assignmentId, retryWithOverride)
        : testApi.startTest(assignmentId)
      
      const [test, content] = await Promise.all([
        testPromise,
        testApi.getReadingContent(assignmentId)
      ])
      
      setTestData(test)
      setReadingContent(content)
      setShowOverrideDialog(false)
    } catch (err: any) {
      console.error('Failed to load test:', err)
      
      // Check if it's a schedule restriction error
      if (err.response?.status === 403) {
        const headers = err.response.headers
        if (headers['x-override-required'] === 'true') {
          setShowOverrideDialog(true)
          return
        }
      }
      
      setError(err.response?.data?.detail || 'Failed to load test')
    } finally {
      setLoading(false)
    }
  }

  const handleOverrideSubmit = () => {
    if (overrideCode.trim()) {
      loadTestData(overrideCode.trim())
    }
  }

  const handleTestComplete = () => {
    router.push('/student/dashboard')
  }

  if (loading) {
    return (
      <StudentGuard>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
            <p className="text-gray-600 text-lg font-medium">Loading test...</p>
            <p className="text-gray-500 text-sm mt-2">Preparing your comprehension test</p>
          </div>
        </div>
      </StudentGuard>
    )
  }

  if (error) {
    return (
      <StudentGuard>
        <div className="min-h-screen bg-gray-50 p-4">
          <div className="max-w-2xl mx-auto mt-8">
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-red-800 mb-2">Unable to Load Test</h3>
              <p className="text-red-700 mb-4">{error}</p>
              <button
                onClick={() => router.back()}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
              >
                Go Back
              </button>
            </div>
          </div>
        </div>
      </StudentGuard>
    )
  }

  if (!testData || !readingContent) {
    return null
  }

  return (
    <StudentGuard>
      {showOverrideDialog && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Testing Restricted
            </h3>
            <p className="text-gray-600 mb-4">
              Testing is not available during this time. If your teacher has provided an override code, enter it below:
            </p>
            <div className="space-y-4">
              <input
                type="text"
                value={overrideCode}
                onChange={(e) => setOverrideCode(e.target.value.toUpperCase())}
                placeholder="Enter override code"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 font-mono"
                maxLength={8}
              />
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => router.back()}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleOverrideSubmit}
                  disabled={!overrideCode.trim()}
                  className="px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Continue
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      <TestInterface
        testData={testData}
        readingContent={readingContent}
        onComplete={handleTestComplete}
      />
    </StudentGuard>
  )
}