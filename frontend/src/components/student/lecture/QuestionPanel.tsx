import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, AlertCircle, Send, Loader2, RotateCcw } from 'lucide-react'
import { umalectureApi } from '@/lib/umalectureApi'
import type { LectureImage } from '@/lib/umalectureApi'

interface Question {
  question: string
  question_type: 'multiple_choice' | 'short_answer'
  difficulty: string
  correct_answer?: string
  options?: string[]
  uses_images?: boolean
}

interface QuestionPanelProps {
  questions: Question[]
  difficulty: string
  topicId: string
  assignmentId: string
  lectureId: string
  questionsCorrect: boolean[]
  images: LectureImage[]
  onQuestionComplete: (questionIndex: number, isCorrect: boolean) => void
  onAllQuestionsComplete?: () => void
}

interface QuestionState {
  answer: string
  submitted: boolean
  isCorrect: boolean | null
  feedback: string | null
  isEvaluating: boolean
  attemptCount: number
}

export function QuestionPanel({
  questions,
  difficulty,
  topicId,
  assignmentId,
  lectureId,
  questionsCorrect,
  images,
  onQuestionComplete,
  onAllQuestionsComplete,
}: QuestionPanelProps) {
  const [questionStates, setQuestionStates] = useState<QuestionState[]>([])

  useEffect(() => {
    // Initialize question states
    setQuestionStates(
      questions.map((_, index) => ({
        answer: '',
        submitted: questionsCorrect[index] === true,
        isCorrect: questionsCorrect[index] || null,
        feedback: null,
        isEvaluating: false,
        attemptCount: 0,
      }))
    )
  }, [questions, questionsCorrect])

  const handleAnswerChange = (questionIndex: number, answer: string) => {
    setQuestionStates(prev => {
      const newStates = [...prev]
      newStates[questionIndex] = {
        ...newStates[questionIndex],
        answer,
      }
      return newStates
    })
  }

  const handleSubmitAnswer = async (questionIndex: number) => {
    const state = questionStates[questionIndex]
    const question = questions[questionIndex]
    
    if (!state.answer.trim() || state.isEvaluating) return

    // Update state to show evaluating
    setQuestionStates(prev => {
      const newStates = [...prev]
      newStates[questionIndex] = {
        ...newStates[questionIndex],
        isEvaluating: true,
      }
      return newStates
    })

    try {
      // Get image descriptions if question uses images
      let imageDescriptions: string[] = []
      if (question.uses_images && images.length > 0) {
        imageDescriptions = images.map(img => img.ai_description || img.teacher_description)
      }

      // Evaluate the answer using AI
      const result = await umalectureApi.evaluateResponse({
        assignment_id: assignmentId,
        topic_id: topicId,
        difficulty,
        question_text: question.question,
        student_answer: state.answer,
        expected_answer: question.correct_answer,
        includes_images: question.uses_images || false,
        image_descriptions: imageDescriptions,
      })

      // Update state with results
      setQuestionStates(prev => {
        const newStates = [...prev]
        newStates[questionIndex] = {
          ...newStates[questionIndex],
          submitted: true,
          isCorrect: result.is_correct,
          feedback: result.is_correct ? 'You have answered this question correctly!' : result.feedback,
          isEvaluating: false,
          attemptCount: (newStates[questionIndex].attemptCount || 0) + 1,
        }
        return newStates
      })

      // Notify parent component
      onQuestionComplete(questionIndex, result.is_correct)

    } catch (error) {
      console.error('Error evaluating answer:', error)
      
      // Show error state
      setQuestionStates(prev => {
        const newStates = [...prev]
        newStates[questionIndex] = {
          ...newStates[questionIndex],
          isEvaluating: false,
          feedback: 'Sorry, there was an error evaluating your answer. Please try again.',
        }
        return newStates
      })
    }
  }

  const handleRetryAnswer = (questionIndex: number) => {
    setQuestionStates(prev => {
      const newStates = [...prev]
      newStates[questionIndex] = {
        ...newStates[questionIndex],
        answer: '',
        submitted: false,
        isCorrect: null,
        feedback: null,
        // Don't increment attempt count here - it's already incremented when submitting
      }
      return newStates
    })
  }

  const allQuestionsCorrect = questionStates.every(state => state.isCorrect === true)

  // Trigger callback when all questions are completed
  useEffect(() => {
    if (allQuestionsCorrect && questions.length > 0 && onAllQuestionsComplete) {
      // Add a small delay to ensure UI updates are visible
      const timer = setTimeout(() => {
        onAllQuestionsComplete()
      }, 1500)
      return () => clearTimeout(timer)
    }
  }, [allQuestionsCorrect, questions.length, onAllQuestionsComplete])

  return (
    <div className="h-full flex flex-col bg-gray-850">
      {/* Header */}
      <div className="bg-gray-900 border-b border-gray-700 px-6 py-4">
        <h3 className="text-lg font-medium text-white">Questions</h3>
        <p className="text-sm text-gray-400 mt-1">
          Answer all questions correctly to complete this difficulty level
        </p>
      </div>

      {/* Questions */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {questions.map((question, index) => {
          const state = questionStates[index] || {
            answer: '',
            submitted: false,
            isCorrect: null,
            feedback: null,
            isEvaluating: false,
            attemptCount: 0,
          }

          return (
            <div 
              key={index}
              className={`
                border rounded-lg p-4 transition-all
                ${state.isCorrect === true 
                  ? 'border-green-600 bg-green-900/20' 
                  : state.isCorrect === false
                  ? 'border-yellow-600 bg-yellow-900/20'
                  : 'border-gray-700 bg-gray-800'
                }
              `}
            >
              {/* Question Header */}
              <div className="flex items-start justify-between mb-3">
                <span className="text-sm font-medium text-gray-400">
                  Question {index + 1}
                </span>
                {state.isCorrect === true && (
                  <CheckCircle className="h-5 w-5 text-green-400" />
                )}
              </div>

              {/* Question Text */}
              <p className="text-white mb-4">{question.question}</p>

              {/* Multiple Choice Options */}
              {question.question_type === 'multiple_choice' && question.options && (
                <div className="space-y-2 mb-4">
                  {question.options.map((option, optIndex) => (
                    <label 
                      key={optIndex}
                      className={`
                        flex items-center p-3 rounded-lg cursor-pointer transition-all
                        ${state.submitted && state.isCorrect === true
                          ? 'cursor-not-allowed opacity-75' 
                          : 'hover:bg-gray-700'
                        }
                        ${state.answer === option 
                          ? 'bg-gray-700 border border-blue-500' 
                          : 'bg-gray-750 border border-gray-600'
                        }
                      `}
                    >
                      <input
                        type="radio"
                        name={`question-${index}`}
                        value={option}
                        checked={state.answer === option}
                        onChange={(e) => handleAnswerChange(index, e.target.value)}
                        disabled={state.submitted && state.isCorrect === true}
                        className="mr-3"
                      />
                      <span className="text-gray-300">{option}</span>
                    </label>
                  ))}
                </div>
              )}

              {/* Short Answer Input */}
              {question.question_type === 'short_answer' && (
                <textarea
                  value={state.answer}
                  onChange={(e) => handleAnswerChange(index, e.target.value)}
                  disabled={state.submitted}
                  placeholder="Type your answer here..."
                  className={`
                    w-full px-3 py-2 rounded-lg bg-gray-750 border text-gray-300
                    placeholder-gray-500 resize-none h-24
                    ${state.submitted && state.isCorrect === true
                      ? 'border-gray-600 cursor-not-allowed opacity-75' 
                      : 'border-gray-600 focus:border-blue-500 focus:outline-none'
                    }
                  `}
                />
              )}

              {/* Submit Button or Retry Button */}
              {(!state.submitted || (state.submitted && state.isCorrect === false)) && (
                <div className="mt-4 flex items-center space-x-3">
                  {!state.submitted && (
                    <button
                      onClick={() => handleSubmitAnswer(index)}
                      disabled={!state.answer.trim() || state.isEvaluating}
                      className={`
                        px-4 py-2 rounded-lg flex items-center space-x-2 transition-all
                        ${!state.answer.trim() || state.isEvaluating
                          ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                          : 'bg-blue-600 text-white hover:bg-blue-700'
                        }
                      `}
                    >
                      {state.isEvaluating ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span>Evaluating...</span>
                        </>
                      ) : (
                        <>
                          <Send className="h-4 w-4" />
                          <span>Submit Answer</span>
                        </>
                      )}
                    </button>
                  )}
                  
                  {state.submitted && state.isCorrect === false && (
                    <button
                      onClick={() => handleRetryAnswer(index)}
                      className="px-4 py-2 rounded-lg flex items-center space-x-2 bg-yellow-600 text-white hover:bg-yellow-700 transition-all"
                    >
                      <RotateCcw className="h-4 w-4" />
                      <span>Try Again</span>
                    </button>
                  )}
                  
                  {state.attemptCount > 1 && (
                    <span className="text-sm text-gray-400">
                      Attempt {state.attemptCount}
                    </span>
                  )}
                </div>
              )}

              {/* Feedback */}
              {state.feedback && (
                <div 
                  className={`
                    mt-4 p-3 rounded-lg flex items-start space-x-2
                    ${state.isCorrect 
                      ? 'bg-green-900/50 text-green-300 border border-green-700' 
                      : 'bg-yellow-900/50 text-yellow-300 border border-yellow-700'
                    }
                  `}
                >
                  {state.isCorrect ? (
                    <CheckCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                  )}
                  <p className="text-sm">{state.feedback}</p>
                </div>
              )}
            </div>
          )
        })}

        {/* Completion Message */}
        {allQuestionsCorrect && questions.length > 0 && (
          <div className="mt-6 p-4 bg-green-900/30 border border-green-600 rounded-lg">
            <div className="flex items-center space-x-2 text-green-400">
              <CheckCircle className="h-6 w-6" />
              <p className="font-medium">
                Excellent! You've completed all questions for this difficulty level.
              </p>
            </div>
            <p className="text-sm text-green-300 mt-2">
              You can now move on to the next difficulty level or explore another topic.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}