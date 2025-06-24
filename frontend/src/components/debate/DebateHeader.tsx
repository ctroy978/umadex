'use client'

import { DebateProgress } from '@/types/debate'
import { studentDebateApi } from '@/lib/studentDebateApi'
import { ArrowLeftIcon, ChatBubbleLeftRightIcon, UserGroupIcon } from '@heroicons/react/24/outline'
import { useRouter } from 'next/navigation'

interface DebateHeaderProps {
  progress: DebateProgress
}

export default function DebateHeader({ progress }: DebateHeaderProps) {
  const router = useRouter()
  
  if (!progress?.studentDebate) {
    return null
  }
  
  const studentDebate = progress.studentDebate
  const currentDebateKey = `debate_${studentDebate.currentDebate}Position` as keyof typeof studentDebate
  const currentPosition = studentDebate[currentDebateKey] as string | null

  return (
    <div className="bg-white border-b shadow-sm">
      <div className="max-w-4xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.push(`/student/debate/${studentDebate.assignmentId}`)}
              className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
            >
              <ArrowLeftIcon className="h-4 w-4 mr-2" />
              Back
            </button>
            
            <div className="flex items-center space-x-3">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 border border-gray-300">
                Debate {studentDebate.currentDebate}/3
              </span>
              
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                Round {studentDebate.currentRound}
              </span>
              
              {currentPosition && (
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  currentPosition === 'pro' 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  <UserGroupIcon className="h-3 w-3 mr-1" />
                  {currentPosition.toUpperCase()}
                </span>
              )}
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <div className="flex items-center text-sm text-gray-600">
              <ChatBubbleLeftRightIcon className="h-4 w-4 mr-1" />
              <span>{progress?.currentPosts?.length || 0} posts</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}