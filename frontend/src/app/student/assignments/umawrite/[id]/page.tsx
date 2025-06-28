'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { studentWritingApi } from '@/lib/studentWritingApi'
import { WritingAssignment, WritingTechnique, WRITING_TECHNIQUES, StudentWritingProgress, WritingSubmissionResponse } from '@/types/writing'
import WritingEditor from '@/components/student/writing/WritingEditor'
import TechniquesPanel from '@/components/student/writing/TechniquesPanel'
import FeedbackModal from '@/components/student/writing/FeedbackModal'
import { BookOpenIcon, ChevronLeftIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

export default function StudentWritingAssignmentPage() {
  const params = useParams()
  const router = useRouter()
  const assignmentId = params.id as string

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
      } else {
        // Start the assignment
        await studentWritingApi.startAssignment(assignmentId)
      }
    } catch (error) {
      console.error('Error loading assignment:', error)
      toast.error('Failed to load assignment')
    } finally {
      setLoading(false)
    }
  }

  // Auto-save draft
  const saveDraft = useCallback(async () => {
    if (!content.trim() || saving) return

    setSaving(true)
    try {
      await studentWritingApi.saveDraft(assignmentId, {
        content,
        selected_techniques: selectedTechniques,
        word_count: wordCount
      })
    } catch (error) {
      console.error('Error saving draft:', error)
    } finally {
      setSaving(false)
    }
  }, [content, selectedTechniques, wordCount, assignmentId, saving])

  // Auto-save timer
  useEffect(() => {
    const timer = setTimeout(() => {
      saveDraft()
    }, 2000) // Save 2 seconds after typing stops

    return () => clearTimeout(timer)
  }, [content, saveDraft])

  const handleTechniqueToggle = (technique: string) => {
    setSelectedTechniques(prev => {
      if (prev.includes(technique)) {
        return prev.filter(t => t !== technique)
      } else if (prev.length < 5) {
        return [...prev, technique]
      }
      toast.error('You can select up to 5 techniques')
      return prev
    })
  }

  const handleSubmit = async (isFinal: boolean) => {
    if (!assignment) return

    // Validate word count
    if (wordCount < assignment.word_count_min || wordCount > assignment.word_count_max) {
      toast.error(`Word count must be between ${assignment.word_count_min} and ${assignment.word_count_max} words`)
      return
    }

    // Validate techniques
    if (selectedTechniques.length === 0) {
      toast.error('Please select at least one writing technique')
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
      
      setLastSubmission(submission)
      toast.success(isFinal ? 'Assignment submitted successfully!' : 'Draft submitted for feedback')
      
      // Check for feedback after a delay
      setTimeout(async () => {
        try {
          const feedback = await studentWritingApi.getFeedback(assignmentId, submission.id)
          if (feedback.feedback) {
            setLastSubmission(prev => prev ? { ...prev, ai_feedback: feedback.feedback } : null)
            setShowFeedback(true)
          }
        } catch (error) {
          console.error('Error getting feedback:', error)
        }
      }, 3000)
    } catch (error) {
      console.error('Error submitting:', error)
      toast.error('Failed to submit assignment')
    } finally {
      setSubmitting(false)
    }
  }

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
            <button
              onClick={() => setShowTechniques(!showTechniques)}
              className="flex items-center px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <BookOpenIcon className="h-5 w-5 mr-2" />
              <span>Writing Techniques</span>
            </button>
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

            {/* Submit Buttons */}
            <div className="mt-6 flex flex-col sm:flex-row gap-4">
              <button
                onClick={() => handleSubmit(false)}
                disabled={submitting || wordCount === 0}
                className="flex-1 px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Save Draft & Get Feedback
              </button>
              <button
                onClick={() => handleSubmit(true)}
                disabled={submitting || wordCount === 0}
                className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Submit Final Response
              </button>
            </div>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1">
            {/* Evaluation Criteria */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Evaluation Criteria</h3>
              <div className="space-y-3">
                {Object.entries(assignment.evaluation_criteria).map(([category, items]) => (
                  items.length > 0 && (
                    <div key={category}>
                      <h4 className="text-sm font-medium text-gray-700 capitalize mb-1">{category}</h4>
                      <div className="flex flex-wrap gap-2">
                        {items.map((item) => (
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

      {/* Feedback Modal */}
      {lastSubmission?.ai_feedback && (
        <FeedbackModal
          isOpen={showFeedback}
          onClose={() => setShowFeedback(false)}
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