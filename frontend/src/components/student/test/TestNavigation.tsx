'use client'

import { ChevronLeft, ChevronRight, Save, Send } from 'lucide-react'

interface TestNavigationProps {
  currentQuestion: number
  totalQuestions: number
  answeredQuestions: number[]
  onNavigate: (direction: 'prev' | 'next') => void
  onQuestionSelect: (index: number) => void
  onSubmit: () => void
  isSaving: boolean
  isSubmitting?: boolean
}

export default function TestNavigation({
  currentQuestion,
  totalQuestions,
  answeredQuestions,
  onNavigate,
  onQuestionSelect,
  onSubmit,
  isSaving,
  isSubmitting = false
}: TestNavigationProps) {
  const isFirstQuestion = currentQuestion === 1
  const isLastQuestion = currentQuestion === totalQuestions

  return (
    <div className="space-y-4">
      {/* Question Navigator Grid */}
      <div className="border-t pt-4">
        <p className="text-sm font-medium text-gray-700 mb-3">Quick Navigation</p>
        <div className="grid grid-cols-10 gap-2">
          {Array.from({ length: totalQuestions }, (_, i) => (
            <button
              key={i}
              onClick={() => onQuestionSelect(i)}
              className={`
                aspect-square rounded-lg text-sm font-medium transition-all
                ${i + 1 === currentQuestion
                  ? 'bg-blue-600 text-white shadow-md'
                  : answeredQuestions.includes(i)
                  ? 'bg-green-100 text-green-800 hover:bg-green-200'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }
              `}
              title={`Go to question ${i + 1}`}
            >
              {i + 1}
            </button>
          ))}
        </div>
      </div>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between border-t pt-4">
        <button
          onClick={() => onNavigate('prev')}
          disabled={isFirstQuestion}
          className="flex items-center px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronLeft className="w-4 h-4 mr-2" />
          Previous
        </button>

        {/* Save Status */}
        <div className="flex items-center text-sm text-gray-500">
          {isSaving ? (
            <>
              <Save className="w-4 h-4 mr-1 animate-pulse" />
              Saving...
            </>
          ) : (
            <>
              <Save className="w-4 h-4 mr-1 text-green-500" />
              Saved
            </>
          )}
        </div>

        {isLastQuestion ? (
          <button
            onClick={onSubmit}
            disabled={isSubmitting}
            className="flex items-center px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-4 h-4 mr-2" />
            Review & Submit
          </button>
        ) : (
          <button
            onClick={() => onNavigate('next')}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Next
            <ChevronRight className="w-4 h-4 ml-2" />
          </button>
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center space-x-6 text-xs text-gray-500">
        <div className="flex items-center">
          <div className="w-3 h-3 bg-blue-600 rounded mr-2" />
          Current
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 bg-green-100 border border-green-300 rounded mr-2" />
          Answered
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 bg-gray-100 border border-gray-300 rounded mr-2" />
          Not Answered
        </div>
      </div>
    </div>
  )
}