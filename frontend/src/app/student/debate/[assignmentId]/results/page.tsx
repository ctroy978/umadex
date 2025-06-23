'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { studentDebateApi } from '@/lib/studentDebateApi'
import { AssignmentScore, DebateAssignmentCard } from '@/types/debate'
import { 
  TrophyIcon, 
  ArrowTrendingUpIcon, 
  CheckBadgeIcon, 
  ArrowLeftIcon,
  CheckCircleIcon,
  XCircleIcon,
  MinusIcon
} from '@heroicons/react/24/outline'

export default function DebateResultsPage() {
  const params = useParams()
  const router = useRouter()
  const assignmentId = params.assignmentId as string

  const [assignment, setAssignment] = useState<DebateAssignmentCard | null>(null)
  const [scores, setScores] = useState<AssignmentScore | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchResults()
  }, [assignmentId])

  const fetchResults = async () => {
    try {
      setLoading(true)
      const [assignmentData, scoresData] = await Promise.all([
        studentDebateApi.getAssignment(assignmentId),
        studentDebateApi.getScores(assignmentId)
      ])
      setAssignment(assignmentData)
      setScores(scoresData)
    } catch (err) {
      console.error('Failed to fetch results:', err)
      setError('Failed to load results')
    } finally {
      setLoading(false)
    }
  }

  const getGradeColor = (percentage: number) => {
    if (percentage >= 90) return 'text-green-600'
    if (percentage >= 80) return 'text-blue-600'
    if (percentage >= 70) return 'text-yellow-600'
    if (percentage >= 60) return 'text-orange-600'
    return 'text-red-600'
  }

  const getGradeLetter = (percentage: number) => {
    if (percentage >= 90) return 'A'
    if (percentage >= 80) return 'B'
    if (percentage >= 70) return 'C'
    if (percentage >= 60) return 'D'
    return 'F'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading results...</p>
        </div>
      </div>
    )
  }

  if (error || !assignment || !scores) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto">
          <p className="text-red-600">{error || 'Results not found'}</p>
          <button 
            onClick={() => router.push('/student/dashboard')}
            className="mt-4 inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
          >
            <ArrowLeftIcon className="mr-2 h-4 w-4" />
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto p-6">
        {/* Header */}
        <div className="mb-6">
          <button 
            onClick={() => router.push('/student/dashboard')}
            className="mb-4 inline-flex items-center text-gray-600 hover:text-gray-900"
          >
            <ArrowLeftIcon className="mr-2 h-4 w-4" />
            Back to Dashboard
          </button>
          
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Debate Results</h1>
          <p className="text-gray-600">{assignment.title}</p>
        </div>

        {/* Overall Grade Card */}
        <div className="mb-6 bg-gradient-to-r from-green-50 to-blue-50 rounded-lg shadow p-6">
          <div className="text-center">
            <TrophyIcon className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
            <h2 className="text-3xl font-bold mb-2">Assignment Complete!</h2>
            <div className={`text-5xl font-bold ${getGradeColor(scores.final_grade)}`}>
              {scores.final_grade.toFixed(1)}%
            </div>
            <div className={`text-2xl font-semibold mt-2 ${getGradeColor(scores.final_grade)}`}>
              Grade: {getGradeLetter(scores.final_grade)}
            </div>
          </div>
        </div>

        {/* Individual Debate Scores */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {[scores.debate_1_score, scores.debate_2_score, scores.debate_3_score].map((debate, index) => (
            debate && (
              <div key={index} className="bg-white rounded-lg shadow p-4">
                <div className="mb-3">
                  <h3 className="text-lg font-medium">Debate {index + 1}</h3>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    {index === 0 ? 'Assigned PRO' : index === 1 ? 'Assigned CON' : 'Your Choice'}
                  </span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Average Score</span>
                    <span className={`font-semibold ${getGradeColor(debate.average_percentage)}`}>
                      {debate.average_percentage.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-green-600 h-2 rounded-full"
                      style={{ width: `${debate.average_percentage}%` }}
                    />
                  </div>
                  
                  {debate.total_bonus_points > 0 && (
                    <div className="flex justify-between items-center pt-2">
                      <span className="text-sm text-gray-600">Challenge Bonus</span>
                      <span className="text-green-600 font-medium">
                        +{debate.total_bonus_points.toFixed(1)}
                      </span>
                    </div>
                  )}
                  
                  <div className="flex justify-between items-center border-t pt-2">
                    <span className="text-sm font-medium">Final</span>
                    <span className={`font-bold ${getGradeColor(debate.final_percentage)}`}>
                      {debate.final_percentage.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            )
          ))}
        </div>

        {/* Bonuses */}
        {(scores.improvement_bonus > 0 || scores.consistency_bonus > 0) && (
          <div className="mb-6 bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium flex items-center">
                <CheckBadgeIcon className="h-5 w-5 mr-2 text-yellow-500" />
                Performance Bonuses
              </h3>
            </div>
            <div className="p-6">
              <div className="space-y-3">
                {scores.improvement_bonus > 0 && (
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <div className="flex items-center">
                      <ArrowTrendingUpIcon className="h-5 w-5 text-green-600 mr-2" />
                      <div>
                        <p className="font-medium">Improvement Bonus</p>
                        <p className="text-sm text-gray-600">
                          Your final debate showed improvement!
                        </p>
                      </div>
                    </div>
                    <span className="text-green-600 font-bold">+{scores.improvement_bonus}%</span>
                  </div>
                )}
                
                {scores.consistency_bonus > 0 && (
                  <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                    <div className="flex items-center">
                      <CheckCircleIcon className="h-5 w-5 text-blue-600 mr-2" />
                      <div>
                        <p className="font-medium">Consistency Bonus</p>
                        <p className="text-sm text-gray-600">
                          All debates within 15% of each other
                        </p>
                      </div>
                    </div>
                    <span className="text-blue-600 font-bold">+{scores.consistency_bonus}%</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Detailed Breakdown */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium">Scoring Breakdown</h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Your posts were evaluated on five criteria: Clarity, Evidence, Logic, 
                Persuasiveness, and Rebuttal. Each category is scored 1-5, contributing 
                to a base score of up to 70%.
              </p>
              
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Base Score (Average of 3 debates)</span>
                  <span>{((scores.debate_1_score?.average_percentage || 0) + 
                          (scores.debate_2_score?.average_percentage || 0) + 
                          (scores.debate_3_score?.average_percentage || 0)) / 3}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Challenge Points</span>
                  <span>+{(scores.debate_1_score?.total_bonus_points || 0) + 
                          (scores.debate_2_score?.total_bonus_points || 0) + 
                          (scores.debate_3_score?.total_bonus_points || 0)}</span>
                </div>
                {scores.improvement_bonus > 0 && (
                  <div className="flex justify-between text-sm">
                    <span>Improvement Bonus</span>
                    <span className="text-green-600">+{scores.improvement_bonus}%</span>
                  </div>
                )}
                {scores.consistency_bonus > 0 && (
                  <div className="flex justify-between text-sm">
                    <span>Consistency Bonus</span>
                    <span className="text-blue-600">+{scores.consistency_bonus}%</span>
                  </div>
                )}
                <div className="flex justify-between font-bold border-t pt-2">
                  <span>Final Grade</span>
                  <span className={getGradeColor(scores.final_grade)}>
                    {scores.final_grade.toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="mt-6 text-center">
          <button 
            onClick={() => router.push('/student/dashboard')}
            className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}