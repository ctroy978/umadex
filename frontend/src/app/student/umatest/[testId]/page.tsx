'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { umatestApi } from '@/lib/umatestApi'
import UMATestInterface from '@/components/student/umatest/UMATestInterface'
import { UMATestStartResponse } from '@/lib/umatestApi'
import { Loader2 } from 'lucide-react'

export default function UMATestPage({ params }: { params: { testId: string } }) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { testId: assignmentId } = params // testId is actually the assignment ID
  
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [testData, setTestData] = useState<UMATestStartResponse | null>(null)
  const [showOverrideDialog, setShowOverrideDialog] = useState(false)
  const [overrideCode, setOverrideCode] = useState('')
  const [retryAttempt, setRetryAttempt] = useState(0)

  useEffect(() => {
    // Check if there's an override code in the URL params
    const urlOverrideCode = searchParams.get('override')
    if (urlOverrideCode) {
      loadTestData(urlOverrideCode)
    } else {
      loadTestData()
    }
  }, [assignmentId, searchParams])

  const loadTestData = async (retryWithOverride?: string, retryCount: number = 0) => {
    try {
      setLoading(true)
      setError(null)
      
      // Start/resume test
      const test = retryWithOverride 
        ? await umatestApi.startTestWithOverride(assignmentId, retryWithOverride)
        : await umatestApi.startTest(assignmentId)
      
      // Check if test is already completed
      if (test.status === 'submitted' || test.status === 'graded') {
        console.log('Test already completed, redirecting to results')
        router.push(`/student/umatest/results/${test.test_attempt_id}`)
        return
      }
      
      setTestData(test)
      setShowOverrideDialog(false)
      setRetryAttempt(0) // Reset retry count on success
    } catch (err: any) {
      console.error('Failed to load test:', err)
      console.error('Error response:', err.response?.data)
      
      // Check if it's a schedule restriction error
      if (err.response?.status === 403) {
        const headers = err.response.headers
        if (headers['x-override-required'] === 'true') {
          setShowOverrideDialog(true)
          return
        }
      }
      
      // Handle 500 errors with automatic retry
      if (err.response?.status === 500 && retryCount < 2) {
        console.log(`Retrying test start (attempt ${retryCount + 1})...`)
        setRetryAttempt(retryCount + 1)
        // Wait a short time before retrying
        setTimeout(() => {
          loadTestData(retryWithOverride, retryCount + 1)
        }, 1000 + (retryCount * 500)) // Increasing delay: 1s, 1.5s
        return
      }
      
      // Handle different error response formats
      let errorMessage = 'Failed to load test'
      if (err.response?.data?.detail) {
        // FastAPI validation errors come as an array of objects
        if (Array.isArray(err.response.data.detail)) {
          errorMessage = err.response.data.detail.map((e: any) => e.msg || e.message).join(', ')
        } else if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail
        } else if (typeof err.response.data.detail === 'object') {
          errorMessage = err.response.data.detail.msg || err.response.data.detail.message || 'Failed to load test'
        }
      }
      setError(errorMessage)
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
    console.log('UMATest complete: Redirecting to results')
    
    if (testData) {
      // Redirect to test results page
      router.push(`/student/umatest/results/${testData.test_attempt_id}`)
    } else {
      // Fallback to dashboard
      router.push('/student/dashboard?refresh=true')
    }
  }

  if (loading) {
    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
            <p className="text-gray-600 text-lg font-medium">Loading test...</p>
            <p className="text-gray-500 text-sm mt-2">
              {retryAttempt > 0 
                ? `Retrying connection (attempt ${retryAttempt})...`
                : 'Preparing your test questions'
              }
            </p>
          </div>
        </div>
    )
  }

  if (error) {
    return (
        <div className="min-h-screen bg-gray-50 p-4">
          <div className="max-w-2xl mx-auto mt-8">
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-red-800 mb-2">Unable to Load Test</h3>
              <p className="text-red-700 mb-4">{error}</p>
              <div className="flex space-x-3">
                <button
                  onClick={() => loadTestData()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  Try Again
                </button>
                <button
                  onClick={() => router.back()}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                >
                  Go Back
                </button>
              </div>
            </div>
          </div>
        </div>
    )
  }

  if (!testData) {
    return null
  }

  return (
    <>
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
      
      <UMATestInterface
        testData={testData}
        onComplete={handleTestComplete}
      />
    </>
  )
}