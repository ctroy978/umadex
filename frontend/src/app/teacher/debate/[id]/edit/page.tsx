'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { ArrowLeftIcon, CheckIcon } from '@heroicons/react/24/outline'
import { debateApi } from '@/lib/debateApi'
import type { DebateAssignment, DebateAssignmentUpdate, DifficultyLevel, FallacyFrequency } from '@/types/debate'

export default function DebateEditPage() {
  const router = useRouter()
  const params = useParams()
  const assignmentId = params.id as string
  
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [assignment, setAssignment] = useState<DebateAssignment | null>(null)
  const [errors, setErrors] = useState<Partial<DebateAssignmentUpdate>>({})
  const [successMessage, setSuccessMessage] = useState('')
  const [hasChanges, setHasChanges] = useState(false)
  
  const [formData, setFormData] = useState<DebateAssignmentUpdate>({
    title: '',
    topic: '',
    description: '',
    gradeLevel: '',
    subject: '',
    roundsPerDebate: 1,
    debateCount: 1,
    timeLimitHours: 24,
    difficultyLevel: 'intermediate',
    fallacyFrequency: 'disabled',
    aiPersonalitiesEnabled: false,
    contentModerationEnabled: true,
    autoFlagOffTopic: false
  })

  useEffect(() => {
    loadAssignment()
  }, [assignmentId])

  const loadAssignment = async () => {
    try {
      setLoading(true)
      const data = await debateApi.getAssignment(assignmentId)
      setAssignment(data)
      
      // Populate form with existing data
      const initialFormData = {
        title: data.title,
        topic: data.topic,
        description: data.description || '',
        gradeLevel: data.gradeLevel,
        subject: data.subject,
        roundsPerDebate: data.roundsPerDebate,
        debateCount: data.debateCount,
        timeLimitHours: data.timeLimitHours,
        difficultyLevel: data.difficultyLevel,
        fallacyFrequency: data.fallacyFrequency,
        aiPersonalitiesEnabled: data.aiPersonalitiesEnabled,
        contentModerationEnabled: data.contentModerationEnabled,
        autoFlagOffTopic: data.autoFlagOffTopic
      }
      setFormData(initialFormData)
    } catch (error) {
      console.error('Error loading assignment:', error)
      alert('Failed to load assignment')
      router.push('/teacher/debate')
    } finally {
      setLoading(false)
    }
  }

  const validateForm = (): boolean => {
    const newErrors: Partial<DebateAssignmentUpdate> = {}
    
    if (!formData.title || formData.title.length < 5) {
      newErrors.title = 'Title must be at least 5 characters'
    }
    
    if (!formData.topic || formData.topic.length < 10) {
      newErrors.topic = 'Topic must be at least 10 characters'
    }
    
    if (!formData.gradeLevel) {
      newErrors.gradeLevel = 'Please select a grade level'
    }
    
    if (!formData.subject) {
      newErrors.subject = 'Please select a subject'
    }
    
    if (formData.description && formData.description.length > 1000) {
      newErrors.description = 'Description must be less than 1000 characters'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }
    
    try {
      setSaving(true)
      const response = await debateApi.updateAssignment(assignmentId, formData)
      setSuccessMessage('Assignment updated successfully!')
      setHasChanges(false)
      
      // Scroll to top to show success message
      window.scrollTo({ top: 0, behavior: 'smooth' })
      
      // Clear success message after 5 seconds
      setTimeout(() => {
        setSuccessMessage('')
      }, 5000)
    } catch (error) {
      console.error('Error updating assignment:', error)
      alert('Failed to update assignment. Check console for details.')
    } finally {
      setSaving(false)
    }
  }

  const handleFieldChange = (field: keyof DebateAssignmentUpdate, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    setHasChanges(true)
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }))
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <button
          onClick={() => router.push('/teacher/debate')}
          className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back to Debates
        </button>
        
        <h1 className="text-3xl font-bold text-gray-900">Edit Debate Assignment</h1>
      </div>

      {successMessage && (
        <div className="mb-6 p-4 bg-green-50 border-2 border-green-400 rounded-md flex items-center animate-pulse">
          <CheckIcon className="h-6 w-6 text-green-600 mr-3" />
          <span className="text-green-800 font-medium text-lg">{successMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6 bg-white shadow rounded-lg p-6">
        {/* Basic Information Section */}
        <div className="border-b pb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Basic Information</h2>
          
          {/* Assignment Title */}
          <div className="mb-4">
            <label htmlFor="title" className="block text-sm font-medium text-gray-700">
              Assignment Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="title"
              value={formData.title}
              onChange={(e) => handleFieldChange('title', e.target.value)}
              className={`mt-1 block w-full rounded-md shadow-sm ${
                errors.title ? 'border-red-300' : 'border-gray-300'
              } focus:border-blue-500 focus:ring-blue-500`}
            />
            {errors.title && (
              <p className="mt-1 text-sm text-red-600">{errors.title}</p>
            )}
          </div>

          {/* Debate Topic */}
          <div className="mb-4">
            <label htmlFor="topic" className="block text-sm font-medium text-gray-700">
              Debate Topic <span className="text-red-500">*</span>
            </label>
            <p className="mt-1 text-sm text-gray-600 italic">
              Remember: Debate topics should be written as statements, not questions.
            </p>
            <textarea
              id="topic"
              rows={3}
              value={formData.topic}
              onChange={(e) => handleFieldChange('topic', e.target.value)}
              className={`mt-2 block w-full rounded-md shadow-sm ${
                errors.topic ? 'border-red-300' : 'border-gray-300'
              } focus:border-blue-500 focus:ring-blue-500`}
            />
            {errors.topic && (
              <p className="mt-1 text-sm text-red-600">{errors.topic}</p>
            )}
          </div>

          {/* Description */}
          <div className="mb-4">
            <label htmlFor="description" className="block text-sm font-medium text-gray-700">
              Description (Optional)
            </label>
            <textarea
              id="description"
              rows={4}
              value={formData.description}
              onChange={(e) => handleFieldChange('description', e.target.value)}
              className={`mt-1 block w-full rounded-md shadow-sm ${
                errors.description ? 'border-red-300' : 'border-gray-300'
              } focus:border-blue-500 focus:ring-blue-500`}
            />
            {errors.description && (
              <p className="mt-1 text-sm text-red-600">{errors.description}</p>
            )}
          </div>

          {/* Grade Level and Subject */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="gradeLevel" className="block text-sm font-medium text-gray-700">
                Grade Level <span className="text-red-500">*</span>
              </label>
              <select
                id="gradeLevel"
                value={formData.gradeLevel}
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

            <div>
              <label htmlFor="subject" className="block text-sm font-medium text-gray-700">
                Subject <span className="text-red-500">*</span>
              </label>
              <select
                id="subject"
                value={formData.subject}
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
        </div>

        {/* Debate Configuration Section */}
        <div className="border-b pb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Debate Configuration</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label htmlFor="debateCount" className="block text-sm font-medium text-gray-700">
                Number of Debates
              </label>
              <input
                type="number"
                id="debateCount"
                min="1"
                max="10"
                value={formData.debateCount}
                onChange={(e) => handleFieldChange('debateCount', parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>

            <div>
              <label htmlFor="roundsPerDebate" className="block text-sm font-medium text-gray-700">
                Rounds per Debate
              </label>
              <input
                type="number"
                id="roundsPerDebate"
                min="1"
                max="10"
                value={formData.roundsPerDebate}
                onChange={(e) => handleFieldChange('roundsPerDebate', parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>

            <div>
              <label htmlFor="timeLimitHours" className="block text-sm font-medium text-gray-700">
                Time Limit (hours)
              </label>
              <input
                type="number"
                id="timeLimitHours"
                min="1"
                max="168"
                value={formData.timeLimitHours}
                onChange={(e) => handleFieldChange('timeLimitHours', parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="difficultyLevel" className="block text-sm font-medium text-gray-700">
                Difficulty Level
              </label>
              <select
                id="difficultyLevel"
                value={formData.difficultyLevel}
                onChange={(e) => handleFieldChange('difficultyLevel', e.target.value as DifficultyLevel)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>

            <div>
              <label htmlFor="fallacyFrequency" className="block text-sm font-medium text-gray-700">
                Logical Fallacy Frequency
              </label>
              <select
                id="fallacyFrequency"
                value={formData.fallacyFrequency}
                onChange={(e) => handleFieldChange('fallacyFrequency', e.target.value as FallacyFrequency)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="disabled">Disabled</option>
                <option value="every_3_4">Every 3-4 rounds</option>
                <option value="every_2_3">Every 2-3 rounds</option>
                <option value="every_1_2">Every 1-2 rounds</option>
              </select>
            </div>
          </div>
        </div>

        {/* Advanced Settings */}
        <div className="pb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Advanced Settings</h2>
          
          <div className="space-y-3">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.aiPersonalitiesEnabled}
                onChange={(e) => handleFieldChange('aiPersonalitiesEnabled', e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">Enable diverse AI personalities</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.contentModerationEnabled}
                onChange={(e) => handleFieldChange('contentModerationEnabled', e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">Enable content moderation</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.autoFlagOffTopic}
                onChange={(e) => handleFieldChange('autoFlagOffTopic', e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">Auto-flag off-topic responses</span>
            </label>
          </div>
        </div>

        {/* Form Actions */}
        <div className="flex justify-between items-center pt-6 border-t">
          <button
            type="button"
            onClick={() => router.push('/teacher/debate')}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <div className="flex items-center gap-4">
            {hasChanges && !saving && !successMessage && (
              <span className="text-sm text-amber-600 font-medium">
                You have unsaved changes
              </span>
            )}
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center px-6 py-3 text-base font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 hover:scale-105"
            >
              {saving ? (
                <>
                  <span className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}