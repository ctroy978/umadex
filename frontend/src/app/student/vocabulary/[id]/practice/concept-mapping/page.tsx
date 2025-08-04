'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { studentApi } from '@/lib/studentApi'
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowRightIcon,
  ExclamationCircleIcon,
  BookOpenIcon,
  ChartBarIcon,
  ClockIcon,
  StarIcon,
  LightBulbIcon,
  EyeIcon
} from '@heroicons/react/24/outline'

interface VocabularyWord {
  id: string
  word: string
  definition: string
  part_of_speech: string
}

interface ConceptMapSession {
  concept_attempt_id: string
  total_words: number
  passing_score: number
  max_possible_score: number
  current_word_index: number
  word: VocabularyWord | null
  grade_level: string
}

interface ConceptMapFormData {
  definition: string
  synonyms: string
  antonyms: string
  context_theme: string
  connotation: string
  example_sentence: string
}

interface ComponentScore {
  score: number
  feedback: string
}

interface Evaluation {
  overall_score: number
  component_scores: {
    definition: ComponentScore
    synonyms: ComponentScore
    antonyms: ComponentScore
    context_theme: ComponentScore
    connotation: ComponentScore
    example_sentence: ComponentScore
  }
  overall_feedback: string
  areas_for_improvement: string[]
}

interface SubmissionResult {
  valid: boolean
  errors?: { [key: string]: string }
  evaluation?: Evaluation
  current_score?: number
  average_score?: number
  words_remaining?: number
  is_complete?: boolean
  passed?: boolean
  percentage_score?: number
  needs_confirmation?: boolean
  next_word?: VocabularyWord
  progress_percentage?: number
}

export default function ConceptMappingPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const vocabularyId = params.id as string
  const classroomId = searchParams.get('classroomId')

  const [session, setSession] = useState<ConceptMapSession | null>(null)
  const [formData, setFormData] = useState<ConceptMapFormData>({
    definition: '',
    synonyms: '',
    antonyms: '',
    context_theme: '',
    connotation: '',
    example_sentence: ''
  })
  const [currentScore, setCurrentScore] = useState(0)
  const [averageScore, setAverageScore] = useState(0)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [showEvaluation, setShowEvaluation] = useState(false)
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null)
  const [errors, setErrors] = useState<{ [key: string]: string }>({})
  const [isComplete, setIsComplete] = useState(false)
  const [passed, setPassed] = useState<boolean | null>(null)
  const [startTime, setStartTime] = useState<Date>(new Date())
  const [wordStartTime, setWordStartTime] = useState<Date>(new Date())
  const [showCompletionDialog, setShowCompletionDialog] = useState(false)
  const [confirmingCompletion, setConfirmingCompletion] = useState(false)
  const [completionResult, setCompletionResult] = useState<{
    percentage_score: number
    needs_confirmation: boolean
  } | null>(null)

  // Auto-save refs
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    initializeSession()
  }, [vocabularyId])

  // Navigation protection
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      // Only show warning if there's an active session and not showing completion dialog
      if (session && !showCompletionDialog && !isComplete) {
        const message = 'You have an assignment in progress. If you leave now, your progress will be lost.'
        e.preventDefault()
        e.returnValue = message
        return message
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [session, showCompletionDialog, isComplete])

  const initializeSession = async () => {
    try {
      setLoading(true)
      const sessionData = await studentApi.startConceptMapping(vocabularyId)
      setSession(sessionData)
      setStartTime(new Date())
      setWordStartTime(new Date())
      
      // Clear any existing form data
      setFormData({
        definition: '',
        synonyms: '',
        antonyms: '',
        context_theme: '',
        connotation: '',
        example_sentence: ''
      })
      setErrors({})
    } catch (err: any) {
      console.error('Failed to start concept mapping:', err)
      alert('Failed to start concept mapping. Please try again.')
      const query = classroomId ? `?classroomId=${classroomId}` : ''
      router.push(`/student/vocabulary/${vocabularyId}/practice${query}`)
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field: keyof ConceptMapFormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    
    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors[field]
        return newErrors
      })
    }

    // Auto-save after 2 seconds of no typing
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current)
    }
    autoSaveTimeoutRef.current = setTimeout(() => {
      // Could implement auto-save to localStorage here
    }, 2000)
  }

  const validateForm = (): boolean => {
    const newErrors: { [key: string]: string } = {}

    if (formData.definition.trim().length < 10) {
      newErrors.definition = 'Please provide a more complete definition (at least 10 characters)'
    }

    if (formData.synonyms.trim().length < 3) {
      newErrors.synonyms = 'Please provide at least one synonym'
    }

    if (formData.antonyms.trim().length < 3) {
      newErrors.antonyms = 'Please provide at least one antonym'
    }

    if (formData.context_theme.trim().length < 10) {
      newErrors.context_theme = 'Please describe where or when this word is used (at least 10 characters)'
    }

    if (formData.connotation.trim().length < 3) {
      newErrors.connotation = 'Please describe the emotional tone'
    }

    if (formData.example_sentence.trim().length < 15) {
      newErrors.example_sentence = 'Please write a complete sentence (at least 15 characters)'
    }

    if (session?.word && !formData.example_sentence.toLowerCase().includes(session.word.word.toLowerCase())) {
      newErrors.example_sentence = `Your example sentence must include the word "${session.word.word}"`
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async () => {
    if (!session?.word || !validateForm()) {
      return
    }

    try {
      setSubmitting(true)
      
      const timeSpent = Math.floor((new Date().getTime() - wordStartTime.getTime()) / 1000)
      
      const result: SubmissionResult = await studentApi.submitConceptMap(
        session.concept_attempt_id,
        {
          word_id: session.word.id,
          definition: formData.definition.trim(),
          synonyms: formData.synonyms.trim(),
          antonyms: formData.antonyms.trim(),
          context_theme: formData.context_theme.trim(),
          connotation: formData.connotation.trim(),
          example_sentence: formData.example_sentence.trim(),
          time_spent_seconds: timeSpent
        }
      )

      if (!result.valid && result.errors) {
        setErrors(result.errors)
        return
      }

      if (result.evaluation) {
        setEvaluation(result.evaluation)
        setCurrentScore(result.current_score || 0)
        setAverageScore(result.average_score || 0)
        setIsComplete(result.is_complete || false)
        setPassed(result.passed || null)
        setShowEvaluation(true)

        // Store completion result but don't show dialog yet - let student read feedback first
        if (result.is_complete && result.needs_confirmation) {
          setCompletionResult({
            percentage_score: result.percentage_score || 0,
            needs_confirmation: result.needs_confirmation
          })
          // Don't show dialog immediately - wait for user to click "See Score"
        }

        // Update session for next word if not complete
        if (!result.is_complete && result.next_word) {
          setSession(prev => prev ? {
            ...prev,
            word: result.next_word!,
            current_word_index: prev.current_word_index + 1
          } : null)
        }
      }
    } catch (err: any) {
      console.error('Failed to submit concept map:', err)
      alert('Failed to submit concept map. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleContinue = () => {
    if (isComplete) {
      // If needs confirmation, show dialog instead of redirecting
      if (completionResult?.needs_confirmation) {
        setShowCompletionDialog(true)
      } else {
        // Otherwise go to practice menu
        const query = classroomId ? `?classroomId=${classroomId}` : ''
        router.push(`/student/vocabulary/${vocabularyId}/practice${query}`)
      }
    } else {
      // Continue to next word
      setShowEvaluation(false)
      setEvaluation(null)
      setFormData({
        definition: '',
        synonyms: '',
        antonyms: '',
        context_theme: '',
        connotation: '',
        example_sentence: ''
      })
      setErrors({})
      setWordStartTime(new Date())
    }
  }

  const handleFinishEarly = async () => {
    if (!session) return

    const confirmed = confirm(
      `Are you sure you want to finish early? You have completed ${session.current_word_index} of ${session.total_words} words. You need to complete at least ${Math.ceil(session.total_words * 0.8)} words to pass.`
    )

    if (!confirmed) return

    try {
      const result = await studentApi.finishConceptMappingEarly(session.concept_attempt_id)
      
      if (!result.success) {
        alert(result.message)
        return
      }

      setIsComplete(true)
      setPassed(result.passed || false)
      setCurrentScore(result.final_score || 0)
      setAverageScore(result.average_score || 0)
      
      // Show completion message
      alert(`Concept mapping completed! You scored ${result.average_score?.toFixed(1)}/4.0 on ${result.words_completed} words.`)
      const query = classroomId ? `?classroomId=${classroomId}` : ''
      router.push(`/student/vocabulary/${vocabularyId}/practice${query}`)
    } catch (err: any) {
      console.error('Failed to finish early:', err)
      alert('Failed to finish early. Please try again.')
    }
  }

  const handleConfirmCompletion = async () => {
    if (!session) return
    
    setConfirmingCompletion(true)
    try {
      const result = await studentApi.confirmConceptCompletion(session.concept_attempt_id)
      // Redirect to practice page with success message
      const query = classroomId ? `&classroomId=${classroomId}` : ''
      router.push(`/student/vocabulary/${vocabularyId}/practice?completed=concept-mapping${query}`)
    } catch (err: any) {
      console.error('Failed to confirm completion:', err)
      alert('Failed to complete assignment. Please try again.')
    } finally {
      setConfirmingCompletion(false)
    }
  }

  const handleDeclineCompletion = async () => {
    if (!session) return
    
    setConfirmingCompletion(true)
    try {
      const result = await studentApi.declineConceptCompletion(session.concept_attempt_id)
      // Redirect to practice page
      const query = classroomId ? `?classroomId=${classroomId}` : ''
      router.push(`/student/vocabulary/${vocabularyId}/practice${query}`)
    } catch (err: any) {
      console.error('Failed to decline completion:', err)
      alert('Failed to process request. Please try again.')
    } finally {
      setConfirmingCompletion(false)
    }
  }

  const getScoreDisplay = (score: number): string => {
    if (score >= 3.5) return '⭐⭐⭐⭐'
    if (score >= 2.5) return '⭐⭐⭐'
    if (score >= 1.5) return '⭐⭐'
    return '⭐'
  }

  const getScoreColor = (score: number): string => {
    if (score >= 3.5) return 'text-green-600'
    if (score >= 2.5) return 'text-yellow-600'
    if (score >= 1.5) return 'text-orange-600'
    return 'text-red-600'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading concept mapping...</p>
        </div>
      </div>
    )
  }

  if (!session) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <ExclamationCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Session Error</h2>
          <p className="text-gray-600 mb-6">Unable to start concept mapping session</p>
          <button
            onClick={() => {
              const query = classroomId ? `?classroomId=${classroomId}` : ''
              router.push(`/student/vocabulary/${vocabularyId}/practice${query}`)
            }}
            className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
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
                onClick={() => {
                  if (session && !isComplete) {
                    const confirmLeave = window.confirm('You have unsaved progress. Are you sure you want to leave?')
                    if (!confirmLeave) return
                  }
                  const query = classroomId ? `?classroomId=${classroomId}` : ''
        router.push(`/student/vocabulary/${vocabularyId}/practice${query}`)
                }}
                className="mr-4 text-gray-500 hover:text-gray-700"
              >
                <ArrowLeftIcon className="h-5 w-5" />
              </button>
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 rounded-lg mr-3">
                  <BookOpenIcon className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">
                    Concept Mapping
                  </h1>
                  <p className="text-sm text-gray-500">
                    Word {session.current_word_index + 1} of {session.total_words}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm text-gray-500">Average Score</p>
                <p className="font-semibold text-gray-900">{averageScore.toFixed(1)}/4.0</p>
              </div>
              {session.current_word_index > 0 && (
                <button
                  onClick={handleFinishEarly}
                  className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  Finish Early
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-600">Progress</span>
            <span className="text-sm text-gray-600">
              {Math.round((session.current_word_index / session.total_words) * 100)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{
                width: `${(session.current_word_index / session.total_words) * 100}%`
              }}
            />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!showEvaluation ? (
          <div className="bg-white rounded-lg shadow">
            <div className="p-6">
              {/* Word Header */}
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-gray-900 mb-2">
                  {session.word?.word}
                </h2>
              </div>

              {/* Instructions */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <div className="flex">
                  <LightBulbIcon className="h-5 w-5 text-blue-600 mt-0.5 mr-2 flex-shrink-0" />
                  <div>
                    <h3 className="font-medium text-blue-900 mb-1">Create a Concept Map</h3>
                    <p className="text-sm text-blue-700">
                      Complete all six components to show your deep understanding of this vocabulary word.
                      All fields are required.
                    </p>
                  </div>
                </div>
              </div>

              {/* Form */}
              <div className="space-y-6">
                {/* Definition */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Definition *
                    <span className="font-normal text-gray-500 ml-1">
                      (What does this word mean?)
                    </span>
                  </label>
                  <textarea
                    value={formData.definition}
                    onChange={(e) => handleInputChange('definition', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                      errors.definition ? 'border-red-500' : 'border-gray-300'
                    }`}
                    rows={3}
                    placeholder="Write your understanding of what this word means..."
                    maxLength={500}
                  />
                  {errors.definition && (
                    <p className="mt-1 text-sm text-red-600">{errors.definition}</p>
                  )}
                </div>

                {/* Synonyms */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Synonyms
                    <span className="font-normal text-gray-500 ml-1">
                      (Words that mean the same or similar)
                    </span>
                  </label>
                  <input
                    type="text"
                    value={formData.synonyms}
                    onChange={(e) => handleInputChange('synonyms', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                      errors.synonyms ? 'border-red-500' : 'border-gray-300'
                    }`}
                    placeholder="List words with similar meanings..."
                    maxLength={200}
                  />
                  {errors.synonyms && (
                    <p className="mt-1 text-sm text-red-600">{errors.synonyms}</p>
                  )}
                </div>

                {/* Antonyms */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Antonyms
                    <span className="font-normal text-gray-500 ml-1">
                      (Words that mean the opposite)
                    </span>
                  </label>
                  <input
                    type="text"
                    value={formData.antonyms}
                    onChange={(e) => handleInputChange('antonyms', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                      errors.antonyms ? 'border-red-500' : 'border-gray-300'
                    }`}
                    placeholder="List words with opposite meanings..."
                    maxLength={200}
                  />
                  {errors.antonyms && (
                    <p className="mt-1 text-sm text-red-600">{errors.antonyms}</p>
                  )}
                </div>

                {/* Context/Theme */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Context/Theme *
                    <span className="font-normal text-gray-500 ml-1">
                      (Where or when is this word used?)
                    </span>
                  </label>
                  <textarea
                    value={formData.context_theme}
                    onChange={(e) => handleInputChange('context_theme', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                      errors.context_theme ? 'border-red-500' : 'border-gray-300'
                    }`}
                    rows={2}
                    placeholder="Describe where or when this word is typically used..."
                    maxLength={300}
                  />
                  {errors.context_theme && (
                    <p className="mt-1 text-sm text-red-600">{errors.context_theme}</p>
                  )}
                </div>

                {/* Connotation */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Connotation
                    <span className="font-normal text-gray-500 ml-1">
                      (What feeling does this word give?)
                    </span>
                  </label>
                  <input
                    type="text"
                    value={formData.connotation}
                    onChange={(e) => handleInputChange('connotation', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                      errors.connotation ? 'border-red-500' : 'border-gray-300'
                    }`}
                    placeholder="Positive, negative, or neutral? What emotion does it create?"
                    maxLength={100}
                  />
                  {errors.connotation && (
                    <p className="mt-1 text-sm text-red-600">{errors.connotation}</p>
                  )}
                </div>

                {/* Example Sentence */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Example Sentence *
                    <span className="font-normal text-gray-500 ml-1">
                      (Use the word correctly in context)
                    </span>
                  </label>
                  <textarea
                    value={formData.example_sentence}
                    onChange={(e) => handleInputChange('example_sentence', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                      errors.example_sentence ? 'border-red-500' : 'border-gray-300'
                    }`}
                    rows={2}
                    placeholder={`Write a complete sentence using the word "${session.word?.word}"...`}
                    maxLength={300}
                  />
                  {errors.example_sentence && (
                    <p className="mt-1 text-sm text-red-600">{errors.example_sentence}</p>
                  )}
                </div>
              </div>

              {/* Submit Button */}
              <div className="flex justify-end mt-8">
                <button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                >
                  {submitting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Evaluating...
                    </>
                  ) : (
                    <>
                      Submit & Next
                      <ArrowRightIcon className="h-4 w-4 ml-2" />
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* Evaluation Display */
          <div className="bg-white rounded-lg shadow">
            <div className="p-6">
              {/* Evaluation Header */}
              <div className="text-center mb-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                  "{session.word?.word}" - Score: {evaluation?.overall_score.toFixed(1)}/4
                  {isComplete && " (Final Word)"}
                </h2>
                <div className="text-3xl mb-2">
                  {evaluation && getScoreDisplay(evaluation.overall_score)}
                </div>
                <p className={`font-medium ${evaluation && getScoreColor(evaluation.overall_score)}`}>
                  {evaluation && evaluation.overall_score >= 3.5 ? 'Excellent!' :
                   evaluation && evaluation.overall_score >= 2.5 ? 'Good work!' :
                   evaluation && evaluation.overall_score >= 1.5 ? 'Keep trying!' : 'Needs improvement'}
                </p>
              </div>

              {/* Component Scores */}
              {evaluation && (
                <div className="space-y-4 mb-6">
                  {Object.entries(evaluation.component_scores).map(([component, score]) => (
                    <div key={component} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-medium text-gray-900 capitalize">
                          {component.replace('_', ' ')}
                        </h3>
                        <div className="flex items-center">
                          <span className={`font-bold mr-2 ${getScoreColor(score.score)}`}>
                            {score.score}/4
                          </span>
                          {score.score >= 3.5 ? (
                            <CheckCircleIcon className="h-5 w-5 text-green-500" />
                          ) : score.score >= 2.5 ? (
                            <CheckCircleIcon className="h-5 w-5 text-yellow-500" />
                          ) : (
                            <XCircleIcon className="h-5 w-5 text-red-500" />
                          )}
                        </div>
                      </div>
                      <p className="text-sm text-gray-600">{score.feedback}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Overall Feedback */}
              {evaluation && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                  <h3 className="font-medium text-blue-900 mb-2">Overall Feedback</h3>
                  <p className="text-blue-700">{evaluation.overall_feedback}</p>
                  {evaluation.areas_for_improvement.length > 0 && (
                    <div className="mt-3">
                      <p className="font-medium text-blue-900 text-sm">Areas to focus on:</p>
                      <ul className="list-disc list-inside text-sm text-blue-700">
                        {evaluation.areas_for_improvement.map((area, index) => (
                          <li key={index}>{area}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Progress Summary */}
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold text-gray-900">{session.current_word_index}</p>
                    <p className="text-sm text-gray-600">Words Completed</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">{currentScore.toFixed(1)}</p>
                    <p className="text-sm text-gray-600">Total Score</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">{averageScore.toFixed(1)}</p>
                    <p className="text-sm text-gray-600">Average Score</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">{session.total_words - session.current_word_index}</p>
                    <p className="text-sm text-gray-600">Words Remaining</p>
                  </div>
                </div>
              </div>

              {/* Final Word Notice */}
              {isComplete && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                  <div className="flex items-center space-x-2">
                    <EyeIcon className="h-5 w-5 text-blue-600" />
                    <p className="text-blue-800">
                      This was your final word! Take your time to read the feedback above, then click "See Score" when you're ready to view your overall results.
                    </p>
                  </div>
                </div>
              )}

              {/* Continue Button */}
              <div className="flex justify-center">
                <button
                  onClick={handleContinue}
                  className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center"
                >
                  {isComplete ? (
                    <>
                      See Score
                      <ChartBarIcon className="h-4 w-4 ml-2" />
                    </>
                  ) : (
                    <>
                      Continue to Next Word
                      <ArrowRightIcon className="h-4 w-4 ml-2" />
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Completion Confirmation Dialog */}
      {showCompletionDialog && completionResult && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full shadow-xl">
            <div className="text-center mb-6">
              <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
                completionResult.percentage_score >= 70 ? 'bg-green-100' : 'bg-amber-100'
              }`}>
                {completionResult.percentage_score >= 70 ? (
                  <CheckCircleIcon className="h-8 w-8 text-green-600" />
                ) : (
                  <ExclamationCircleIcon className="h-8 w-8 text-amber-600" />
                )}
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-2">
                Concept Mapping Complete!
              </h3>
              <p className="text-lg text-gray-700 mb-4">
                You scored <span className="font-bold text-primary-600">{Math.round(completionResult.percentage_score)}%</span>
              </p>
              {completionResult.percentage_score >= 70 ? (
                <p className="text-green-700">
                  Congratulations! You scored 70% or higher.
                  <br />
                  <span className="font-semibold">Assignment completed successfully!</span>
                </p>
              ) : (
                <p className="text-amber-700">
                  You scored below 70%.
                  <br />
                  <span className="font-semibold">You need 70% or higher to complete this assignment.</span>
                </p>
              )}
            </div>

            {completionResult.percentage_score >= 70 ? (
              <button
                onClick={handleConfirmCompletion}
                disabled={confirmingCompletion}
                className="w-full px-6 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {confirmingCompletion ? 'Completing...' : 'Complete Assignment'}
              </button>
            ) : (
              <button
                onClick={handleDeclineCompletion}
                disabled={confirmingCompletion}
                className="w-full px-6 py-3 bg-amber-600 text-white rounded-lg font-medium hover:bg-amber-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {confirmingCompletion ? 'Processing...' : 'Retake Assignment Later'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}