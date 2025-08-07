'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { 
  ChevronLeft,
  Loader,
  Save,
  AlertCircle,
  BookOpen,
  ChevronDown,
  ChevronRight,
  Edit3,
  Plus,
  Trash2,
  Users,
  Eye,
  CheckCircle
} from 'lucide-react'
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

export default function EditLecturePage() {
  const router = useRouter()
  const params = useParams()
  const lectureId = params.id as string

  const [lecture, setLecture] = useState<LectureAssignment | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  
  const [lectureStructure, setLectureStructure] = useState<any>(null)
  const [images, setImages] = useState<LectureImage[]>([])
  const [expandedTopics, setExpandedTopics] = useState<Set<string>>(new Set())
  const [editingContent, setEditingContent] = useState<{
    topicId: string
    difficulty: string
    field: 'content' | 'question'
    index?: number
  } | null>(null)
  const [editValue, setEditValue] = useState('')

  useEffect(() => {
    fetchLectureData()
  }, [lectureId])

  const fetchLectureData = async () => {
    try {
      const [lectureData, imageData] = await Promise.all([
        umalectureApi.getLecture(lectureId),
        umalectureApi.listImages(lectureId)
      ])
      
      setLecture(lectureData)
      setImages(imageData)
      
      if (lectureData.lecture_structure) {
        setLectureStructure(lectureData.lecture_structure)
      }
    } catch (err) {
      setError('Failed to load lecture data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const toggleTopic = (topicId: string) => {
    const newExpanded = new Set(expandedTopics)
    if (newExpanded.has(topicId)) {
      newExpanded.delete(topicId)
    } else {
      newExpanded.add(topicId)
    }
    setExpandedTopics(newExpanded)
  }

  const startEditing = (
    topicId: string, 
    difficulty: string, 
    field: 'content' | 'question', 
    value: string,
    index?: number
  ) => {
    setEditingContent({ topicId, difficulty, field, index })
    setEditValue(value)
  }

  const saveEdit = async () => {
    if (!editingContent || !lectureStructure) return
    
    try {
      const newStructure = { ...lectureStructure }
      const topic = newStructure.topics[editingContent.topicId]
      
      if (editingContent.field === 'content') {
        topic.difficulty_levels[editingContent.difficulty].content = editValue
      } else if (editingContent.field === 'question' && editingContent.index !== undefined) {
        topic.difficulty_levels[editingContent.difficulty].questions[editingContent.index].question = editValue
      }
      
      // Update local state first
      setLectureStructure(newStructure)
      setEditingContent(null)
      
      // Auto-save to database
      await saveLectureStructure(newStructure)
    } catch (error) {
      console.error('Error saving edit:', error)
      setError('Failed to save edit. Please try again.')
    }
  }

  const cancelEdit = () => {
    setEditingContent(null)
    setEditValue('')
  }

  const saveLectureStructure = async (structure?: any) => {
    setSaving(true)
    setError(null)
    
    try {
      console.log('Saving lecture structure:', structure || lectureStructure)
      
      const response = await umalectureApi.updateLectureStructure(
        lectureId, 
        structure || lectureStructure
      )
      
      console.log('Save response:', response)
      
      setSuccess('Changes saved successfully')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err: any) {
      console.error('Error saving lecture structure:', err)
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to save changes'
      setError(errorMessage)
    } finally {
      setSaving(false)
    }
  }

  const publishLecture = async () => {
    if (!confirm('Are you ready to publish this lecture? Students will be able to access it once assigned to classrooms.')) {
      return
    }
    
    try {
      await umalectureApi.publishLecture(lectureId)
      setSuccess('Lecture published successfully!')
      // Update local state
      if (lecture) {
        setLecture({ ...lecture, status: 'published' })
      }
    } catch (err) {
      setError('Failed to publish lecture')
      console.error(err)
    }
  }

  const assignToClassrooms = () => {
    router.push(`/teacher/uma-lecture/${lectureId}/assign`)
  }

  const previewAsStudent = () => {
    window.open(`/preview/lecture/${lectureId}`, '_blank')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!lecture || !lectureStructure) {
    return (
      <div className="container mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          Lecture not found or not processed yet
        </div>
      </div>
    )
  }

  const difficulties = ['basic', 'intermediate', 'advanced', 'expert']
  const difficultyColors = {
    basic: 'bg-green-100 text-green-800',
    intermediate: 'bg-yellow-100 text-yellow-800',
    advanced: 'bg-orange-100 text-orange-800',
    expert: 'bg-red-100 text-red-800'
  }

  return (
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <Link
          href="/teacher/uma-lecture"
          className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Back to Lectures
        </Link>
        
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Review & Edit: {lecture.title}
            </h1>
            <p className="text-gray-600">
              Review AI-generated content and make any necessary adjustments
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={() => saveLectureStructure()}
              disabled={saving}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center disabled:opacity-50"
            >
              <Save className="w-4 h-4 mr-2" />
              {saving ? 'Saving...' : 'Save All Changes'}
            </button>
            
            <button
              onClick={previewAsStudent}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center"
            >
              <Eye className="w-4 h-4 mr-2" />
              Preview
            </button>
            
            {lecture.status === 'published' ? (
              <button
                onClick={assignToClassrooms}
                className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark flex items-center"
              >
                <Users className="w-4 h-4 mr-2" />
                Assign to Classes
              </button>
            ) : (
              <button
                onClick={publishLecture}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center"
              >
                <CheckCircle className="w-4 h-4 mr-2" />
                Publish Lecture
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Status Messages */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-red-800 flex items-start">
          <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
          {error}
        </div>
      )}
      
      {success && (
        <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4 text-green-800 flex items-start">
          <CheckCircle className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
          {success}
        </div>
      )}

      {/* Lecture Info */}
      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <span className="text-sm text-gray-600">Subject</span>
            <p className="font-medium">{lecture.subject}</p>
          </div>
          <div>
            <span className="text-sm text-gray-600">Grade Level</span>
            <p className="font-medium">{lecture.grade_level}</p>
          </div>
          <div>
            <span className="text-sm text-gray-600">Status</span>
            <p className="font-medium capitalize">{lecture.status}</p>
          </div>
        </div>
      </div>

      {/* Topics and Content */}
      <div className="space-y-4">
        {Object.entries(lectureStructure.topics).map(([topicId, topicData]: [string, any]) => (
          <div key={topicId} className="bg-white rounded-lg border border-gray-200">
            {/* Topic Header */}
            <button
              onClick={() => toggleTopic(topicId)}
              className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50"
            >
              <div className="flex items-center">
                <BookOpen className="w-5 h-5 mr-3 text-gray-600" />
                <h3 className="font-semibold text-lg">{topicData.title}</h3>
              </div>
              {expandedTopics.has(topicId) ? (
                <ChevronDown className="w-5 h-5 text-gray-600" />
              ) : (
                <ChevronRight className="w-5 h-5 text-gray-600" />
              )}
            </button>

            {/* Topic Content */}
            {expandedTopics.has(topicId) && (
              <div className="border-t border-gray-200">
                {difficulties.map(difficulty => {
                  const content = topicData.difficulty_levels[difficulty]
                  if (!content) return null

                  return (
                    <div key={difficulty} className="border-b border-gray-100 last:border-0">
                      <div className="px-6 py-4">
                        <div className="flex items-center justify-between mb-3">
                          <span className={`px-3 py-1 rounded-full text-sm font-medium ${(difficultyColors as any)[difficulty]}`}>
                            {difficulty.charAt(0).toUpperCase() + difficulty.slice(1)} Level
                          </span>
                          <span className="text-sm text-gray-500">
                            {content.questions?.length || 0} questions • {content.images?.length || 0} images
                          </span>
                        </div>

                        {/* Content */}
                        <div className="mb-4">
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="font-medium text-sm text-gray-700">Content</h4>
                            {!(editingContent?.topicId === topicId && 
                              editingContent?.difficulty === difficulty && 
                              editingContent?.field === 'content') && (
                              <button
                                onClick={() => startEditing(topicId, difficulty, 'content', content.content)}
                                className="text-xs text-primary-600 hover:text-primary-700 flex items-center"
                              >
                                <Edit3 className="w-3 h-3 mr-1" />
                                Edit
                              </button>
                            )}
                          </div>
                          {editingContent?.topicId === topicId && 
                           editingContent?.difficulty === difficulty && 
                           editingContent?.field === 'content' ? (
                            <div>
                              <textarea
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-600 focus:border-transparent"
                                rows={6}
                                autoFocus
                              />
                              <div className="mt-2 flex space-x-2">
                                <button
                                  onClick={saveEdit}
                                  className="px-3 py-1 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
                                >
                                  Save
                                </button>
                                <button
                                  onClick={cancelEdit}
                                  className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div 
                              className="prose prose-sm max-w-none text-gray-700 p-3 rounded border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-colors"
                              onClick={() => startEditing(topicId, difficulty, 'content', content.content)}
                              title="Click to edit"
                            >
                              {content.content}
                            </div>
                          )}
                        </div>

                        {/* Questions */}
                        {content.questions && content.questions.length > 0 && (
                          <div>
                            <h4 className="font-medium text-sm text-gray-700 mb-2">Questions</h4>
                            <div className="space-y-2">
                              {content.questions.map((question: any, index: number) => (
                                <div key={index} className="bg-gray-50 rounded p-3">
                                  {editingContent?.topicId === topicId && 
                                   editingContent?.difficulty === difficulty && 
                                   editingContent?.field === 'question' &&
                                   editingContent?.index === index ? (
                                    <div>
                                      <textarea
                                        value={editValue}
                                        onChange={(e) => setEditValue(e.target.value)}
                                        className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-primary-600 focus:border-transparent text-sm"
                                        rows={3}
                                        autoFocus
                                      />
                                      <div className="mt-2 flex space-x-2">
                                        <button
                                          onClick={saveEdit}
                                          className="px-3 py-1 bg-primary-600 text-white rounded text-sm hover:bg-primary-700"
                                        >
                                          Save
                                        </button>
                                        <button
                                          onClick={cancelEdit}
                                          className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
                                        >
                                          Cancel
                                        </button>
                                      </div>
                                    </div>
                                  ) : (
                                    <div className="flex items-start justify-between">
                                      <div className="flex-1">
                                        <p className="text-sm font-medium">Q{index + 1}: {question.question}</p>
                                        <p className="text-sm text-gray-600 mt-1">
                                          Answer: {question.correct_answer}
                                        </p>
                                        {question.options && (
                                          <p className="text-xs text-gray-500 mt-1">
                                            Options: {question.options.join(', ')}
                                          </p>
                                        )}
                                      </div>
                                      <button
                                        onClick={() => startEditing(topicId, difficulty, 'question', question.question, index)}
                                        className="ml-2 text-primary-600 hover:text-primary-700 p-1"
                                        title="Edit question"
                                      >
                                        <Edit3 className="w-4 h-4" />
                                      </button>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Save Bar */}
      {saving && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4">
          <div className="container mx-auto flex items-center justify-center">
            <Loader className="w-5 h-5 mr-2 animate-spin text-primary-600" />
            <span>Saving changes...</span>
          </div>
        </div>
      )}
    </div>
  )
}