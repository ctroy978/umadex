'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { 
  ChatBubbleLeftRightIcon, 
  PlusIcon, 
  PencilIcon, 
  ArchiveBoxArrowDownIcon, 
  ArrowPathIcon,
  MagnifyingGlassIcon
} from '@heroicons/react/24/outline'
import { debateApi } from '@/lib/debateApi'
import type { 
  DebateAssignmentSummary, 
  DebateAssignmentListResponse
} from '@/types/debate'

export default function UmaDebatePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  
  const [data, setData] = useState<DebateAssignmentListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [archivingId, setArchivingId] = useState<string | null>(null)
  const [restoringId, setRestoringId] = useState<string | null>(null)
  
  // Search and filter state
  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [includeArchived, setIncludeArchived] = useState(false)
  
  const [currentPage, setCurrentPage] = useState(1)
  const perPage = 20

  const loadAssignments = useCallback(async () => {
    try {
      setLoading(true)
      
      const params: any = {
        page: currentPage,
        per_page: perPage,
        include_archived: includeArchived
      }
      
      if (search) params.search = search
      
      const response = await debateApi.listAssignments(params)
      setData(response)
    } catch (err) {
      setError('Failed to load debate assignments')
      console.error('Error loading assignments:', err)
    } finally {
      setLoading(false)
    }
  }, [search, currentPage, includeArchived])

  useEffect(() => {
    loadAssignments()
  }, [loadAssignments])

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setSearch(value)
    setCurrentPage(1)
  }


  const handleArchive = async (id: string) => {
    if (!confirm('Archive this debate assignment? You can restore it later from the archived view.')) {
      return
    }
    
    try {
      setArchivingId(id)
      await debateApi.archiveAssignment(id)
      await loadAssignments()
    } catch (err: any) {
      console.error('Error archiving assignment:', err)
      
      // Check for 400 error with specific message about classrooms
      if (err.response?.status === 400 && err.response?.data?.detail) {
        alert(err.response.data.detail)
      } else if (err.response?.data?.message) {
        // Some error responses might use 'message' instead of 'detail'
        alert(err.response.data.message)
      } else {
        alert('Failed to archive assignment')
      }
    } finally {
      setArchivingId(null)
    }
  }

  const handleRestore = async (id: string) => {
    try {
      setRestoringId(id)
      await debateApi.restoreAssignment(id)
      await loadAssignments()
    } catch (err) {
      console.error('Error restoring assignment:', err)
      alert('Failed to restore assignment')
    } finally {
      setRestoringId(null)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const getDifficultyBadge = (level: string) => {
    const styles = {
      beginner: 'bg-green-100 text-green-800',
      intermediate: 'bg-yellow-100 text-yellow-800',
      advanced: 'bg-red-100 text-red-800'
    }
    
    return (
      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${styles[level as keyof typeof styles]}`}>
        {level.charAt(0).toUpperCase() + level.slice(1)}
      </span>
    )
  }

  const assignments = data?.assignments || []
  const totalPages = data ? Math.ceil(data.total / perPage) : 0

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">uMaDebate</h1>
        <p className="text-gray-600">Create engaging debate assignments where students argue with AI opponents</p>
      </div>

      <div>
          {/* Search and Create Button */}
          <div className="mb-6 flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  value={search}
                  onChange={handleSearchChange}
                  placeholder="Search debate assignments..."
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
            
            <div className="flex gap-2">
              <select
                value={includeArchived ? 'archived' : 'active'}
                onChange={(e) => {
                  setIncludeArchived(e.target.value === 'archived')
                  setCurrentPage(1)
                }}
                className="px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="active">Active</option>
                <option value="archived">Include Archived</option>
              </select>
              
              <button 
                onClick={() => router.push('/teacher/debate/create')}
                className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <PlusIcon className="h-5 w-5 mr-2" />
                Create New Assignment
              </button>
            </div>
          </div>

          {/* Results Count */}
          {data && (
            <div className="mb-4 text-sm text-gray-600">
              Showing {assignments.length} of {data.filtered} assignments
              {data.filtered < data.total && ` (filtered from ${data.total} total)`}
            </div>
          )}

          {/* Assignment List */}
          <div className="bg-white rounded-lg shadow">
            {loading ? (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                <p className="mt-2 text-gray-500">Loading debate assignments...</p>
              </div>
            ) : error ? (
              <div className="text-center py-12">
                <p className="text-red-600">{error}</p>
                <button onClick={loadAssignments} className="mt-2 text-blue-600 hover:text-blue-800">
                  Try again
                </button>
              </div>
            ) : assignments.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <ChatBubbleLeftRightIcon className="h-12 w-12 mx-auto mb-3 text-gray-400" />
                <p>{search 
                  ? 'No assignments match your search' 
                  : includeArchived 
                    ? 'No assignments found'
                    : 'No debate assignments yet. Create your first one!'}</p>
              </div>
            ) : (
              <div className="overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Assignment
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Topic
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Configuration
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Grade/Subject
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Created
                      </th>
                      <th className="relative px-6 py-3">
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {assignments.map((assignment) => {
                      const isArchived = !!assignment.deletedAt
                      return (
                        <tr key={assignment.id} className={`hover:bg-gray-50 ${isArchived ? 'bg-gray-50 opacity-75' : ''}`}>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900">
                              {assignment.title}
                              {isArchived && (
                                <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                                  Archived
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900 max-w-xs truncate" title={assignment.topic}>
                              {assignment.topic}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-900">
                              {assignment.debateCount} debates, {assignment.roundsPerDebate} rounds each
                            </div>
                            <div className="text-sm text-gray-500">
                              {assignment.timeLimitHours}h time limit
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-900">{assignment.gradeLevel}</div>
                            <div className="text-sm text-gray-500">{assignment.subject}</div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {formatDate(assignment.createdAt)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <div className="flex items-center justify-end space-x-3">
                              <button
                                onClick={() => router.push(`/teacher/debate/${assignment.id}/edit`)}
                                className="text-blue-600 hover:text-blue-900"
                                title="Edit"
                              >
                                <PencilIcon className="h-5 w-5" />
                              </button>
                              {isArchived ? (
                                <button
                                  onClick={() => handleRestore(assignment.id)}
                                  disabled={restoringId === assignment.id}
                                  className="text-green-600 hover:text-green-900 disabled:opacity-50"
                                  title="Restore"
                                >
                                  {restoringId === assignment.id ? (
                                    <ArrowPathIcon className="h-5 w-5 animate-spin" />
                                  ) : (
                                    <ArrowPathIcon className="h-5 w-5" />
                                  )}
                                </button>
                              ) : (
                                <button
                                  onClick={() => handleArchive(assignment.id)}
                                  disabled={archivingId === assignment.id}
                                  className="text-gray-600 hover:text-gray-900 disabled:opacity-50"
                                  title="Archive"
                                >
                                  {archivingId === assignment.id ? (
                                    <ArrowPathIcon className="h-5 w-5 animate-spin" />
                                  ) : (
                                    <ArchiveBoxArrowDownIcon className="h-5 w-5" />
                                  )}
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-6 flex justify-between items-center">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-sm text-gray-700">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}
      </div>
    </div>
  )
}