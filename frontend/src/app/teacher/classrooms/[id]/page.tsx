'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { teacherClassroomApi } from '@/lib/classroomApi'
import { teacherApi } from '@/lib/teacherApi'
import {
  UserGroupIcon,
  ClipboardDocumentListIcon,
  ArrowLeftIcon,
  DocumentDuplicateIcon,
  TrashIcon,
  PlusIcon,
  ShieldExclamationIcon,
  ClockIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import type {
  ClassroomDetail,
  StudentInClassroom,
  AssignmentInClassroom
} from '@/types/classroom'
import TestScheduleManager from '@/components/teacher/TestScheduleManager'

export default function ClassroomDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { user } = useAuth()
  const classroomId = params.id as string

  const [classroom, setClassroom] = useState<ClassroomDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'students' | 'assignments' | 'security' | 'schedule'>('students')
  const [securityIncidents, setSecurityIncidents] = useState<any[]>([])
  const [lockedTests, setLockedTests] = useState<any[]>([])
  const [loadingSecurity, setLoadingSecurity] = useState(false)

  useEffect(() => {
    fetchClassroomDetails()
  }, [classroomId])

  useEffect(() => {
    if (activeTab === 'security') {
      fetchSecurityData()
    }
  }, [activeTab, classroomId])

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

  const fetchSecurityData = async () => {
    try {
      setLoadingSecurity(true)
      const data = await teacherApi.getClassroomSecurityIncidents(classroomId)
      setSecurityIncidents(data.incidents)
      
      // Group locked tests by test_attempt_id to avoid duplicates
      const lockedTestsMap = new Map()
      data.incidents.forEach(incident => {
        if (incident.test_locked && !lockedTestsMap.has(incident.test_attempt_id)) {
          // Count total violations for this test attempt
          const violations = data.incidents.filter(i => i.test_attempt_id === incident.test_attempt_id)
          lockedTestsMap.set(incident.test_attempt_id, {
            test_attempt_id: incident.test_attempt_id,
            student_name: incident.student_name,
            assignment_title: incident.assignment_title,
            locked_at: incident.created_at,
            locked_reason: incident.incident_type,
            violation_count: violations.length
          })
        }
      })
      setLockedTests(Array.from(lockedTestsMap.values()))
    } catch (error) {
      console.error('Failed to fetch security data:', error)
    } finally {
      setLoadingSecurity(false)
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

  const handleDeleteSecurityIncident = async (incidentId: string) => {
    if (!confirm('Are you sure you want to delete this security incident?')) return

    try {
      await teacherApi.deleteSecurityIncident(classroomId, incidentId)
      // Remove the incident from the local state
      setSecurityIncidents(prev => prev.filter(incident => incident.id !== incidentId))
    } catch (error) {
      console.error('Failed to delete security incident:', error)
      alert('Failed to delete security incident. Please try again.')
    }
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
          <button
            onClick={() => setActiveTab('security')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'security'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <ShieldExclamationIcon className="h-5 w-5 inline mr-2" />
            Test Security
            {lockedTests.length > 0 && (
              <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                {lockedTests.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('schedule')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'schedule'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <ClockIcon className="h-5 w-5 inline mr-2" />
            Test Schedule
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
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">{assignment.title}</p>
                        <p className="text-sm text-gray-500 capitalize">{assignment.assignment_type}</p>
                        <div className="text-xs text-gray-400 mt-1">
                          <span>Assigned {new Date(assignment.assigned_at).toLocaleDateString()}</span>
                          {assignment.start_date && (
                            <span className="ml-2">• Starts {new Date(assignment.start_date).toLocaleDateString()}</span>
                          )}
                          {assignment.end_date && (
                            <span className="ml-2">• Ends {new Date(assignment.end_date).toLocaleDateString()}</span>
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

      {activeTab === 'security' && (
        <div>
          {loadingSecurity ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Locked Tests Section */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Locked Tests ({lockedTests.length})
                </h3>
                {lockedTests.length === 0 ? (
                  <div className="text-center py-8">
                    <ShieldExclamationIcon className="h-12 w-12 mx-auto mb-3 text-green-400" />
                    <p className="text-gray-500">No locked tests - all students are on track!</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {lockedTests.map((lockedTest) => (
                      <div
                        key={lockedTest.test_attempt_id}
                        className="bg-red-50 border border-red-200 rounded-lg p-4"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-medium text-red-900">
                              {lockedTest.student_name}
                            </h4>
                            <p className="text-sm text-red-600">
                              {lockedTest.assignment_title}
                            </p>
                            <p className="text-xs text-red-500 mt-1">
                              Locked: {new Date(lockedTest.locked_at).toLocaleString()}
                            </p>
                          </div>
                          <div className="text-sm text-red-600 bg-white px-3 py-1 rounded border">
                            Use bypass codes in Settings
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Security Incidents Section */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Recent Security Incidents ({securityIncidents.length})
                  </h3>
                  <p className="text-sm text-gray-500">
                    Showing incidents from the last 30 days
                  </p>
                </div>
                {securityIncidents.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-gray-500">No security incidents reported</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Student
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Assignment
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Incident Type
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            When
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Status
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {securityIncidents.slice(0, 20).map((incident, index) => (
                          <tr key={index}>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                              {incident.student_name}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {incident.assignment_title}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800">
                                {incident.incident_type.replace('_', ' ')}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {new Date(incident.created_at).toLocaleString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {incident.test_locked ? (
                                <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                                  Test Locked
                                </span>
                              ) : incident.resulted_in_lock ? (
                                <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-orange-100 text-orange-800">
                                  Warning Given
                                </span>
                              ) : (
                                <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
                                  Monitored
                                </span>
                              )}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              <button
                                onClick={() => handleDeleteSecurityIncident(incident.id)}
                                className="text-red-600 hover:text-red-700"
                                title="Delete incident"
                              >
                                <XMarkIcon className="h-5 w-5" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {securityIncidents.length > 20 && (
                      <div className="mt-4 text-center">
                        <p className="text-sm text-gray-500">
                          Showing 20 of {securityIncidents.length} incidents
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'schedule' && (
        <TestScheduleManager classroomId={classroomId} />
      )}


    </div>
  )
}