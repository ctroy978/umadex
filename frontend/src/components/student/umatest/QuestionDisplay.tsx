'use client'

import { UMATestQuestion } from '@/lib/umatestApi'

interface QuestionDisplayProps {
  question: UMATestQuestion
  questionNumber: number
  answer: string
  onAnswerChange: (answer: string) => void
  isDisabled?: boolean
}

export default function QuestionDisplay({
  question,
  questionNumber,
  answer,
  onAnswerChange,
  isDisabled = false
}: QuestionDisplayProps) {
  return (
    <div className="p-6">
      {/* Question Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Question {questionNumber}
        </h3>
      </div>

      {/* Question Text */}
      <div className="mb-6">
        <p className="text-gray-800 whitespace-pre-wrap leading-relaxed">
          {question.question_text}
        </p>
      </div>

      {/* Answer Input */}
      <div className="space-y-2">
        <label htmlFor="answer" className="block text-sm font-medium text-gray-700">
          Your Answer
        </label>
        <textarea
          id="answer"
          value={answer}
          onChange={(e) => onAnswerChange(e.target.value)}
          disabled={isDisabled}
          className="w-full min-h-[200px] p-4 border border-gray-300 rounded-lg 
                     focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                     disabled:bg-gray-100 disabled:cursor-not-allowed
                     resize-y text-gray-800"
          placeholder="Type your answer here..."
        />
        <p className="text-xs text-gray-500">
          Your answer will be automatically saved as you type. Focus on demonstrating your understanding of the concepts.
        </p>
      </div>
    </div>
  )
}