'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { teacherClassroomApi } from '@/lib/classroomApi'
// Simple debounce implementation
const debounce = (func: Function, wait: number) => {
  let timeout: NodeJS.Timeout
  return (...args: any[]) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}
import {
  ArrowLeftIcon,
  MagnifyingGlassIcon,
  CheckIcon
} from '@heroicons/react/24/outline'
import type {
  ClassroomDetail,
  AvailableAssignment,
  AvailableAssignmentsResponse
} from '@/types/classroom'

const ASSIGNMENT_TYPES = [
  { value: 'all', label: 'All Types' },
  { value: 'UMARead', label: 'UMA Read' },
  { value: 'UMAVocab', label: 'UMA Vocabulary' },
  { value: 'UMADebate', label: 'UMA Debate' },
  { value: 'UMAWrite', label: 'UMA Write' },
  { value: 'UMALecture', label: 'UMA Lecture' }
]

const GRADE_LEVELS = [
  { value: 'all', label: 'All Grades' },
  { value: 'K-2', label: 'K-2' },
  { value: '3-5', label: '3-5' },
  { value: '6-8', label: '6-8' },
  { value: '9-10', label: '9-10' },
  { value: '11-12', label: '11-12' },
  { value: 'College', label: 'College' },
  { value: 'Adult Education', label: 'Adult Education' }
]

const STATUS_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'assigned', label: 'Assigned' },
  { value: 'unassigned', label: 'Not Assigned' },
  { value: 'published', label: 'Published' }
]

export default function AssignmentManagementPage() {
  const params = useParams()
  const router = useRouter()
  const { user } = useAuth()
  const classroomId = params.id as string

  const [classroom, setClassroom] = useState<ClassroomDetail | null>(null)
  const [assignments, setAssignments] = useState<AvailableAssignment[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [originalIds, setOriginalIds] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [filters, setFilters] = useState({
    search: '',
    assignment_type: 'all',
    grade_level: 'all',
    status: 'all'
  })
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 20,
    total_count: 0
  })

  // Fetch classroom details
  useEffect(() => {
    fetchClassroomDetails()
  }, [classroomId])

  // Fetch assignments when filters change
  useEffect(() => {
    fetchAssignments()
  }, [classroomId, filters, pagination.page])

  const fetchClassroomDetails = async () => {
    try {
      const data = await teacherClassroomApi.getClassroom(classroomId)
      setClassroom(data)
    } catch (error) {
      console.error('Failed to fetch classroom details:', error)
      router.push('/teacher/classrooms')
    }
  }

  const fetchAssignments = async () => {
    try {
      setLoading(true)
      const response = await teacherClassroomApi.getClassroomAvailableAssignments(classroomId, {
        search: filters.search || undefined,
        assignment_type: filters.assignment_type !== 'all' ? filters.assignment_type : undefined,
        grade_level: filters.grade_level !== 'all' ? filters.grade_level : undefined,
        status: filters.status !== 'all' ? filters.status : undefined,
        page: pagination.page,
        per_page: pagination.per_page
      })
      
      setAssignments(response.assignments)
      setPagination(prev => ({ ...prev, total_count: response.total_count }))
      
      // Initialize selected IDs on first load
      if (pagination.page === 1 && filters.search === '' && filters.assignment_type === 'all' && 
          filters.grade_level === 'all' && filters.status === 'all') {
        const assignedIds = new Set(response.assignments.filter(a => a.is_assigned).map(a => a.id))
        setSelectedIds(assignedIds)
        setOriginalIds(assignedIds)
      }
    } catch (error) {
      console.error('Failed to fetch assignments:', error)
    } finally {
      setLoading(false)
    }
  }

  // Debounced search
  const debouncedSearch = useCallback(
    debounce((searchTerm: string) => {
      setFilters(prev => ({ ...prev, search: searchTerm }))
      setPagination(prev => ({ ...prev, page: 1 }))
    }, 500),
    []
  )

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setPagination(prev => ({ ...prev, page: 1 }))
  }

  const toggleAssignment = (assignmentId: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(assignmentId)) {
      newSelected.delete(assignmentId)
    } else {
      newSelected.add(assignmentId)
    }
    setSelectedIds(newSelected)
  }

  const toggleAll = () => {
    const visibleIds = assignments.map(a => a.id)
    const allSelected = visibleIds.every(id => selectedIds.has(id))
    
    const newSelected = new Set(selectedIds)
    if (allSelected) {
      visibleIds.forEach(id => newSelected.delete(id))
    } else {
      visibleIds.forEach(id => newSelected.add(id))
    }
    setSelectedIds(newSelected)
  }

  const getChanges = () => {
    const added = [...selectedIds].filter(id => !originalIds.has(id))
    const removed = [...originalIds].filter(id => !selectedIds.has(id))
    return { added, removed, hasChanges: added.length > 0 || removed.length > 0 }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const assignmentIds = Array.from(selectedIds)
      await teacherClassroomApi.updateClassroomAssignments(classroomId, {
        assignment_ids: assignmentIds
      })
      router.push(`/teacher/classrooms/${classroomId}`)
    } catch (error) {
      console.error('Failed to save assignments:', error)
      alert('Failed to save assignments. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    router.push(`/teacher/classrooms/${classroomId}`)
  }

  const { added, removed, hasChanges } = getChanges()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4 flex items-center justify-between">
            <div className="flex items-center">
              <button
                onClick={handleCancel}
                className="mr-4 text-gray-500 hover:text-gray-700"
              >
                <ArrowLeftIcon className="h-5 w-5" />
              </button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  Manage Assignments: {classroom?.name}
                </h1>
                <p className="text-sm text-gray-500 mt-1">
                  {selectedIds.size} assignments selected
                  {hasChanges && (
                    <span className="ml-2 text-amber-600">
                      ({added.length} to add, {removed.length} to remove)
                    </span>
                  )}
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={handleCancel}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !hasChanges}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="md:col-span-2">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search assignments..."
                  onChange={(e) => debouncedSearch(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                />
                <MagnifyingGlassIcon className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
              </div>
            </div>
            
            <select
              value={filters.assignment_type}
              onChange={(e) => handleFilterChange('assignment_type', e.target.value)}
              className="block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-primary-500 focus:border-primary-500 rounded-md"
            >
              {ASSIGNMENT_TYPES.map(type => (
                <option key={type.value} value={type.value}>{type.label}</option>
              ))}
            </select>
            
            <select
              value={filters.grade_level}
              onChange={(e) => handleFilterChange('grade_level', e.target.value)}
              className="block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-primary-500 focus:border-primary-500 rounded-md"
            >
              {GRADE_LEVELS.map(grade => (
                <option key={grade.value} value={grade.value}>{grade.label}</option>
              ))}
            </select>
            
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-primary-500 focus:border-primary-500 rounded-md"
            >
              {STATUS_OPTIONS.map(status => (
                <option key={status.value} value={status.value}>{status.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Assignment List */}
        <div className="bg-white rounded-lg shadow">
          {loading ? (
            <div className="p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
              <p className="mt-4 text-gray-500">Loading assignments...</p>
            </div>
          ) : assignments.length === 0 ? (
            <div className="p-12 text-center">
              <p className="text-gray-500">No assignments match your filters</p>
              <p className="text-sm text-gray-400 mt-2">Try adjusting your search criteria</p>
            </div>
          ) : (
            <>
              {/* Select All */}
              <div className="px-6 py-3 border-b border-gray-200">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={assignments.every(a => selectedIds.has(a.id))}
                    onChange={toggleAll}
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <span className="ml-3 text-sm font-medium text-gray-700">
                    Select All ({assignments.length} visible)
                  </span>
                </label>
              </div>
              
              {/* Assignment Items */}
              <div className="divide-y divide-gray-200">
                {assignments.map((assignment) => (
                  <label
                    key={assignment.id}
                    className="flex items-start p-4 hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.has(assignment.id)}
                      onChange={() => toggleAssignment(assignment.id)}
                      className="mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    />
                    <div className="ml-3 flex-1">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900">
                            {assignment.assignment_title}
                          </h4>
                          <p className="text-sm text-gray-600 mt-1">
                            {assignment.work_title}
                            {assignment.author && ` • By ${assignment.author}`}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            {assignment.assignment_type} • {assignment.grade_level} • 
                            <span className={`ml-1 ${
                              assignment.status === 'published' ? 'text-green-600' : 'text-amber-600'
                            }`}>
                              {assignment.status}
                            </span>
                          </p>
                        </div>
                        {assignment.is_assigned && !selectedIds.has(assignment.id) && (
                          <span className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
                            Will be removed
                          </span>
                        )}
                        {!assignment.is_assigned && selectedIds.has(assignment.id) && (
                          <span className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded">
                            Will be added
                          </span>
                        )}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
              
              {/* Pagination */}
              {pagination.total_count > pagination.per_page && (
                <div className="px-6 py-3 border-t border-gray-200 flex items-center justify-between">
                  <p className="text-sm text-gray-700">
                    Showing {((pagination.page - 1) * pagination.per_page) + 1} to{' '}
                    {Math.min(pagination.page * pagination.per_page, pagination.total_count)} of{' '}
                    {pagination.total_count} assignments
                  </p>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => setPagination(prev => ({ ...prev, page: prev.page - 1 }))}
                      disabled={pagination.page === 1}
                      className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))}
                      disabled={pagination.page * pagination.per_page >= pagination.total_count}
                      className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}