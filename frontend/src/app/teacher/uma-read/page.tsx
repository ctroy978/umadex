'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { BookOpenIcon, PlusIcon, PencilIcon, ArchiveBoxArrowDownIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import { ReadingAssignmentList, ReadingAssignmentListResponse } from '@/types/reading'
import { readingApi } from '@/lib/readingApi'
import AssignmentSearch from '@/components/teacher/umaread/AssignmentSearch'
import AssignmentFilters, { FilterValues } from '@/components/teacher/umaread/AssignmentFilters'
import ArchivedBadge from '@/components/teacher/umaread/ArchivedBadge'

export default function UmaReadPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  
  const [data, setData] = useState<ReadingAssignmentListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [archivingId, setArchivingId] = useState<string | null>(null)
  const [restoringId, setRestoringId] = useState<string | null>(null)
  
  // Search and filter state
  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [filters, setFilters] = useState<FilterValues>({
    dateRange: searchParams.get('dateRange') || 'all',
    dateFrom: searchParams.get('dateFrom') || undefined,
    dateTo: searchParams.get('dateTo') || undefined,
    gradeLevel: searchParams.get('gradeLevel') || '',
    workType: searchParams.get('workType') || '',
    includeArchived: searchParams.get('includeArchived') === 'true'
  })
  
  const [currentPage, setCurrentPage] = useState(1)
  const perPage = 20

  // Update URL with current filters
  const updateURL = useCallback((newSearch: string, newFilters: FilterValues) => {
    const params = new URLSearchParams()
    if (newSearch) params.set('search', newSearch)
    if (newFilters.dateRange !== 'all') params.set('dateRange', newFilters.dateRange)
    if (newFilters.dateFrom) params.set('dateFrom', newFilters.dateFrom)
    if (newFilters.dateTo) params.set('dateTo', newFilters.dateTo)
    if (newFilters.gradeLevel) params.set('gradeLevel', newFilters.gradeLevel)
    if (newFilters.workType) params.set('workType', newFilters.workType)
    if (newFilters.includeArchived) params.set('includeArchived', 'true')
    
    const queryString = params.toString()
    router.push(`/teacher/uma-read${queryString ? `?${queryString}` : ''}`)
  }, [router])

  const loadAssignments = useCallback(async () => {
    try {
      setLoading(true)
      
      const params: any = {
        skip: (currentPage - 1) * perPage,
        limit: perPage,
        include_archived: filters.includeArchived
      }
      
      if (search) params.search = search
      if (filters.dateFrom) params.date_from = filters.dateFrom
      if (filters.dateTo) params.date_to = filters.dateTo
      if (filters.gradeLevel) params.grade_level = filters.gradeLevel
      if (filters.workType) params.work_type = filters.workType
      
      const response = await readingApi.listAssignments(params)
      setData(response)
    } catch (err) {
      setError('Failed to load assignments')
      console.error('Error loading assignments:', err)
    } finally {
      setLoading(false)
    }
  }, [search, filters, currentPage])

  useEffect(() => {
    loadAssignments()
  }, [loadAssignments])

  const handleSearchChange = (value: string) => {
    setSearch(value)
    setCurrentPage(1)
    updateURL(value, filters)
  }

  const handleFilterChange = (newFilters: FilterValues) => {
    setFilters(newFilters)
    setCurrentPage(1)
    updateURL(search, newFilters)
  }

  const handleClearFilters = () => {
    const defaultFilters: FilterValues = {
      dateRange: 'all',
      dateFrom: undefined,
      dateTo: undefined,
      gradeLevel: '',
      workType: '',
      includeArchived: false
    }
    setFilters(defaultFilters)
    setSearch('')
    setCurrentPage(1)
    router.push('/teacher/uma-read')
  }

  const handleArchive = async (id: string) => {
    if (!confirm('Archive this assignment? You can restore it later from the archived view.')) {
      return
    }
    
    try {
      setArchivingId(id)
      await readingApi.archiveAssignment(id)
      await loadAssignments()
    } catch (err) {
      console.error('Error archiving assignment:', err)
      alert('Failed to archive assignment')
    } finally {
      setArchivingId(null)
    }
  }

  const handleRestore = async (id: string) => {
    try {
      setRestoringId(id)
      await readingApi.restoreAssignment(id)
      await loadAssignments()
    } catch (err) {
      console.error('Error restoring assignment:', err)
      alert('Failed to restore assignment')
    } finally {
      setRestoringId(null)
    }
  }

  const handleCreateNew = () => {
    router.push('/teacher/assignments/reading/new')
  }

  const handleEdit = (id: string) => {
    router.push(`/teacher/assignments/${id}/edit`)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const getStatusBadge = (status: string) => {
    const statusStyles = {
      draft: 'bg-gray-100 text-gray-800',
      published: 'bg-green-100 text-green-800',
    }

    return (
      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${statusStyles[status as keyof typeof statusStyles] || statusStyles.draft}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const getAvailabilityStatus = (assignment: ReadingAssignmentList) => {
    const now = new Date()
    const startDate = assignment.start_date ? new Date(assignment.start_date) : null
    const endDate = assignment.end_date ? new Date(assignment.end_date) : null

    if (assignment.status !== 'published') {
      return null
    }

    if (startDate && startDate > now) {
      return {
        status: 'scheduled',
        label: 'Not yet available',
        color: 'bg-yellow-100 text-yellow-800',
        tooltip: `Available from ${startDate.toLocaleString()}`
      }
    }

    if (endDate && endDate < now) {
      return {
        status: 'expired',
        label: 'Expired',
        color: 'bg-red-100 text-red-800',
        tooltip: `Expired on ${endDate.toLocaleString()}`
      }
    }

    if (startDate || endDate) {
      return {
        status: 'active',
        label: 'Currently available',
        color: 'bg-green-100 text-green-800',
        tooltip: endDate ? `Available until ${endDate.toLocaleString()}` : 'Always available'
      }
    }

    return null
  }

  const assignments = data?.assignments || []
  const totalPages = data ? Math.ceil(data.total / perPage) : 0

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">uMaRead</h1>
        <p className="text-gray-600">Create engaging reading comprehension activities for your students</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar with Filters */}
        <div className="lg:w-80">
          <AssignmentFilters
            filters={filters}
            onChange={handleFilterChange}
            onClearAll={handleClearFilters}
          />
        </div>

        {/* Main Content */}
        <div className="flex-1">
          {/* Search and Create Button */}
          <div className="mb-6 flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <AssignmentSearch
                value={search}
                onChange={handleSearchChange}
              />
            </div>
            <button 
              onClick={handleCreateNew}
              className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <PlusIcon className="h-5 w-5 mr-2" />
              Create New Assignment
            </button>
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
                <p className="mt-2 text-gray-500">Loading assignments...</p>
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
                <BookOpenIcon className="h-12 w-12 mx-auto mb-3 text-gray-400" />
                <p>{search || filters.dateRange !== 'all' || filters.gradeLevel || filters.workType 
                  ? 'No assignments match your search' 
                  : 'No reading assignments yet. Create your first one!'}</p>
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
                        Work Details
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Grade/Subject
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Availability
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
                      const isArchived = !!assignment.deleted_at
                      return (
                        <tr key={assignment.id} className={`hover:bg-gray-50 ${isArchived ? 'bg-gray-50 opacity-75' : ''}`}>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div>
                              <div className="text-sm font-medium text-gray-900 flex items-center gap-2">
                                {assignment.assignment_title}
                                {isArchived && <ArchivedBadge />}
                              </div>
                              {assignment.total_chunks && (
                                <div className="text-sm text-gray-500">
                                  {assignment.total_chunks} chunks
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-900">{assignment.work_title}</div>
                            {assignment.author && (
                              <div className="text-sm text-gray-500">by {assignment.author}</div>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-900">{assignment.grade_level}</div>
                            <div className="text-sm text-gray-500">{assignment.subject}</div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {getStatusBadge(assignment.status)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {(() => {
                              const availability = getAvailabilityStatus(assignment)
                              if (!availability) {
                                return <span className="text-sm text-gray-500">Always available</span>
                              }
                              return (
                                <span 
                                  className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${availability.color}`}
                                  title={availability.tooltip}
                                >
                                  {availability.label}
                                </span>
                              )
                            })()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {formatDate(assignment.created_at)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <div className="flex items-center justify-end space-x-3">
                              <button
                                onClick={() => handleEdit(assignment.id)}
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
    </div>
  )
}