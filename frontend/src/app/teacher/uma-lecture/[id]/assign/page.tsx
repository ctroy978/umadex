'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { 
  ChevronLeft,
  Loader,
  Save,
  AlertCircle,
  Users,
  Calendar,
  Clock,
  CheckCircle
} from 'lucide-react'
import { umalectureApi } from '@/lib/umalectureApi'
import { teacherApi } from '@/lib/teacherApi'
import { teacherClassroomApi } from '@/lib/classroomApi'
import type { LectureAssignment } from '@/lib/umalectureApi'
import type { Classroom } from '@/lib/teacherApi'

export default function AssignLecturePage() {
  const router = useRouter()
  const params = useParams()
  const lectureId = params.id as string

  const [lecture, setLecture] = useState<LectureAssignment | null>(null)
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [selectedClassrooms, setSelectedClassrooms] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  useEffect(() => {
    fetchData()
  }, [lectureId])

  const fetchData = async () => {
    try {
      const [lectureData, classroomsData] = await Promise.all([
        umalectureApi.getLecture(lectureId),
        teacherApi.getClassrooms()
      ])
      
      setLecture(lectureData)
      setClassrooms(classroomsData)
      
      // Set default dates
      const today = new Date()
      setStartDate(today.toISOString().split('T')[0])
      
      const twoWeeksLater = new Date(today)
      twoWeeksLater.setDate(twoWeeksLater.getDate() + 14)
      setEndDate(twoWeeksLater.toISOString().split('T')[0])
    } catch (err) {
      setError('Failed to load data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const toggleClassroom = (classroomId: string) => {
    const newSelected = new Set(selectedClassrooms)
    if (newSelected.has(classroomId)) {
      newSelected.delete(classroomId)
    } else {
      newSelected.add(classroomId)
    }
    setSelectedClassrooms(newSelected)
  }

  const handleAssign = async () => {
    if (selectedClassrooms.size === 0) {
      setError('Please select at least one classroom')
      return
    }
    
    setSaving(true)
    setError(null)
    
    try {
      // Convert dates to ISO format with time
      const startDateTime = startDate ? new Date(startDate + 'T00:00:00').toISOString() : null
      const endDateTime = endDate ? new Date(endDate + 'T23:59:59').toISOString() : null
      
      // Use the standard classroom assignment API with scheduling
      for (const classroomId of selectedClassrooms) {
        await teacherClassroomApi.updateClassroomAssignmentsAll(classroomId, {
          assignments: [{
            assignment_id: lectureId,
            assignment_type: 'UMALecture',
            start_date: startDateTime,
            end_date: endDateTime
          }]
        })
      }
      
      setSuccess(true)
      setTimeout(() => {
        router.push(`/teacher/uma-lecture/${lectureId}/edit`)
      }, 1500)
    } catch (err) {
      setError('Failed to assign lecture to classrooms')
      console.error(err)
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!lecture) {
    return (
      <div className="container mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          Lecture not found
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      {/* Header */}
      <div className="mb-6">
        <Link
          href={`/teacher/uma-lecture/${lectureId}/edit`}
          className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Back to Lecture
        </Link>
        
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Assign Lecture to Classrooms
        </h1>
        <p className="text-gray-600">
          Select which classrooms should receive this interactive lecture
        </p>
      </div>

      {/* Status Messages */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-red-800 flex items-start">
          <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
          {error}
        </div>
      )}
      
      {success && (
        <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4 text-green-800 flex items-start">
          <CheckCircle className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
          Successfully assigned lecture! Redirecting...
        </div>
      )}

      {/* Lecture Info */}
      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <h2 className="font-semibold text-lg mb-2">{lecture.title}</h2>
        <div className="text-sm text-gray-600">
          <span>{lecture.subject}</span>
          <span className="mx-2">•</span>
          <span>{lecture.grade_level}</span>
        </div>
      </div>

      {/* Date Selection */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h3 className="font-medium text-lg mb-4 flex items-center">
          <Calendar className="w-5 h-5 mr-2 text-gray-600" />
          Assignment Dates
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              End Date (Optional)
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              min={startDate}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
        </div>
        
        <p className="mt-3 text-sm text-gray-600 flex items-start">
          <Clock className="w-4 h-4 mr-1 mt-0.5 flex-shrink-0" />
          Students can access the lecture between these dates. Leave end date empty for no deadline.
        </p>
      </div>

      {/* Classroom Selection */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h3 className="font-medium text-lg mb-4 flex items-center">
          <Users className="w-5 h-5 mr-2 text-gray-600" />
          Select Classrooms ({selectedClassrooms.size} selected)
        </h3>
        
        {classrooms.length === 0 ? (
          <p className="text-gray-600 text-center py-8">
            No classrooms found. Create a classroom first.
          </p>
        ) : (
          <div className="space-y-2">
            {classrooms.map(classroom => (
              <label
                key={classroom.id}
                className={`block p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                  selectedClassrooms.has(classroom.id)
                    ? 'border-primary bg-primary-light'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={selectedClassrooms.has(classroom.id)}
                    onChange={() => toggleClassroom(classroom.id)}
                    className="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary"
                  />
                  
                  <div className="ml-3 flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium">{classroom.name}</h4>
                      <span className="text-sm text-gray-500">
                        {classroom.student_count || 0} students
                      </span>
                    </div>
                    {classroom.description && (
                      <p className="text-sm text-gray-600 mt-1">
                        {classroom.description}
                      </p>
                    )}
                  </div>
                </div>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex justify-between items-center">
        <Link
          href={`/teacher/uma-lecture/${lectureId}/edit`}
          className="text-gray-600 hover:text-gray-900"
        >
          Cancel
        </Link>
        
        <button
          onClick={handleAssign}
          disabled={selectedClassrooms.size === 0 || saving}
          className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center"
        >
          {saving ? (
            <>
              <Loader className="w-4 h-4 mr-2 animate-spin" />
              Assigning...
            </>
          ) : (
            <>
              <Users className="w-4 h-4 mr-2" />
              Assign to {selectedClassrooms.size} Classroom{selectedClassrooms.size !== 1 ? 's' : ''}
            </>
          )}
        </button>
      </div>
    </div>
  )
}