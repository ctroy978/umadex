'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { XMarkIcon, ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import { CheckCircleIcon } from '@heroicons/react/24/solid'
import { umalectureApi } from '@/lib/umalectureApi'
import type { LectureAssignment, LectureImage } from '@/lib/umalectureApi'

export default function TeacherUmaLecturePreview() {
  const params = useParams()
  const router = useRouter()
  const [lecture, setLecture] = useState<LectureAssignment | null>(null)
  const [images, setImages] = useState<LectureImage[]>([])
  const [currentTopicId, setCurrentTopicId] = useState<string>('')
  const [topicIds, setTopicIds] = useState<string[]>([])
  const [activeTab, setActiveTab] = useState<'basic' | 'intermediate' | 'advanced' | 'expert'>('basic')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedImage, setExpandedImage] = useState<string | null>(null)
  const [showQuestions, setShowQuestions] = useState(true)

  useEffect(() => {
    const loadLecture = async () => {
      try {
        const data = await umalectureApi.getLecture(params.id as string)
        setLecture(data)
        
        // Extract topic IDs from lecture structure
        if (data.lecture_structure?.topics) {
          const ids = Object.keys(data.lecture_structure.topics)
          setTopicIds(ids)
          if (ids.length > 0) {
            setCurrentTopicId(ids[0])
          }
        }
        
        // Load images
        const imageData = await umalectureApi.listImages(params.id as string)
        setImages(imageData)
      } catch (err) {
        setError('Failed to load lecture')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    loadLecture()
  }, [params.id])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
      </div>
    )
  }

  if (error || !lecture || !lecture.lecture_structure?.topics) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || 'Lecture not found or has no content'}</p>
          <button
            onClick={() => router.back()}
            className="text-primary-600 hover:text-primary-700"
          >
            Go back
          </button>
        </div>
      </div>
    )
  }

  const currentTopicIndex = topicIds.indexOf(currentTopicId)
  const currentTopic = lecture.lecture_structure.topics[currentTopicId]
  const currentDifficultyLevel = currentTopic?.difficulty_levels?.[activeTab]
  const currentContent = currentDifficultyLevel?.content || ''
  const currentQuestions = currentDifficultyLevel?.questions || []
  const currentImageIds = currentDifficultyLevel?.images || []

  const renderContent = (content: string) => {
    const parts = content.split(/(\[Image \d+\])/g)
    
    return parts.map((part, index) => {
      const imageMatch = part.match(/\[Image (\d+)\]/)
      if (imageMatch) {
        const imageIndex = parseInt(imageMatch[1]) - 1
        const imageId = currentImageIds[imageIndex]
        const image = images.find(img => img.id === imageId)
        
        if (image) {
          return (
            <div key={index} className="my-4">
              <img
                src={image.display_url || image.original_url}
                alt={image.ai_description || image.teacher_description || `Image ${imageIndex + 1}`}
                className="max-w-full h-auto rounded-lg shadow-md cursor-pointer"
                onClick={() => setExpandedImage(image.display_url || image.original_url)}
              />
              <p className="text-sm text-gray-600 mt-2 text-center">
                {image.ai_description || image.teacher_description || `Image ${imageIndex + 1}`}
              </p>
            </div>
          )
        }
        return <span key={index} className="text-gray-500">[Image {imageIndex + 1} not found]</span>
      }
      
      return (
        <span key={index} className="whitespace-pre-wrap">
          {part}
        </span>
      )
    })
  }

  const navigateToTopic = (direction: 'prev' | 'next') => {
    const newIndex = direction === 'prev' 
      ? Math.max(0, currentTopicIndex - 1)
      : Math.min(topicIds.length - 1, currentTopicIndex + 1)
    setCurrentTopicId(topicIds[newIndex])
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{lecture.title}</h1>
              <p className="text-sm text-gray-600 mt-1">
                {lecture.subject} • {lecture.grade_level} • Teacher Preview Mode
              </p>
            </div>
            <button
              onClick={() => router.back()}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Content Area */}
          <div className="lg:col-span-2">
            {/* Topic Header */}
            <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Topic {currentTopicIndex + 1}: {currentTopic.title}
              </h2>
            </div>

            {/* Difficulty Tabs */}
            <div className="bg-white rounded-lg shadow-sm mb-6">
              <div className="border-b">
                <nav className="-mb-px flex">
                  {(['basic', 'intermediate', 'advanced', 'expert'] as const).map((level) => (
                    <button
                      key={level}
                      onClick={() => setActiveTab(level)}
                      className={`py-3 px-6 text-sm font-medium capitalize transition-colors ${
                        activeTab === level
                          ? 'border-b-2 border-primary-600 text-primary-600'
                          : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      {level}
                    </button>
                  ))}
                </nav>
              </div>

              {/* Content */}
              <div className="p-6">
                {currentContent ? (
                  <div className="prose max-w-none">
                    {renderContent(currentContent)}
                  </div>
                ) : (
                  <p className="text-gray-500">No content available for this difficulty level.</p>
                )}
              </div>
            </div>

            {/* Topic Navigation */}
            <div className="flex items-center justify-between">
              <button
                onClick={() => navigateToTopic('prev')}
                disabled={currentTopicIndex === 0}
                className={`flex items-center px-4 py-2 rounded-lg transition-colors ${
                  currentTopicIndex === 0
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-primary-600 text-white hover:bg-primary-700'
                }`}
              >
                <ChevronLeftIcon className="h-5 w-5 mr-2" />
                Previous Topic
              </button>

              <span className="text-sm text-gray-600">
                Topic {currentTopicIndex + 1} of {topicIds.length}
              </span>

              <button
                onClick={() => navigateToTopic('next')}
                disabled={currentTopicIndex === topicIds.length - 1}
                className={`flex items-center px-4 py-2 rounded-lg transition-colors ${
                  currentTopicIndex === topicIds.length - 1
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-primary-600 text-white hover:bg-primary-700'
                }`}
              >
                Next Topic
                <ChevronRightIcon className="h-5 w-5 ml-2" />
              </button>
            </div>
          </div>

          {/* Questions Panel */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm sticky top-4">
              <div className="p-4 border-b">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900">Questions</h3>
                  <button
                    onClick={() => setShowQuestions(!showQuestions)}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    {showQuestions ? 'Hide' : 'Show'}
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Teacher preview - AI evaluation disabled
                </p>
              </div>

              {showQuestions && (
                <div className="p-4 max-h-[600px] overflow-y-auto">
                  {currentQuestions.length > 0 ? (
                    <div className="space-y-4">
                      {currentQuestions.map((question, idx) => (
                        <div key={idx} className="border rounded-lg p-4 bg-gray-50">
                          <div className="flex items-start justify-between mb-2">
                            <span className="text-sm font-medium text-gray-700">
                              Question {idx + 1}
                            </span>
                            <span className="text-xs text-gray-500 capitalize">
                              {question.question_type}
                            </span>
                          </div>
                          
                          <p className="text-sm text-gray-900 mb-3">{question.question}</p>
                          
                          {question.question_type === 'multiple_choice' && question.options && (
                            <div className="space-y-2 mb-3">
                              {question.options.map((option, optIdx) => (
                                <div
                                  key={optIdx}
                                  className={`flex items-center text-sm p-2 rounded ${
                                    option === question.correct_answer
                                      ? 'bg-green-50 text-green-800'
                                      : 'text-gray-700'
                                  }`}
                                >
                                  {option === question.correct_answer && (
                                    <CheckCircleIcon className="h-4 w-4 mr-2 flex-shrink-0" />
                                  )}
                                  <span>{option}</span>
                                </div>
                              ))}
                            </div>
                          )}
                          
                          <div className="border-t pt-2">
                            <p className="text-xs font-medium text-gray-600 mb-1">Expected Answer:</p>
                            <p className="text-sm text-gray-800 bg-white p-2 rounded border">
                              {question.correct_answer}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No questions available for this difficulty level.</p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Image Modal */}
      {expandedImage && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={() => setExpandedImage(null)}
        >
          <div className="relative max-w-4xl max-h-[90vh]">
            <img
              src={expandedImage}
              alt="Expanded"
              className="max-w-full max-h-full object-contain"
            />
            <button
              onClick={() => setExpandedImage(null)}
              className="absolute top-4 right-4 p-2 bg-white rounded-full shadow-lg hover:bg-gray-100"
            >
              <XMarkIcon className="h-6 w-6 text-gray-700" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}