'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { vocabularyApi } from '@/lib/vocabularyApi'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'
import type { VocabularyList, VocabularyListUpdate } from '@/types/vocabulary'

// Grade level options matching the reading module
const GRADE_LEVELS = [
  { value: '3-5', label: 'Grades 3-5' },
  { value: '6-8', label: 'Grades 6-8' },
  { value: '9-10', label: 'Grades 9-10' },
  { value: '11-12', label: 'Grades 11-12' },
  { value: 'college', label: 'College' },
]

// Subject options matching the reading module
const SUBJECTS = ['English Literature', 'History', 'Science', 'Social Studies', 'ESL/ELL', 'Other'] as const;

export default function EditVocabularyPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [list, setList] = useState<VocabularyList | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors }
  } = useForm<VocabularyListUpdate>()

  useEffect(() => {
    loadVocabularyList()
  }, [params.id])

  const loadVocabularyList = async () => {
    try {
      setIsLoading(true)
      const data = await vocabularyApi.getList(params.id)
      setList(data)
      // Reset form with loaded data
      reset({
        title: data.title,
        context_description: data.context_description || '',
        grade_level: data.grade_level,
        subject_area: data.subject_area || ''
      })
    } catch (error) {
      console.error('Failed to load vocabulary list:', error)
      setError('Failed to load vocabulary list')
    } finally {
      setIsLoading(false)
    }
  }

  const onSubmit = async (data: VocabularyListUpdate) => {
    setIsSubmitting(true)
    try {
      await vocabularyApi.updateList(params.id, data)
      router.push(`/teacher/vocabulary/${params.id}`)
    } catch (error) {
      console.error('Failed to update vocabulary list:', error)
      alert('Failed to update vocabulary list')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  if (error || !list) {
    return (
      <div className="container mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error || 'Failed to load vocabulary list'}</p>
          <button
            onClick={() => router.back()}
            className="mt-4 text-red-600 hover:text-red-700"
          >
            Go back
          </button>
        </div>
      </div>
    )
  }

  // Don't allow editing published lists
  if (list.status === 'published') {
    return (
      <div className="container mx-auto p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800">Published vocabulary lists cannot be edited.</p>
          <button
            onClick={() => router.back()}
            className="mt-4 text-yellow-600 hover:text-yellow-700"
          >
            Go back
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <button
          onClick={() => router.push(`/teacher/vocabulary/${params.id}`)}
          className="inline-flex items-center text-gray-600 hover:text-gray-900"
        >
          <ArrowLeftIcon className="h-5 w-5 mr-2" />
          Back to List
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold mb-6">Edit Vocabulary List</h1>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
              Title *
            </label>
            <input
              type="text"
              id="title"
              {...register('title', { required: 'Title is required' })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {errors.title && (
              <p className="mt-1 text-sm text-red-600">{errors.title.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="context_description" className="block text-sm font-medium text-gray-700 mb-1">
              Context/Description
              <span className="text-gray-500 text-xs ml-2">(Optional)</span>
            </label>
            <textarea
              id="context_description"
              {...register('context_description')}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Provide context about the reading material or topic these words relate to..."
            />
          </div>

          <div>
            <label htmlFor="grade_level" className="block text-sm font-medium text-gray-700 mb-1">
              Grade Level *
            </label>
            <select
              id="grade_level"
              {...register('grade_level', { required: 'Grade level is required' })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {GRADE_LEVELS.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            {errors.grade_level && (
              <p className="mt-1 text-sm text-red-600">{errors.grade_level.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="subject_area" className="block text-sm font-medium text-gray-700 mb-1">
              Subject Area
            </label>
            <select
              id="subject_area"
              {...register('subject_area')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Select a subject</option>
              {SUBJECTS.map((subject) => (
                <option key={subject} value={subject}>{subject}</option>
              ))}
            </select>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              <strong>Note:</strong> This page allows you to edit the list metadata only. 
              To modify individual words, use the Review page where you can edit definitions and examples.
            </p>
          </div>

          <div className="flex gap-4">
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Saving...' : 'Save Changes'}
            </button>
            <button
              type="button"
              onClick={() => router.push(`/teacher/vocabulary/${params.id}`)}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}