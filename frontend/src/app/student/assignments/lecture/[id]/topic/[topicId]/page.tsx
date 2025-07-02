'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams, useSearchParams } from 'next/navigation'
import { 
  ChevronLeft, 
  ChevronRight, 
  BookOpen, 
  CheckCircle, 
  AlertCircle,
  Sparkles,
  Send,
  RotateCcw
} from 'lucide-react'
import { umalectureApi } from '@/lib/umalectureApi'
import type { LectureTopicContent } from '@/lib/umalectureApi'

const DIFFICULTY_LEVELS = ['basic', 'intermediate', 'advanced', 'expert'] as const
type DifficultyLevel = typeof DIFFICULTY_LEVELS[number]

const DIFFICULTY_DISPLAY = {
  basic: { name: 'Basic', color: 'bg-green-500' },
  intermediate: { name: 'Intermediate', color: 'bg-blue-500' },
  advanced: { name: 'Advanced', color: 'bg-purple-500' },
  expert: { name: 'Expert', color: 'bg-red-500' }
}

export default function TopicViewPage() {
  const router = useRouter()
  const params = useParams()
  const searchParams = useSearchParams()
  const assignmentId = params.id as string
  const topicId = params.topicId as string
  const classroomId = searchParams.get('classroomId')
  
  const [currentDifficulty, setCurrentDifficulty] = useState<DifficultyLevel>('basic')
  const [content, setContent] = useState<LectureTopicContent | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showQuestions, setShowQuestions] = useState(false)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [userAnswer, setUserAnswer] = useState('')
  const [feedback, setFeedback] = useState<{ correct: boolean; message: string } | null>(null)
  const [answeredQuestions, setAnsweredQuestions] = useState<Set<number>>(new Set())

  useEffect(() => {
    fetchContent(currentDifficulty)
  }, [currentDifficulty, topicId])

  const fetchContent = async (difficulty: DifficultyLevel) => {
    try {
      setLoading(true)
      setError(null)
      const data = await umalectureApi.getTopicContent(assignmentId, topicId, difficulty)
      setContent(data)
      setShowQuestions(false)
      setCurrentQuestionIndex(0)
      setAnsweredQuestions(new Set())
      setFeedback(null)
    } catch (err) {
      console.error('Failed to load content:', err)
      setError('Failed to load content. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleDifficultyChange = (newDifficulty: DifficultyLevel) => {
    if (newDifficulty !== currentDifficulty) {
      setCurrentDifficulty(newDifficulty)
    }
  }

  const handleAnswerSubmit = async () => {
    if (!content || !userAnswer.trim()) return

    try {
      const result = await umalectureApi.answerTopicQuestion(
        assignmentId,
        topicId,
        {
          difficulty: currentDifficulty,
          question_index: currentQuestionIndex,
          answer: userAnswer
        }
      )
      
      setFeedback({
        correct: result.correct,
        message: result.correct ? 'Correct! Well done!' : 'Not quite right. Try again!'
      })
      
      if (result.correct) {
        setAnsweredQuestions(prev => new Set(prev).add(currentQuestionIndex))
      }
    } catch (err) {
      console.error('Failed to submit answer:', err)
      setFeedback({
        correct: false,
        message: 'Failed to submit answer. Please try again.'
      })
    }
  }

  const handleNextQuestion = () => {
    if (!content) return
    
    if (currentQuestionIndex < content.questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1)
      setUserAnswer('')
      setFeedback(null)
    } else if (answeredQuestions.size === content.questions.length) {
      // All questions answered correctly - suggest next difficulty
      const currentIndex = DIFFICULTY_LEVELS.indexOf(currentDifficulty)
      if (currentIndex < DIFFICULTY_LEVELS.length - 1) {
        setCurrentDifficulty(DIFFICULTY_LEVELS[currentIndex + 1])
      }
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading content...</p>
        </div>
      </div>
    )
  }

  if (error || !content) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600">{error || 'Failed to load content'}</p>
          <button
            onClick={() => router.push(`/student/assignment/lecture/${assignmentId}?classroomId=${classroomId}`)}
            className="mt-4 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark"
          >
            Back to Topics
          </button>
        </div>
      </div>
    )
  }

  const currentQuestion = content.questions[currentQuestionIndex]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4 flex items-center justify-between">
            <div className="flex items-center">
              <button
                onClick={() => router.push(`/student/assignment/lecture/${assignmentId}?classroomId=${classroomId}`)}
                className="mr-4 text-gray-500 hover:text-gray-700"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">{content.topic_title}</h1>
                <p className="text-sm text-gray-500">{content.lecture_title}</p>
              </div>
            </div>
            
            {/* Difficulty Selector */}
            <div className="flex items-center space-x-2">
              {DIFFICULTY_LEVELS.map((level) => (
                <button
                  key={level}
                  onClick={() => handleDifficultyChange(level)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-all ${
                    currentDifficulty === level
                      ? `${DIFFICULTY_DISPLAY[level].color} text-white`
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  {DIFFICULTY_DISPLAY[level].name}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!showQuestions ? (
          <>
            {/* Educational Content */}
            <div className="bg-white rounded-lg shadow p-8 mb-6">
              <div className="prose max-w-none">
                <p className="text-gray-700 whitespace-pre-wrap">{content.content}</p>
              </div>
              
              {/* Images */}
              {content.images && content.images.length > 0 && (
                <div className="mt-6 space-y-4">
                  <h3 className="text-lg font-medium text-gray-900">Visual Aids</h3>
                  {content.images.map((imageId, index) => (
                    <div key={imageId} className="rounded-lg overflow-hidden border border-gray-200">
                      <img 
                        src={`/api/v1/umalecture/images/${imageId}`} 
                        alt={`Visual aid ${index + 1}`}
                        className="w-full"
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {/* Actions */}
            <div className="flex justify-between items-center">
              <p className="text-sm text-gray-600">
                Read through the content above, then test your understanding with questions.
              </p>
              <button
                onClick={() => setShowQuestions(true)}
                className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark flex items-center"
              >
                <Sparkles className="h-4 w-4 mr-2" />
                Test Your Knowledge
              </button>
            </div>
          </>
        ) : (
          <>
            {/* Questions */}
            <div className="bg-white rounded-lg shadow p-8">
              <div className="mb-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-medium text-gray-900">
                    Question {currentQuestionIndex + 1} of {content.questions.length}
                  </h2>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    DIFFICULTY_DISPLAY[currentDifficulty].color
                  } text-white`}>
                    {DIFFICULTY_DISPLAY[currentDifficulty].name}
                  </span>
                </div>
                
                <p className="text-gray-700 text-lg mb-4">{currentQuestion.question}</p>
                
                {currentQuestion.question_type === 'multiple_choice' && currentQuestion.options ? (
                  <div className="space-y-2">
                    {currentQuestion.options.map((option, index) => (
                      <label key={index} className="flex items-center p-3 rounded-lg border-2 cursor-pointer hover:bg-gray-50 transition-colors">
                        <input
                          type="radio"
                          name="answer"
                          value={option}
                          checked={userAnswer === option}
                          onChange={(e) => setUserAnswer(e.target.value)}
                          className="mr-3"
                        />
                        <span>{option}</span>
                      </label>
                    ))}
                  </div>
                ) : (
                  <textarea
                    value={userAnswer}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    placeholder="Type your answer here..."
                    className="w-full p-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                    rows={4}
                  />
                )}
              </div>
              
              {/* Feedback */}
              {feedback && (
                <div className={`mb-4 p-4 rounded-lg ${
                  feedback.correct ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                }`}>
                  <div className="flex items-start">
                    {feedback.correct ? (
                      <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 mr-2" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 mr-2" />
                    )}
                    <p className={feedback.correct ? 'text-green-800' : 'text-red-800'}>
                      {feedback.message}
                    </p>
                  </div>
                </div>
              )}
              
              {/* Actions */}
              <div className="flex justify-between items-center">
                <button
                  onClick={() => setShowQuestions(false)}
                  className="text-gray-600 hover:text-gray-900"
                >
                  Back to Content
                </button>
                
                <div className="flex space-x-3">
                  {!feedback && (
                    <button
                      onClick={handleAnswerSubmit}
                      disabled={!userAnswer.trim()}
                      className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center"
                    >
                      <Send className="h-4 w-4 mr-2" />
                      Submit Answer
                    </button>
                  )}
                  
                  {feedback && !feedback.correct && (
                    <button
                      onClick={() => {
                        setUserAnswer('')
                        setFeedback(null)
                      }}
                      className="px-6 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 flex items-center"
                    >
                      <RotateCcw className="h-4 w-4 mr-2" />
                      Try Again
                    </button>
                  )}
                  
                  {feedback && feedback.correct && (
                    <button
                      onClick={handleNextQuestion}
                      className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center"
                    >
                      {currentQuestionIndex < content.questions.length - 1 ? (
                        <>
                          Next Question
                          <ChevronRight className="h-4 w-4 ml-2" />
                        </>
                      ) : answeredQuestions.size === content.questions.length && 
                        DIFFICULTY_LEVELS.indexOf(currentDifficulty) < DIFFICULTY_LEVELS.length - 1 ? (
                        <>
                          Next Difficulty
                          <Sparkles className="h-4 w-4 ml-2" />
                        </>
                      ) : (
                        <>
                          Complete
                          <CheckCircle className="h-4 w-4 ml-2" />
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>
            </div>
            
            {/* Progress Indicator */}
            <div className="mt-4">
              <div className="flex space-x-2">
                {content.questions.map((_, index) => (
                  <div
                    key={index}
                    className={`h-2 flex-1 rounded-full ${
                      answeredQuestions.has(index)
                        ? 'bg-green-500'
                        : index === currentQuestionIndex
                        ? 'bg-primary'
                        : 'bg-gray-300'
                    }`}
                  />
                ))}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}