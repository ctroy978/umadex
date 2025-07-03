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
  const [stepProgress, setStepProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [stepStatuses, setStepStatuses] = useState<{[key: string]: string}>({})
  const [overallProgress, setOverallProgress] = useState(0)

  // Initialize step statuses
  useEffect(() => {
    const initialStatuses: {[key: string]: string} = {}
    processingSteps.forEach(step => {
      initialStatuses[step.id] = 'pending'
    })
    setStepStatuses(initialStatuses)
  }, [])

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const processingStatus = await umalectureApi.getProcessingStatus(lectureId)
        setStatus(processingStatus)
        console.log('Processing status:', processingStatus)
        console.log('Processing steps:', processingStatus.processing_steps)
        
        if (processingStatus.status === 'published') {
          // Processing complete, redirect to review
          router.push(`/teacher/uma-lecture/${lectureId}/review`)
        } else if (processingStatus.status === 'draft' && processingStatus.processing_error) {
          setError(processingStatus.processing_error)
        } else if (processingStatus.status === 'processing') {
          // Calculate elapsed time
          let elapsed = 0
          if (processingStatus.processing_started_at) {
            const startTime = new Date(processingStatus.processing_started_at).getTime()
            elapsed = Date.now() - startTime
            setElapsedTime(Math.floor(elapsed / 1000))
          }
          
          // Use actual processing steps if available
          if (processingStatus.processing_steps) {
            let activeStepIndex = -1
            let activeStepProgress = 0
            const newStepStatuses: {[key: string]: string} = {}
            
            // Build step statuses map
            processingSteps.forEach((step, index) => {
              const stepData = processingStatus.processing_steps?.[step.id]
              if (stepData) {
                newStepStatuses[step.id] = stepData.status
                if (stepData.status === 'in_progress') {
                  activeStepIndex = index
                  // Calculate progress based on time in current step
                  if (stepData.started_at) {
                    const stepElapsed = Date.now() - new Date(stepData.started_at).getTime()
                    activeStepProgress = Math.min((stepElapsed / 15000) * 100, 90) // Cap at 90%
                  }
                }
              } else {
                newStepStatuses[step.id] = 'pending'
              }
            })
            
            // If no step is in progress, find the last completed step
            if (activeStepIndex === -1) {
              processingSteps.forEach((step, index) => {
                if (newStepStatuses[step.id] === 'completed') {
                  activeStepIndex = index
                }
              })
              activeStepProgress = 100 // Last completed step is 100% done
            }
            
            setStepStatuses(newStepStatuses)
            setCurrentStep(Math.max(0, activeStepIndex))
            setStepProgress(activeStepProgress)
            
            // Calculate overall progress
            const completedSteps = Object.values(newStepStatuses).filter(s => s === 'completed').length || 0
            const inProgressBonus = activeStepIndex >= 0 && newStepStatuses[processingSteps[activeStepIndex]?.id] === 'in_progress' 
              ? (activeStepProgress / 100) || 0
              : 0
            const totalSteps = processingSteps.length || 1 // Avoid division by zero
            const calculatedProgress = Math.max(0, Math.min(100, 
              ((completedSteps + inProgressBonus) / totalSteps) * 100
            ))
            setOverallProgress(Math.round(calculatedProgress) || 0)
          } else {
            // Fallback to estimation
            const estimatedStep = Math.min(
              Math.floor(elapsed / 20000),
              processingSteps.length - 1
            )
            setCurrentStep(estimatedStep)
            
            const progressInStep = Math.min(
              ((elapsed % 20000) / 20000) * 100,
              100
            )
            setStepProgress(progressInStep)
            
            // Calculate overall progress for fallback
            const estimatedOverallProgress = Math.max(0, Math.min(100,
              ((estimatedStep + (progressInStep / 100)) / processingSteps.length) * 100
            ))
            setOverallProgress(Math.round(estimatedOverallProgress))
          }
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
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-3">
            <AcademicCapIcon className="h-8 w-8 text-red-500" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Creating Your Interactive Lecture</h1>
              <p className="text-gray-600 mt-1">AI is processing your content. This may take a few minutes.</p>
            </div>
          </div>
          {elapsedTime > 0 && (
            <div className="text-right">
              <p className="text-sm text-gray-500">Elapsed time</p>
              <p className="text-lg font-medium text-gray-900">
                {Math.floor(elapsedTime / 60)}:{(elapsedTime % 60).toString().padStart(2, '0')}
              </p>
            </div>
          )}
        </div>

        {/* Overall Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Overall Progress</span>
            <span className="text-sm text-gray-500">{overallProgress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-primary-500 to-primary-600 h-3 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${overallProgress}%` }}
            >
              <div className="h-full bg-white/20 animate-pulse"></div>
            </div>
          </div>
        </div>

        {/* Processing Steps */}
        <div className="space-y-4 mb-8">
          {processingSteps.map((step, index) => {
            const StepIcon = step.icon
            const stepStatus = stepStatuses[step.id] || 'pending'
            const isActive = stepStatus === 'in_progress'
            const isComplete = stepStatus === 'completed'
            const isPending = stepStatus === 'pending'
            
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
                  <p className={`text-sm font-medium ${isActive ? 'text-gray-900' : isComplete ? 'text-gray-700' : 'text-gray-500'}`}>
                    {step.label}
                  </p>
                  {isActive && (
                    <div className="mt-1 w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                      <div 
                        className="bg-primary-600 h-2 rounded-full transition-all duration-500 ease-out"
                        style={{ width: `${index === currentStep ? stepProgress : 0}%` }}
                      ></div>
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