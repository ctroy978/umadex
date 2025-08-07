'use client'

import { useState, useEffect, useCallback, useRef, Fragment } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuthSupabase } from '@/hooks/useAuthSupabase'
import { teacherClassroomApi } from '@/lib/classroomApi'
import { Dialog, Transition } from '@headlessui/react'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { formatAssignmentForAPI, getBackendType } from '@/utils/assignmentTypes'
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
  AvailableAssignmentsResponse,
  AssignmentSchedule,
  CheckAssignmentRemovalResponse
} from '@/types/classroom'
import { format } from 'date-fns'
import { CalendarIcon } from '@heroicons/react/24/outline'

const ASSIGNMENT_TYPES = [
  { value: 'all', label: 'All Types' },
  { value: 'UMARead', label: 'UMA Read' },
  { value: 'UMAVocab', label: 'UMA Vocabulary' },
  { value: 'UMADebate', label: 'UMA Debate' },
  { value: 'UMAWrite', label: 'UMA Write' },
  { value: 'UMALecture', label: 'UMA Lecture' },
  { value: 'UMATest', label: 'UMA Test' }
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
  const { user } = useAuthSupabase()
  const classroomId = params.id as string

  const [classroom, setClassroom] = useState<ClassroomDetail | null>(null)
  const [assignments, setAssignments] = useState<AvailableAssignment[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [originalIds, setOriginalIds] = useState<Set<string>>(new Set())
  const [schedules, setSchedules] = useState<Map<string, AssignmentSchedule>>(new Map())
  const [originalSchedules, setOriginalSchedules] = useState<Map<string, AssignmentSchedule>>(new Map())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [removalInfo, setRemovalInfo] = useState<CheckAssignmentRemovalResponse | null>(null)
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
      
      // Update selected IDs based on current assignments
      // This needs to happen for all pages and filter combinations to properly reflect the saved state
      const currentPageAssignedIds = new Set(
        response.assignments.filter(a => a.is_assigned).map(a => a.id)
      )
      
      // For non-filtered first load, completely reset the state
      if (pagination.page === 1 && filters.search === '' && filters.assignment_type === 'all' && 
          filters.grade_level === 'all' && filters.status === 'all') {
        // This is the initial load - set everything fresh
        setSelectedIds(currentPageAssignedIds)
        setOriginalIds(new Set(currentPageAssignedIds))
        
        // Initialize schedules for ALL assigned assignments
        const initialSchedules = new Map<string, AssignmentSchedule>()
        response.assignments.filter(a => a.is_assigned).forEach(assignment => {
          initialSchedules.set(assignment.id, {
            assignment_id: assignment.id,
            start_date: assignment.current_schedule?.start_date || null,
            end_date: assignment.current_schedule?.end_date || null
          })
        })
        setSchedules(new Map(initialSchedules))
        setOriginalSchedules(new Map(initialSchedules))
      } else {
        // For filtered views or subsequent pages, update selected state based on server response
        setSelectedIds(prev => {
          const newSelected = new Set(prev)
          
          // For each assignment on this page, update its selected state based on is_assigned
          response.assignments.forEach(assignment => {
            if (assignment.is_assigned) {
              newSelected.add(assignment.id)
            } else {
              newSelected.delete(assignment.id)
            }
          })
          
          return newSelected
        })
        
        // Update schedules for newly assigned items
        setSchedules(prev => {
          const newSchedules = new Map(prev)
          response.assignments.filter(a => a.is_assigned).forEach(assignment => {
            if (!newSchedules.has(assignment.id) || assignment.current_schedule) {
              newSchedules.set(assignment.id, {
                assignment_id: assignment.id,
                start_date: assignment.current_schedule?.start_date || null,
                end_date: assignment.current_schedule?.end_date || null
              })
            }
          })
          return newSchedules
        })
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
    setSelectedIds(prev => {
      const newSelected = new Set(prev)
      if (newSelected.has(assignmentId)) {
        newSelected.delete(assignmentId)
      } else {
        newSelected.add(assignmentId)
      }
      return newSelected
    })
    
    setSchedules(prev => {
      const newSchedules = new Map(prev)
      if (selectedIds.has(assignmentId)) {
        // Removing - delete schedule
        newSchedules.delete(assignmentId)
      } else {
        // Adding - set schedule with existing dates if available
        const assignment = assignments.find(a => a.id === assignmentId)
        newSchedules.set(assignmentId, {
          assignment_id: assignmentId,
          start_date: assignment?.current_schedule?.start_date || null,
          end_date: assignment?.current_schedule?.end_date || null
        })
      }
      return newSchedules
    })
  }

  const toggleAll = () => {
    const visibleIds = assignments.map(a => a.id)
    const allSelected = visibleIds.every(id => selectedIds.has(id))
    
    setSelectedIds(prev => {
      const newSelected = new Set(prev)
      if (allSelected) {
        visibleIds.forEach(id => newSelected.delete(id))
      } else {
        visibleIds.forEach(id => newSelected.add(id))
      }
      return newSelected
    })
    
    setSchedules(prev => {
      const newSchedules = new Map(prev)
      if (allSelected) {
        visibleIds.forEach(id => newSchedules.delete(id))
      } else {
        visibleIds.forEach(id => {
          if (!newSchedules.has(id)) {
            const assignment = assignments.find(a => a.id === id)
            newSchedules.set(id, {
              assignment_id: id,
              start_date: assignment?.current_schedule?.start_date || null,
              end_date: assignment?.current_schedule?.end_date || null
            })
          }
        })
      }
      return newSchedules
    })
  }

  const getChanges = () => {
    const added = Array.from(selectedIds).filter(id => !originalIds.has(id))
    const removed = Array.from(originalIds).filter(id => !selectedIds.has(id))
    
    // Check for date changes on existing assignments
    let dateChanges = false
    for (const id of Array.from(selectedIds)) {
      if (originalIds.has(id)) {
        const current = schedules.get(id)
        const original = originalSchedules.get(id)
        
        // Compare dates, treating null/undefined as equivalent
        const currentStart = current?.start_date || null
        const currentEnd = current?.end_date || null
        const originalStart = original?.start_date || null
        const originalEnd = original?.end_date || null
        
        if (currentStart !== originalStart || currentEnd !== originalEnd) {
          dateChanges = true
          break
        }
      }
    }
    
    return { added, removed, hasChanges: added.length > 0 || removed.length > 0 || dateChanges }
  }

  const updateSchedule = (assignmentId: string, field: 'start_date' | 'end_date', value: string | null) => {
    setSchedules(prev => {
      const newSchedules = new Map(prev)
      const current = newSchedules.get(assignmentId) || { assignment_id: assignmentId, start_date: null, end_date: null }
      newSchedules.set(assignmentId, {
        ...current,
        [field]: value
      })
      return newSchedules
    })
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const assignmentsToSave = Array.from(selectedIds).map(id => {
        const schedule = schedules.get(id) || { assignment_id: id, start_date: null, end_date: null }
        const assignment = assignments.find(a => a.id === id)
        return formatAssignmentForAPI(
          id,
          assignment?.assignment_type || assignment?.item_type || 'reading',
          schedule.start_date,
          schedule.end_date
        )
      })
      
      // Check if any students will be affected
      const removalCheck = await teacherClassroomApi.checkAssignmentRemoval(classroomId, {
        assignments: assignmentsToSave
      })
      
      if (removalCheck.total_students_affected > 0) {
        setRemovalInfo(removalCheck)
        setShowConfirmDialog(true)
        setSaving(false)
        return
      }
      
      // No students affected, proceed with save
      await teacherClassroomApi.updateClassroomAssignmentsAll(classroomId, {
        assignments: assignmentsToSave
      })
      
      // Update the original state to reflect saved changes
      setOriginalIds(new Set(selectedIds))
      setOriginalSchedules(new Map(schedules))
      
      // Force a complete refresh of assignments to get updated state
      // This ensures all assignments reflect their correct is_assigned status
      await fetchAssignments()
      
      // Show success message
      alert('Assignments saved successfully!')
    } catch (error: any) {
      console.error('Failed to save assignments:', error)
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to save assignments'
      alert(`Error: ${errorMessage}. Please try again.`)
    } finally {
      setSaving(false)
    }
  }

  const handleConfirmRemoval = async () => {
    setSaving(true)
    setShowConfirmDialog(false)
    try {
      const assignmentsToSave = Array.from(selectedIds).map(id => {
        const schedule = schedules.get(id) || { assignment_id: id, start_date: null, end_date: null }
        const assignment = assignments.find(a => a.id === id)
        return formatAssignmentForAPI(
          id,
          assignment?.assignment_type || assignment?.item_type || 'reading',
          schedule.start_date,
          schedule.end_date
        )
      })
      
      await teacherClassroomApi.updateClassroomAssignmentsAll(classroomId, {
        assignments: assignmentsToSave
      })
      
      // Update the original state to reflect saved changes
      setOriginalIds(new Set(selectedIds))
      setOriginalSchedules(new Map(schedules))
      
      // Force a complete refresh of assignments to get updated state
      // This ensures all assignments reflect their correct is_assigned status
      await fetchAssignments()
      
      // Show success message
      alert('Assignments saved successfully!')
    } catch (error: any) {
      console.error('Failed to save assignments:', error)
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to save assignments'
      alert(`Error: ${errorMessage}. Please try again.`)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    router.push(`/teacher/classrooms/${classroomId}`)
  }

  const { added, removed, hasChanges } = getChanges()
  const archivedCount = assignments.filter(a => a.is_archived && selectedIds.has(a.id)).length

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

        {/* Archived Assignments Warning */}
        {archivedCount > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 flex items-start">
            <ExclamationTriangleIcon className="h-5 w-5 text-amber-600 mt-0.5 mr-3 flex-shrink-0" />
            <div>
              <p className="text-sm text-amber-800 font-medium">
                {archivedCount} archived assignment{archivedCount > 1 ? 's' : ''} in this classroom
              </p>
              <p className="text-sm text-amber-700 mt-1">
                Students can still access these until you remove them.
              </p>
            </div>
          </div>
        )}

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
                {assignments.map((assignment) => {
                  const isSelected = selectedIds.has(assignment.id)
                  const schedule = schedules.get(assignment.id)
                  
                  
                  return (
                    <div
                      key={assignment.id}
                      className={`p-4 ${
                        isSelected ? 'bg-blue-50 border-l-4 border-blue-500' : 'hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-start">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleAssignment(assignment.id)}
                          className="mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                        />
                        <div className="ml-3 flex-1">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <h4 className="text-sm font-medium text-gray-900">
                                {assignment.assignment_title}
                                {assignment.is_archived && (
                                  <span className="ml-2 text-xs text-amber-600 bg-amber-100 px-2 py-0.5 rounded">
                                    Archived
                                  </span>
                                )}
                              </h4>
                              <p className="text-sm text-gray-600 mt-1">
                                {assignment.work_title}
                                {assignment.author && ` • By ${assignment.author}`}
                                {assignment.word_count && ` • ${assignment.word_count} words`}
                              </p>
                              <p className="text-xs text-gray-500 mt-1">
                                {assignment.assignment_type} • {assignment.grade_level}
                                {assignment.item_type === 'vocabulary' && ' • Vocabulary List'}
                              </p>
                              
                              {/* Date display and inputs - only shown when selected */}
                              {isSelected && (
                                <div className="mt-3 space-y-2">
                                  
                                  {/* Display current dates if set */}
                                  {(schedule?.start_date || schedule?.end_date) && (
                                    <div className="text-sm text-gray-600 bg-gray-100 rounded p-2">
                                      {schedule?.start_date && (
                                        <div>Start: {format(new Date(schedule.start_date), 'MMM d, yyyy h:mm a')}</div>
                                      )}
                                      {schedule?.end_date && (
                                        <div>End: {format(new Date(schedule.end_date), 'MMM d, yyyy h:mm a')}</div>
                                      )}
                                    </div>
                                  )}
                                  
                                  {/* Date input controls */}
                                  <div className="space-y-3">
                                    <div className="flex items-center gap-2">
                                      <CalendarIcon className="h-4 w-4 text-gray-400" />
                                      <label className="text-sm text-gray-600 w-16">Start:</label>
                                      <input
                                        type="date"
                                        value={schedule?.start_date ? new Date(schedule.start_date).toISOString().slice(0, 10) : ''}
                                        onChange={(e) => {
                                          if (e.target.value) {
                                            // Set to beginning of day in user's timezone
                                            const date = new Date(e.target.value + 'T00:00:00')
                                            updateSchedule(assignment.id, 'start_date', date.toISOString())
                                          } else {
                                            updateSchedule(assignment.id, 'start_date', null)
                                          }
                                        }}
                                        className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-primary-500"
                                      />
                                      {schedule?.start_date && (
                                        <select
                                          value={new Date(schedule.start_date).getHours().toString()}
                                          onChange={(e) => {
                                            const existingDate = new Date(schedule.start_date!)
                                            existingDate.setHours(parseInt(e.target.value), 0, 0, 0)
                                            updateSchedule(assignment.id, 'start_date', existingDate.toISOString())
                                          }}
                                          className="text-sm border border-gray-300 rounded px-2 py-1"
                                        >
                                          {Array.from({length: 24}, (_, i) => (
                                            <option key={i} value={i}>{i.toString().padStart(2, '0')}:00</option>
                                          ))}
                                        </select>
                                      )}
                                      {schedule?.start_date && (
                                        <button
                                          onClick={() => updateSchedule(assignment.id, 'start_date', null)}
                                          className="text-xs text-red-600 hover:text-red-800"
                                        >
                                          Clear
                                        </button>
                                      )}
                                    </div>
                                    <div className="flex items-center gap-2">
                                      <CalendarIcon className="h-4 w-4 text-gray-400" />
                                      <label className="text-sm text-gray-600 w-16">End:</label>
                                      <input
                                        type="date"
                                        value={schedule?.end_date ? new Date(schedule.end_date).toISOString().slice(0, 10) : ''}
                                        onChange={(e) => {
                                          if (e.target.value) {
                                            // Set to end of day (23:59) in user's timezone
                                            const date = new Date(e.target.value + 'T23:59:00')
                                            updateSchedule(assignment.id, 'end_date', date.toISOString())
                                          } else {
                                            updateSchedule(assignment.id, 'end_date', null)
                                          }
                                        }}
                                        className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-primary-500"
                                      />
                                      {schedule?.end_date && (
                                        <select
                                          value={new Date(schedule.end_date).getHours().toString()}
                                          onChange={(e) => {
                                            const existingDate = new Date(schedule.end_date!)
                                            existingDate.setHours(parseInt(e.target.value), 59, 59, 999)
                                            updateSchedule(assignment.id, 'end_date', existingDate.toISOString())
                                          }}
                                          className="text-sm border border-gray-300 rounded px-2 py-1"
                                        >
                                          {Array.from({length: 24}, (_, i) => (
                                            <option key={i} value={i}>{i.toString().padStart(2, '0')}:59</option>
                                          ))}
                                        </select>
                                      )}
                                      {schedule?.end_date && (
                                        <button
                                          onClick={() => updateSchedule(assignment.id, 'end_date', null)}
                                          className="text-xs text-red-600 hover:text-red-800"
                                        >
                                          Clear
                                        </button>
                                      )}
                                    </div>
                                    {schedule?.start_date && schedule?.end_date && 
                                     new Date(schedule.end_date) <= new Date(schedule.start_date) && (
                                      <span className="text-xs text-red-600">
                                        End date must be after start date
                                      </span>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                            <div className="ml-4 flex-shrink-0">
                              {assignment.is_assigned && !isSelected && (
                                <span className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
                                  Will be removed
                                </span>
                              )}
                              {!assignment.is_assigned && isSelected && (
                                <span className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded">
                                  Will be added
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
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

      {/* Confirmation Dialog */}
      <Transition appear show={showConfirmDialog} as={Fragment}>
        <Dialog as="div" className="relative z-50" onClose={() => setShowConfirmDialog(false)}>
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black bg-opacity-25" />
          </Transition.Child>

          <div className="fixed inset-0 overflow-y-auto">
            <div className="flex min-h-full items-center justify-center p-4 text-center">
              <Transition.Child
                as={Fragment}
                enter="ease-out duration-300"
                enterFrom="opacity-0 scale-95"
                enterTo="opacity-100 scale-100"
                leave="ease-in duration-200"
                leaveFrom="opacity-100 scale-100"
                leaveTo="opacity-0 scale-95"
              >
                <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="flex-shrink-0">
                      <ExclamationTriangleIcon className="h-6 w-6 text-amber-600" />
                    </div>
                    <Dialog.Title
                      as="h3"
                      className="text-lg font-medium leading-6 text-gray-900"
                    >
                      Students Will Lose Progress
                    </Dialog.Title>
                  </div>

                  <div className="mt-2">
                    <p className="text-sm text-gray-500">
                      {removalInfo?.total_students_affected} student{removalInfo?.total_students_affected === 1 ? ' is' : 's are'} currently working on assignment{removalInfo?.assignments_with_students.length === 1 ? '' : 's'} you're removing:
                    </p>
                    
                    <ul className="mt-3 space-y-2">
                      {removalInfo?.assignments_with_students.map((assignment) => (
                        <li key={assignment.assignment_id} className="text-sm text-gray-700 bg-gray-50 rounded p-2">
                          <span className="font-medium">{assignment.assignment_title}</span>
                          <span className="text-gray-500 ml-2">
                            ({assignment.student_count} student{assignment.student_count === 1 ? '' : 's'})
                          </span>
                        </li>
                      ))}
                    </ul>

                    <p className="mt-4 text-sm text-gray-500">
                      Removing these assignments will <span className="font-semibold text-gray-700">permanently delete</span> all student progress.
                    </p>
                  </div>

                  <div className="mt-6 flex gap-3 justify-end">
                    <button
                      type="button"
                      className="inline-flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
                      onClick={() => setShowConfirmDialog(false)}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="inline-flex justify-center rounded-md border border-transparent bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
                      onClick={handleConfirmRemoval}
                    >
                      Remove Anyway
                    </button>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </Dialog>
      </Transition>
    </div>
  )
}