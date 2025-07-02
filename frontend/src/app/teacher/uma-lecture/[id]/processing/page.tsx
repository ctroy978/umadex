'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { 
  AcademicCapIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  SparklesIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import { umalectureApi } from '@/lib/umalectureApi'
import type { LectureProcessingStatus } from '@/lib/umalectureApi'

const processingSteps = [
  { id: 'parse', label: 'Parsing outline structure', icon: ClockIcon },
  { id: 'analyze', label: 'Analyzing images with AI', icon: SparklesIcon },
  { id: 'generate', label: 'Generating interactive content', icon: SparklesIcon },
  { id: 'questions', label: 'Creating assessment questions', icon: ClockIcon },
  { id: 'finalize', label: 'Finalizing lecture structure', icon: CheckCircleIcon }
]

export default function LectureProcessingPage() {
  const router = useRouter()
  const params = useParams()
  const lectureId = params.id as string
  
  const [status, setStatus] = useState<LectureProcessingStatus | null>(null)
  const [currentStep, setCurrentStep] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const processingStatus = await umalectureApi.getProcessingStatus(lectureId)
        setStatus(processingStatus)
        
        if (processingStatus.status === 'published') {
          // Processing complete, redirect to review
          router.push(`/teacher/uma-lecture/${lectureId}/review`)
        } else if (processingStatus.status === 'draft' && processingStatus.processing_error) {
          setError(processingStatus.processing_error)
        } else if (processingStatus.status === 'processing') {
          // Simulate progress through steps
          const stepProgress = Math.min(
            Math.floor((Date.now() - new Date(processingStatus.processing_started_at!).getTime()) / 10000),
            processingSteps.length - 1
          )
          setCurrentStep(stepProgress)
        }
      } catch (err) {
        console.error('Error checking status:', err)
        setError('Failed to check processing status')
      }
    }

    // Check immediately
    checkStatus()

    // Poll every 3 seconds
    const interval = setInterval(checkStatus, 3000)

    return () => clearInterval(interval)
  }, [lectureId, router])

  if (error) {
    return (
      <div className="max-w-2xl mx-auto p-8">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <ExclamationCircleIcon className="h-8 w-8 text-red-500" />
            <h1 className="text-2xl font-bold text-gray-900">Processing Failed</h1>
          </div>
          
          <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
            <p className="text-red-800">{error}</p>
          </div>
          
          <div className="flex items-center justify-between">
            <Link
              href="/teacher/uma-lecture"
              className="text-gray-600 hover:text-gray-700"
            >
              Back to Lectures
            </Link>
            <Link
              href={`/teacher/uma-lecture/${lectureId}/edit`}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
            >
              Edit Lecture
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto p-8">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {/* Header */}
        <div className="flex items-center space-x-3 mb-8">
          <AcademicCapIcon className="h-8 w-8 text-red-500" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Creating Your Interactive Lecture</h1>
            <p className="text-gray-600 mt-1">AI is processing your content. This may take a few minutes.</p>
          </div>
        </div>

        {/* Processing Steps */}
        <div className="space-y-4 mb-8">
          {processingSteps.map((step, index) => {
            const StepIcon = step.icon
            const isActive = index === currentStep
            const isComplete = index < currentStep
            
            return (
              <div key={step.id} className="flex items-center space-x-3">
                <div className={`
                  flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center
                  ${isComplete ? 'bg-green-100' : isActive ? 'bg-primary-100' : 'bg-gray-100'}
                `}>
                  {isComplete ? (
                    <CheckCircleIcon className="h-6 w-6 text-green-600" />
                  ) : (
                    <StepIcon className={`h-6 w-6 ${isActive ? 'text-primary-600 animate-pulse' : 'text-gray-400'}`} />
                  )}
                </div>
                <div className="flex-1">
                  <p className={`text-sm font-medium ${isActive ? 'text-gray-900' : 'text-gray-500'}`}>
                    {step.label}
                  </p>
                  {isActive && (
                    <div className="mt-1 w-full bg-gray-200 rounded-full h-1.5">
                      <div className="bg-primary-600 h-1.5 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* Loading Animation */}
        <div className="flex justify-center mb-6">
          <div className="relative">
            <ArrowPathIcon className="h-12 w-12 text-primary-600 animate-spin" />
            <SparklesIcon className="h-6 w-6 text-yellow-500 absolute top-0 right-0 animate-pulse" />
          </div>
        </div>

        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
          <p className="text-sm text-blue-800">
            <strong>Did you know?</strong> The AI is creating multiple difficulty levels for each topic, 
            generating questions that reference your images, and building an interactive learning path 
            tailored to your students&apos; needs.
          </p>
        </div>

        {/* Action */}
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-500">
            You&apos;ll be automatically redirected when processing is complete.
          </p>
        </div>
      </div>
    </div>
  )
}