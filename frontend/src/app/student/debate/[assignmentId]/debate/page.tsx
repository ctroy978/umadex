'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { studentDebateApi } from '@/lib/studentDebateApi'
import { DebateProgress, DebatePost, StudentPostCreate, DebateAssignmentCard } from '@/types/debate'
import DebatePostComponent from '@/components/debate/DebatePost'
import PostComposer from '@/components/debate/PostComposer'
import DebateHeader from '@/components/debate/DebateHeader'
import PositionSelector from '@/components/debate/PositionSelector'
import RoundComplete from '@/components/debate/RoundComplete'
import RhetoricalTechniquesPanel from '@/components/debate/RhetoricalTechniquesPanel'
import { ExclamationCircleIcon } from '@heroicons/react/24/outline'
import AntiCheatWrapper from '@/components/debate/AntiCheatWrapper'

export default function DebateInterfacePage() {
  const params = useParams()
  const router = useRouter()
  const assignmentId = params.assignmentId as string
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const [progress, setProgress] = useState<DebateProgress | null>(null)
  const [assignment, setAssignment] = useState<DebateAssignmentCard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [showPositionSelector, setShowPositionSelector] = useState(false)

  useEffect(() => {
    fetchInitialData()
    // Poll for updates every 30 seconds when waiting for AI
    const interval = setInterval(() => {
      if (progress?.nextAction === 'await_ai') {
        fetchDebateProgress()
      }
    }, 30000)
    return () => clearInterval(interval)
  }, [assignmentId])

  useEffect(() => {
    // Scroll to bottom when new posts are added
    scrollToBottom()
  }, [progress?.currentPosts])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const fetchInitialData = async () => {
    try {
      setError(null)
      // Fetch both assignment details and progress
      const [assignmentData, progressData] = await Promise.all([
        studentDebateApi.getAssignment(assignmentId),
        studentDebateApi.getCurrentDebate(assignmentId)
      ])
      
      setAssignment(assignmentData)
      setProgress(progressData)
      
      // Check if we need position selection
      if (progressData.nextAction === 'choose_position') {
        setShowPositionSelector(true)
      }
    } catch (err) {
      setError('Failed to load debate. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const fetchDebateProgress = async () => {
    try {
      setError(null)
      const data = await studentDebateApi.getCurrentDebate(assignmentId)
      
      // Ensure data has the expected structure
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid response format')
      }
      
      // Ensure currentPosts is an array
      if (!data.currentPosts) {
        data.currentPosts = []
      }
      
      setProgress(data)
      
      // Check if we need position selection
      if (data.nextAction === 'choose_position') {
        setShowPositionSelector(true)
      }
    } catch (err) {
      setError('Failed to load debate. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitPost = async (content: string, selectedTechnique?: string) => {
    if (!progress || !progress.canSubmitPost) return

    try {
      setSubmitting(true)
      const post: StudentPostCreate = {
        content,
        word_count: studentDebateApi.countWords(content),
        selectedTechnique
      }

      await studentDebateApi.submitPost(assignmentId, post)
      
      // Refresh progress to get AI response
      await fetchDebateProgress()
      
      // Post submitted successfully, AI is preparing response
    } catch (err: any) {
      
      if (err.message === 'Post submitted for review') {
        setError('Your post has been flagged for teacher review.')
      } else if (err.response?.data?.detail) {
        setError(`Failed to submit post: ${err.response.data.detail}`)
      } else {
        setError('Failed to submit post. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handlePositionSelected = async (position: 'pro' | 'con') => {
    try {
      await studentDebateApi.selectPosition(assignmentId, { position })
      setShowPositionSelector(false)
      await fetchDebateProgress()
      
      // Position selected successfully
    } catch (err) {
      setError('Failed to select position. Please try again.')
    }
  }

  const handleDebateComplete = async () => {
    try {
      // Call the advance endpoint to move to next debate
      await studentDebateApi.advanceDebate(assignmentId)
      // Navigate directly back to UMADebate dashboard
      router.push(`/student/debate/${assignmentId}`)
    } catch (err) {
      setError('Failed to continue to next debate. Please try again.')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading debate...</p>
        </div>
      </div>
    )
  }

  if (error || !progress) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <ExclamationCircleIcon className="h-5 w-5 text-red-400" />
              <p className="ml-3 text-sm text-red-800">
                {error || 'Failed to load debate'}
              </p>
            </div>
          </div>
          <button
            onClick={() => router.push(`/student/debate/${assignmentId}`)}
            className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Back to Assignment
          </button>
        </div>
      </div>
    )
  }

  // Don't show RoundComplete screen immediately - let user see their final feedback first

  if (progress.nextAction === 'assignment_complete') {
    router.push(`/student/debate/${assignmentId}/results`)
    return null
  }

  return (
    <AntiCheatWrapper>
      <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <DebateHeader progress={progress} />

      {/* Rhetorical Techniques Panel */}
      <RhetoricalTechniquesPanel />

      {/* Position Selection Modal */}
      {showPositionSelector && (
        <PositionSelector
          onSelect={handlePositionSelected}
          topic={assignment?.topic || ''}
        />
      )}

      {/* Chat Interface */}
      <div className="flex-1 overflow-hidden flex flex-col max-w-4xl w-full mx-auto">
        {/* Topic Section */}
        {assignment && progress && (
          <div className={(() => {
            const studentDebate = progress.studentDebate
            if (!studentDebate) return "bg-blue-50 border-b border-blue-200"
            
            const currentDebate = studentDebate.currentDebate
            let position = null
            
            // Access position fields directly based on current debate
            if (currentDebate === 1) {
              position = studentDebate.debate_1Position
            } else if (currentDebate === 2) {
              position = studentDebate.debate_2Position
            } else if (currentDebate === 3) {
              position = studentDebate.debate_3Position
            }
            
            if (position === 'pro') {
              return "bg-green-50 border-b border-green-200"
            } else if (position === 'con') {
              return "bg-red-50 border-b border-red-200"
            }
            return "bg-blue-50 border-b border-blue-200"
          })() + " p-4"}>
            <div className="max-w-4xl mx-auto">
              <h2 className={`text-lg font-semibold mb-1 ${(() => {
                const studentDebate = progress.studentDebate
                if (!studentDebate) return "text-blue-900"
                
                const currentDebate = studentDebate.currentDebate
                let position = null
                
                if (currentDebate === 1) {
                  position = studentDebate.debate_1Position
                } else if (currentDebate === 2) {
                  position = studentDebate.debate_2Position
                } else if (currentDebate === 3) {
                  position = studentDebate.debate_3Position
                }
                
                if (position === 'pro') {
                  return "text-green-900"
                } else if (position === 'con') {
                  return "text-red-900"
                }
                return "text-blue-900"
              })()}`}>Debate Topic:</h2>
              <p className={`text-base mb-3 ${(() => {
                const studentDebate = progress.studentDebate
                if (!studentDebate) return "text-blue-800"
                
                const currentDebate = studentDebate.currentDebate
                let position = null
                
                if (currentDebate === 1) {
                  position = studentDebate.debate_1Position
                } else if (currentDebate === 2) {
                  position = studentDebate.debate_2Position
                } else if (currentDebate === 3) {
                  position = studentDebate.debate_3Position
                }
                
                if (position === 'pro') {
                  return "text-green-800"
                } else if (position === 'con') {
                  return "text-red-800"
                }
                return "text-blue-800"
              })()}`}>{assignment.topic}</p>
              
              
              {/* Position Indicator */}
              {(() => {
                const studentDebate = progress.studentDebate
                if (!studentDebate) return null
                
                const currentDebate = studentDebate.currentDebate
                let position = null
                
                // Access position fields directly based on current debate
                // The API returns them as debate_1Position, debate_2Position, etc.
                if (currentDebate === 1) {
                  position = studentDebate.debate_1Position
                } else if (currentDebate === 2) {
                  position = studentDebate.debate_2Position
                } else if (currentDebate === 3) {
                  position = studentDebate.debate_3Position
                }
                
                if (!position) return null
                
                return (
                  <div className={`inline-flex items-center px-4 py-2 rounded-lg text-sm font-bold ${
                    position === 'pro' 
                      ? 'bg-green-100 text-green-800 border-2 border-green-300' 
                      : 'bg-red-100 text-red-800 border-2 border-red-300'
                  }`}>
                    <span className="mr-2">Your Position:</span>
                    <span className="text-lg uppercase">
                      {position === 'pro' ? 'PRO (Supporting)' : 'CON (Opposing)'}
                    </span>
                  </div>
                )
              })()}
            </div>
          </div>
        )}
        
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {progress?.currentPosts && progress.currentPosts.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500 mb-2">
                Start Round {progress.studentDebate?.currentDebate || 1} by presenting your opening argument on a single, focused point
                {(() => {
                  const studentDebate = progress.studentDebate
                  if (!studentDebate) return '.'
                  
                  const currentDebate = studentDebate.currentDebate
                  let position = null
                  
                  if (currentDebate === 1) {
                    position = studentDebate.debate_1Position
                  } else if (currentDebate === 2) {
                    position = studentDebate.debate_2Position
                  } else if (currentDebate === 3) {
                    position = studentDebate.debate_3Position
                  }
                  
                  if (position) {
                    return position === 'pro' 
                      ? ' in support of the topic.'
                      : ' against the topic.'
                  }
                  return '.'
                })()}
              </p>
              <p className="text-sm text-gray-400">
                This round will have 5 statements total. Focus on one specific argument throughout the round.
              </p>
            </div>
          )}

          {progress?.currentPosts?.map((post, index) => (
            <DebatePostComponent
              key={post.id}
              post={post}
              isLast={index === (progress?.currentPosts?.length || 0) - 1}
              availableChallenges={
                index === (progress?.currentPosts?.length || 0) - 1 && 
                post.postType === 'ai' ? 
                progress.availableChallenges : 
                []
              }
              onChallenge={async (challenge) => {
                try {
                  const result = await studentDebateApi.submitChallenge(assignmentId, challenge)
                  
                  // Show challenge result notification
                  if (result.isCorrect) {
                    alert(`✅ Correct! ${result.aiFeedback}\n\nYou earned ${result.pointsAwarded} bonus points!`)
                  } else {
                    alert(`❌ ${result.aiFeedback}`)
                  }
                  
                  // Refresh to update scores
                  await fetchDebateProgress()
                } catch (err) {
                  alert('Failed to submit challenge. Please try again.')
                }
              }}
            />
          ))}

          {/* Loading indicator for AI response */}
          {progress.nextAction === 'await_ai' && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-lg p-4 max-w-md">
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                  <span className="text-gray-600">AI is typing...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Composer */}
        {progress.canSubmitPost && (
          <div className="border-t bg-white">
            <PostComposer
              onSubmit={handleSubmitPost}
              disabled={submitting || progress.nextAction !== 'submit_post'}
              minWords={75}
              maxWords={300}
            />
          </div>
        )}

        {/* Complete Round Button */}
        {progress.nextAction === 'debate_complete' && (
          <div className="border-t bg-white p-6">
            <div className="max-w-2xl mx-auto text-center">
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Round {progress.studentDebate?.currentDebate || 1} Complete!
                </h3>
                <p className="text-gray-600">
                  Great job completing this debate round. Review your feedback above, then click continue when you're ready.
                </p>
              </div>
              <button
                onClick={handleDebateComplete}
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
              >
                {progress.studentDebate?.currentDebate === 3 
                  ? 'Complete Assignment' 
                  : 'Continue to Next Debate'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
    </AntiCheatWrapper>
  )
}