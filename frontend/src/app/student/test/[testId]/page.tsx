'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { testApi } from '@/lib/testApi'
import TestInterface from '@/components/student/test/TestInterface'
import { TestStartResponse, ReadingContentResponse } from '@/types/test'
import { Loader2, LockIcon } from 'lucide-react'
import UnlockTestModal from '@/components/student/test/UnlockTestModal'

export default function TestPage({ params }: { params: { testId: string } }) {
  const router = useRouter()
  const { testId: assignmentId } = params // testId is actually the assignment ID
  
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [testData, setTestData] = useState<TestStartResponse | null>(null)
  const [readingContent, setReadingContent] = useState<ReadingContentResponse | null>(null)
  const [showOverrideDialog, setShowOverrideDialog] = useState(false)
  const [overrideCode, setOverrideCode] = useState('')
  const [retryAttempt, setRetryAttempt] = useState(0)
  const [isTestLocked, setIsTestLocked] = useState(false)
  const [showUnlockModal, setShowUnlockModal] = useState(false)
  const [testAttemptId, setTestAttemptId] = useState<string | null>(null)

  useEffect(() => {
    loadTestData()
  }, [assignmentId])

  const loadTestData = async (retryWithOverride?: string, retryCount: number = 0) => {
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
      
      // Check if test is locked
      if (test.status === 'locked') {
        setIsTestLocked(true)
        setTestAttemptId(test.test_attempt_id)
        setError('This test has been locked due to security violations.')
        return
      }
      
      setTestData(test)
      setReadingContent(content)
      setShowOverrideDialog(false)
      setRetryAttempt(0) // Reset retry count on success
    } catch (err: any) {
      console.error('Failed to load test:', err)
      
      // Check if it's a test locked error (403 with locked message)
      if (err.response?.status === 403 && err.response?.data?.detail?.includes('locked')) {
        setIsTestLocked(true)
        // Try to extract test attempt ID from error message or response
        const attemptIdMatch = err.response?.data?.detail?.match(/attempt_id[:\s]+([a-f0-9-]+)/i)
        if (attemptIdMatch) {
          setTestAttemptId(attemptIdMatch[1])
        }
        setError('This test has been locked due to security violations.')
        return
      }
      
      // Check if it's a schedule restriction error
      if (err.response?.status === 403) {
        const headers = err.response.headers
        if (headers['x-override-required'] === 'true') {
          setShowOverrideDialog(true)
          return
        }
      }
      
      // Check if it's a test locked error in 500 response
      if (err.response?.data?.detail?.includes('locked')) {
        setIsTestLocked(true)
        // Try to extract test attempt ID from error message or response
        const attemptIdMatch = err.response?.data?.detail?.match(/attempt_id[:\s]+([a-f0-9-]+)/i)
        if (attemptIdMatch) {
          setTestAttemptId(attemptIdMatch[1])
        }
        setError('This test has been locked due to security violations.')
        return
      }
      
      // Handle 500 errors (like duplicate key constraints) with automatic retry
      if (err.response?.status === 500 && retryCount < 2) {
        console.log(`Retrying test start (attempt ${retryCount + 1})...`)
        setRetryAttempt(retryCount + 1)
        // Wait a short time before retrying
        setTimeout(() => {
          loadTestData(retryWithOverride, retryCount + 1)
        }, 1000 + (retryCount * 500)) // Increasing delay: 1s, 1.5s
        return
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
    console.log('=== TEST COMPLETE: Redirecting and triggering data refresh ===')
    
    // Try to go back to where they came from, or default to dashboard
    // Check if they came from a classroom page
    const referrer = document.referrer
    const classroomMatch = referrer.match(/\/student\/classrooms\/([^\/]+)/)
    
    if (classroomMatch) {
      // They came from a classroom page, redirect back there with refresh
      const classroomId = classroomMatch[1]
      router.push(`/student/classrooms/${classroomId}?refresh=true`)
    } else {
      // Default to dashboard with refresh
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
                : 'Preparing your comprehension test'
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
              {isTestLocked && (
                <div className="flex justify-center mb-4">
                  <LockIcon className="h-12 w-12 text-red-600" />
                </div>
              )}
              <h3 className="text-lg font-semibold text-red-800 mb-2">
                {isTestLocked ? 'Test Locked' : 'Unable to Load Test'}
              </h3>
              <p className="text-red-700 mb-4">{error}</p>
              {isTestLocked && (
                <p className="text-red-600 mb-4 text-sm">
                  Contact your teacher for assistance or use a bypass code if you have one.
                </p>
              )}
              <div className="flex space-x-3">
                {isTestLocked && (
                  <button
                    onClick={() => setShowUnlockModal(true)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                  >
                    Enter Bypass Code
                  </button>
                )}
                {!isTestLocked && (
                  <button
                    onClick={() => loadTestData()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                  >
                    Try Again
                  </button>
                )}
                <button
                  onClick={() => router.push('/student/dashboard')}
                  className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
                >
                  Return to Dashboard
                </button>
              </div>
            </div>
          </div>
          
          {/* Unlock Modal */}
          {showUnlockModal && testAttemptId && (
            <UnlockTestModal
              isOpen={showUnlockModal}
              testAttemptId={testAttemptId}
              onUnlockSuccess={() => {
                setShowUnlockModal(false)
                setIsTestLocked(false)
                setError(null)
                loadTestData() // Reload the test
              }}
              onCancel={() => setShowUnlockModal(false)}
            />
          )}
        </div>
    )
  }

  if (!testData || !readingContent) {
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
                  onClick={() => router.push('/student/dashboard')}
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
    </>
  )
}