'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import api from '@/lib/api'
import { UserGroupIcon, PlusIcon } from '@heroicons/react/24/outline'

interface Classroom {
  id: string
  name: string
  subject: string
  grade_level: string
  school_year: string
  student_count: number
  created_at: string
}

export default function ClassroomsPage() {
  const { user } = useAuth()
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchClassrooms()
  }, [])

  const fetchClassrooms = async () => {
    try {
      const response = await api.get('/v1/teacher/classrooms')
      setClassrooms(response.data)
    } catch (error) {
      console.error('Failed to fetch classrooms:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">My Classrooms</h1>
        <p className="text-gray-600">Manage your classrooms and student enrollments</p>
      </div>

      <div className="mb-6">
        <button className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
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
            <div key={classroom.id} className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{classroom.name}</h3>
              <p className="text-gray-600 text-sm mb-4">{classroom.subject}</p>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Grade Level:</span>
                  <span className="text-gray-900">{classroom.grade_level || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">School Year:</span>
                  <span className="text-gray-900">{classroom.school_year || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Students:</span>
                  <span className="text-gray-900">{classroom.student_count}</span>
                </div>
              </div>
              <div className="mt-4 flex space-x-2">
                <button className="flex-1 px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                  View Details
                </button>
                <button className="flex-1 px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                  Manage
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}