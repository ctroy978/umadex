'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthSupabase } from '@/hooks/useAuthSupabase'
import { teacherClassroomApi } from '@/lib/classroomApi'
import { UserGroupIcon, PlusIcon, AcademicCapIcon, ClipboardDocumentListIcon } from '@heroicons/react/24/outline'
import type { Classroom, ClassroomCreateRequest } from '@/types/classroom'

export default function ClassroomsPage() {
  const { user } = useAuthSupabase()
  const router = useRouter()
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createLoading, setCreateLoading] = useState(false)
  const [classroomName, setClassroomName] = useState('')

  useEffect(() => {
    fetchClassrooms()
  }, [])

  const fetchClassrooms = async () => {
    try {
      const data = await teacherClassroomApi.listClassrooms()
      setClassrooms(data)
    } catch (error) {
      console.error('Failed to fetch classrooms:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateClassroom = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!classroomName.trim()) return

    setCreateLoading(true)
    try {
      const newClassroom = await teacherClassroomApi.createClassroom({ name: classroomName })
      setClassrooms([newClassroom, ...classrooms])
      setShowCreateModal(false)
      setClassroomName('')
      
      // Show success message with class code
      alert(`Classroom created successfully!\nClass Code: ${newClassroom.class_code}\n\nShare this code with your students.`)
    } catch (error) {
      console.error('Failed to create classroom:', error)
      alert('Failed to create classroom. Please try again.')
    } finally {
      setCreateLoading(false)
    }
  }

  const handleClassroomClick = (classroomId: string) => {
    router.push(`/teacher/classrooms/${classroomId}`)
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">My Classrooms</h1>
        <p className="text-gray-600">Manage your classrooms and student enrollments</p>
      </div>

      <div className="mb-6">
        <button 
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          Create New Classroom
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : classrooms.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <UserGroupIcon className="h-12 w-12 mx-auto mb-3 text-gray-400" />
          <p className="text-gray-500 mb-4">No classrooms yet</p>
          <p className="text-sm text-gray-400">Create your first classroom to get started</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {classrooms.map((classroom) => (
            <div 
              key={classroom.id} 
              className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6 cursor-pointer"
              onClick={() => handleClassroomClick(classroom.id)}
            >
              <div className="mb-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-1">{classroom.name}</h3>
                <div className="bg-gray-100 inline-block px-3 py-1 rounded-full">
                  <span className="text-sm font-medium text-gray-700">Code: {classroom.class_code}</span>
                </div>
              </div>
              
              <div className="space-y-3">
                <div className="flex items-center text-gray-600">
                  <UserGroupIcon className="h-5 w-5 mr-2" />
                  <span className="text-sm">{classroom.student_count} Students</span>
                </div>
                <div className="flex items-center text-gray-600">
                  <ClipboardDocumentListIcon className="h-5 w-5 mr-2" />
                  <span className="text-sm">{classroom.assignment_count} Assignments</span>
                </div>
              </div>
              
              <div className="mt-4 pt-4 border-t">
                <button 
                  className="w-full px-3 py-2 text-sm font-medium text-primary-600 hover:text-primary-700"
                  onClick={(e) => {
                    e.stopPropagation()
                    handleClassroomClick(classroom.id)
                  }}
                >
                  Manage Classroom →
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Classroom Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Classroom</h3>
            <form onSubmit={handleCreateClassroom}>
              <div className="mb-4">
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                  Classroom Name
                </label>
                <input
                  type="text"
                  id="name"
                  value={classroomName}
                  onChange={(e) => setClassroomName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                  placeholder="e.g., English 101, Math Period 3"
                  required
                  autoFocus
                />
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false)
                    setClassroomName('')
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50"
                >
                  {createLoading ? 'Creating...' : 'Create Classroom'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}