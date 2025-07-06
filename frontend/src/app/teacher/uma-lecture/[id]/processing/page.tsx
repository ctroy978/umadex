'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { 
  AcademicCapIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  DocumentTextIcon,
  PhotoIcon,
  SparklesIcon,
  QuestionMarkCircleIcon,
  RocketLaunchIcon
} from '@heroicons/react/24/outline'
import { umalectureApi } from '@/lib/umalectureApi'
import type { LectureProcessingStatus } from '@/lib/umalectureApi'

const processingSteps = [
  { 
    id: 'parse', 
    label: 'Parsing outline structure', 
    icon: DocumentTextIcon,
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    description: 'Analyzing your lecture outline'
  },
  { 
    id: 'analyze', 
    label: 'Analyzing images with AI', 
    icon: PhotoIcon,
    color: 'text-purple-600',
    bgColor: 'bg-purple-100',
    description: 'Processing visual content'
  },
  { 
    id: 'generate', 
    label: 'Generating interactive content', 
    icon: SparklesIcon,
    color: 'text-amber-600',
    bgColor: 'bg-amber-100',
    description: 'Creating engaging materials'
  },
  { 
    id: 'questions', 
    label: 'Creating assessment questions', 
    icon: QuestionMarkCircleIcon,
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-100',
    description: 'Building comprehension checks'
  },
  { 
    id: 'finalize', 
    label: 'Finalizing lecture structure', 
    icon: RocketLaunchIcon,
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    description: 'Preparing for launch'
  }
]

export default function LectureProcessingPage() {
  const router = useRouter()
  const params = useParams()
  const lectureId = params.id as string
  
  const [status, setStatus] = useState<LectureProcessingStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [stepStatuses, setStepStatuses] = useState<{[key: string]: string}>({})
  const [currentMessage, setCurrentMessage] = useState(0)

  // Rotating messages for engagement
  const messages = [
    "AI is analyzing your content and creating personalized learning paths...",
    "Building interactive elements to engage your students...",
    "Crafting questions that reinforce key concepts...",
    "Almost there! Finalizing your interactive lecture..."
  ]

  // Initialize step statuses
  useEffect(() => {
    const initialStatuses: {[key: string]: string} = {}
    processingSteps.forEach(step => {
      initialStatuses[step.id] = 'pending'
    })
    setStepStatuses(initialStatuses)
  }, [])

  // Rotate messages
  useEffect(() => {
    const messageInterval = setInterval(() => {
      setCurrentMessage((prev) => (prev + 1) % messages.length)
    }, 4000)
    return () => clearInterval(messageInterval)
  }, [messages.length])

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const processingStatus = await umalectureApi.getProcessingStatus(lectureId)
        setStatus(processingStatus)
        
        if (processingStatus.status === 'published') {
          // Add a small delay before redirect for visual satisfaction
          setTimeout(() => {
            router.push(`/teacher/uma-lecture/${lectureId}/review`)
          }, 1000)
        } else if (processingStatus.status === 'draft' && processingStatus.processing_error) {
          setError(processingStatus.processing_error)
        } else if (processingStatus.status === 'processing') {
          // Calculate elapsed time
          if (processingStatus.processing_started_at) {
            const startTime = new Date(processingStatus.processing_started_at).getTime()
            const elapsed = Date.now() - startTime
            setElapsedTime(Math.floor(elapsed / 1000))
          }
          
          // Update step statuses from actual processing data
          if (processingStatus.processing_steps) {
            const newStepStatuses: {[key: string]: string} = {}
            
            processingSteps.forEach((step) => {
              const stepData = processingStatus.processing_steps?.[step.id]
              if (stepData) {
                newStepStatuses[step.id] = stepData.status
              } else {
                newStepStatuses[step.id] = 'pending'
              }
            })
            
            setStepStatuses(newStepStatuses)
          }
        }
      } catch (err) {
        console.error('Error checking status:', err)
        setError('Failed to check processing status')
      }
    }

    // Check immediately
    checkStatus()

    // Poll every 2 seconds for more responsive updates
    const interval = setInterval(checkStatus, 2000)

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

  // Check if all steps are completed
  const allCompleted = Object.values(stepStatuses).every(status => status === 'completed')

  return (
    <div className="max-w-3xl mx-auto p-8">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
            <AcademicCapIcon className="h-10 w-10 text-red-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {allCompleted ? 'Lecture Ready!' : 'Creating Your Interactive Lecture'}
          </h1>
          <p className="text-gray-600 text-lg">
            {allCompleted ? 'Your lecture has been successfully created!' : messages[currentMessage]}
          </p>
        </div>

        {/* Timer Display */}
        {elapsedTime > 0 && !allCompleted && (
          <div className="text-center mb-8">
            <div className="inline-flex items-center px-4 py-2 bg-gray-100 rounded-full">
              <span className="text-sm text-gray-500 mr-2">Time elapsed:</span>
              <span className="text-sm font-medium text-gray-900">
                {Math.floor(elapsedTime / 60)}:{(elapsedTime % 60).toString().padStart(2, '0')}
              </span>
            </div>
          </div>
        )}

        {/* Processing Steps Grid */}
        <div className="grid gap-4 mb-8">
          {processingSteps.map((step) => {
            const StepIcon = step.icon
            const stepStatus = stepStatuses[step.id] || 'pending'
            const isActive = stepStatus === 'in_progress'
            const isComplete = stepStatus === 'completed'
            const isPending = stepStatus === 'pending'
            
            return (
              <div 
                key={step.id} 
                className={`
                  relative rounded-lg border-2 p-4 transition-all duration-500
                  ${isComplete ? 'border-green-500 bg-green-50' : 
                    isActive ? 'border-primary-500 bg-primary-50 shadow-lg' : 
                    'border-gray-200 bg-white'}
                `}
              >
                <div className="flex items-center">
                  {/* Icon Container */}
                  <div className="relative mr-4">
                    <div className={`
                      w-12 h-12 rounded-full flex items-center justify-center transition-all duration-500
                      ${isComplete ? 'bg-green-100' : isActive ? step.bgColor : 'bg-gray-100'}
                    `}>
                      {isComplete ? (
                        <CheckCircleIcon className="h-7 w-7 text-green-600" />
                      ) : (
                        <StepIcon 
                          className={`
                            h-7 w-7 transition-all duration-500
                            ${isActive ? `${step.color} animate-pulse` : 'text-gray-400'}
                          `} 
                        />
                      )}
                    </div>
                    
                    {/* Loading spinner for active step */}
                    {isActive && (
                      <div className="absolute inset-0 -m-1">
                        <svg className="w-14 h-14 animate-spin" viewBox="0 0 24 24">
                          <circle 
                            className="opacity-25" 
                            cx="12" 
                            cy="12" 
                            r="10" 
                            stroke="currentColor" 
                            strokeWidth="3"
                            fill="none"
                          />
                          <path 
                            className="opacity-75" 
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="3"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                          />
                        </svg>
                      </div>
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1">
                    <h3 className={`
                      font-semibold transition-all duration-500
                      ${isComplete ? 'text-green-700' : isActive ? 'text-gray-900' : 'text-gray-500'}
                    `}>
                      {step.label}
                    </h3>
                    <p className={`
                      text-sm mt-1 transition-all duration-500
                      ${isComplete ? 'text-green-600' : isActive ? 'text-gray-600' : 'text-gray-400'}
                    `}>
                      {isComplete ? 'Completed' : isActive ? step.description : 'Waiting...'}
                    </p>
                  </div>

                  {/* Status indicator */}
                  <div className="ml-4">
                    {isActive && (
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                        <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Success State */}
        {allCompleted && (
          <div className="text-center">
            <div className="inline-flex items-center px-6 py-3 bg-green-100 text-green-700 rounded-full mb-4">
              <CheckCircleIcon className="h-5 w-5 mr-2" />
              <span className="font-medium">All steps completed successfully!</span>
            </div>
            <p className="text-sm text-gray-500">Redirecting to your lecture...</p>
          </div>
        )}

        {/* Info Box */}
        {!allCompleted && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex">
              <SparklesIcon className="h-5 w-5 text-blue-600 mt-0.5 mr-2 flex-shrink-0" />
              <div>
                <p className="text-sm text-blue-800">
                  <strong>AI Magic in Progress</strong>
                </p>
                <p className="text-sm text-blue-700 mt-1">
                  We're creating multiple difficulty levels, generating contextual questions, 
                  and building an adaptive learning experience tailored to your content.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}