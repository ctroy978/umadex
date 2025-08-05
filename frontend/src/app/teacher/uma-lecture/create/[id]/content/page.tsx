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
import { supabase } from '@/lib/supabase'

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

const generateOutlineFromTopicData = (topicData: { topic: string; subtopics: string[] }) => {
  let outline = `Topic: ${topicData.topic}\n`
  
  topicData.subtopics.forEach((subtopic, index) => {
    outline += `- ${subtopic}\n`
  })
  
  return outline
}

interface ImageUpload {
  id: string
  file: File
  preview: string
  description: string
  difficultyLevel?: string
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
  const [topicData, setTopicData] = useState<{ topic: string; subtopics: string[] } | null>(null)
  const [imageUploads, setImageUploads] = useState<ImageUpload[]>([])
  const [uploadedImages, setUploadedImages] = useState<LectureImage[]>([])
  
  // Extract topics for image association
  const extractedTopics = (() => {
    if (topicData) {
      return [topicData.topic, ...topicData.subtopics]
    }
    
    // Fallback: try to parse from outline if we have one
    if (outline) {
      const lines = outline.split('\n').filter(line => line.trim())
      const topics = []
      
      for (const line of lines) {
        const trimmed = line.trim()
        if (trimmed.startsWith('Topic:')) {
          topics.push(trimmed.replace('Topic:', '').trim())
        } else if (trimmed.startsWith('-')) {
          topics.push(trimmed.replace(/^-\s*/, '').trim())
        }
      }
      
      return topics.filter(t => t && t !== 'Key concepts' && t !== 'Main ideas' && t !== 'Applications')
    }
    
    return []
  })()

  useEffect(() => {
    // Load topic data from session storage first
    const topicDataStr = sessionStorage.getItem('lectureTopicData')
    if (topicDataStr) {
      const data = JSON.parse(topicDataStr)
      setTopicData(data)
      const generatedOutline = generateOutlineFromTopicData(data)
      setOutline(generatedOutline)
      // Don't clear session storage yet - we need it for submission
    }
    
    // Then load lecture data
    loadLecture(topicDataStr)
  }, [lectureId])

  const loadLecture = async (topicDataStr?: string | null) => {
    try {
      setLoading(true)
      const data = await umalectureApi.getLecture(lectureId)
      setLecture(data)
      
      // If we don't have an outline yet, try to use the saved one or create a basic one
      if (!outline) {
        if (data.topic_outline) {
          setOutline(data.topic_outline)
        } else if (!topicDataStr) {
          // Only create a basic outline if we didn't get data from session storage
          // This means the user likely came directly to this page
          console.warn('No topic data found in session storage - user may need to go back to step 1')
          setError('Please complete step 1 first to define your topic and subtopics.')
        }
      }
      
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
            description: '',
            difficultyLevel: 'basic'
          })
          
          if (newUploads.length === files.length) {
            setImageUploads([...imageUploads, ...newUploads])
          }
        }
        reader.readAsDataURL(file)
      }
    })
  }

  const handleImageUpdate = (id: string, field: 'description' | 'difficultyLevel', value: string) => {
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
      // Find the image to get its storage path
      const imageToDelete = uploadedImages.find(img => img.id === imageId)
      
      if (imageToDelete && imageToDelete.storage_path) {
        // Delete from Supabase Storage
        const { error: storageError } = await supabase.storage
          .from('lecture-images')
          .remove([imageToDelete.storage_path])
        
        if (storageError) {
          console.error('Error deleting from storage:', storageError)
        }
      }
      
      // Delete reference from backend
      await umalectureApi.deleteImage(lectureId, imageId)
      setUploadedImages(uploadedImages.filter(img => img.id !== imageId))
    } catch (err) {
      console.error('Error deleting image:', err)
      alert('Failed to delete image')
    }
  }

  const uploadImages = async () => {
    for (const upload of imageUploads) {
      if (!upload.description) continue
      
      setImageUploads(prev => prev.map(img => 
        img.id === upload.id ? { ...img, uploading: true } : img
      ))
      
      try {
        // Generate a unique filename
        const fileExt = upload.file.name.split('.').pop()
        const fileName = `${Date.now()}-${Math.random().toString(36).substring(7)}.${fileExt}`
        const filePath = `lectures/${lectureId}/${fileName}`
        
        // Upload to Supabase Storage
        const { data: storageData, error: storageError } = await supabase.storage
          .from('lecture-images')
          .upload(filePath, upload.file, {
            cacheControl: '3600',
            upsert: false
          })
        
        if (storageError) {
          throw new Error(`Storage upload failed: ${storageError.message}`)
        }
        
        // Get the public URL
        const { data: { publicUrl } } = supabase.storage
          .from('lecture-images')
          .getPublicUrl(filePath)
        
        // Save reference to backend - use difficulty level as the node_id
        // Use the main topic for all images since there's only one topic per lecture
        const mainTopic = topicData?.topic || 'lecture'
        const nodeIdWithDifficulty = `${mainTopic}|${upload.difficultyLevel || 'basic'}`
        const imageReference = await umalectureApi.createImageReference({
          lecture_id: lectureId,
          filename: fileName,
          storage_path: filePath,
          public_url: publicUrl,
          teacher_description: upload.description,
          node_id: nodeIdWithDifficulty,
          position: 1
        })
        
        // Add to uploaded images
        setUploadedImages(prev => [...prev, imageReference])
        
        // Remove from pending uploads
        setImageUploads(prev => prev.filter(img => img.id !== upload.id))
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
    if (!outline.trim()) {
      setError('Missing topic outline. Please go back to step 1.')
      return
    }
    
    // Check if there are images that have been configured but not uploaded
    const pendingImages = imageUploads.filter(img => !img.uploaded)
    if (pendingImages.length > 0) {
      const hasValidPending = pendingImages.some(img => img.nodeId && img.description)
      if (hasValidPending) {
        setError('Please upload all pending images before creating the lecture. You can also remove these images if you don\'t want to include them.')
        return
      }
      // If there are pending images without topic/description, we can ignore them
    }
    
    try {
      setSaving(true)
      setError(null)
      
      // Save outline (from the first page)
      await umalectureApi.updateLecture(lectureId, { topic_outline: outline })
      
      // Start AI processing
      setProcessing(true)
      await umalectureApi.processLecture(lectureId)
      
      // Clear session storage now that we're done
      sessionStorage.removeItem('lectureTopicData')
      
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
            <p className="text-gray-600 mt-1">Step 2: Add Images (Optional)</p>
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
            <span className="ml-2 text-sm font-medium text-gray-900">Add Images</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Topic Summary */}
      {topicData && (
        <div className="mb-6 bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Your Lecture Structure</h3>
          <div className="text-sm text-gray-600">
            <p className="font-medium text-gray-800">Topic: {topicData.topic}</p>
            <ul className="mt-2 ml-4 space-y-1">
              {topicData.subtopics.map((subtopic, index) => (
                <li key={index}>• {subtopic}</li>
              ))}
            </ul>
          </div>
          <p className="text-xs text-gray-500 mt-3">
            The AI will create interactive content for each subtopic at Basic, Intermediate, Advanced, and Expert levels.
          </p>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Add Images to Your Lecture</h2>
          <p className="text-gray-600 mb-8">
            Images help students visualize concepts and retain information better. 
            Upload relevant images and associate them with your topic or subtopics.
          </p>

          {/* Image Guidelines */}
          <div className="mb-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex">
              <InformationCircleIcon className="h-5 w-5 text-blue-600 mr-2 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-blue-800 font-medium">Image Guidelines</p>
                <ul className="text-sm text-blue-700 mt-1 ml-4 space-y-1">
                  <li>• Choose clear, relevant images that illustrate key concepts</li>
                  <li>• Each image should be associated with a specific topic or subtopic</li>
                  <li>• Provide a brief description of what the image shows</li>
                  <li>• Images are optional - only add them if they enhance understanding</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Upload Section */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Upload Images</h3>
              
              {/* Upload Button */}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full mb-6 px-6 py-8 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-primary-500 hover:text-primary-600 transition-colors"
              >
                <PhotoIcon className="h-12 w-12 mx-auto mb-2" />
                <span className="text-base font-medium">Click to upload images</span>
                <p className="text-sm mt-1">or drag and drop</p>
              </button>
              
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                onChange={handleImageSelect}
                className="hidden"
              />

              {/* Pending Uploads */}
              {imageUploads.length > 0 && (
                <div className="space-y-4">
                  <h4 className="text-sm font-medium text-gray-700">New Images ({imageUploads.length})</h4>
                  {imageUploads.map(upload => (
                    <div key={upload.id} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                      <div className="flex items-start space-x-3">
                        <img 
                          src={upload.preview} 
                          alt="Preview"
                          className="w-20 h-20 object-cover rounded"
                        />
                        <div className="flex-1">
                          <select
                            value={upload.difficultyLevel || 'basic'}
                            onChange={(e) => handleImageUpdate(upload.id, 'difficultyLevel', e.target.value)}
                            className="w-full mb-2 px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                            disabled={upload.uploading || upload.uploaded}
                          >
                            <option value="basic">Basic</option>
                            <option value="intermediate">Intermediate</option>
                            <option value="advanced">Advanced</option>
                            <option value="expert">Expert</option>
                          </select>
                          
                          <input
                            type="text"
                            value={upload.description}
                            onChange={(e) => handleImageUpdate(upload.id, 'description', e.target.value)}
                            placeholder="Describe what this image shows"
                            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                            disabled={upload.uploading || upload.uploaded}
                          />
                          
                          {upload.uploading && (
                            <p className="text-xs text-blue-600 mt-1 flex items-center">
                              <ArrowPathIcon className="h-3 w-3 mr-1 animate-spin" />
                              Uploading...
                            </p>
                          )}
                          {upload.uploaded && (
                            <p className="text-xs text-green-600 mt-1">✓ Uploaded successfully</p>
                          )}
                          {upload.error && (
                            <p className="text-xs text-red-600 mt-1">{upload.error}</p>
                          )}
                        </div>
                        <button
                          onClick={() => handleImageRemove(upload.id)}
                          className="text-gray-400 hover:text-red-600"
                          disabled={upload.uploading}
                        >
                          <XMarkIcon className="h-5 w-5" />
                        </button>
                      </div>
                    </div>
                  ))}
                  
                  {imageUploads.some(img => img.description && !img.uploading) && (
                    <button
                      onClick={uploadImages}
                      className="w-full py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
                    >
                      Upload {imageUploads.filter(img => img.description).length} image(s)
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Uploaded Images Section */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Uploaded Images ({uploadedImages.length})
              </h3>
              
              {uploadedImages.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <PhotoIcon className="h-12 w-12 mx-auto mb-3 text-gray-400" />
                  <p>No images uploaded yet</p>
                  <p className="text-sm mt-1">Images are optional but can enhance learning</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {uploadedImages.map(image => (
                    <div key={image.id} className="border border-gray-200 rounded-lg p-3 bg-white">
                      <div className="flex items-start space-x-3">
                        <img 
                          src={image.public_url || image.display_url || image.original_url} 
                          alt={image.teacher_description}
                          className="w-16 h-16 object-cover rounded"
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900">{image.node_id}</p>
                          <p className="text-sm text-gray-600 truncate">{image.teacher_description}</p>
                        </div>
                        <button
                          onClick={() => handleUploadedImageRemove(image.id)}
                          className="text-gray-400 hover:text-red-600"
                        >
                          <XMarkIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              <p className="text-xs text-gray-500 mt-4">
                Max 10 images • 5MB each • JPEG, PNG, GIF, WebP
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="mt-8 flex items-center justify-between">
        <Link
          href="/teacher/uma-lecture/create"
          className="text-gray-600 hover:text-gray-700"
        >
          ← Back to Step 1
        </Link>
        
        <div className="flex items-center space-x-4">
          <span className="text-sm text-gray-500">
            {uploadedImages.length > 0 
              ? `${uploadedImages.length} image(s) added` 
              : 'No images added (optional)'}
          </span>
          
          {imageUploads.filter(img => img.description).length > 0 && (
            <span className="text-sm text-amber-600">
              {imageUploads.filter(img => img.description).length} image(s) need uploading
            </span>
          )}
          
          <button
            onClick={handleSaveAndProcess}
            disabled={saving || processing || !outline || !outline.trim()}
            className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
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
    </div>
  )
}