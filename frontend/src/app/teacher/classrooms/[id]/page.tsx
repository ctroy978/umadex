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
  AssignmentInClassroom
} from '@/types/classroom'

export default function ClassroomDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { user } = useAuth()
  const classroomId = params.id as string

  const [classroom, setClassroom] = useState<ClassroomDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'students' | 'assignments'>('students')

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

  const handleManageAssignments = () => {
    router.push(`/teacher/classrooms/${classroomId}/assignments`)
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
      {activeTab === 'students' && (
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
      )}
      
      {activeTab === 'assignments' && (
        <div>
          <div className="mb-4">
            <button
              onClick={handleManageAssignments}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
            >
              <PlusIcon className="h-5 w-5 mr-2" />
              Manage Assignments ({classroom.assignment_count})
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
                {classroom.assignments.map((assignment, index) => (
                  <li key={`${assignment.assignment_id}-${index}`} className="px-6 py-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{assignment.title}</p>
                        <p className="text-sm text-gray-500 capitalize">{assignment.assignment_type}</p>
                        <div className="text-xs text-gray-400 mt-1">
                          <span>Assigned {new Date(assignment.assigned_at).toLocaleDateString()}</span>
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

    </div>
  )
}