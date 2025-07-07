'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { umatestApi, UMATestResultsResponse } from '@/lib/umatestApi'
import { CheckCircleIcon, XCircleIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline'
import { Loader2 } from 'lucide-react'

export default function UMATestResultsPage({ params }: { params: { resultId: string } }) {
  const router = useRouter()
  const { resultId } = params
  
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<UMATestResultsResponse | null>(null)
  const [expandedQuestions, setExpandedQuestions] = useState<Set<number>>(new Set())

  useEffect(() => {
    loadResults()
  }, [resultId])

  const loadResults = async () => {
    try {
      setLoading(true)
      const data = await umatestApi.getTestResults(resultId)
      setResults(data)
    } catch (err: any) {
      console.error('Failed to load results:', err)
      setError(err.response?.data?.detail || 'Failed to load test results')
    } finally {
      setLoading(false)
    }
  }

  const toggleQuestion = (index: number) => {
    setExpandedQuestions(prev => {
      const newSet = new Set(prev)
      if (newSet.has(index)) {
        newSet.delete(index)
      } else {
        newSet.add(index)
      }
      return newSet
    })
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600'
    if (score >= 80) return 'text-blue-600'
    if (score >= 70) return 'text-yellow-600'
    if (score >= 60) return 'text-orange-600'
    return 'text-red-600'
  }

  const getRubricLabel = (rubricScore: number) => {
    switch (rubricScore) {
      case 4: return { label: 'Excellent', color: 'text-green-600' }
      case 3: return { label: 'Good', color: 'text-blue-600' }
      case 2: return { label: 'Fair', color: 'text-yellow-600' }
      case 1: return { label: 'Poor', color: 'text-orange-600' }
      case 0: return { label: 'No Credit', color: 'text-red-600' }
      default: return { label: 'Unknown', color: 'text-gray-600' }
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 text-lg font-medium">Loading results...</p>
        </div>
      </div>
    )
  }

  if (error || !results) {
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-2xl mx-auto mt-8">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-red-800 mb-2">Unable to Load Results</h3>
            <p className="text-red-700 mb-4">{error}</p>
            <button
              onClick={() => router.push('/student/dashboard')}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    )
  }

  const passed = results.score >= 70

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Test Results</h1>
          
          {/* Score Display */}
          <div className="flex items-center justify-between mb-6">
            <div className="text-center">
              <div className={`text-5xl font-bold ${getScoreColor(results.score)}`}>
                {results.score.toFixed(1)}%
              </div>
              <p className="text-gray-600 mt-1">Overall Score</p>
            </div>
            
            <div className="text-center">
              <div className={`flex items-center justify-center ${passed ? 'text-green-600' : 'text-red-600'}`}>
                {passed ? (
                  <>
                    <CheckCircleIcon className="h-12 w-12" />
                    <span className="ml-2 text-2xl font-semibold">Passed</span>
                  </>
                ) : (
                  <>
                    <XCircleIcon className="h-12 w-12" />
                    <span className="ml-2 text-2xl font-semibold">Not Passed</span>
                  </>
                )}
              </div>
              <p className="text-gray-600 mt-1">70% to pass</p>
            </div>
          </div>

          {/* Overall Feedback */}
          {results.feedback && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-blue-900">{results.feedback}</p>
            </div>
          )}
        </div>

        {/* Question-by-Question Breakdown */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Question Breakdown ({results.question_evaluations.length} questions)
          </h2>
          
          <div className="space-y-4">
            {results.question_evaluations.map((evaluation, index) => {
              const isExpanded = expandedQuestions.has(index)
              const rubricInfo = getRubricLabel(evaluation.rubric_score)
              
              return (
                <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
                  {/* Question Header */}
                  <button
                    onClick={() => toggleQuestion(index)}
                    className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center space-x-4">
                      <span className="text-lg font-medium text-gray-900">
                        Question {evaluation.question_index + 1}
                      </span>
                      <span className={`text-sm font-medium ${rubricInfo.color}`}>
                        {rubricInfo.label}
                      </span>
                    </div>
                    <div className="flex items-center space-x-4">
                      <span className="text-gray-700">
                        {evaluation.points_earned.toFixed(1)} / {evaluation.max_points.toFixed(1)} points
                      </span>
                      {isExpanded ? (
                        <ChevronUpIcon className="h-5 w-5 text-gray-500" />
                      ) : (
                        <ChevronDownIcon className="h-5 w-5 text-gray-500" />
                      )}
                    </div>
                  </button>
                  
                  {/* Question Details (Expanded) */}
                  {isExpanded && (
                    <div className="border-t border-gray-200 p-4 bg-gray-50">
                      {/* Scoring Rationale */}
                      <div className="mb-4">
                        <h4 className="text-sm font-semibold text-gray-700 mb-1">Scoring Rationale</h4>
                        <p className="text-gray-600">{evaluation.scoring_rationale}</p>
                      </div>
                      
                      {/* Feedback */}
                      {evaluation.feedback && (
                        <div className="mb-4">
                          <h4 className="text-sm font-semibold text-gray-700 mb-1">Feedback for Improvement</h4>
                          <p className="text-gray-600">{evaluation.feedback}</p>
                        </div>
                      )}
                      
                      {/* Key Concepts */}
                      {evaluation.key_concepts_identified.length > 0 && (
                        <div className="mb-4">
                          <h4 className="text-sm font-semibold text-gray-700 mb-1">Key Concepts Identified</h4>
                          <div className="flex flex-wrap gap-2">
                            {evaluation.key_concepts_identified.map((concept, i) => (
                              <span key={i} className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                                {concept}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Misconceptions */}
                      {evaluation.misconceptions_detected.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-700 mb-1">Areas for Review</h4>
                          <div className="flex flex-wrap gap-2">
                            {evaluation.misconceptions_detected.map((misconception, i) => (
                              <span key={i} className="px-2 py-1 bg-amber-100 text-amber-800 text-xs rounded-full">
                                {misconception}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Actions */}
        <div className="mt-6 flex justify-center">
          <button
            onClick={() => router.push('/student/dashboard')}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}