'use client'

import { useState, useEffect } from 'react'
import { AssignmentImage } from '@/types/reading'

interface AssignmentEditorProps {
  assignmentId: string
  initialContent: string
  images: AssignmentImage[]
  onSave: (content: string, editMode: 'text' | 'image', imageId?: string) => Promise<void>
  onArchive: () => void
}

type EditMode = 'text' | 'image'

export default function AssignmentEditor({
  assignmentId,
  initialContent,
  images,
  onSave,
  onArchive
}: AssignmentEditorProps) {
  const [content, setContent] = useState(initialContent)
  const [editMode, setEditMode] = useState<EditMode>('text')
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [showArchiveModal, setShowArchiveModal] = useState(false)

  useEffect(() => {
    setContent(initialContent)
  }, [initialContent])

  const handleImageSelect = (image: AssignmentImage) => {
    if (hasUnsavedChanges) {
      if (!confirm('You have unsaved changes. Do you want to discard them?')) {
        return
      }
    }
    
    setEditMode('image')
    setSelectedImageId(image.id)
    
    // Parse AI description if it's JSON
    let description = ''
    if (image.ai_description) {
      try {
        const parsed = JSON.parse(image.ai_description)
        // If it's the full analysis object, extract the description
        if (parsed.description) {
          description = parsed.description
        } else {
          description = image.ai_description
        }
      } catch {
        // If parsing fails, use as-is
        description = image.ai_description
      }
    }
    
    setContent(description)
    setHasUnsavedChanges(false)
  }

  const handleBackToText = () => {
    if (hasUnsavedChanges) {
      if (!confirm('You have unsaved changes. Do you want to discard them?')) {
        return
      }
    }
    
    setEditMode('text')
    setSelectedImageId(null)
    setContent(initialContent)
    setHasUnsavedChanges(false)
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      if (editMode === 'text') {
        await onSave(content, 'text')
      } else if (editMode === 'image' && selectedImageId) {
        await onSave(content, 'image', selectedImageId)
      }
      setHasUnsavedChanges(false)
    } catch (error) {
      console.error('Error saving:', error)
      alert('Failed to save changes')
    } finally {
      setIsSaving(false)
    }
  }

  const handleArchive = () => {
    setShowArchiveModal(true)
  }

  const confirmArchive = () => {
    onArchive()
    setShowArchiveModal(false)
  }

  return (
    <div className="flex h-full">
      {/* Main Editor Area */}
      <div className="flex-1 flex flex-col">
        {/* Editor Header */}
        <div className="bg-white border-b px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h2 className="text-lg font-medium text-gray-900">
                {editMode === 'text' ? 'Editing Assignment Text' : `Editing Image Description`}
              </h2>
              {editMode === 'image' && selectedImageId && (
                <button
                  onClick={handleBackToText}
                  className="text-sm text-primary-600 hover:text-primary-700"
                >
                  ← Back to text
                </button>
              )}
            </div>
            <div className="flex items-center space-x-3">
              {hasUnsavedChanges && (
                <span className="text-sm text-amber-600">Unsaved changes</span>
              )}
              <button
                onClick={handleSave}
                disabled={!hasUnsavedChanges || isSaving}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSaving ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={handleArchive}
                className="px-4 py-2 text-sm font-medium text-white bg-gray-600 rounded-md hover:bg-gray-700"
              >
                Archive
              </button>
            </div>
          </div>
        </div>

        {/* Textarea */}
        <div className="flex-1 p-6">
          <textarea
            value={content}
            onChange={(e) => {
              setContent(e.target.value)
              setHasUnsavedChanges(true)
            }}
            className="w-full h-full p-4 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none font-mono text-sm"
            placeholder={editMode === 'text' 
              ? "Enter your assignment text here. Use <chunk></chunk> tags to define reading chunks and <important></important> tags for important sections."
              : "Enter the image description (minimum 50 characters)"
            }
          />
        </div>
      </div>

      {/* Sidebar with Images */}
      {images.length > 0 && (
        <div className="w-80 bg-gray-50 border-l overflow-y-auto">
          <div className="p-4">
            <h3 className="text-sm font-medium text-gray-900 mb-4">Assignment Images</h3>
            <div className="space-y-3">
              {images.map((image) => (
                <div
                  key={image.id}
                  onClick={() => handleImageSelect(image)}
                  className={`cursor-pointer rounded-lg overflow-hidden border-2 transition-all ${
                    editMode === 'image' && selectedImageId === image.id
                      ? 'border-primary-500 shadow-lg'
                      : 'border-transparent hover:border-gray-300'
                  }`}
                >
                  <img
                    src={`http://localhost${image.thumbnail_url || image.display_url}`}
                    alt={image.image_tag || 'Assignment image'}
                    className="w-full h-32 object-cover"
                  />
                  <div className="p-2 bg-white">
                    <p className="text-xs font-medium text-gray-700">{image.image_tag}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {(() => {
                        if (!image.ai_description) return 'No description yet'
                        try {
                          const parsed = JSON.parse(image.ai_description)
                          return parsed.description ? 'AI generated' : 'Has description'
                        } catch {
                          return 'Has description'
                        }
                      })()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Archive Confirmation Modal */}
      {showArchiveModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Archive Assignment</h3>
            <p className="text-gray-600 mb-6">
              Archive this assignment? You can restore it later from the archived view.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowArchiveModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmArchive}
                className="px-4 py-2 text-sm font-medium text-white bg-gray-600 rounded-md hover:bg-gray-700"
              >
                Archive Assignment
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}