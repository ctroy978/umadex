'use client'

import { AlertTriangle, CheckCircle, X } from 'lucide-react'

interface SubmissionModalProps {
  answeredCount: number
  totalQuestions: number
  answeredQuestions: number[]
  onConfirm: () => void
  onCancel: () => void
}

export default function SubmissionModal({
  answeredCount,
  totalQuestions,
  answeredQuestions,
  onConfirm,
  onCancel
}: SubmissionModalProps) {
  const unansweredCount = totalQuestions - answeredCount
  const allAnswered = answeredCount === totalQuestions

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" onClick={onCancel} />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
          {/* Close Button */}
          <button
            onClick={onCancel}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Icon */}
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full mb-4">
            {allAnswered ? (
              <CheckCircle className="h-12 w-12 text-green-500" />
            ) : (
              <AlertTriangle className="h-12 w-12 text-amber-500" />
            )}
          </div>

          {/* Title */}
          <h3 className="text-lg font-semibold text-center text-gray-900 mb-2">
            {allAnswered ? 'Ready to Submit?' : 'Submit Incomplete Test?'}
          </h3>

          {/* Message */}
          <div className="text-center mb-6">
            {allAnswered ? (
              <p className="text-gray-600">
                Great job! You've answered all {totalQuestions} questions. 
                Once you submit, you cannot change your answers.
              </p>
            ) : (
              <>
                <p className="text-gray-600 mb-2">
                  You have {unansweredCount} unanswered question{unansweredCount !== 1 ? 's' : ''}.
                </p>
                <p className="text-sm text-gray-500">
                  Unanswered questions will be marked as incorrect.
                  Are you sure you want to submit now?
                </p>
              </>
            )}
          </div>

          {/* Question Summary */}
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <div className="flex justify-between text-sm mb-3">
              <span className="text-gray-600">Questions Answered:</span>
              <span className="font-medium text-gray-900">{answeredCount} / {totalQuestions}</span>
            </div>
            <div className="mt-2 mb-3">
              <div className="bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    allAnswered ? 'bg-green-500' : 'bg-amber-500'
                  }`}
                  style={{ width: `${(answeredCount / totalQuestions) * 100}%` }}
                />
              </div>
            </div>
            
            {/* Question Status Grid */}
            <div className="text-xs text-gray-600 mb-2">Questions with saved answers:</div>
            <div className="grid grid-cols-10 gap-1">
              {Array.from({length: totalQuestions}, (_, i) => {
                const questionNum = i + 1
                const isAnswered = answeredQuestions.includes(i)
                return (
                  <div
                    key={i}
                    className={`w-6 h-6 rounded text-xs flex items-center justify-center font-medium ${
                      isAnswered 
                        ? 'bg-green-100 text-green-800 border border-green-300' 
                        : 'bg-red-100 text-red-800 border border-red-300'
                    }`}
                  >
                    {questionNum}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={onCancel}
              className="flex-1 px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Review Answers
            </button>
            <button
              onClick={() => {
                console.log('=== SUBMISSION MODAL: Submit button clicked ===')
                console.log('Answered questions:', answeredQuestions)
                console.log('Total questions:', totalQuestions)
                onConfirm()
              }}
              className={`flex-1 px-4 py-2 text-white rounded-lg transition-colors ${
                allAnswered
                  ? 'bg-green-600 hover:bg-green-700'
                  : 'bg-amber-600 hover:bg-amber-700'
              }`}
            >
              Submit Test
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}