'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { 
  AcademicCapIcon,
  ArrowLeftIcon,
  PhotoIcon,
  XMarkIcon,
  ArrowPathIcon,
  InformationCircleIcon,
  SparklesIcon
} from '@heroicons/react/24/outline'
import { umalectureApi } from '@/lib/umalectureApi'
import type { LectureAssignment, LectureImage } from '@/lib/umalectureApi'

const OUTLINE_EXAMPLE = `Topic: Photosynthesis
- Basics
  - What is photosynthesis?
  - Why is it important?
- Process Details
  - Light-dependent reactions
  - Light-independent reactions
- Real-World Applications
  - In agriculture
  - In renewable energy`

interface ImageUpload {
  id: string
  file: File
  preview: string
  nodeId: string
  description: string
  uploading?: boolean
  uploaded?: boolean
  error?: string
}

export default function CreateLectureContentPage() {
  const router = useRouter()
  const params = useParams()
  const lectureId = params.id as string
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const [lecture, setLecture] = useState<LectureAssignment | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const [outline, setOutline] = useState('')
  const [imageUploads, setImageUploads] = useState<ImageUpload[]>([])
  const [uploadedImages, setUploadedImages] = useState<LectureImage[]>([])
  
  // Extract topics from outline for image association
  const extractedTopics = outline
    .split('\n')
    .map((line, index, lines) => {
      const trimmed = line.trim()
      const originalIndent = line.length - trimmed.length
      
      // Skip empty lines or sub-items
      if (!trimmed || trimmed.startsWith('-') || trimmed.startsWith('*') || trimmed.startsWith('•')) {
        return null
      }
      
      // Check if next line is more indented (making this a topic)
      if (index + 1 < lines.length) {
        const nextLine = lines[index + 1]
        const nextTrimmed = nextLine.trim()
        const nextIndent = nextLine.length - nextTrimmed.length
        
        // This is a topic if next line is more indented or starts with a bullet
        if (nextIndent > originalIndent || nextTrimmed.startsWith('-') || nextTrimmed.startsWith('*')) {
          return trimmed.replace(':', '')
        }
      }
      
      // Also include lines that look like topics (no indent, not too short)
      if (originalIndent === 0 && trimmed.length > 3) {
        return trimmed.replace(':', '')
      }
      
      return null
    })
    .filter(topic => topic !== null)

  useEffect(() => {
    loadLecture()
  }, [lectureId])

  const loadLecture = async () => {
    try {
      setLoading(true)
      const data = await umalectureApi.getLecture(lectureId)
      setLecture(data)
      setOutline(data.topic_outline || '')
      
      // Load existing images
      const images = await umalectureApi.listImages(lectureId)
      setUploadedImages(images)
    } catch (err) {
      console.error('Error loading lecture:', err)
      setError('Failed to load lecture')
    } finally {
      setLoading(false)
    }
  }

  const handleOutlineChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setOutline(e.target.value)
  }

  const handleOutlineKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault()
      const textarea = e.currentTarget
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const value = textarea.value
      
      // Insert tab character (or spaces)
      const tabChar = '  ' // Using 2 spaces instead of tab for better compatibility
      setOutline(value.substring(0, start) + tabChar + value.substring(end))
      
      // Move cursor after the inserted tab
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + tabChar.length
      }, 0)
    }
  }

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    const newUploads: ImageUpload[] = []
    
    files.forEach(file => {
      if (file.type.startsWith('image/') && file.size <= 5 * 1024 * 1024) {
        const reader = new FileReader()
        reader.onloadend = () => {
          newUploads.push({
            id: `temp-${Date.now()}-${Math.random()}`,
            file,
            preview: reader.result as string,
            nodeId: '',
            description: ''
          })
          
          if (newUploads.length === files.length) {
            setImageUploads([...imageUploads, ...newUploads])
          }
        }
        reader.readAsDataURL(file)
      }
    })
  }

  const handleImageUpdate = (id: string, field: 'nodeId' | 'description', value: string) => {
    setImageUploads(imageUploads.map(img => 
      img.id === id ? { ...img, [field]: value } : img
    ))
  }

  const handleImageRemove = (id: string) => {
    setImageUploads(imageUploads.filter(img => img.id !== id))
  }

  const handleUploadedImageRemove = async (imageId: string) => {
    if (!confirm('Are you sure you want to remove this image?')) return
    
    try {
      await umalectureApi.deleteImage(lectureId, imageId)
      setUploadedImages(uploadedImages.filter(img => img.id !== imageId))
    } catch (err) {
      console.error('Error deleting image:', err)
      alert('Failed to delete image')
    }
  }

  const uploadImages = async () => {
    for (const upload of imageUploads) {
      if (!upload.nodeId || !upload.description || upload.uploaded) continue
      
      setImageUploads(prev => prev.map(img => 
        img.id === upload.id ? { ...img, uploading: true } : img
      ))
      
      try {
        const formData = new FormData()
        formData.append('file', upload.file)
        formData.append('node_id', upload.nodeId)
        formData.append('teacher_description', upload.description)
        formData.append('position', '1')
        
        const uploadedImage = await umalectureApi.uploadImage(lectureId, formData)
        
        setUploadedImages(prev => [...prev, uploadedImage])
        setImageUploads(prev => prev.map(img => 
          img.id === upload.id ? { ...img, uploading: false, uploaded: true } : img
        ))
      } catch (err) {
        console.error('Error uploading image:', err)
        setImageUploads(prev => prev.map(img => 
          img.id === upload.id ? { ...img, uploading: false, error: 'Upload failed' } : img
        ))
      }
    }
  }

  const handleSaveAndProcess = async () => {
    // Validate
    if (!outline.trim() || outline.trim().split('\n').length < 3) {
      setError('Please provide a detailed outline with at least 3 lines')
      return
    }
    
    const pendingImages = imageUploads.filter(img => img.nodeId && img.description && !img.uploaded)
    if (pendingImages.length > 0) {
      setError('Please upload all pending images before processing')
      return
    }
    
    try {
      setSaving(true)
      setError(null)
      
      // Save outline
      await umalectureApi.updateLecture(lectureId, { topic_outline: outline })
      
      // Upload any pending images
      if (imageUploads.some(img => !img.uploaded && img.nodeId && img.description)) {
        await uploadImages()
      }
      
      // Start AI processing
      setProcessing(true)
      await umalectureApi.processLecture(lectureId)
      
      // Redirect to processing status page
      router.push(`/teacher/uma-lecture/${lectureId}/processing`)
    } catch (err) {
      console.error('Error processing lecture:', err)
      setError('Failed to process lecture. Please try again.')
      setProcessing(false)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <ArrowPathIcon className="h-8 w-8 text-gray-400 animate-spin" />
      </div>
    )
  }

  if (!lecture) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Lecture not found</p>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto p-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/teacher/uma-lecture"
          className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back to Lectures
        </Link>
        
        <div className="flex items-center space-x-3">
          <AcademicCapIcon className="h-8 w-8 text-red-500" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{lecture.title}</h1>
            <p className="text-gray-600 mt-1">Step 2: Add Content & Images</p>
          </div>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center">
          <div className="flex items-center">
            <div className="w-8 h-8 bg-green-600 text-white rounded-full flex items-center justify-center">
              ✓
            </div>
            <span className="ml-2 text-sm font-medium text-gray-900">Basic Info</span>
          </div>
          <div className="flex-1 mx-4">
            <div className="h-1 bg-primary-600 rounded"></div>
          </div>
          <div className="flex items-center">
            <div className="w-8 h-8 bg-primary-600 text-white rounded-full flex items-center justify-center font-semibold">
              2
            </div>
            <span className="ml-2 text-sm font-medium text-gray-900">Content & Images</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content Area */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Topic Outline</h2>
            
            <div className="mb-4 bg-blue-50 border border-blue-200 rounded-md p-4">
              <div className="flex">
                <InformationCircleIcon className="h-5 w-5 text-blue-600 mr-2 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-blue-800 mb-2">
                    Create a hierarchical outline with main topics and subtopics. Use indentation or bullet points.
                  </p>
                  <details className="text-sm text-blue-700">
                    <summary className="cursor-pointer hover:text-blue-800">View example</summary>
                    <pre className="mt-2 p-2 bg-white rounded text-xs overflow-x-auto">{OUTLINE_EXAMPLE}</pre>
                  </details>
                </div>
              </div>
            </div>

            <textarea
              value={outline}
              onChange={handleOutlineChange}
              onKeyDown={handleOutlineKeyDown}
              className="w-full h-96 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 font-mono text-sm"
              placeholder="Enter your lecture outline here..."
            />
            
            <div className="mt-2 text-sm text-gray-500">
              {outline.length} characters • {outline.split('\n').filter(l => l.trim()).length} lines
            </div>
          </div>
        </div>

        {/* Image Upload Sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Images</h2>
            
            <p className="text-sm text-gray-600 mb-4">
              Upload images to enhance your lecture. Each image needs a topic association and description.
            </p>

            {/* Upload Button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="w-full mb-4 px-4 py-2 border-2 border-dashed border-gray-300 rounded-md text-gray-600 hover:border-primary-500 hover:text-primary-600 transition-colors"
            >
              <PhotoIcon className="h-6 w-6 mx-auto mb-1" />
              <span className="text-sm">Click to upload images</span>
            </button>
            
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              onChange={handleImageSelect}
              className="hidden"
            />

            {/* Uploaded Images */}
            {uploadedImages.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Uploaded Images</h3>
                <div className="space-y-2">
                  {uploadedImages.map(image => (
                    <div key={image.id} className="border border-gray-200 rounded p-2">
                      <div className="flex items-start space-x-2">
                        <img 
                          src={image.thumbnail_url || image.display_url || image.original_url} 
                          alt={image.teacher_description}
                          className="w-16 h-16 object-cover rounded"
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-gray-700">{image.node_id}</p>
                          <p className="text-xs text-gray-600 truncate">{image.teacher_description}</p>
                        </div>
                        <button
                          onClick={() => handleUploadedImageRemove(image.id)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <XMarkIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Pending Uploads */}
            {imageUploads.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-gray-700">Pending Uploads</h3>
                {imageUploads.map(upload => (
                  <div key={upload.id} className="border border-gray-200 rounded p-3">
                    <div className="flex items-start space-x-2 mb-2">
                      <img 
                        src={upload.preview} 
                        alt="Preview"
                        className="w-16 h-16 object-cover rounded"
                      />
                      <button
                        onClick={() => handleImageRemove(upload.id)}
                        className="ml-auto text-red-600 hover:text-red-700"
                        disabled={upload.uploading}
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                    
                    <select
                      value={upload.nodeId}
                      onChange={(e) => handleImageUpdate(upload.id, 'nodeId', e.target.value)}
                      className="w-full mb-2 px-2 py-1 text-sm border border-gray-300 rounded"
                      disabled={upload.uploading || upload.uploaded}
                    >
                      <option value="">Select topic</option>
                      {extractedTopics.map(topic => (
                        <option key={topic} value={topic}>{topic}</option>
                      ))}
                    </select>
                    
                    <input
                      type="text"
                      value={upload.description}
                      onChange={(e) => handleImageUpdate(upload.id, 'description', e.target.value)}
                      placeholder="Brief description"
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                      disabled={upload.uploading || upload.uploaded}
                    />
                    
                    {upload.uploading && (
                      <p className="text-xs text-blue-600 mt-1">Uploading...</p>
                    )}
                    {upload.uploaded && (
                      <p className="text-xs text-green-600 mt-1">✓ Uploaded</p>
                    )}
                    {upload.error && (
                      <p className="text-xs text-red-600 mt-1">{upload.error}</p>
                    )}
                  </div>
                ))}
                
                {imageUploads.some(img => !img.uploaded && img.nodeId && img.description) && (
                  <button
                    onClick={uploadImages}
                    className="w-full text-sm text-primary-600 hover:text-primary-700"
                  >
                    Upload pending images
                  </button>
                )}
              </div>
            )}
            
            <p className="text-xs text-gray-500 mt-4">
              Max 10 images • 5MB each • JPEG, PNG, GIF, WebP
            </p>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="mt-8 flex items-center justify-between">
        <button
          onClick={() => router.push(`/teacher/uma-lecture/${lectureId}/edit`)}
          className="text-gray-600 hover:text-gray-700"
        >
          Save as Draft
        </button>
        
        <button
          onClick={handleSaveAndProcess}
          disabled={saving || processing || !outline.trim()}
          className="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {processing ? (
            <>
              <ArrowPathIcon className="h-5 w-5 mr-2 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <SparklesIcon className="h-5 w-5 mr-2" />
              Create Interactive Lecture
            </>
          )}
        </button>
      </div>
    </div>
  )
}