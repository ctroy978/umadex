'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeftIcon, ArrowRightIcon } from '@heroicons/react/24/outline'
import type { DebateAssignmentMetadata } from '@/types/debate'
import AntiCheatWrapper from '@/components/debate/AntiCheatWrapper'

export default function DebateCreatePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<Partial<DebateAssignmentMetadata>>({})
  
  const [metadata, setMetadata] = useState<DebateAssignmentMetadata>({
    title: '',
    topic: '',
    description: '',
    gradeLevel: '',
    subject: ''
  })

  const validateForm = (): boolean => {
    const newErrors: Partial<DebateAssignmentMetadata> = {}
    
    if (!metadata.title || metadata.title.length < 5) {
      newErrors.title = 'Title must be at least 5 characters'
    }
    
    if (!metadata.topic || metadata.topic.length < 10) {
      newErrors.topic = 'Topic must be at least 10 characters'
    }
    
    if (!metadata.gradeLevel) {
      newErrors.gradeLevel = 'Please select a grade level'
    }
    
    if (!metadata.subject) {
      newErrors.subject = 'Please select a subject'
    }
    
    if (metadata.description && metadata.description.length > 1000) {
      newErrors.description = 'Description must be less than 1000 characters'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }
    
    // Store metadata in session storage and proceed to configuration step
    sessionStorage.setItem('debate_metadata', JSON.stringify(metadata))
    router.push('/teacher/debate/create/configure')
  }

  const handleFieldChange = (field: keyof DebateAssignmentMetadata, value: string) => {
    setMetadata(prev => ({ ...prev, [field]: value }))
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }))
    }
  }

  return (
    <AntiCheatWrapper>
      <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <button
          onClick={() => router.push('/teacher/debate')}
          className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back to Debates
        </button>
        
        <h1 className="text-3xl font-bold text-gray-900">Create Debate Assignment</h1>
        <p className="mt-2 text-gray-600">Step 1 of 2: Basic Information</p>
      </div>

      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex items-center">
          <div className="flex-1">
            <div className="h-2 bg-gray-200 rounded-full">
              <div className="h-2 bg-blue-600 rounded-full" style={{ width: '50%' }} />
            </div>
          </div>
          <div className="ml-4 text-sm text-gray-600">50% Complete</div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 bg-white shadow rounded-lg p-6">
        {/* Assignment Title */}
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-gray-700">
            Assignment Title <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="title"
            value={metadata.title}
            onChange={(e) => handleFieldChange('title', e.target.value)}
            className={`mt-1 block w-full rounded-md shadow-sm ${
              errors.title ? 'border-red-300' : 'border-gray-300'
            } focus:border-blue-500 focus:ring-blue-500`}
            placeholder="e.g., Climate Change Debate"
          />
          {errors.title && (
            <p className="mt-1 text-sm text-red-600">{errors.title}</p>
          )}
          <p className="mt-1 text-sm text-gray-500">5-200 characters</p>
        </div>

        {/* Debate Topic */}
        <div>
          <label htmlFor="topic" className="block text-sm font-medium text-gray-700">
            Debate Topic <span className="text-red-500">*</span>
          </label>
          <p className="mt-1 text-sm text-gray-600 italic">
            Remember: Debate topics should be written as statements, not questions.
          </p>
          <textarea
            id="topic"
            rows={3}
            value={metadata.topic}
            onChange={(e) => handleFieldChange('topic', e.target.value)}
            className={`mt-2 block w-full rounded-md shadow-sm ${
              errors.topic ? 'border-red-300' : 'border-gray-300'
            } focus:border-blue-500 focus:ring-blue-500`}
            placeholder="e.g., Schools should implement a four-day school week"
          />
          {errors.topic && (
            <p className="mt-1 text-sm text-red-600">{errors.topic}</p>
          )}
          <p className="mt-1 text-sm text-gray-500">
            Enter a clear, debatable statement (10-500 characters)
          </p>
        </div>

        {/* Description */}
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700">
            Description (Optional)
          </label>
          <textarea
            id="description"
            rows={4}
            value={metadata.description}
            onChange={(e) => handleFieldChange('description', e.target.value)}
            className={`mt-1 block w-full rounded-md shadow-sm ${
              errors.description ? 'border-red-300' : 'border-gray-300'
            } focus:border-blue-500 focus:ring-blue-500`}
            placeholder="Provide additional context or instructions for the debate..."
          />
          {errors.description && (
            <p className="mt-1 text-sm text-red-600">{errors.description}</p>
          )}
          <p className="mt-1 text-sm text-gray-500">Max 1000 characters</p>
        </div>

        {/* Grade Level and Subject */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Grade Level */}
          <div>
            <label htmlFor="gradeLevel" className="block text-sm font-medium text-gray-700">
              Grade Level <span className="text-red-500">*</span>
            </label>
            <select
              id="gradeLevel"
              value={metadata.gradeLevel}
              onChange={(e) => handleFieldChange('gradeLevel', e.target.value)}
              className={`mt-1 block w-full rounded-md shadow-sm ${
                errors.gradeLevel ? 'border-red-300' : 'border-gray-300'
              } focus:border-blue-500 focus:ring-blue-500`}
            >
              <option value="">Select grade level</option>
              <option value="K-2">K-2</option>
              <option value="3-5">3-5</option>
              <option value="6-8">6-8</option>
              <option value="9-12">9-12</option>
            </select>
            {errors.gradeLevel && (
              <p className="mt-1 text-sm text-red-600">{errors.gradeLevel}</p>
            )}
          </div>

          {/* Subject */}
          <div>
            <label htmlFor="subject" className="block text-sm font-medium text-gray-700">
              Subject <span className="text-red-500">*</span>
            </label>
            <select
              id="subject"
              value={metadata.subject}
              onChange={(e) => handleFieldChange('subject', e.target.value)}
              className={`mt-1 block w-full rounded-md shadow-sm ${
                errors.subject ? 'border-red-300' : 'border-gray-300'
              } focus:border-blue-500 focus:ring-blue-500`}
            >
              <option value="">Select subject</option>
              <option value="English Language Arts">English Language Arts</option>
              <option value="Social Studies">Social Studies</option>
              <option value="Science">Science</option>
              <option value="History">History</option>
              <option value="Other">Other</option>
            </select>
            {errors.subject && (
              <p className="mt-1 text-sm text-red-600">{errors.subject}</p>
            )}
          </div>
        </div>

        {/* Form Actions */}
        <div className="flex justify-between pt-6 border-t">
          <button
            type="button"
            onClick={() => router.push('/teacher/debate')}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            Next: Configure Debate
            <ArrowRightIcon className="ml-2 h-4 w-4" />
          </button>
        </div>
      </form>

      {/* Tips Section */}
      <div className="mt-8 bg-blue-50 rounded-lg p-6">
        <h3 className="text-lg font-medium text-blue-900 mb-3">Tips for Creating Effective Debate Topics</h3>
        <ul className="space-y-2 text-sm text-blue-800">
          <li>• Choose topics that have clear opposing viewpoints</li>
          <li>• Ensure the topic is age-appropriate and relevant to students</li>
          <li>• Avoid topics that might be too sensitive or controversial for the classroom</li>
          <li>• Frame topics as clear statements (e.g., "Schools should..." not "Should schools...?")</li>
          <li>• Consider current events or issues relevant to your curriculum</li>
        </ul>
      </div>
      </div>
    </AntiCheatWrapper>
  )
}