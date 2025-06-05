'use client'

interface TestProgressProps {
  currentQuestion: number
  totalQuestions: number
  answeredQuestions: number[]
}

export default function TestProgress({ 
  currentQuestion, 
  totalQuestions, 
  answeredQuestions 
}: TestProgressProps) {
  const progressPercentage = (answeredQuestions.length / totalQuestions) * 100

  return (
    <div className="bg-white border-b">
      <div className="max-w-7xl mx-auto px-4 py-3">
        {/* Progress Info */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">
            Question {currentQuestion} of {totalQuestions}
          </span>
          <span className="text-sm text-gray-600">
            {answeredQuestions.length} answered
          </span>
        </div>
        
        {/* Progress Bar */}
        <div className="relative">
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-600 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
          
          {/* Question Dots */}
          <div className="absolute inset-0 flex items-center justify-between px-1">
            {Array.from({ length: totalQuestions }, (_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full transition-colors ${
                  i + 1 === currentQuestion
                    ? 'bg-blue-600 ring-2 ring-blue-300'
                    : answeredQuestions.includes(i)
                    ? 'bg-green-500'
                    : 'bg-gray-300'
                }`}
                title={`Question ${i + 1}`}
              />
            ))}
          </div>
        </div>
        
        {/* Progress Text */}
        <div className="mt-2 text-center text-xs text-gray-500">
          {progressPercentage.toFixed(0)}% Complete
        </div>
      </div>
    </div>
  )
}