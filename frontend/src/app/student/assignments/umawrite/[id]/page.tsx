'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { studentWritingApi } from '@/lib/studentWritingApi'
import { WritingAssignment, WritingTechnique, WRITING_TECHNIQUES, StudentWritingProgress, WritingSubmissionResponse } from '@/types/writing'
import WritingEditor from '@/components/student/writing/WritingEditor'
import TechniquesPanel from '@/components/student/writing/TechniquesPanel'
import FeedbackModal from '@/components/student/writing/FeedbackModal'
import { BookOpenIcon, ChevronLeftIcon } from '@heroicons/react/24/outline'

export default function StudentWritingAssignmentPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const assignmentId = params.id as string
  const isResultsView = searchParams.get('view') === 'results'

  const [assignment, setAssignment] = useState<WritingAssignment | null>(null)
  const [progress, setProgress] = useState<StudentWritingProgress | null>(null)
  const [content, setContent] = useState('')
  const [selectedTechniques, setSelectedTechniques] = useState<string[]>([])
  const [wordCount, setWordCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [showTechniques, setShowTechniques] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [lastSubmission, setLastSubmission] = useState<WritingSubmissionResponse | null>(null)
  const [lastSavedContent, setLastSavedContent] = useState('')
  const [lastSavedTechniques, setLastSavedTechniques] = useState<string[]>([])
  const [evaluating, setEvaluating] = useState(false)

  // Load assignment and progress
  useEffect(() => {
    loadAssignment()
  }, [assignmentId])

  const loadAssignment = async () => {
    try {
      const [assignmentData, progressData] = await Promise.all([
        studentWritingApi.getAssignment(assignmentId),
        studentWritingApi.getProgress(assignmentId).catch(() => null)
      ])

      setAssignment(assignmentData)
      
      if (progressData) {
        setProgress(progressData)
        setContent(progressData.draft_content || '')
        setSelectedTechniques(progressData.selected_techniques || [])
        setWordCount(progressData.word_count || 0)
        // Initialize last saved state
        setLastSavedContent(progressData.draft_content || '')
        setLastSavedTechniques(progressData.selected_techniques || [])
      } else {
        // Start the assignment
        await studentWritingApi.startAssignment(assignmentId)
      }
    } catch (error) {
      // Error loading assignment
      alert('Failed to load assignment')
    } finally {
      setLoading(false)
    }
  }

  // Auto-save draft
  const saveDraft = useCallback(async () => {
    if (!content.trim() || saving) return
    
    // Check if content or techniques actually changed
    const contentChanged = content !== lastSavedContent
    const techniquesChanged = JSON.stringify(selectedTechniques) !== JSON.stringify(lastSavedTechniques)
    
    if (!contentChanged && !techniquesChanged) {
      return // Don't save if nothing changed
    }

    setSaving(true)
    try {
      await studentWritingApi.saveDraft(assignmentId, {
        content,
        selected_techniques: selectedTechniques,
        word_count: wordCount
      })
      // Update last saved state
      setLastSavedContent(content)
      setLastSavedTechniques(selectedTechniques)
    } catch (error) {
      // Error saving draft
    } finally {
      setSaving(false)
    }
  }, [content, selectedTechniques, wordCount, assignmentId, saving, lastSavedContent, lastSavedTechniques])

  // Auto-save timer
  useEffect(() => {
    const timer = setTimeout(() => {
      saveDraft()
    }, 2000) // Save 2 seconds after typing stops

    return () => clearTimeout(timer)
  }, [content, selectedTechniques, saveDraft])

  const handleTechniqueToggle = (technique: string) => {
    setSelectedTechniques(prev => {
      if (prev.includes(technique)) {
        return prev.filter(t => t !== technique)
      } else if (prev.length < 5) {
        return [...prev, technique]
      }
      alert('You can select up to 5 techniques')
      return prev
    })
  }

  const handleSubmit = async (isFinal: boolean) => {
    if (!assignment) return

    // Validate word count
    if (wordCount < assignment.word_count_min || wordCount > assignment.word_count_max) {
      alert(`Word count must be between ${assignment.word_count_min} and ${assignment.word_count_max} words`)
      return
    }

    // Validate techniques
    if (selectedTechniques.length === 0) {
      alert('Please select at least one writing technique')
      return
    }

    setSubmitting(true)
    try {
      const submission = await studentWritingApi.submitAssignment(assignmentId, {
        content,
        selected_techniques: selectedTechniques,
        word_count: wordCount,
        is_final: isFinal
      })
      
      // Submission created successfully
      setLastSubmission(submission)
      alert(isFinal ? 'Assignment submitted successfully!' : 'Draft submitted for feedback')
      
      // Show evaluating state
      setEvaluating(true)
      
      // Trigger AI evaluation
      setTimeout(async () => {
        try {
          // Triggering evaluation
          const evalResult = await studentWritingApi.evaluateSubmission(submission.id)
          // Evaluation completed
          
          if (evalResult.ai_feedback) {
            setLastSubmission(prev => {
              const updated = prev ? { ...prev, ai_feedback: evalResult.ai_feedback, score: evalResult.score } : null
              // Updated submission with feedback
              return updated
            })
            setShowFeedback(true)
          } else {
            // Try polling for feedback
            // No immediate feedback, trying to poll...
            const feedback = await studentWritingApi.getFeedback(assignmentId, submission.id)
            // Received feedback after polling
            
            if (feedback.feedback) {
              setLastSubmission(prev => prev ? { ...prev, ai_feedback: feedback.feedback, score: feedback.score } : null)
              setShowFeedback(true)
            } else {
              alert('Feedback is being generated. Please refresh the page in a few moments.')
            }
          }
        } catch (error) {
          // Error triggering evaluation
          // Try to get feedback anyway
          try {
            const feedback = await studentWritingApi.getFeedback(assignmentId, submission.id)
            // Fallback feedback received
            if (feedback.feedback) {
              setLastSubmission(prev => prev ? { ...prev, ai_feedback: feedback.feedback, score: feedback.score } : null)
              setShowFeedback(true)
            }
          } catch (feedbackError) {
            // Error getting feedback
            alert('Failed to get feedback. Please try refreshing the page.')
          }
        }
        setEvaluating(false) // Clear evaluating state
      }, 3000) // Increased timeout to 3 seconds
    } catch (error) {
      // Error submitting
      alert('Failed to submit assignment')
    } finally {
      setSubmitting(false)
    }
  }

  // Handle redirects in useEffect to avoid state updates during render
  useEffect(() => {
    // If results view but not completed, redirect to regular view
    if (isResultsView && (!progress || !progress.is_completed)) {
      router.push(`/student/assignments/umawrite/${assignmentId}`)
    }
    // If assignment is completed but not in results view, redirect to results view
    else if (!isResultsView && progress && progress.is_completed) {
      router.push(`/student/assignments/umawrite/${assignmentId}?view=results`)
    }
  }, [isResultsView, progress, assignmentId, router])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading assignment...</p>
        </div>
      </div>
    )
  }

  if (!assignment) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Assignment not found</p>
          <button
            onClick={() => router.push('/student/dashboard')}
            className="mt-4 text-blue-600 hover:text-blue-700"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    )
  }

  const wordCountColor = wordCount < assignment.word_count_min ? 'text-red-600' :
                        wordCount > assignment.word_count_max ? 'text-red-600' :
                        'text-green-600'

  // Results view - show only score for completed assignments
  if (isResultsView && progress && progress.is_completed) {
    const finalSubmission = progress.submissions?.find(s => s.is_final_submission)
    
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between py-4">
              <div className="flex items-center">
                <button
                  onClick={() => router.push('/student/dashboard')}
                  className="mr-4 p-2 text-gray-400 hover:text-gray-600"
                >
                  <ChevronLeftIcon className="h-5 w-5" />
                </button>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">{assignment.title}</h1>
                  <p className="text-sm text-gray-600 mt-1">Assignment Results</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Assignment Completed</h2>
            <p className="text-gray-600 mb-6">You have successfully completed this writing assignment.</p>
            
            {finalSubmission && finalSubmission.score !== null && finalSubmission.score !== undefined && (
              <div className="mb-8">
                <div className="text-5xl font-bold text-blue-600 mb-2">
                  {Math.round(finalSubmission.score)}%
                </div>
                <p className="text-lg text-gray-700">Your Score</p>
              </div>
            )}
            
            <div className="text-sm text-gray-500 mb-6">
              <p>Submitted on: {finalSubmission ? new Date(finalSubmission.submitted_at).toLocaleDateString() : 'N/A'}</p>
              <p>Word Count: {finalSubmission?.word_count || 0} words</p>
            </div>
            
            <button
              onClick={() => router.push('/student/dashboard')}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center">
              <button
                onClick={() => router.push('/student/dashboard')}
                className="mr-4 p-2 text-gray-400 hover:text-gray-600"
              >
                <ChevronLeftIcon className="h-5 w-5" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{assignment.title}</h1>
                <p className="text-sm text-gray-600 mt-1">
                  Word Count: {assignment.word_count_min} - {assignment.word_count_max} words
                  {progress && progress.submission_count > 0 && (
                    <span className="ml-3">• Attempt {progress.submission_count + 1}</span>
                  )}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2">
            {/* Prompt */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Writing Prompt</h2>
              <p className="text-gray-700 whitespace-pre-wrap">{assignment.prompt_text}</p>
              {assignment.instructions && (
                <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-900">{assignment.instructions}</p>
                </div>
              )}
            </div>

            {/* Writing Editor */}
            <WritingEditor
              content={content}
              onChange={setContent}
              onWordCountChange={setWordCount}
              selectedTechniques={selectedTechniques}
              wordCount={wordCount}
              minWords={assignment.word_count_min}
              maxWords={assignment.word_count_max}
              saving={saving}
            />

            {/* Submit Button */}
            <div className="mt-6 flex justify-center">
              <button
                onClick={() => handleSubmit(true)}
                disabled={submitting || wordCount === 0 || (progress?.is_completed ?? false)}
                className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {progress?.is_completed ? 'Assignment Completed' : 'Submit Final Response'}
              </button>
            </div>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1">
            {/* Evaluation Criteria */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Evaluation Criteria</h3>
              <div className="space-y-3">
                {Object.entries(assignment.evaluation_criteria).map(([category, items]: [string, string[]]) => (
                  items.length > 0 && (
                    <div key={category}>
                      <h4 className="text-sm font-medium text-gray-700 capitalize mb-1">{category}</h4>
                      <div className="flex flex-wrap gap-2">
                        {items.map((item: string) => (
                          <span key={item} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  )
                ))}
              </div>
            </div>

            {/* Writing Techniques Button */}
            <div className="mb-6">
              <button
                onClick={() => setShowTechniques(!showTechniques)}
                className="w-full flex items-center justify-center px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <BookOpenIcon className="h-5 w-5 mr-2" />
                <span className="font-medium">Select Writing Techniques</span>
              </button>
            </div>

            {/* Selected Techniques */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Selected Techniques ({selectedTechniques.length}/5)
              </h3>
              {selectedTechniques.length === 0 ? (
                <p className="text-sm text-gray-600">
                  Click "Writing Techniques" to select techniques you'll use in your writing.
                </p>
              ) : (
                <div className="space-y-2">
                  {selectedTechniques.map((techniqueName) => {
                    const technique = WRITING_TECHNIQUES.find(t => t.name === techniqueName)
                    return technique ? (
                      <div key={techniqueName} className="p-3 bg-blue-50 rounded-lg">
                        <p className="text-sm font-medium text-blue-900">{technique.displayName}</p>
                        <p className="text-xs text-blue-700 mt-1">{technique.description}</p>
                      </div>
                    ) : null
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Techniques Panel */}
      <TechniquesPanel
        isOpen={showTechniques}
        onClose={() => setShowTechniques(false)}
        techniques={WRITING_TECHNIQUES}
        selectedTechniques={selectedTechniques}
        onTechniqueToggle={handleTechniqueToggle}
      />

      {/* Evaluating Indicator */}
      {evaluating && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
            <div className="flex flex-col items-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Evaluating Your Writing</h3>
              <p className="text-sm text-gray-600 text-center">
                Our AI is analyzing your submission and generating personalized feedback...
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Feedback Modal */}
      {lastSubmission?.ai_feedback && (
        <FeedbackModal
          isOpen={showFeedback}
          onClose={() => {
            setShowFeedback(false)
            // Redirect to dashboard after closing feedback for final submissions
            if (lastSubmission.is_final_submission) {
              router.push('/student/dashboard')
            }
          }}
          feedback={lastSubmission.ai_feedback}
          canRevise={!lastSubmission.is_final_submission}
          onRevise={() => {
            setShowFeedback(false)
            // Content is already in the editor, just let them continue
          }}
        />
      )}
    </div>
  )
}