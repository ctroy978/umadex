'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { PencilSquareIcon } from '@heroicons/react/24/outline'
import { WritingAssignmentCreate, EvaluationCriteria, GRADE_LEVELS, SUBJECT_AREAS, TONE_OPTIONS, STYLE_OPTIONS, PERSPECTIVE_OPTIONS, TECHNIQUE_OPTIONS, STRUCTURE_OPTIONS } from '@/types/writing'
import { writingApi } from '@/lib/writingApi'
import Link from 'next/link'

export default function CreateWritingAssignmentPage() {
  const router = useRouter()
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Form data
  const [formData, setFormData] = useState<WritingAssignmentCreate>({
    title: '',
    prompt_text: '',
    word_count_min: 50,
    word_count_max: 500,
    evaluation_criteria: {
      tone: [],
      style: [],
      perspective: [],
      techniques: [],
      structure: []
    },
    instructions: '',
    grade_level: '',
    subject: ''
  })

  const handleStep1Submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.title) {
      setError('Title is required')
      return
    }
    if (formData.word_count_min >= formData.word_count_max) {
      setError('Maximum word count must be greater than minimum')
      return
    }
    setError('')
    setStep(2)
  }

  const handleStep2Submit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.prompt_text || formData.prompt_text.length < 10) {
      setError('Prompt must be at least 10 characters')
      return
    }
    
    // Check if at least one criterion is selected
    const hasAnyCriteria = Object.values(formData.evaluation_criteria).some(arr => arr.length > 0)
    if (!hasAnyCriteria) {
      setError('Please select at least one evaluation criterion')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      const assignment = await writingApi.createAssignment(formData)
      // Redirect to the list page - assignments should be added to classrooms through Classroom Management
      router.push('/teacher/uma-write?created=true')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create assignment')
      setLoading(false)
    }
  }

  const updateFormData = (field: keyof WritingAssignmentCreate, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const toggleCriterion = (category: keyof EvaluationCriteria, value: string) => {
    setFormData(prev => ({
      ...prev,
      evaluation_criteria: {
        ...prev.evaluation_criteria,
        [category]: prev.evaluation_criteria[category].includes(value)
          ? prev.evaluation_criteria[category].filter(v => v !== value)
          : [...prev.evaluation_criteria[category], value]
      }
    }))
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center space-x-4 mb-8">
        <PencilSquareIcon className="h-8 w-8 text-orange-500" />
        <h1 className="text-3xl font-bold text-gray-900">Create Writing Assignment</h1>
      </div>

      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center">
          <div className={`flex items-center justify-center w-10 h-10 rounded-full ${
            step >= 1 ? 'bg-primary-600 text-white' : 'bg-gray-300 text-gray-600'
          }`}>
            1
          </div>
          <div className={`flex-1 h-1 mx-2 ${
            step >= 2 ? 'bg-primary-600' : 'bg-gray-300'
          }`}></div>
          <div className={`flex items-center justify-center w-10 h-10 rounded-full ${
            step >= 2 ? 'bg-primary-600 text-white' : 'bg-gray-300 text-gray-600'
          }`}>
            2
          </div>
        </div>
        <div className="flex justify-between mt-2">
          <span className="text-sm text-gray-600">Basic Information</span>
          <span className="text-sm text-gray-600">Prompt & Criteria</span>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {/* Step 1: Basic Information */}
      {step === 1 && (
        <form onSubmit={handleStep1Submit} className="space-y-6">
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
              Assignment Title *
            </label>
            <input
              type="text"
              id="title"
              value={formData.title}
              onChange={(e) => updateFormData('title', e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              placeholder="Enter assignment title"
              maxLength={255}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <label htmlFor="grade_level" className="block text-sm font-medium text-gray-700 mb-1">
                Grade Level
              </label>
              <select
                id="grade_level"
                value={formData.grade_level || ''}
                onChange={(e) => updateFormData('grade_level', e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">Select grade level</option>
                {GRADE_LEVELS.map(level => (
                  <option key={level} value={level}>{level}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-1">
                Subject Area
              </label>
              <select
                id="subject"
                value={formData.subject || ''}
                onChange={(e) => updateFormData('subject', e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">Select subject</option>
                {SUBJECT_AREAS.map(subject => (
                  <option key={subject} value={subject}>{subject}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <label htmlFor="word_count_min" className="block text-sm font-medium text-gray-700 mb-1">
                Minimum Word Count *
              </label>
              <input
                type="number"
                id="word_count_min"
                value={formData.word_count_min}
                onChange={(e) => updateFormData('word_count_min', parseInt(e.target.value))}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                min={10}
                max={1000}
                required
              />
            </div>

            <div>
              <label htmlFor="word_count_max" className="block text-sm font-medium text-gray-700 mb-1">
                Maximum Word Count *
              </label>
              <input
                type="number"
                id="word_count_max"
                value={formData.word_count_max}
                onChange={(e) => updateFormData('word_count_max', parseInt(e.target.value))}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                min={50}
                max={2000}
                required
              />
            </div>
          </div>

          <div>
            <label htmlFor="instructions" className="block text-sm font-medium text-gray-700 mb-1">
              Additional Instructions (Optional)
            </label>
            <textarea
              id="instructions"
              value={formData.instructions || ''}
              onChange={(e) => updateFormData('instructions', e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              rows={3}
              maxLength={1000}
              placeholder="Any additional guidance for students..."
            />
          </div>

          <div className="flex justify-between">
            <Link
              href="/teacher/uma-write"
              className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </Link>
            <button
              type="submit"
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              Next Step
            </button>
          </div>
        </form>
      )}

      {/* Step 2: Prompt & Criteria */}
      {step === 2 && (
        <form onSubmit={handleStep2Submit} className="space-y-6">
          <div>
            <label htmlFor="prompt_text" className="block text-sm font-medium text-gray-700 mb-1">
              Writing Prompt *
            </label>
            <textarea
              id="prompt_text"
              value={formData.prompt_text}
              onChange={(e) => updateFormData('prompt_text', e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              rows={4}
              maxLength={1000}
              placeholder="Enter the writing prompt for students..."
              required
            />
            <p className="mt-1 text-sm text-gray-500">
              {formData.prompt_text.length}/1000 characters
            </p>
          </div>

          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Evaluation Criteria</h3>
            <p className="text-sm text-gray-600 mb-4">
              Select the criteria you want students to focus on in their writing:
            </p>

            {/* Tone */}
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Tone</h4>
              <div className="flex flex-wrap gap-2">
                {TONE_OPTIONS.map(tone => (
                  <button
                    key={tone}
                    type="button"
                    onClick={() => toggleCriterion('tone', tone)}
                    className={`px-3 py-1 rounded-full text-sm transition-colors ${
                      formData.evaluation_criteria.tone.includes(tone)
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {tone}
                  </button>
                ))}
              </div>
            </div>

            {/* Style */}
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Style</h4>
              <div className="flex flex-wrap gap-2">
                {STYLE_OPTIONS.map(style => (
                  <button
                    key={style}
                    type="button"
                    onClick={() => toggleCriterion('style', style)}
                    className={`px-3 py-1 rounded-full text-sm transition-colors ${
                      formData.evaluation_criteria.style.includes(style)
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {style}
                  </button>
                ))}
              </div>
            </div>

            {/* Perspective */}
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Perspective</h4>
              <div className="flex flex-wrap gap-2">
                {PERSPECTIVE_OPTIONS.map(perspective => (
                  <button
                    key={perspective}
                    type="button"
                    onClick={() => toggleCriterion('perspective', perspective)}
                    className={`px-3 py-1 rounded-full text-sm transition-colors ${
                      formData.evaluation_criteria.perspective.includes(perspective)
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {perspective}
                  </button>
                ))}
              </div>
            </div>

            {/* Techniques */}
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Techniques</h4>
              <div className="flex flex-wrap gap-2">
                {TECHNIQUE_OPTIONS.map(technique => (
                  <button
                    key={technique}
                    type="button"
                    onClick={() => toggleCriterion('techniques', technique)}
                    className={`px-3 py-1 rounded-full text-sm transition-colors ${
                      formData.evaluation_criteria.techniques.includes(technique)
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {technique}
                  </button>
                ))}
              </div>
            </div>

            {/* Structure */}
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Structure</h4>
              <div className="flex flex-wrap gap-2">
                {STRUCTURE_OPTIONS.map(structure => (
                  <button
                    key={structure}
                    type="button"
                    onClick={() => toggleCriterion('structure', structure)}
                    className={`px-3 py-1 rounded-full text-sm transition-colors ${
                      formData.evaluation_criteria.structure.includes(structure)
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {structure}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex justify-between">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Previous
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating...' : 'Create Assignment'}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}