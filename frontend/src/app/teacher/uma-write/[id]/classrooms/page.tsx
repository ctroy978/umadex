'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { PencilSquareIcon, UserGroupIcon, ArrowLeftIcon, CheckIcon } from '@heroicons/react/24/outline'
import { WritingAssignment } from '@/types/writing'
import { writingApi } from '@/lib/writingApi'

interface Classroom {
  id: string
  name: string
  class_code: string
  student_count: number
  has_assignment?: boolean
}

export default function WritingAssignmentClassroomsPage() {
  const params = useParams()
  const router = useRouter()
  const assignmentId = params.id as string
  
  const [assignment, setAssignment] = useState<WritingAssignment | null>(null)
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [selectedClassrooms, setSelectedClassrooms] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    loadData()
  }, [assignmentId])

  const loadData = async () => {
    try {
      setLoading(true)
      
      // Load assignment details
      const assignmentData = await writingApi.getAssignment(assignmentId)
      setAssignment(assignmentData)
      
      // For now, we'll mock the classroom data
      // TODO: Integrate with actual classroom API
      const mockClassrooms: Classroom[] = [
        { id: '1', name: 'English 101', class_code: 'ENG101', student_count: 25 },
        { id: '2', name: 'Creative Writing', class_code: 'CW2024', student_count: 18 },
        { id: '3', name: 'Advanced Composition', class_code: 'ADV456', student_count: 22 }
      ]
      setClassrooms(mockClassrooms)
      
    } catch (err) {
      setError('Failed to load data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const toggleClassroom = (classroomId: string) => {
    setSelectedClassrooms(prev => {
      const newSet = new Set(prev)
      if (newSet.has(classroomId)) {
        newSet.delete(classroomId)
      } else {
        newSet.add(classroomId)
      }
      return newSet
    })
  }

  const handleSave = async () => {
    setSaving(true)
    setError('')
    
    try {
      // TODO: Implement actual API call to attach classrooms
      console.log('Attaching to classrooms:', Array.from(selectedClassrooms))
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      router.push('/teacher/uma-write')
    } catch (err) {
      setError('Failed to attach classrooms')
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!assignment) {
    return (
      <div className="p-8">
        <p className="text-red-600">Assignment not found</p>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/teacher/uma-write"
          className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-2" />
          Back to Assignments
        </Link>
        
        <div className="flex items-center space-x-4">
          <PencilSquareIcon className="h-8 w-8 text-orange-500" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{assignment.title}</h1>
            <p className="text-gray-600 mt-1">Attach to Classrooms</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {/* Assignment Details */}
      <div className="bg-gray-50 rounded-lg p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Assignment Details</h2>
        <div className="space-y-2 text-sm">
          <p><span className="font-medium">Prompt:</span> {assignment.prompt_text.substring(0, 200)}...</p>
          <p><span className="font-medium">Word Count:</span> {assignment.word_count_min}-{assignment.word_count_max} words</p>
          {assignment.grade_level && <p><span className="font-medium">Grade Level:</span> {assignment.grade_level}</p>}
          {assignment.subject && <p><span className="font-medium">Subject:</span> {assignment.subject}</p>}
        </div>
      </div>

      {/* Classroom Selection */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Select Classrooms</h2>
        
        {classrooms.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 rounded-lg">
            <UserGroupIcon className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-gray-600">No classrooms available</p>
            <Link
              href="/teacher/classrooms"
              className="mt-4 inline-flex items-center text-primary-600 hover:text-primary-700"
            >
              Create a classroom first
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {classrooms.map((classroom) => (
              <div
                key={classroom.id}
                onClick={() => toggleClassroom(classroom.id)}
                className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                  selectedClassrooms.has(classroom.id)
                    ? 'border-primary-600 bg-primary-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900">{classroom.name}</h3>
                    <p className="text-sm text-gray-600">
                      Code: {classroom.class_code} • {classroom.student_count} students
                    </p>
                  </div>
                  <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${
                    selectedClassrooms.has(classroom.id)
                      ? 'border-primary-600 bg-primary-600'
                      : 'border-gray-300'
                  }`}>
                    {selectedClassrooms.has(classroom.id) && (
                      <CheckIcon className="h-4 w-4 text-white" />
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="mt-8 flex justify-between">
        <Link
          href="/teacher/uma-write"
          className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Skip for Now
        </Link>
        <button
          onClick={handleSave}
          disabled={saving || selectedClassrooms.size === 0}
          className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : `Attach to ${selectedClassrooms.size} Classroom${selectedClassrooms.size !== 1 ? 's' : ''}`}
        </button>
      </div>
    </div>
  )
}