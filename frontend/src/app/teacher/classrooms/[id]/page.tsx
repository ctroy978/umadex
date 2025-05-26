'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { teacherClassroomApi } from '@/lib/classroomApi'
import {
  UserGroupIcon,
  ClipboardDocumentListIcon,
  ArrowLeftIcon,
  DocumentDuplicateIcon,
  TrashIcon,
  PlusIcon
} from '@heroicons/react/24/outline'
import type {
  ClassroomDetail,
  StudentInClassroom,
  AssignmentInClassroom,
  AvailableAssignment
} from '@/types/classroom'

export default function ClassroomDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { user } = useAuth()
  const classroomId = params.id as string

  const [classroom, setClassroom] = useState<ClassroomDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'students' | 'assignments'>('students')
  const [showAssignmentModal, setShowAssignmentModal] = useState(false)
  const [availableAssignments, setAvailableAssignments] = useState<AvailableAssignment[]>([])
  const [selectedAssignments, setSelectedAssignments] = useState<Set<string>>(new Set())
  const [updateLoading, setUpdateLoading] = useState(false)

  useEffect(() => {
    fetchClassroomDetails()
  }, [classroomId])

  const fetchClassroomDetails = async () => {
    try {
      const data = await teacherClassroomApi.getClassroom(classroomId)
      setClassroom(data)
    } catch (error) {
      console.error('Failed to fetch classroom details:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCopyCode = () => {
    if (classroom) {
      navigator.clipboard.writeText(classroom.class_code)
      alert('Class code copied to clipboard!')
    }
  }

  const handleRemoveStudent = async (studentId: string) => {
    if (!confirm('Are you sure you want to remove this student from the classroom?')) return

    try {
      await teacherClassroomApi.removeStudent(classroomId, studentId)
      if (classroom) {
        setClassroom({
          ...classroom,
          students: classroom.students.filter(s => s.id !== studentId),
          student_count: classroom.student_count - 1
        })
      }
    } catch (error) {
      console.error('Failed to remove student:', error)
      alert('Failed to remove student. Please try again.')
    }
  }

  const handleManageAssignments = async () => {
    setShowAssignmentModal(true)
    try {
      const assignments = await teacherClassroomApi.getAvailableAssignments(classroomId)
      setAvailableAssignments(assignments)
      
      // Pre-select currently assigned items
      const assigned = new Set(assignments.filter(a => a.is_assigned).map(a => a.id))
      setSelectedAssignments(assigned)
    } catch (error) {
      console.error('Failed to fetch available assignments:', error)
    }
  }

  const handleUpdateAssignments = async () => {
    setUpdateLoading(true)
    try {
      const result = await teacherClassroomApi.updateClassroomAssignments(classroomId, {
        assignment_ids: Array.from(selectedAssignments)
      })
      
      // Refresh classroom details to get updated assignment list
      await fetchClassroomDetails()
      setShowAssignmentModal(false)
      
      alert(`Assignments updated! Added: ${result.added.length}, Removed: ${result.removed.length}`)
    } catch (error) {
      console.error('Failed to update assignments:', error)
      alert('Failed to update assignments. Please try again.')
    } finally {
      setUpdateLoading(false)
    }
  }

  const toggleAssignment = (assignmentId: string) => {
    const newSelected = new Set(selectedAssignments)
    if (newSelected.has(assignmentId)) {
      newSelected.delete(assignmentId)
    } else {
      newSelected.add(assignmentId)
    }
    setSelectedAssignments(newSelected)
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!classroom) {
    return (
      <div className="p-8 text-center">
        <p className="text-gray-500">Classroom not found</p>
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => router.push('/teacher/classrooms')}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-5 w-5 mr-2" />
          Back to Classrooms
        </button>
        
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">{classroom.name}</h1>
            <div className="flex items-center space-x-4">
              <div className="bg-gray-100 px-4 py-2 rounded-full flex items-center">
                <span className="text-sm font-medium text-gray-700">Class Code: </span>
                <span className="text-lg font-bold text-primary-600 ml-2">{classroom.class_code}</span>
                <button
                  onClick={handleCopyCode}
                  className="ml-3 text-gray-500 hover:text-gray-700"
                  title="Copy code"
                >
                  <DocumentDuplicateIcon className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
          
          <div className="flex space-x-4 text-sm">
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{classroom.student_count}</p>
              <p className="text-gray-600">Students</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{classroom.assignment_count}</p>
              <p className="text-gray-600">Assignments</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('students')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'students'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <UserGroupIcon className="h-5 w-5 inline mr-2" />
            Students
          </button>
          <button
            onClick={() => setActiveTab('assignments')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'assignments'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <ClipboardDocumentListIcon className="h-5 w-5 inline mr-2" />
            Assignments
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'students' ? (
        <div>
          {classroom.students.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <UserGroupIcon className="h-12 w-12 mx-auto mb-3 text-gray-400" />
              <p className="text-gray-500 mb-2">No students enrolled yet</p>
              <p className="text-sm text-gray-400">
                Share the class code <span className="font-semibold">{classroom.class_code}</span> with your students
              </p>
            </div>
          ) : (
            <div className="bg-white shadow overflow-hidden sm:rounded-md">
              <ul className="divide-y divide-gray-200">
                {classroom.students.map((student) => (
                  <li key={student.id} className="px-6 py-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{student.full_name}</p>
                        <p className="text-sm text-gray-500">{student.email}</p>
                        <p className="text-xs text-gray-400 mt-1">
                          Joined {new Date(student.joined_at).toLocaleDateString()}
                        </p>
                      </div>
                      <button
                        onClick={() => handleRemoveStudent(student.id)}
                        className="text-red-600 hover:text-red-700"
                        title="Remove student"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div>
          <div className="mb-4">
            <button
              onClick={handleManageAssignments}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
            >
              <PlusIcon className="h-5 w-5 mr-2" />
              Manage Assignments
            </button>
          </div>

          {classroom.assignments.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <ClipboardDocumentListIcon className="h-12 w-12 mx-auto mb-3 text-gray-400" />
              <p className="text-gray-500 mb-2">No assignments added yet</p>
              <p className="text-sm text-gray-400">Click "Manage Assignments" to add assignments to this classroom</p>
            </div>
          ) : (
            <div className="bg-white shadow overflow-hidden sm:rounded-md">
              <ul className="divide-y divide-gray-200">
                {classroom.assignments.map((assignment) => (
                  <li key={assignment.assignment_id} className="px-6 py-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{assignment.title}</p>
                        <p className="text-sm text-gray-500 capitalize">{assignment.assignment_type}</p>
                        <div className="text-xs text-gray-400 mt-1 space-x-4">
                          <span>Assigned {new Date(assignment.assigned_at).toLocaleDateString()}</span>
                          {assignment.due_date && (
                            <span>Due {new Date(assignment.due_date).toLocaleDateString()}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Assignment Selection Modal */}
      {showAssignmentModal && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Manage Assignments</h3>
            
            <div className="flex-1 overflow-y-auto mb-4">
              {availableAssignments.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No assignments available</p>
              ) : (
                <div className="space-y-2">
                  {availableAssignments.map((assignment) => (
                    <label
                      key={assignment.id}
                      className="flex items-center p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedAssignments.has(assignment.id)}
                        onChange={() => toggleAssignment(assignment.id)}
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      />
                      <div className="ml-3 flex-1">
                        <p className="text-sm font-medium text-gray-900">{assignment.title}</p>
                        <p className="text-xs text-gray-500">
                          {assignment.assignment_type} • Created {new Date(assignment.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
            
            <div className="flex justify-end space-x-3 pt-4 border-t">
              <button
                onClick={() => setShowAssignmentModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleUpdateAssignments}
                disabled={updateLoading}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50"
              >
                {updateLoading ? 'Updating...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}