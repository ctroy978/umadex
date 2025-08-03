'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { PencilSquareIcon, PlusIcon, PencilIcon, ArchiveBoxArrowDownIcon, ArrowPathIcon, ClipboardDocumentListIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { WritingAssignment, WritingAssignmentListResponse } from '@/types/writing'
import { writingApi } from '@/lib/writingApi'
import Link from 'next/link'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'

interface FilterValues {
  gradeLevel: string
  subject: string
  includeArchived: boolean
}

export default function UmaWritePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  
  const [data, setData] = useState<WritingAssignmentListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [archivingId, setArchivingId] = useState<string | null>(null)
  const [restoringId, setRestoringId] = useState<string | null>(null)
  const [showSuccessMessage, setShowSuccessMessage] = useState(false)
  const [errorDialog, setErrorDialog] = useState<{ open: boolean; title: string; message: string }>({
    open: false,
    title: '',
    message: ''
  })
  
  // Search and filter state
  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [filters, setFilters] = useState<FilterValues>({
    gradeLevel: searchParams.get('gradeLevel') || '',
    subject: searchParams.get('subject') || '',
    includeArchived: searchParams.get('includeArchived') === 'true'
  })
  
  const [currentPage, setCurrentPage] = useState(1)
  const perPage = 20

  // Update URL with current filters
  const updateURL = useCallback((newSearch: string, newFilters: FilterValues) => {
    const params = new URLSearchParams()
    if (newSearch) params.set('search', newSearch)
    if (newFilters.gradeLevel) params.set('gradeLevel', newFilters.gradeLevel)
    if (newFilters.subject) params.set('subject', newFilters.subject)
    if (newFilters.includeArchived) params.set('includeArchived', 'true')
    
    const queryString = params.toString()
    router.push(`/teacher/uma-write${queryString ? `?${queryString}` : ''}`)
  }, [router])

  const loadAssignments = useCallback(async () => {
    try {
      setLoading(true)
      
      const params: any = {
        page: currentPage,
        per_page: perPage,
        archived: filters.includeArchived ? undefined : false
      }
      
      if (search) params.search = search
      if (filters.gradeLevel) params.grade_level = filters.gradeLevel
      if (filters.subject) params.subject = filters.subject
      
      const response = await writingApi.getAssignments(params)
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

  // Check for success message from creation
  useEffect(() => {
    if (searchParams.get('created') === 'true') {
      setShowSuccessMessage(true)
      // Remove the query parameter after showing the message
      setTimeout(() => {
        router.push('/teacher/uma-write')
      }, 100)
      // Hide the message after 5 seconds
      setTimeout(() => {
        setShowSuccessMessage(false)
      }, 5000)
    }
  }, [searchParams, router])


  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setSearch(value)
    setCurrentPage(1)
    updateURL(value, filters)
  }

  const handleFilterChange = (key: keyof FilterValues, value: any) => {
    const newFilters = { ...filters, [key]: value }
    setFilters(newFilters)
    setCurrentPage(1)
    updateURL(search, newFilters)
  }

  const handleArchive = async (assignment: WritingAssignment) => {
    // First, fetch fresh assignment data to check current classroom count
    try {
      const freshAssignment = await writingApi.getAssignment(assignment.id)
      
      // Check if assignment is attached to classrooms using fresh data
      if (freshAssignment.classroom_count > 0) {
        setErrorDialog({
          open: true,
          title: 'Cannot Archive Assignment',
          message: `This assignment is currently attached to ${freshAssignment.classroom_count} classroom${freshAssignment.classroom_count > 1 ? 's' : ''}. To archive this assignment, you must first remove it from all classrooms. Go to Classroom Management and remove this assignment from the assigned classrooms.`
        })
        return
      }
      
      if (!confirm(`Are you sure you want to archive "${assignment.title}"?`)) {
        return
      }
      
      setArchivingId(assignment.id)
      await writingApi.archiveAssignment(assignment.id)
      await loadAssignments()
    } catch (err: any) {
      // Display the actual error message from the backend
      const errorMessage = err.response?.data?.detail || 'Failed to archive assignment'
      setErrorDialog({
        open: true,
        title: 'Archive Failed',
        message: errorMessage
      })
    } finally {
      setArchivingId(null)
    }
  }

  const handleRestore = async (assignment: WritingAssignment) => {
    try {
      setRestoringId(assignment.id)
      await writingApi.restoreAssignment(assignment.id)
      await loadAssignments()
    } catch (err) {
      alert('Failed to restore assignment')
    } finally {
      setRestoringId(null)
    }
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-4">
          <PencilSquareIcon className="h-8 w-8 text-orange-500" />
          <h1 className="text-3xl font-bold text-gray-900">Writing Assignments</h1>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => loadAssignments()}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            title="Refresh assignment list"
          >
            <ArrowPathIcon className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <Link
            href="/teacher/uma-write/create"
            className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
            Create New Assignment
          </Link>
        </div>
      </div>

      {/* Success Message */}
      {showSuccessMessage && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-green-800">
            ✓ Writing assignment created successfully! To assign it to classrooms, go to Classroom Management → Select a classroom → Manage Assignments.
          </p>
        </div>
      )}

      {/* Search and Filters */}
      <div className="mb-6 space-y-4">
        <div className="flex gap-4">
          <input
            type="text"
            placeholder="Search assignments..."
            value={search}
            onChange={handleSearchChange}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
        
        <div className="flex gap-4 items-center">
          <select
            value={filters.gradeLevel}
            onChange={(e) => handleFilterChange('gradeLevel', e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Grade Levels</option>
            <option value="Elementary (K-2)">Elementary (K-2)</option>
            <option value="Elementary (3-5)">Elementary (3-5)</option>
            <option value="Middle School (6-8)">Middle School (6-8)</option>
            <option value="High School (9-12)">High School (9-12)</option>
            <option value="College/Adult">College/Adult</option>
          </select>
          
          <select
            value={filters.subject}
            onChange={(e) => handleFilterChange('subject', e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Subjects</option>
            <option value="English Language Arts">English Language Arts</option>
            <option value="Science">Science</option>
            <option value="Social Studies">Social Studies</option>
            <option value="Mathematics">Mathematics</option>
            <option value="Foreign Language">Foreign Language</option>
            <option value="Arts">Arts</option>
            <option value="Other">Other</option>
          </select>
          
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.includeArchived}
              onChange={(e) => handleFilterChange('includeArchived', e.target.checked)}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700">Show archived</span>
          </label>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="text-center py-12">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* Assignments Grid */}
      {!loading && !error && data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {data.assignments.map((assignment) => (
              <div
                key={assignment.id}
                className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow ${
                  assignment.is_archived ? 'opacity-60' : ''
                }`}
              >
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
                    {assignment.title}
                  </h3>
                  {assignment.is_archived && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                      Archived
                    </span>
                  )}
                </div>
                
                <p className="text-gray-600 text-sm mb-4 line-clamp-3">
                  {assignment.prompt_text}
                </p>
                
                <div className="flex justify-between items-center text-sm text-gray-500 mb-4">
                  <span>{assignment.word_count_min}-{assignment.word_count_max} words</span>
                  <span>{assignment.classroom_count} classroom{assignment.classroom_count !== 1 ? 's' : ''}</span>
                </div>
                
                <div className="flex justify-between items-center">
                  <div className="flex space-x-2">
                    
                    {!assignment.is_archived ? (
                      <button
                        onClick={() => handleArchive(assignment)}
                        disabled={archivingId === assignment.id}
                        className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                      >
                        <ArchiveBoxArrowDownIcon className="h-5 w-5" />
                      </button>
                    ) : (
                      <button
                        onClick={() => handleRestore(assignment)}
                        disabled={restoringId === assignment.id}
                        className="p-2 text-gray-600 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors disabled:opacity-50"
                      >
                        <ArrowPathIcon className="h-5 w-5" />
                      </button>
                    )}
                  </div>
                  
                  <Link
                    href="/teacher/classrooms"
                    className="inline-flex items-center px-3 py-1 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors text-sm"
                  >
                    <ClipboardDocumentListIcon className="h-4 w-4 mr-1" />
                    Classrooms
                  </Link>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {data.total_pages > 1 && (
            <div className="mt-8 flex justify-center space-x-2">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              
              <span className="px-4 py-2 text-gray-700">
                Page {currentPage} of {data.total_pages}
              </span>
              
              <button
                onClick={() => setCurrentPage(Math.min(data.total_pages, currentPage + 1))}
                disabled={currentPage === data.total_pages}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}

          {/* Empty State */}
          {data.assignments.length === 0 && (
            <div className="text-center py-12">
              <PencilSquareIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No assignments found</h3>
              <p className="mt-1 text-sm text-gray-500">
                {search || filters.gradeLevel || filters.subject || filters.includeArchived
                  ? 'Try adjusting your filters'
                  : 'Get started by creating a new writing assignment'}
              </p>
              {!search && !filters.gradeLevel && !filters.subject && !filters.includeArchived && (
                <div className="mt-6">
                  <Link
                    href="/teacher/uma-write/create"
                    className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                  >
                    <PlusIcon className="h-5 w-5 mr-2" />
                    Create New Assignment
                  </Link>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Error Dialog */}
      <Dialog open={errorDialog.open} onOpenChange={(open) => setErrorDialog({ ...errorDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <div className="flex items-center space-x-2">
              <ExclamationTriangleIcon className="h-6 w-6 text-yellow-600" />
              <DialogTitle>{errorDialog.title}</DialogTitle>
            </div>
          </DialogHeader>
          <DialogDescription className="text-base">
            {errorDialog.message}
          </DialogDescription>
          <DialogFooter>
            <button
              onClick={() => setErrorDialog({ ...errorDialog, open: false })}
              className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary-500"
            >
              Got it
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}