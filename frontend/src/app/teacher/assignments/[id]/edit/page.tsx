'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import TeacherGuard from '@/components/TeacherGuard'
import AssignmentEditor from '@/components/AssignmentEditor'
import { readingApi } from '@/lib/readingApi'
import { ReadingAssignment } from '@/types/reading'

export default function EditAssignmentPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const { user } = useAuth()
  const [assignment, setAssignment] = useState<ReadingAssignment | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (user) {
      loadAssignment()
    }
  }, [user, params.id])

  const loadAssignment = async () => {
    try {
      setLoading(true)
      const data = await readingApi.getAssignmentForEdit(params.id)
      setAssignment(data)
    } catch (err) {
      setError('Failed to load assignment')
      console.error('Error loading assignment:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async (content: string, editMode: 'text' | 'image', imageId?: string) => {
    try {
      if (editMode === 'text') {
        await readingApi.updateAssignmentContent(params.id, { raw_content: content })
        // Reload assignment to get updated chunks
        await loadAssignment()
      } else if (editMode === 'image' && imageId) {
        await readingApi.updateImageDescription(params.id, imageId, { ai_description: content })
        // Update local state with new description
        setAssignment(prev => {
          if (!prev) return prev
          return {
            ...prev,
            images: prev.images.map(img => {
              if (img.id === imageId) {
                // Try to preserve JSON structure if it exists
                try {
                  const existing = JSON.parse(img.ai_description || '{}')
                  if (existing.description !== undefined) {
                    // Update the description field in the JSON
                    existing.description = content
                    return { ...img, ai_description: JSON.stringify(existing) }
                  }
                } catch {
                  // Not JSON or parsing failed
                }
                // Fall back to plain text
                return { ...img, ai_description: content }
              }
              return img
            })
          }
        })
      }
    } catch (err) {
      console.error('Error saving:', err)
      throw err
    }
  }

  const handleDelete = async () => {
    try {
      await readingApi.deleteAssignment(params.id)
      router.push('/teacher/uma-read')
    } catch (err) {
      console.error('Error deleting assignment:', err)
      alert('Failed to delete assignment')
    }
  }

  if (loading) {
    return (
      <TeacherGuard>
        <div className="flex items-center justify-center h-screen">
          <div className="text-gray-500">Loading assignment...</div>
        </div>
      </TeacherGuard>
    )
  }

  if (error || !assignment) {
    return (
      <TeacherGuard>
        <div className="flex items-center justify-center h-screen">
          <div className="text-red-500">{error || 'Assignment not found'}</div>
        </div>
      </TeacherGuard>
    )
  }

  return (
    <TeacherGuard>
      <div className="h-screen flex flex-col">
        {/* Header */}
        <div className="bg-white border-b px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">Edit Assignment</h1>
              <p className="text-sm text-gray-600 mt-1">{assignment.assignment_title}</p>
            </div>
            <button
              onClick={() => router.push('/teacher/uma-read')}
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              ← Back to assignments
            </button>
          </div>
        </div>

        {/* Editor */}
        <div className="flex-1 overflow-hidden">
          <AssignmentEditor
            assignmentId={params.id}
            initialContent={assignment.raw_content}
            images={assignment.images || []}
            onSave={handleSave}
            onDelete={handleDelete}
          />
        </div>
      </div>
    </TeacherGuard>
  )
}