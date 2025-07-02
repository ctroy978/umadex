'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { 
  ChevronLeft,
  ChevronRight,
  Loader,
  AlertCircle,
  BookOpen,
  Trophy,
  Target,
  Star,
  CheckCircle,
  XCircle,
  ArrowRight
} from 'lucide-react'
import { umalectureStudentApi } from '@/lib/umalectureApi'
import type { LectureTopicContent, LectureStudentProgress } from '@/lib/umalectureApi'

interface Topic {
  topic_id: string
  title: string
  available_difficulties: string[]
  completed_difficulties: string[]
}

export default function StudentLecturePage() {
  const router = useRouter()
  const params = useParams()
  const assignmentId = params.id as string

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState<LectureStudentProgress | null>(null)
  const [topics, setTopics] = useState<Topic[]>([])
  const [currentContent, setCurrentContent] = useState<LectureTopicContent | null>(null)
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState('')
  const [showFeedback, setShowFeedback] = useState(false)
  const [answerResult, setAnswerResult] = useState<any>(null)

  useEffect(() => {
    initializeLecture()
  }, [assignmentId])

  const initializeLecture = async () => {
    try {
      // Start assignment and get progress
      const progressData = await umalectureStudentApi.startAssignment(assignmentId)
      setProgress(progressData)
      
      // Get available topics
      const topicsData = await umalectureStudentApi.getTopics(assignmentId)
      setTopics(topicsData)
      
      // If no current topic, select the first one
      if (!progressData.current_topic && topicsData.length > 0) {
        await selectTopic(topicsData[0].topic_id, 'basic')
      }
    } catch (err) {
      setError('Failed to load lecture')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const selectTopic = async (topicId: string, difficulty: string) => {
    setLoading(true)
    try {
      const content = await umalectureStudentApi.getTopicContent(
        assignmentId,
        topicId,
        difficulty
      )
      setCurrentContent(content)
      setCurrentQuestion(0)
      setSelectedAnswer('')
      setShowFeedback(false)
      setAnswerResult(null)
    } catch (err) {
      setError('Failed to load topic content')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const submitAnswer = async () => {
    if (!currentContent || !selectedAnswer) return
    
    try {
      const result = await umalectureStudentApi.submitAnswer(
        assignmentId,
        currentContent.topic_id,
        currentContent.difficulty_level,
        currentQuestion,
        selectedAnswer
      )
      
      setAnswerResult(result)
      setShowFeedback(true)
      
      // Update local progress
      if (progress && result.points_earned > 0) {
        setProgress({
          ...progress,
          total_points: progress.total_points + result.points_earned
        })
      }
    } catch (err) {
      setError('Failed to submit answer')
      console.error(err)
    }
  }

  const continueToNext = () => {
    if (!currentContent || !answerResult) return
    
    if (answerResult.next_action === 'next_question') {
      // Next question in same topic/difficulty
      setCurrentQuestion(currentQuestion + 1)
      setSelectedAnswer('')
      setShowFeedback(false)
      setAnswerResult(null)
    } else if (answerResult.next_action === 'next_difficulty') {
      // Next difficulty level
      const nextDiff = currentContent.next_difficulties[0]
      if (nextDiff) {
        selectTopic(currentContent.topic_id, nextDiff)
      }
    } else if (answerResult.next_action === 'complete_topic') {
      // Topic completed - go to topic selection
      setCurrentContent(null)
      initializeLecture() // Refresh progress
    }
  }

  const getDifficultyColor = (difficulty: string) => {
    const colors = {
      basic: 'text-green-600 bg-green-100',
      intermediate: 'text-yellow-600 bg-yellow-100',
      advanced: 'text-orange-600 bg-orange-100',
      expert: 'text-red-600 bg-red-100'
    }
    return colors[difficulty] || 'text-gray-600 bg-gray-100'
  }

  if (loading && !currentContent) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800 flex items-start">
          <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
          {error}
        </div>
      </div>
    )
  }

  // Topic Selection View
  if (!currentContent) {
    return (
      <div className="container mx-auto p-6 max-w-4xl">
        <div className="mb-6">
          <Link
            href="/student/dashboard"
            className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Back to Dashboard
          </Link>
          
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Interactive Lecture
          </h1>
        </div>

        {/* Progress Summary */}
        {progress && (
          <div className="bg-blue-50 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-blue-600">Total Points</p>
                <p className="text-2xl font-bold text-blue-800">{progress.total_points}</p>
              </div>
              <Trophy className="w-8 h-8 text-blue-600" />
            </div>
            <div className="mt-2 text-sm text-blue-700">
              {progress.topics_completed.length} of {topics.length} topics completed
            </div>
          </div>
        )}

        {/* Topic Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {topics.map(topic => {
            const isCompleted = progress?.topics_completed.includes(topic.topic_id)
            
            return (
              <div
                key={topic.topic_id}
                className={`bg-white rounded-lg border-2 p-6 ${
                  isCompleted ? 'border-green-300 bg-green-50' : 'border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between mb-4">
                  <h3 className="font-semibold text-lg">{topic.title}</h3>
                  {isCompleted && (
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  )}
                </div>
                
                <div className="mb-4">
                  <p className="text-sm text-gray-600 mb-2">Choose difficulty:</p>
                  <div className="flex flex-wrap gap-2">
                    {topic.available_difficulties.map(difficulty => {
                      const isCompletedDiff = topic.completed_difficulties.includes(difficulty)
                      
                      return (
                        <button
                          key={difficulty}
                          onClick={() => selectTopic(topic.topic_id, difficulty)}
                          className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                            getDifficultyColor(difficulty)
                          } ${isCompletedDiff ? 'ring-2 ring-green-500' : ''}`}
                        >
                          {isCompletedDiff && <Star className="w-3 h-3 inline mr-1" />}
                          {difficulty}
                        </button>
                      )
                    })}
                  </div>
                </div>
                
                <button
                  onClick={() => selectTopic(topic.topic_id, topic.available_difficulties[0])}
                  className="w-full py-2 bg-primary text-white rounded-lg hover:bg-primary-dark flex items-center justify-center"
                >
                  Start Learning
                  <ArrowRight className="w-4 h-4 ml-2" />
                </button>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  // Content View
  const question = currentContent.questions[currentQuestion]
  
  return (
    <div className="container mx-auto p-6 max-w-4xl">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => setCurrentContent(null)}
          className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Back to Topics
        </button>
        
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {topics.find(t => t.topic_id === currentContent.topic_id)?.title}
            </h1>
            <span className={`inline-flex px-3 py-1 rounded-full text-sm font-medium mt-2 ${
              getDifficultyColor(currentContent.difficulty_level)
            }`}>
              {currentContent.difficulty_level} Level
            </span>
          </div>
          
          <div className="text-right">
            <p className="text-sm text-gray-600">Points</p>
            <p className="text-2xl font-bold text-primary">{progress?.total_points || 0}</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <div className="prose prose-lg max-w-none mb-6">
          {currentContent.content.split('\n').map((paragraph, index) => (
            <p key={index} className="mb-4">{paragraph}</p>
          ))}
        </div>
        
        {/* Images */}
        {currentContent.images.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            {currentContent.images.map((image: any) => (
              <div key={image.id} className="border rounded-lg overflow-hidden">
                <img
                  src={image.display_url || image.original_url}
                  alt={image.ai_description || image.teacher_description}
                  className="w-full h-48 object-cover"
                />
                <div className="p-3 bg-gray-50">
                  <p className="text-sm text-gray-700">
                    {image.ai_description || image.teacher_description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Question */}
      {question && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-lg">
              Question {currentQuestion + 1} of {currentContent.questions.length}
            </h3>
            <Target className="w-5 h-5 text-gray-600" />
          </div>
          
          <p className="text-lg mb-4">{question.question}</p>
          
          {question.question_type === 'multiple_choice' && question.options ? (
            <div className="space-y-2">
              {question.options.map((option: string, index: number) => (
                <label
                  key={index}
                  className={`block p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedAnswer === option
                      ? 'border-primary bg-primary-light'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="answer"
                    value={option}
                    checked={selectedAnswer === option}
                    onChange={(e) => setSelectedAnswer(e.target.value)}
                    className="sr-only"
                    disabled={showFeedback}
                  />
                  {option}
                </label>
              ))}
            </div>
          ) : (
            <input
              type="text"
              value={selectedAnswer}
              onChange={(e) => setSelectedAnswer(e.target.value)}
              placeholder="Type your answer here..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              disabled={showFeedback}
            />
          )}
          
          {/* Feedback */}
          {showFeedback && answerResult && (
            <div className={`mt-4 p-4 rounded-lg ${
              answerResult.is_correct
                ? 'bg-green-50 border border-green-200'
                : 'bg-red-50 border border-red-200'
            }`}>
              <div className="flex items-start">
                {answerResult.is_correct ? (
                  <CheckCircle className="w-5 h-5 text-green-600 mr-2 flex-shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                )}
                <div>
                  <p className={`font-medium ${
                    answerResult.is_correct ? 'text-green-800' : 'text-red-800'
                  }`}>
                    {answerResult.feedback}
                  </p>
                  {answerResult.points_earned > 0 && (
                    <p className="text-sm text-green-700 mt-1">
                      +{answerResult.points_earned} points!
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
          
          {/* Actions */}
          <div className="mt-6 flex justify-end space-x-3">
            {!showFeedback ? (
              <button
                onClick={submitAnswer}
                disabled={!selectedAnswer}
                className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                Submit Answer
              </button>
            ) : (
              <button
                onClick={continueToNext}
                className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark flex items-center"
              >
                {answerResult?.next_action === 'complete_topic' ? 'Complete Topic' : 'Continue'}
                <ChevronRight className="w-4 h-4 ml-2" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}