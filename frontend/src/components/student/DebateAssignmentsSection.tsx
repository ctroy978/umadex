'use client'

import { useState, useEffect } from 'react'
import { studentDebateApi } from '@/lib/studentDebateApi'
import { DebateAssignmentCard as DebateCardType } from '@/types/debate'
import DebateAssignmentCard from '@/components/debate/DebateAssignmentCard'
import { MessageSquare, AlertCircle } from 'lucide-react'

export default function DebateAssignmentsSection() {
  const [assignments, setAssignments] = useState<DebateCardType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDebateAssignments()
  }, [])

  const fetchDebateAssignments = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await studentDebateApi.getAssignments()
      setAssignments(data)
    } catch (err) {
      setError('Failed to load debate assignments')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center mb-4">
          <MessageSquare className="h-5 w-5 text-green-600 mr-2" />
          <h2 className="text-lg font-semibold text-gray-900">UMADebate Assignments</h2>
        </div>
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-3 text-sm text-gray-500">Loading debate assignments...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center mb-4">
          <MessageSquare className="h-5 w-5 text-green-600 mr-2" />
          <h2 className="text-lg font-semibold text-gray-900">UMADebate Assignments</h2>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
            <div className="ml-3">
              <p className="text-sm text-red-800">{error}</p>
              <button
                onClick={fetchDebateAssignments}
                className="mt-2 text-sm font-medium text-red-600 hover:text-red-500"
              >
                Try again
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (assignments.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center mb-4">
          <MessageSquare className="h-5 w-5 text-green-600 mr-2" />
          <h2 className="text-lg font-semibold text-gray-900">UMADebate Assignments</h2>
        </div>
        <div className="text-center py-8">
          <MessageSquare className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No debate assignments available yet</p>
          <p className="text-sm text-gray-400 mt-1">Check back later for new debates!</p>
        </div>
      </div>
    )
  }

  // Group assignments by status
  const activeAssignments = assignments.filter(a => 
    a.status !== 'not_started' && a.status !== 'completed'
  )
  const notStartedAssignments = assignments.filter(a => a.status === 'not_started')
  const completedAssignments = assignments.filter(a => a.status === 'completed')

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <MessageSquare className="h-5 w-5 text-green-600 mr-2" />
            <h2 className="text-lg font-semibold text-gray-900">UMADebate Assignments</h2>
          </div>
          <span className="text-sm text-gray-500">
            {assignments.length} total
          </span>
        </div>

        {/* Active Debates */}
        {activeAssignments.length > 0 && (
          <div className="mb-8">
            <h3 className="text-sm font-medium text-gray-700 mb-3">In Progress</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {activeAssignments.map((assignment) => (
                <DebateAssignmentCard key={assignment.assignment_id} assignment={assignment} />
              ))}
            </div>
          </div>
        )}

        {/* Not Started */}
        {notStartedAssignments.length > 0 && (
          <div className="mb-8">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Ready to Start</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {notStartedAssignments.map((assignment) => (
                <DebateAssignmentCard key={assignment.assignment_id} assignment={assignment} />
              ))}
            </div>
          </div>
        )}

        {/* Completed */}
        {completedAssignments.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">Completed</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {completedAssignments.map((assignment) => (
                <DebateAssignmentCard key={assignment.assignment_id} assignment={assignment} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}