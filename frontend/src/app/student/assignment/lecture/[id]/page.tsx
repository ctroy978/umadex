'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams, useSearchParams } from 'next/navigation'
import { ChevronLeft, BookOpen, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { studentApi } from '@/lib/studentApi'
import { umalectureApi } from '@/lib/umalectureApi'
import type { LectureStudentProgress, LectureTopicResponse } from '@/lib/umalectureApi'

export default function StudentLecturePage() {
  const router = useRouter()
  const params = useParams()
  const searchParams = useSearchParams()
  const assignmentId = params.id as string
  const classroomId = searchParams.get('classroomId')
  
  const [progress, setProgress] = useState<LectureStudentProgress | null>(null)
  const [topics, setTopics] = useState<LectureTopicResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchLectureData()
  }, [assignmentId])

  const fetchLectureData = async () => {
    try {
      setLoading(true)
      const [progressData, topicsData] = await Promise.all([
        umalectureApi.startLectureAssignment(assignmentId),
        umalectureApi.getLectureTopics(assignmentId)
      ])
      
      setProgress(progressData)
      setTopics(topicsData)
    } catch (err) {
      console.error('Failed to load lecture:', err)
      setError('Failed to load lecture. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleTopicClick = (topicId: string) => {
    router.push(`/student/assignments/lecture/${assignmentId}/topic/${topicId}?classroomId=${classroomId}`)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading lecture...</p>
        </div>
      </div>
    )
  }

  if (error || !progress) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600">{error || 'Failed to load lecture'}</p>
          <button
            onClick={() => router.push(classroomId ? `/student/classrooms/${classroomId}` : '/student/dashboard')}
            className="mt-4 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4 flex items-center justify-between">
            <div className="flex items-center">
              <button
                onClick={() => router.push(classroomId ? `/student/classrooms/${classroomId}` : '/student/dashboard')}
                className="mr-4 text-gray-500 hover:text-gray-700"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">{progress.title}</h1>
                <p className="text-sm text-gray-500">
                  {progress.subject} • {progress.grade_level}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Progress Overview */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Your Progress</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600">Topics Completed</p>
              <p className="text-2xl font-bold text-gray-900">
                {progress.topics_completed} / {progress.total_topics}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Questions Answered</p>
              <p className="text-2xl font-bold text-gray-900">
                {progress.questions_answered} / {progress.total_questions}
              </p>
            </div>
          </div>
          {progress.topics_completed === progress.total_topics && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center text-green-800">
                <CheckCircle className="h-5 w-5 mr-2" />
                <span className="font-medium">Congratulations! You've completed all topics.</span>
              </div>
            </div>
          )}
        </div>

        {/* Learning Objectives */}
        {progress.learning_objectives && progress.learning_objectives.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Learning Objectives</h2>
            <ul className="space-y-2">
              {progress.learning_objectives.map((objective, index) => (
                <li key={index} className="flex items-start">
                  <span className="text-primary mr-2">•</span>
                  <span className="text-gray-700">{objective}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Topics */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Choose a Topic to Explore</h2>
          <div className="space-y-3">
            {topics.map((topic) => (
              <button
                key={topic.id}
                onClick={() => handleTopicClick(topic.id)}
                className="w-full text-left p-4 rounded-lg border-2 transition-all hover:shadow-md hover:border-primary"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900">{topic.title}</h3>
                    <div className="mt-1 flex items-center space-x-4 text-sm text-gray-600">
                      <span className="flex items-center">
                        <BookOpen className="h-4 w-4 mr-1" />
                        {topic.difficulty_levels_available} difficulty levels
                      </span>
                      {topic.completed_levels > 0 && (
                        <span className="flex items-center text-green-600">
                          <CheckCircle className="h-4 w-4 mr-1" />
                          {topic.completed_levels} completed
                        </span>
                      )}
                    </div>
                  </div>
                  <ChevronLeft className="h-5 w-5 text-gray-400 rotate-180" />
                </div>
              </button>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}