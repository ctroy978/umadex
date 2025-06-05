'use client'

import { TestQuestion } from '@/types/test'

interface QuestionDisplayProps {
  question: TestQuestion
  questionNumber: number
  answer: string
  onAnswerChange: (answer: string) => void
  isDisabled: boolean
}

export default function QuestionDisplay({
  question,
  questionNumber,
  answer,
  onAnswerChange,
  isDisabled
}: QuestionDisplayProps) {
  const characterCount = answer.length
  const wordCount = answer.trim().split(/\s+/).filter(word => word.length > 0).length

  return (
    <div className="p-6">
      {/* Question Header */}
      <div className="mb-6">
        <div className="flex items-start justify-between mb-2">
          <h2 className="text-lg font-semibold text-gray-900">
            Question {questionNumber}
          </h2>
          <span className="text-sm text-gray-500">
            Difficulty: {question.difficulty}/8
          </span>
        </div>
        
        {/* Question Text */}
        <p className="text-gray-800 leading-relaxed">
          {question.question}
        </p>
      </div>

      {/* Answer Area */}
      <div className="space-y-3">
        <label className="block text-sm font-medium text-gray-700">
          Your Answer
        </label>
        
        <textarea
          value={answer}
          onChange={(e) => onAnswerChange(e.target.value)}
          disabled={isDisabled}
          placeholder="Type your answer here..."
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:bg-gray-50 disabled:text-gray-500"
          rows={10}
        />
        
        {/* Character/Word Count */}
        <div className="flex justify-between text-sm text-gray-500">
          <span>{wordCount} words</span>
          <span>{characterCount} characters</span>
        </div>
        
        {/* Helpful Tip */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-sm text-blue-800">
            <span className="font-medium">Tip:</span> Reference specific details from the reading material to support your answer.
          </p>
        </div>
      </div>
    </div>
  )
}