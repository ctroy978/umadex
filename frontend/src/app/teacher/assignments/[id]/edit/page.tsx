'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthSupabase } from '@/hooks/useAuthSupabase'
import AssignmentEditor from '@/components/AssignmentEditor'
import AssignmentMetadataEditor from '@/components/AssignmentMetadataEditor'
import { readingApi } from '@/lib/readingApi'
import { ReadingAssignment, ReadingAssignmentUpdate } from '@/types/reading'

export default function EditAssignmentPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const { user } = useAuthSupabase()
  const [assignment, setAssignment] = useState<ReadingAssignment | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editMode, setEditMode] = useState<'content' | 'metadata'>('content')

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

  const handleArchive = async () => {
    try {
      await readingApi.archiveAssignment(params.id)
      router.push('/teacher/uma-read')
    } catch (err) {
      console.error('Error archiving assignment:', err)
      alert('Failed to archive assignment')
    }
  }

  const handleMetadataSave = async (data: ReadingAssignmentUpdate) => {
    try {
      const updated = await readingApi.updateAssignment(params.id, data)
      setAssignment(updated)
      setEditMode('content')
    } catch (err) {
      console.error('Error saving metadata:', err)
      throw err
    }
  }

  if (loading) {
    return (
        <div className="flex items-center justify-center h-screen">
          <div className="text-gray-500">Loading assignment...</div>
        </div>
    )
  }

  if (error || !assignment) {
    return (
        <div className="flex items-center justify-center h-screen">
          <div className="text-red-500">{error || 'Assignment not found'}</div>
        </div>
    )
  }

  return (
      <div className="h-screen flex flex-col">
        {/* Header */}
        <div className="bg-white border-b px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">Edit Assignment</h1>
              <p className="text-sm text-gray-600 mt-1">{assignment.assignment_title}</p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex space-x-2">
                <button
                  onClick={() => setEditMode('content')}
                  className={`px-4 py-2 text-sm font-medium rounded-md ${
                    editMode === 'content'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Edit Content
                </button>
                <button
                  onClick={() => setEditMode('metadata')}
                  className={`px-4 py-2 text-sm font-medium rounded-md ${
                    editMode === 'metadata'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Edit Metadata
                </button>
              </div>
              <button
                onClick={() => router.push('/teacher/uma-read')}
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                ← Back to assignments
              </button>
            </div>
          </div>
        </div>

        {/* Editor */}
        <div className="flex-1 overflow-hidden">
          {editMode === 'content' ? (
            <AssignmentEditor
              assignmentId={params.id}
              initialContent={assignment.raw_content}
              images={assignment.images || []}
              onSave={handleSave}
              onArchive={handleArchive}
            />
          ) : (
            <AssignmentMetadataEditor
              assignment={assignment}
              onSave={handleMetadataSave}
              onCancel={() => setEditMode('content')}
            />
          )}
        </div>
      </div>
  )
}