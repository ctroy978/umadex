'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { ChevronLeft, X, CheckCircle, Circle, ChevronRight, ChevronDown } from 'lucide-react'
import { umalectureApi } from '@/lib/umalectureApi'
import type { LectureAssignment, LectureImage } from '@/lib/umalectureApi'

interface TopicContent {
  topic_id: string
  title: string
  difficulty_levels: {
    [key: string]: {
      content: string
      images: string[]
      questions: Array<{
        question: string
        question_type: string
        difficulty: string
        correct_answer: string
        options?: string[]
        uses_images: boolean
      }>
    }
  }
}

const TABS = [
  { id: 'basic', label: 'Basic', icon: '🌱' },
  { id: 'intermediate', label: 'Intermediate', icon: '🌿' },
  { id: 'advanced', label: 'Advanced', icon: '🌳' },
  { id: 'expert', label: 'Expert', icon: '🏆' },
] as const

export default function TeacherLecturePreviewPage() {
  const router = useRouter()
  const params = useParams()
  const lectureId = params.id as string
  
  const [lecture, setLecture] = useState<LectureAssignment | null>(null)
  const [lectureStructure, setLectureStructure] = useState<any>(null)
  const [images, setImages] = useState<LectureImage[]>([])
  const [currentTopic, setCurrentTopic] = useState<string | null>(null)
  const [currentTab, setCurrentTab] = useState<'basic' | 'intermediate' | 'advanced' | 'expert'>('basic')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedImage, setExpandedImage] = useState<string | null>(null)
  const [showQuestions, setShowQuestions] = useState(true)
  const [expandedQuestions, setExpandedQuestions] = useState<Set<number>>(new Set())

  useEffect(() => {
    fetchLectureData()
  }, [lectureId])

  const fetchLectureData = async () => {
    try {
      setLoading(true)
      const [lectureData, imageData] = await Promise.all([
        umalectureApi.getLecture(lectureId),
        umalectureApi.listImages(lectureId)
      ])
      
      setLecture(lectureData)
      setImages(imageData)
      
      if (lectureData.lecture_structure) {
        setLectureStructure(lectureData.lecture_structure)
        // Set first topic as current
        const firstTopic = Object.keys(lectureData.lecture_structure.topics)[0]
        setCurrentTopic(firstTopic)
      }
    } catch (err) {
      console.error('Failed to load lecture:', err)
      setError('Failed to load lecture. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleTopicChange = (topicId: string) => {
    setCurrentTopic(topicId)
    setCurrentTab('basic')
    setExpandedQuestions(new Set())
  }

  const handleTabChange = (tab: typeof currentTab) => {
    setCurrentTab(tab)
    setExpandedQuestions(new Set())
  }

  const toggleQuestion = (index: number) => {
    const newExpanded = new Set(expandedQuestions)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedQuestions(newExpanded)
  }

  const renderContent = (content: string, topicImages: string[]) => {
    if (!content) return <p className="text-gray-400">Content not available</p>

    // Get relevant images for this topic and difficulty level
    const topicTitle = currentTopic ? lectureStructure.topics[currentTopic]?.title : ''
    const currentDifficulty = currentTab // currentTab holds the difficulty level
    
    const relevantImages = images.filter(img => {
      if (!img.node_id) return false
      
      // Check if node_id contains difficulty level (format: "topic|difficulty")
      if (img.node_id.includes('|')) {
        const [imgTopic, imgDifficulty] = img.node_id.split('|')
        // Check if difficulty matches
        if (imgDifficulty !== currentDifficulty) return false
        // Check if topic matches
        const nodeWords = imgTopic.toLowerCase()
        const topicWords = topicTitle.toLowerCase().split(/\s+/).filter((w: string) => w.length > 3)
        return topicWords.some((word: string) => nodeWords.includes(word))
      } else {
        // Legacy format without difficulty - show in all tabs for backward compatibility
        const nodeWords = img.node_id.toLowerCase()
        const topicWords = topicTitle.toLowerCase().split(/\s+/).filter((w: string) => w.length > 3)
        return topicWords.some((word: string) => nodeWords.includes(word))
      }
    })
    
    console.log('Preview - All images:', images)
    console.log('Preview - Topic title:', topicTitle)
    console.log('Preview - Current difficulty:', currentDifficulty)
    console.log('Preview - Relevant images:', relevantImages)

    // Split content into paragraphs
    const paragraphs = content.split('\n\n')

    return (
      <div className="prose prose-invert max-w-none">
        {paragraphs.map((paragraph, index) => {
          // Check if paragraph references an image
          const imageMatch = paragraph.match(/\[Image (\d+)\]/)
          if (imageMatch && relevantImages[parseInt(imageMatch[1]) - 1]) {
            const image = relevantImages[parseInt(imageMatch[1]) - 1]
            return (
              <div key={index} className="my-6">
                <div 
                  className="cursor-pointer group"
                  onClick={() => setExpandedImage(image.display_url || image.original_url)}
                >
                  <img
                    src={image.thumbnail_url || image.original_url}
                    alt={image.teacher_description}
                    className="rounded-lg shadow-lg max-w-xs mx-auto group-hover:opacity-90 transition-opacity"
                  />
                  <p className="text-sm text-gray-400 mt-2 text-center italic">
                    {image.ai_description || image.teacher_description}
                  </p>
                  <p className="text-xs text-gray-500 text-center mt-1">
                    Click to enlarge
                  </p>
                </div>
              </div>
            )
          }

          return (
            <p key={index} className="mb-4 text-gray-300 leading-relaxed">
              {paragraph}
            </p>
          )
        })}
        
        {/* Display images at the bottom if there are any */}
        {relevantImages.length > 0 && (
          <div className="mt-8 pt-6 border-t border-gray-700">
            <h3 className="text-lg font-medium text-gray-200 mb-4">Reference Images</h3>
            <div className="grid grid-cols-2 gap-4">
              {relevantImages.map((image, idx) => (
                <div
                  key={image.id}
                  className="cursor-pointer group"
                  onClick={() => setExpandedImage(image.original_url || image.display_url || image.thumbnail_url || null)}
                >
                  <img
                    src={image.original_url || image.display_url || image.thumbnail_url}
                    alt={image.teacher_description}
                    className="w-full h-32 object-cover rounded-lg shadow-lg group-hover:opacity-90 transition-opacity"
                  />
                  <p className="text-xs text-gray-400 mt-2">{image.teacher_description}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto"></div>
          <p className="mt-4 text-gray-400">Loading lecture preview...</p>
        </div>
      </div>
    )
  }

  if (error || !lecture || !lectureStructure) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error || 'Failed to load lecture'}</p>
          <button
            onClick={() => window.close()}
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
          >
            Close Preview
          </button>
        </div>
      </div>
    )
  }

  const topics = Object.entries(lectureStructure.topics)
  const currentTopicData = currentTopic ? lectureStructure.topics[currentTopic] : null
  const currentContent = currentTopicData?.difficulty_levels[currentTab]

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-white font-medium">{lecture.title}</h1>
          <span className="text-sm text-gray-400 bg-gray-700 px-2 py-1 rounded">Teacher Preview</span>
        </div>
        <button
          onClick={() => window.close()}
          className="text-gray-400 hover:text-white transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Content */}
        <div className="flex-1 bg-gray-800 flex flex-col">
          {/* Topic Title and Tabs */}
          {currentTopicData && (
            <div className="bg-gray-900 border-b border-gray-700 px-6 py-3">
              <h2 className="text-xl font-medium text-white mb-3">{currentTopicData.title}</h2>
              <div className="flex space-x-4">
                {TABS.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => handleTabChange(tab.id as any)}
                    className={`
                      px-4 py-2 rounded-lg flex items-center space-x-2 transition-all
                      ${currentTab === tab.id 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }
                    `}
                  >
                    <span className="text-lg">{tab.icon}</span>
                    <span>{tab.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Content Area */}
          <div className="flex-1 overflow-y-auto px-6 py-6">
            {currentContent && renderContent(
              currentContent.content,
              currentContent.images || []
            )}
          </div>
        </div>

        {/* Right Panel - Questions */}
        {showQuestions && currentContent?.questions && currentContent.questions.length > 0 && (
          <div className="w-[480px] bg-gray-850 border-l border-gray-700">
            <div className="p-6 h-full overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-white">
                  Questions ({currentContent.questions.length})
                </h3>
                <button
                  onClick={() => setShowQuestions(false)}
                  className="text-gray-400 hover:text-white"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              
              <div className="bg-blue-900/20 border border-blue-700/50 rounded-lg p-3 mb-4">
                <p className="text-sm text-blue-300">
                  Preview Mode: Questions are shown with correct answers. 
                  AI evaluation is disabled in preview.
                </p>
              </div>
              
              <div className="space-y-4">
                {currentContent.questions.map((question: any, index: number) => (
                  <div 
                    key={index} 
                    className="bg-gray-800 rounded-lg p-4 border border-gray-700"
                  >
                    <button
                      onClick={() => toggleQuestion(index)}
                      className="w-full flex items-start justify-between text-left"
                    >
                      <div className="flex-1">
                        <p className="text-sm font-medium text-white">
                          Question {index + 1}
                        </p>
                        <p className="text-gray-300 mt-1">{question.question}</p>
                      </div>
                      {expandedQuestions.has(index) ? (
                        <ChevronDown className="h-5 w-5 text-gray-400 ml-2 flex-shrink-0" />
                      ) : (
                        <ChevronRight className="h-5 w-5 text-gray-400 ml-2 flex-shrink-0" />
                      )}
                    </button>
                    
                    {expandedQuestions.has(index) && (
                      <div className="mt-4 pt-4 border-t border-gray-700">
                        <div className="space-y-2">
                          <div>
                            <span className="text-xs text-gray-500">Type:</span>
                            <p className="text-sm text-gray-400 capitalize">
                              {question.question_type.replace('_', ' ')}
                            </p>
                          </div>
                          
                          {question.options && question.options.length > 0 && (
                            <div>
                              <span className="text-xs text-gray-500">Options:</span>
                              <ul className="mt-1 space-y-1">
                                {question.options.map((option: string, optIndex: number) => (
                                  <li 
                                    key={optIndex}
                                    className={`text-sm ${
                                      option === question.correct_answer
                                        ? 'text-green-400 font-medium'
                                        : 'text-gray-400'
                                    }`}
                                  >
                                    {String.fromCharCode(65 + optIndex)}. {option}
                                    {option === question.correct_answer && (
                                      <CheckCircle className="inline-block h-3 w-3 ml-1" />
                                    )}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          
                          <div>
                            <span className="text-xs text-gray-500">Expected Answer:</span>
                            <p className="text-sm text-green-400">{question.correct_answer}</p>
                          </div>
                          
                          {question.uses_images && (
                            <div className="text-xs text-yellow-400 flex items-center">
                              <span className="mr-1">📷</span>
                              Uses images
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
        
        {!showQuestions && (
          <button
            onClick={() => setShowQuestions(true)}
            className="fixed right-4 top-1/2 -translate-y-1/2 bg-gray-700 text-white p-2 rounded-l-lg hover:bg-gray-600"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Bottom Navigation */}
      <div className="bg-gray-800 border-t border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-400">Topics:</span>
          </div>
          <div className="flex space-x-2">
            {topics.map(([topicId, topicData]: [string, any], index) => (
              <button
                key={topicId}
                onClick={() => handleTopicChange(topicId)}
                className={`
                  px-4 py-2 rounded-lg flex items-center space-x-2 transition-all
                  ${currentTopic === topicId
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }
                `}
              >
                <span className="text-sm">{index + 1}. {topicData.title}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Image Modal */}
      {expandedImage && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-90 z-50 flex items-center justify-center p-4"
          onClick={() => setExpandedImage(null)}
        >
          <img
            src={expandedImage}
            alt="Expanded view"
            className="max-w-full max-h-full rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
          <button
            onClick={() => setExpandedImage(null)}
            className="absolute top-4 right-4 text-white bg-gray-800 rounded-full p-2 hover:bg-gray-700"
          >
            <X className="h-6 w-6" />
          </button>
        </div>
      )}
    </div>
  )
}