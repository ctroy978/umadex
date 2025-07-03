'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { 
  PlusIcon, 
  MagnifyingGlassIcon,
  AcademicCapIcon,
  PencilSquareIcon,
  TrashIcon,
  ArrowPathIcon,
  EyeIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline'
import { umalectureApi } from '@/lib/umalectureApi'
import type { LectureAssignment } from '@/lib/umalectureApi'

const statusColors = {
  draft: 'bg-gray-100 text-gray-800',
  processing: 'bg-yellow-100 text-yellow-800',
  published: 'bg-green-100 text-green-800',
  archived: 'bg-red-100 text-red-800',
}

const statusIcons = {
  draft: PencilSquareIcon,
  processing: ClockIcon,
  published: CheckCircleIcon,
  archived: ExclamationCircleIcon,
}

export default function UMALecturePage() {
  const router = useRouter()
  const [lectures, setLectures] = useState<LectureAssignment[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadLectures()
  }, [statusFilter])

  const loadLectures = async () => {
    try {
      setLoading(true)
      const data = await umalectureApi.listLectures({
        status: statusFilter === 'all' ? undefined : statusFilter,
        search: searchTerm || undefined,
      })
      setLectures(data)
      setError(null)
    } catch (err) {
      console.error('Error loading lectures:', err)
      setError('Failed to load lectures')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    loadLectures()
  }

  const handleDelete = async (lectureId: string) => {
    if (!confirm('Are you sure you want to archive this lecture?')) return

    try {
      await umalectureApi.deleteLecture(lectureId)
      await loadLectures()
    } catch (err: any) {
      console.error('Error deleting lecture:', err)
      
      // Check for 400 error with specific message about classrooms
      if (err.response?.status === 400 && err.response?.data?.detail) {
        alert(err.response.data.detail)
      } else if (err.response?.data?.message) {
        // Some error responses might use 'message' instead of 'detail'
        alert(err.response.data.message)
      } else {
        alert('Failed to archive lecture')
      }
    }
  }

  const handleRestore = async (lectureId: string) => {
    try {
      await umalectureApi.restoreLecture(lectureId)
      await loadLectures()
    } catch (err) {
      console.error('Error restoring lecture:', err)
      alert('Failed to restore lecture')
    }
  }

  const filteredLectures = lectures.filter(lecture =>
    lecture.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lecture.subject.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <AcademicCapIcon className="h-8 w-8 text-red-500" />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">uMaLecture</h1>
              <p className="text-gray-600 mt-1">Create interactive lectures for your students</p>
            </div>
          </div>
          <Link
            href="/teacher/uma-lecture/create"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
            Create New Lecture
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-6 bg-white p-4 rounded-lg shadow-sm border border-gray-200">
        <div className="flex flex-col sm:flex-row gap-4">
          <form onSubmit={handleSearch} className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search lectures..."
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </form>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="all">All Status</option>
            <option value="draft">Draft</option>
            <option value="processing">Processing</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Lectures Grid */}
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <ArrowPathIcon className="h-8 w-8 text-gray-400 animate-spin" />
        </div>
      ) : filteredLectures.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <AcademicCapIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No lectures found</h3>
          <p className="mt-1 text-sm text-gray-500">
            {searchTerm ? 'Try adjusting your search terms' : 'Get started by creating a new lecture'}
          </p>
          {!searchTerm && (
            <div className="mt-6">
              <Link
                href="/teacher/uma-lecture/create"
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <PlusIcon className="h-5 w-5 mr-2" />
                Create New Lecture
              </Link>
            </div>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredLectures.map((lecture) => {
            const StatusIcon = statusIcons[lecture.status]
            return (
              <div
                key={lecture.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
                      {lecture.title}
                    </h3>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[lecture.status]}`}>
                      <StatusIcon className="h-3 w-3 mr-1" />
                      {lecture.status}
                    </span>
                  </div>

                  <div className="space-y-2 mb-4">
                    <p className="text-sm text-gray-600">
                      <span className="font-medium">Subject:</span> {lecture.subject}
                    </p>
                    <p className="text-sm text-gray-600">
                      <span className="font-medium">Grade:</span> {lecture.grade_level}
                    </p>
                    <p className="text-sm text-gray-600">
                      <span className="font-medium">Objectives:</span> {lecture.learning_objectives.length}
                    </p>
                  </div>

                  {lecture.processing_error && (
                    <div className="mb-4 p-2 bg-red-50 rounded text-xs text-red-700">
                      {lecture.processing_error}
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-4 border-t border-gray-200">
                    <div className="flex space-x-2">
                      {lecture.status === 'published' && (
                        <Link
                          href={`/teacher/uma-lecture/${lecture.id}`}
                          className="text-primary-600 hover:text-primary-700"
                          title="View"
                        >
                          <EyeIcon className="h-5 w-5" />
                        </Link>
                      )}
                      {(lecture.status === 'draft' || lecture.status === 'published') && (
                        <Link
                          href={`/teacher/uma-lecture/${lecture.id}/edit`}
                          className="text-gray-600 hover:text-gray-700"
                          title="Edit"
                        >
                          <PencilSquareIcon className="h-5 w-5" />
                        </Link>
                      )}
                      {lecture.status === 'archived' ? (
                        <button
                          onClick={() => handleRestore(lecture.id)}
                          className="text-green-600 hover:text-green-700"
                          title="Restore"
                        >
                          <ArrowPathIcon className="h-5 w-5" />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleDelete(lecture.id)}
                          className="text-red-600 hover:text-red-700"
                          title="Archive"
                        >
                          <TrashIcon className="h-5 w-5" />
                        </button>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">
                      {new Date(lecture.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}