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

  useEffect(() => {
    loadTestData()
  }, [assignmentId])

  const loadTestData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Start/resume test and get reading content in parallel
      const [test, content] = await Promise.all([
        testApi.startTest(assignmentId),
        testApi.getReadingContent(assignmentId)
      ])
      
      setTestData(test)
      setReadingContent(content)
    } catch (err: any) {
      console.error('Failed to load test:', err)
      setError(err.response?.data?.detail || 'Failed to load test')
    } finally {
      setLoading(false)
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
      <TestInterface
        testData={testData}
        readingContent={readingContent}
        onComplete={handleTestComplete}
      />
    </StudentGuard>
  )
}