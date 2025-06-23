'use client'

import { useState } from 'react'
import { DebatePost, ChallengeOption, ChallengeCreate } from '@/types/debate'
import { 
  UserIcon, 
  CpuChipIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline'
import { format } from 'date-fns'

interface DebatePostProps {
  post: DebatePost
  isLast: boolean
  availableChallenges: ChallengeOption[]
  onChallenge?: (challenge: ChallengeCreate) => Promise<void>
}

export default function DebatePostComponent({ 
  post, 
  isLast, 
  availableChallenges, 
  onChallenge 
}: DebatePostProps) {
  const [showChallenge, setShowChallenge] = useState(false)
  const [selectedChallenge, setSelectedChallenge] = useState<string>('')
  const [explanation, setExplanation] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const isStudent = post.postType === 'student'

  const handleSubmitChallenge = async () => {
    if (!selectedChallenge || !onChallenge) return

    const [type, value] = selectedChallenge.split(':')
    const challenge: ChallengeCreate = {
      postId: post.id,
      challengeType: type as 'fallacy' | 'appeal',
      challengeValue: value,
      explanation: explanation.trim() || undefined
    }

    try {
      setSubmitting(true)
      await onChallenge(challenge)
      setShowChallenge(false)
      setSelectedChallenge('')
      setExplanation('')
    } catch (err) {
      // Error handled by parent
    } finally {
      setSubmitting(false)
    }
  }

  const getScoreBadge = () => {
    if (!isStudent || !post.finalPercentage) return null

    const percentage = Number(post.finalPercentage)
    let colorClass = 'bg-gray-100 text-gray-800'
    
    if (percentage >= 80) colorClass = 'bg-green-100 text-green-800'
    else if (percentage < 60) colorClass = 'bg-red-100 text-red-800'

    return (
      <span className={`ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
        {percentage.toFixed(0)}%
      </span>
    )
  }

  return (
    <div className={`flex ${isStudent ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-2xl ${isStudent ? 'order-2' : ''}`}>
        <div className={`rounded-lg shadow-sm border ${
          isStudent ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'
        }`}>
          <div className="p-4">
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center">
                {isStudent ? (
                  <UserIcon className="h-5 w-5 text-blue-600 mr-2" />
                ) : (
                  <CpuChipIcon className="h-5 w-5 text-gray-600 mr-2" />
                )}
                <span className="font-medium text-sm">
                  {isStudent ? 'You' : post.aiPersonality || 'AI Opponent'}
                </span>
                {getScoreBadge()}
              </div>
              <span className="text-xs text-gray-500">
                {post.createdAt ? format(new Date(post.createdAt), 'h:mm a') : 'Just now'}
              </span>
            </div>

            {/* Content */}
            <div className="text-gray-700">
              <p className="whitespace-pre-wrap">{post.content}</p>
            </div>

            {/* AI Feedback for student posts */}
            {isStudent && post.aiFeedback && (
              <div className="mt-3 p-3 bg-blue-100 rounded-lg">
                <p className="text-sm text-blue-800">{post.aiFeedback}</p>
              </div>
            )}

            {/* Scoring breakdown for student posts */}
            {isStudent && post.clarityScore && (
              <div className="mt-3 pt-3 border-t border-blue-200">
                <div className="grid grid-cols-5 gap-2 text-xs">
                  <div className="text-center">
                    <div className="font-medium">Clarity</div>
                    <div>{post.clarityScore}/5</div>
                  </div>
                  <div className="text-center">
                    <div className="font-medium">Evidence</div>
                    <div>{post.evidenceScore}/5</div>
                  </div>
                  <div className="text-center">
                    <div className="font-medium">Logic</div>
                    <div>{post.logicScore}/5</div>
                  </div>
                  <div className="text-center">
                    <div className="font-medium">Persuasive</div>
                    <div>{post.persuasivenessScore}/5</div>
                  </div>
                  <div className="text-center">
                    <div className="font-medium">Rebuttal</div>
                    <div>{post.rebuttalScore}/5</div>
                  </div>
                </div>
              </div>
            )}

            {/* Challenge button for AI posts */}
            {!isStudent && isLast && availableChallenges.length > 0 && !showChallenge && (
              <div className="mt-3 pt-3 border-t border-gray-200">
                <button
                  onClick={() => setShowChallenge(true)}
                  className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                >
                  <ExclamationTriangleIcon className="h-4 w-4 mr-2" />
                  Challenge This Argument
                </button>
              </div>
            )}

            {/* Challenge form */}
            {showChallenge && (
              <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
                <select
                  value={selectedChallenge}
                  onChange={(e) => setSelectedChallenge(e.target.value)}
                  className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-green-500 focus:border-green-500 sm:text-sm rounded-md"
                >
                  <option value="">Select a challenge type</option>
                  {availableChallenges.map((option) => (
                    <option 
                      key={`${option.type}:${option.value}`} 
                      value={`${option.type}:${option.value}`}
                    >
                      {option.displayName} - {option.description}
                    </option>
                  ))}
                </select>

                {selectedChallenge && (
                  <textarea
                    placeholder="Explain why you think this applies (optional but recommended for full points)"
                    value={explanation}
                    onChange={(e) => setExplanation(e.target.value)}
                    rows={3}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 sm:text-sm"
                  />
                )}

                <div className="flex space-x-2">
                  <button
                    onClick={handleSubmitChallenge}
                    disabled={!selectedChallenge || submitting}
                    className={`inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white ${
                      !selectedChallenge || submitting
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500'
                    }`}
                  >
                    {submitting ? 'Submitting...' : 'Submit Challenge'}
                  </button>
                  <button
                    onClick={() => {
                      setShowChallenge(false)
                      setSelectedChallenge('')
                      setExplanation('')
                    }}
                    disabled={submitting}
                    className="inline-flex justify-center py-2 px-4 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Moderation warning */}
            {post.content_flagged && (
              <div className="mt-3 p-2 bg-yellow-100 border border-yellow-300 rounded flex items-center">
                <ExclamationTriangleIcon className="h-4 w-4 text-yellow-700 mr-2" />
                <span className="text-sm text-yellow-700">
                  This post is under review
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}