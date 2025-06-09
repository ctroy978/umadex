'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useForm, useFieldArray } from 'react-hook-form'
import { vocabularyApi } from '@/lib/vocabularyApi'
import { PlusIcon, XMarkIcon, InformationCircleIcon } from '@heroicons/react/24/outline'
import type { VocabularyListCreate, VocabularyWordCreate } from '@/types/vocabulary'

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

interface FormData extends Omit<VocabularyListCreate, 'words'> {
  words: (VocabularyWordCreate & { id?: string })[]
}

export default function CreateVocabularyPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [autoSaveStatus, setAutoSaveStatus] = useState<'saved' | 'saving' | 'unsaved'>('saved')
  const [draftLoaded, setDraftLoaded] = useState(false)

  const {
    register,
    control,
    handleSubmit,
    watch,
    formState: { errors },
    getValues,
    reset
  } = useForm<FormData>({
    defaultValues: {
      title: '',
      context_description: '',
      grade_level: '6-8',
      subject_area: '',
      words: [
        { word: '', teacher_definition: '', teacher_example_1: '', teacher_example_2: '' }
      ]
    }
  })

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'words'
  })

  // Load draft from localStorage on mount (only once)
  useEffect(() => {
    if (!draftLoaded) {
      const isNewList = searchParams.get('new') === 'true'
      
      if (isNewList) {
        // Clear any existing draft when creating a new list
        localStorage.removeItem('vocabulary-draft')
        setDraftLoaded(true)
        return
      }
      
      const savedDraft = localStorage.getItem('vocabulary-draft')
      if (savedDraft) {
        try {
          const draft = JSON.parse(savedDraft)
          
          // Validate the draft before loading
          if (draft.words && Array.isArray(draft.words)) {
            // Remove duplicate words based on the word text
            const uniqueWords = draft.words.reduce((acc: any[], word: any) => {
              if (!acc.find(w => w.word === word.word)) {
                acc.push(word)
              }
              return acc
            }, [])
            
            // Limit to 50 words max
            draft.words = uniqueWords.slice(0, 50)
            
            // If draft has more than 50 words, it's likely corrupted
            if (uniqueWords.length > 50) {
              console.warn('Draft had too many words, truncating to 50')
              localStorage.removeItem('vocabulary-draft')
            }
          }
          
          // Use reset to properly set all form values including the words array
          reset(draft)
          setDraftLoaded(true)
        } catch (error) {
          console.error('Failed to load draft:', error)
          localStorage.removeItem('vocabulary-draft')
        }
      }
      setDraftLoaded(true)
    }
  }, [draftLoaded, reset, searchParams])

  // Auto-save to localStorage (but only after draft is loaded)
  const formData = watch()
  useEffect(() => {
    if (!draftLoaded) return // Don't save until draft is loaded
    
    const timeoutId = setTimeout(() => {
      setAutoSaveStatus('saving')
      
      // Validate before saving - ensure words array is reasonable
      if (formData.words && formData.words.length <= 50) {
        localStorage.setItem('vocabulary-draft', JSON.stringify(formData))
        setAutoSaveStatus('saved')
      } else {
        console.error('Invalid form data - too many words:', formData.words?.length)
        setAutoSaveStatus('unsaved')
      }
    }, 1000)

    return () => {
      clearTimeout(timeoutId)
      setAutoSaveStatus('unsaved')
    }
  }, [formData, draftLoaded])

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true)
    try {
      // Filter out empty words
      const validWords = data.words.filter(word => word.word.trim())
      
      if (validWords.length < 5) {
        alert('Please provide at least 5 vocabulary words')
        setIsSubmitting(false)
        return
      }

      const vocabularyData: VocabularyListCreate = {
        ...data,
        words: validWords.map(({ id, ...word }) => word) // Remove id field
      }

      const createdList = await vocabularyApi.createList(vocabularyData)
      
      // Clear draft
      localStorage.removeItem('vocabulary-draft')
      
      // Redirect to review page
      router.push(`/teacher/vocabulary/${createdList.id}/review`)
    } catch (error: any) {
      console.error('Failed to create vocabulary list:', error)
      
      // Show detailed error message
      let errorMessage = 'Failed to create vocabulary list. '
      if (error.response?.data?.detail) {
        if (typeof error.response.data.detail === 'string') {
          errorMessage += error.response.data.detail
        } else if (Array.isArray(error.response.data.detail)) {
          errorMessage += error.response.data.detail.map((e: any) => e.msg).join(', ')
        }
      } else {
        errorMessage += 'Please try again.'
      }
      
      alert(errorMessage)
    } finally {
      setIsSubmitting(false)
    }
  }

  const addWord = () => {
    if (fields.length < 50) {
      append({ word: '', teacher_definition: '', teacher_example_1: '', teacher_example_2: '' })
    }
  }

  const removeWord = (index: number) => {
    if (fields.length > 1) {
      remove(index)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Create Vocabulary List</h1>
        <p className="mt-2 text-sm text-gray-600">
          Create a vocabulary list with AI-enhanced definitions and examples.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* List Metadata */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium mb-4">List Information</h2>
          
          <div className="grid grid-cols-1 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                List Title
              </label>
              <input
                type="text"
                {...register('title', { required: 'Title is required' })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                placeholder="e.g., SAT Vocabulary Week 1"
              />
              {errors.title && (
                <p className="mt-1 text-sm text-red-600">{errors.title.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Context Description
              </label>
              <textarea
                {...register('context_description', { 
                  required: 'Context description is required',
                  minLength: { value: 10, message: 'Description must be at least 10 characters' }
                })}
                rows={3}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                placeholder="e.g., Advanced vocabulary for SAT preparation focusing on words commonly found in reading passages"
              />
              {errors.context_description && (
                <p className="mt-1 text-sm text-red-600">{errors.context_description.message}</p>
              )}
              <p className="mt-1 text-xs text-gray-500">
                This helps AI generate appropriate definitions and examples for your students.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Grade Level
                </label>
                <select
                  {...register('grade_level', { required: 'Grade level is required' })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                >
                  {GRADE_LEVELS.map(level => (
                    <option key={level.value} value={level.value}>
                      {level.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Subject *
                </label>
                <select
                  {...register('subject_area', { required: 'Subject is required' })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                >
                  <option value="">Select a subject</option>
                  {SUBJECTS.map(subject => (
                    <option key={subject} value={subject}>{subject}</option>
                  ))}
                </select>
                {errors.subject_area && (
                  <p className="mt-1 text-sm text-red-600">{errors.subject_area.message}</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Vocabulary Words */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-lg font-medium">Vocabulary Words</h2>
              <p className="text-sm text-gray-600">
                Add 5-50 words. You can optionally provide definitions and examples.
              </p>
            </div>
            <div className="text-sm">
              <span className={fields.length < 5 ? "text-red-600 font-medium" : "text-gray-500"}>
                {fields.length} / 50 words
              </span>
              {fields.length < 5 && (
                <span className="text-red-600 ml-2">(minimum 5 required)</span>
              )}
            </div>
          </div>

          <div className="space-y-4">
            {fields.map((field, index) => (
              <div key={field.id} className="border rounded-lg p-4 bg-gray-50">
                <div className="flex justify-between items-start mb-3">
                  <h3 className="font-medium">Word {index + 1}</h3>
                  {fields.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeWord(index)}
                      className="text-red-600 hover:text-red-800"
                    >
                      <XMarkIcon className="h-5 w-5" />
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 gap-3">
                  <div>
                    <input
                      {...register(`words.${index}.word` as const, { 
                        required: 'Word is required' 
                      })}
                      placeholder="Enter vocabulary word"
                      className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                    />
                    {errors.words?.[index]?.word && (
                      <p className="mt-1 text-sm text-red-600">
                        {errors.words[index]?.word?.message}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs text-gray-600 mb-1">
                      Custom Definition (optional)
                    </label>
                    <textarea
                      {...register(`words.${index}.teacher_definition` as const)}
                      rows={2}
                      placeholder="Leave blank to use AI-generated definition"
                      className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">
                        Example 1 (optional)
                      </label>
                      <input
                        {...register(`words.${index}.teacher_example_1` as const)}
                        placeholder="First example sentence"
                        className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">
                        Example 2 (optional)
                      </label>
                      <input
                        {...register(`words.${index}.teacher_example_2` as const)}
                        placeholder="Second example sentence"
                        className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {fields.length < 50 && (
            <button
              type="button"
              onClick={addWord}
              className="mt-4 w-full flex items-center justify-center px-4 py-2 border-2 border-dashed border-gray-300 rounded-md text-sm font-medium text-gray-600 hover:border-gray-400 hover:text-gray-700"
            >
              <PlusIcon className="h-5 w-5 mr-2" />
              Add Word
            </button>
          )}
        </div>

        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex">
            <InformationCircleIcon className="h-5 w-5 text-blue-600 mt-0.5" />
            <div className="ml-3 text-sm text-blue-900">
              <p className="font-medium mb-1">How it works:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>After submission, AI will generate definitions and examples for words without teacher-provided content</li>
                <li>You'll review and approve all AI-generated content before publishing</li>
                <li>You can reject and regenerate content or provide your own</li>
                <li>Your work is auto-saved every few seconds</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Submit Buttons */}
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-500">
              {autoSaveStatus === 'saving' && 'Saving...'}
              {autoSaveStatus === 'saved' && 'All changes saved'}
              {autoSaveStatus === 'unsaved' && 'Unsaved changes'}
            </div>
            <button
              type="button"
              onClick={() => {
                if (confirm('Are you sure you want to clear this draft and start over?')) {
                  localStorage.removeItem('vocabulary-draft')
                  reset({
                    title: '',
                    context_description: '',
                    grade_level: '6-8',
                    subject_area: '',
                    words: [
                      { word: '', teacher_definition: '', teacher_example_1: '', teacher_example_2: '' }
                    ]
                  })
                  setAutoSaveStatus('saved')
                }
              }}
              className="text-sm text-red-600 hover:text-red-700 underline"
            >
              Clear Draft
            </button>
          </div>
          
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => {
                if (confirm('Are you sure you want to cancel? Your draft will be saved.')) {
                  router.push('/teacher/uma-vocab')
                }
              }}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50"
            >
              {isSubmitting ? 'Creating...' : 'Create & Generate AI Content'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}