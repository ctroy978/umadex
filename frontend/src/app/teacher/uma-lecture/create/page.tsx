'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { 
  AcademicCapIcon,
  ArrowLeftIcon,
  PlusIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'
import { umalectureApi } from '@/lib/umalectureApi'

const subjects = [
  'Science',
  'History',
  'Math',
  'Language Arts',
  'Social Studies',
  'Computer Science',
  'Art',
  'Music',
  'Physical Education',
  'Other'
]

const gradeLevels = [
  'Kindergarten',
  '1st Grade',
  '2nd Grade',
  '3rd Grade',
  '4th Grade',
  '5th Grade',
  '6th Grade',
  '7th Grade',
  '8th Grade',
  '9th Grade',
  '10th Grade',
  '11th Grade',
  '12th Grade',
  'College',
  'Adult Education'
]

export default function CreateLecturePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const [formData, setFormData] = useState({
    title: '',
    subject: '',
    grade_level: '',
    learning_objectives: ['']
  })

  const handleAddObjective = () => {
    if (formData.learning_objectives.length < 10) {
      setFormData({
        ...formData,
        learning_objectives: [...formData.learning_objectives, '']
      })
    }
  }

  const handleRemoveObjective = (index: number) => {
    if (formData.learning_objectives.length > 1) {
      setFormData({
        ...formData,
        learning_objectives: formData.learning_objectives.filter((_, i) => i !== index)
      })
    }
  }

  const handleObjectiveChange = (index: number, value: string) => {
    const newObjectives = [...formData.learning_objectives]
    newObjectives[index] = value
    setFormData({
      ...formData,
      learning_objectives: newObjectives
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate form
    if (!formData.title || !formData.subject || !formData.grade_level) {
      setError('Please fill in all required fields')
      return
    }
    
    const validObjectives = formData.learning_objectives.filter(obj => obj.trim())
    if (validObjectives.length === 0) {
      setError('Please add at least one learning objective')
      return
    }

    try {
      setLoading(true)
      setError(null)
      
      const lecture = await umalectureApi.createLecture({
        ...formData,
        learning_objectives: validObjectives
      })
      
      // Navigate to Step 2: content creation
      router.push(`/teacher/uma-lecture/create/${lecture.id}/content`)
    } catch (err) {
      console.error('Error creating lecture:', err)
      setError('Failed to create lecture. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/teacher/uma-lecture"
          className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back to Lectures
        </Link>
        
        <div className="flex items-center space-x-3">
          <AcademicCapIcon className="h-8 w-8 text-red-500" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Create New Lecture</h1>
            <p className="text-gray-600 mt-1">Step 1: Basic Information</p>
          </div>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center">
          <div className="flex items-center">
            <div className="w-8 h-8 bg-primary-600 text-white rounded-full flex items-center justify-center font-semibold">
              1
            </div>
            <span className="ml-2 text-sm font-medium text-gray-900">Basic Info</span>
          </div>
          <div className="flex-1 mx-4">
            <div className="h-1 bg-gray-200 rounded"></div>
          </div>
          <div className="flex items-center">
            <div className="w-8 h-8 bg-gray-200 text-gray-400 rounded-full flex items-center justify-center font-semibold">
              2
            </div>
            <span className="ml-2 text-sm text-gray-500">Content & Images</span>
          </div>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Title */}
        <div className="mb-6">
          <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
            Lecture Title <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="title"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder="e.g., Introduction to Photosynthesis"
            required
          />
        </div>

        {/* Subject */}
        <div className="mb-6">
          <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-2">
            Subject <span className="text-red-500">*</span>
          </label>
          <select
            id="subject"
            value={formData.subject}
            onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            required
          >
            <option value="">Select a subject</option>
            {subjects.map(subject => (
              <option key={subject} value={subject}>{subject}</option>
            ))}
          </select>
        </div>

        {/* Grade Level */}
        <div className="mb-6">
          <label htmlFor="grade_level" className="block text-sm font-medium text-gray-700 mb-2">
            Grade Level <span className="text-red-500">*</span>
          </label>
          <select
            id="grade_level"
            value={formData.grade_level}
            onChange={(e) => setFormData({ ...formData, grade_level: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            required
          >
            <option value="">Select a grade level</option>
            {gradeLevels.map(grade => (
              <option key={grade} value={grade}>{grade}</option>
            ))}
          </select>
        </div>

        {/* Learning Objectives */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Learning Objectives <span className="text-red-500">*</span>
          </label>
          <p className="text-sm text-gray-600 mb-3">
            Add 3-5 key goals students should achieve by completing this lecture
          </p>
          
          <div className="space-y-3">
            {formData.learning_objectives.map((objective, index) => (
              <div key={index} className="flex items-center space-x-2">
                <span className="text-sm text-gray-500 w-6">{index + 1}.</span>
                <input
                  type="text"
                  value={objective}
                  onChange={(e) => handleObjectiveChange(index, e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  placeholder="e.g., Understand the process of photosynthesis"
                />
                {formData.learning_objectives.length > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveObjective(index)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                )}
              </div>
            ))}
          </div>
          
          {formData.learning_objectives.length < 10 && (
            <button
              type="button"
              onClick={handleAddObjective}
              className="mt-3 inline-flex items-center text-sm text-primary-600 hover:text-primary-700"
            >
              <PlusIcon className="h-4 w-4 mr-1" />
              Add another objective
            </button>
          )}
        </div>

        {/* Form Actions */}
        <div className="flex items-center justify-between pt-6 border-t border-gray-200">
          <Link
            href="/teacher/uma-lecture"
            className="text-gray-600 hover:text-gray-700"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Creating...' : 'Next: Add Content'}
          </button>
        </div>
      </form>
    </div>
  )
}