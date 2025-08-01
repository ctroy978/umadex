'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { 
  AcademicCapIcon,
  ArrowLeftIcon,
  BeakerIcon,
  BookOpenIcon,
  InformationCircleIcon
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

// Example cards data
const examples = [
  {
    icon: BeakerIcon,
    color: 'bg-green-50 text-green-700 border-green-200',
    iconColor: 'text-green-600',
    subject: 'Science Example',
    topic: 'Photosynthesis Process',
    subtopics: [
      'What photosynthesis is and why plants need it',
      'The step-by-step chemical reactions involved',
      'How photosynthesis impacts ecosystems and food production'
    ]
  },
  {
    icon: BookOpenIcon,
    color: 'bg-purple-50 text-purple-700 border-purple-200',
    iconColor: 'text-purple-600',
    subject: 'English Literature Example',
    topic: 'Symbolism in Romeo and Juliet',
    subtopics: [
      'Light and darkness imagery throughout the play',
      'The balcony as symbol of forbidden love',
      'How symbols foreshadow the tragic ending'
    ]
  }
]

export default function CreateLecturePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const [formData, setFormData] = useState({
    title: '',
    subject: '',
    grade_level: '',
    topic: '',
    subtopic1: '',
    subtopic2: '',
    subtopic3: ''
  })

  const validateForm = () => {
    // Check required fields
    if (!formData.title || !formData.subject || !formData.grade_level || 
        !formData.topic || !formData.subtopic1 || !formData.subtopic2) {
      setError('Please fill in all required fields')
      return false
    }

    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    try {
      setLoading(true)
      setError(null)
      
      // Generate learning objectives from the topic and subtopics
      const learningObjectives = [
        `Understand the key concepts of ${formData.topic.toLowerCase()}`,
        `Explain ${formData.subtopic1.toLowerCase()}`,
        `Analyze ${formData.subtopic2.toLowerCase()}`
      ]
      
      if (formData.subtopic3) {
        learningObjectives.push(`Evaluate ${formData.subtopic3.toLowerCase()}`)
      }
      
      // Use topic as title if title is not provided
      const lectureTitle = formData.title.trim() || formData.topic.trim()
      
      const lecture = await umalectureApi.createLecture({
        title: lectureTitle,
        subject: formData.subject,
        grade_level: formData.grade_level,
        learning_objectives: learningObjectives
      })
      
      // Store the topic and subtopics in session storage to use in the next step
      sessionStorage.setItem('lectureTopicData', JSON.stringify({
        topic: formData.topic,
        subtopics: [
          formData.subtopic1,
          formData.subtopic2,
          ...(formData.subtopic3 ? [formData.subtopic3] : [])
        ]
      }))
      
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
            <h1 className="text-3xl font-bold text-gray-900">Create Focused Lecture</h1>
            <p className="text-gray-600 mt-1">Design a 15-25 minute interactive learning experience</p>
          </div>
        </div>
      </div>

      {/* Guidance Message */}
      <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <InformationCircleIcon className="h-5 w-5 text-blue-600 mr-2 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-blue-800 font-medium">Create focused, digestible content</p>
            <p className="text-sm text-blue-700 mt-1">
              Focus on one topic with 2-3 key subtopics for best student engagement. 
              This approach creates 8-12 content sections across difficulty levels.
            </p>
          </div>
        </div>
      </div>

      {/* Example Cards */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Examples of Well-Structured Lectures</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {examples.map((example, index) => (
            <div key={index} className={`rounded-lg border p-4 ${example.color}`}>
              <div className="flex items-start space-x-3">
                <example.icon className={`h-6 w-6 ${example.iconColor} flex-shrink-0 mt-1`} />
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900">{example.subject}</h3>
                  <p className="text-sm font-semibold mt-2">Topic: {example.topic}</p>
                  <div className="mt-2 space-y-1">
                    {example.subtopics.map((subtopic, idx) => (
                      <p key={idx} className="text-sm">
                        • {subtopic}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
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

        {/* Lecture Topic */}
        <div className="mb-6">
          <label htmlFor="topic" className="block text-sm font-medium text-gray-700 mb-2">
            Lecture Topic <span className="text-red-500">*</span>
          </label>
          <p className="text-sm text-gray-500 mb-2">
            Choose one focused topic for this lecture (max 100 characters)
          </p>
          <input
            type="text"
            id="topic"
            value={formData.topic}
            onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder="e.g., The Water Cycle"
            maxLength={100}
            required
          />
          <div className="mt-1 text-xs text-gray-500">{formData.topic.length}/100 characters</div>
        </div>

        {/* Subtopics */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Key Subtopics
          </label>
          <p className="text-sm text-gray-500 mb-3">
            Break down your topic into 2-3 specific learning points (max 150 characters each)
          </p>
          
          <div className="space-y-3">
            {/* Subtopic 1 */}
            <div>
              <label htmlFor="subtopic1" className="block text-sm text-gray-600 mb-1">
                Subtopic 1 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="subtopic1"
                value={formData.subtopic1}
                onChange={(e) => setFormData({ ...formData, subtopic1: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="e.g., How water evaporates from oceans and lakes"
                maxLength={150}
                required
              />
              <div className="mt-1 text-xs text-gray-500">{formData.subtopic1.length}/150 characters</div>
            </div>

            {/* Subtopic 2 */}
            <div>
              <label htmlFor="subtopic2" className="block text-sm text-gray-600 mb-1">
                Subtopic 2 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="subtopic2"
                value={formData.subtopic2}
                onChange={(e) => setFormData({ ...formData, subtopic2: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="e.g., Cloud formation and types of precipitation"
                maxLength={150}
                required
              />
              <div className="mt-1 text-xs text-gray-500">{formData.subtopic2.length}/150 characters</div>
            </div>

            {/* Subtopic 3 (Optional) */}
            <div>
              <label htmlFor="subtopic3" className="block text-sm text-gray-600 mb-1">
                Subtopic 3 <span className="text-gray-400">(Optional)</span>
              </label>
              <input
                type="text"
                id="subtopic3"
                value={formData.subtopic3}
                onChange={(e) => setFormData({ ...formData, subtopic3: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="e.g., Human impact on the water cycle"
                maxLength={150}
              />
              <div className="mt-1 text-xs text-gray-500">{formData.subtopic3.length}/150 characters</div>
            </div>
          </div>
        </div>

        {/* Preview Section */}
        {(formData.topic || formData.subtopic1 || formData.subtopic2) && (
          <div className="mb-6 bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Preview</h3>
            <p className="text-sm text-gray-600">
              This will create 8-12 interactive content sections covering:
            </p>
            {formData.topic && (
              <div className="mt-2 text-sm text-gray-700">
                <span className="font-medium">Topic:</span> {formData.topic}
                <div className="ml-4 mt-1">
                  {formData.subtopic1 && <div>• {formData.subtopic1}</div>}
                  {formData.subtopic2 && <div>• {formData.subtopic2}</div>}
                  {formData.subtopic3 && <div>• {formData.subtopic3}</div>}
                </div>
              </div>
            )}
            <p className="text-sm text-gray-600 mt-2">
              Each subtopic will have content at Basic, Intermediate, Advanced, and Expert levels.
            </p>
          </div>
        )}

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