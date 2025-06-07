'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { studentApi } from '@/lib/studentApi'
import { AcademicCapIcon, CheckCircleIcon } from '@heroicons/react/24/outline'

export default function JoinClassroomPage() {
  const router = useRouter()
  const { user } = useAuth()
  const [classCode, setClassCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess(null)
    
    if (!classCode.trim()) {
      setError('Please enter a class code')
      return
    }

    setLoading(true)
    try {
      const response = await studentApi.joinClassroom({
        class_code: classCode.trim().toUpperCase()
      })
      
      if (response.success) {
        setSuccess(`Successfully joined ${response.classroom?.name || 'the classroom'}!`)
        // Redirect after a short delay to show success message
        setTimeout(() => {
          router.push('/student/dashboard')
        }, 2000)
      } else {
        setError(response.message || 'Failed to join classroom')
      }
    } catch (error: any) {
      if (error.response?.status === 404) {
        setError('Invalid class code. Please check and try again.')
      } else if (error.response?.status === 403) {
        setError('You are already enrolled in this classroom.')
      } else {
        setError('Failed to join classroom. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-primary-100">
            <AcademicCapIcon className="h-8 w-8 text-primary-600" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Join a Classroom
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Enter the class code provided by your teacher
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="class-code" className="sr-only">
                Class Code
              </label>
              <input
                id="class-code"
                name="class-code"
                type="text"
                required
                value={classCode}
                onChange={(e) => setClassCode(e.target.value.toUpperCase())}
                className="appearance-none rounded-md relative block w-full px-3 py-4 border border-gray-300 placeholder-gray-500 text-gray-900 text-center text-2xl font-mono tracking-wider focus:outline-none focus:ring-primary-500 focus:border-primary-500 focus:z-10"
                placeholder="ABC123"
                maxLength={8}
              />
            </div>
          </div>

          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="flex">
                <div className="ml-3">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              </div>
            </div>
          )}

          {success && (
            <div className="rounded-md bg-green-50 p-4">
              <div className="flex">
                <CheckCircleIcon className="h-5 w-5 text-green-400" />
                <div className="ml-3">
                  <p className="text-sm text-green-800">{success}</p>
                  <p className="text-xs text-green-600 mt-1">Redirecting to dashboard...</p>
                </div>
              </div>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={loading || !classCode.trim() || success !== null}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Joining...' : success ? 'Joined!' : 'Join Classroom'}
            </button>
          </div>

          <div className="text-center">
            <button
              type="button"
              onClick={() => router.push('/student/dashboard')}
              className="text-sm text-primary-600 hover:text-primary-500"
            >
              Back to Dashboard
            </button>
          </div>
        </form>

        <div className="mt-6">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-gray-50 text-gray-500">Tips</span>
            </div>
          </div>

          <div className="mt-6 text-sm text-gray-600 space-y-2">
            <p>• Class codes are usually 6 characters long</p>
            <p>• They contain letters and numbers (no O, 0, I, or 1)</p>
            <p>• Ask your teacher if you're having trouble</p>
          </div>
        </div>
        </div>
      </div>
  )
}