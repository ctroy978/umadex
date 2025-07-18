'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { vocabularyApi } from '@/lib/vocabularyApi'
import {
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  PencilIcon,
  TrashIcon,
  ArrowLeftIcon
} from '@heroicons/react/24/outline'
import { CheckIcon, XMarkIcon } from '@heroicons/react/20/solid'
import type {
  VocabularyList,
  VocabularyWord,
  VocabularyWordManualUpdate,
  VocabularyProgress,
  ReviewStatus,
  VocabularyStatus
} from '@/types/vocabulary'

interface WordReviewCardProps {
  word: VocabularyWord
  onAccept: () => void
  onEdit: (data: VocabularyWordManualUpdate) => void
  onRegenerate: () => void
  isProcessing: boolean
}

function WordReviewCard({
  word,
  onAccept,
  onEdit,
  onRegenerate,
  isProcessing
}: WordReviewCardProps) {
  const [showEditDialog, setShowEditDialog] = useState(false)
  const [editData, setEditData] = useState<VocabularyWordManualUpdate>({
    definition: word.teacher_definition || word.ai_definition || '',
    example_1: word.teacher_example_1 || word.ai_example_1 || '',
    example_2: word.teacher_example_2 || word.ai_example_2 || ''
  })

  const reviewStatus = word.review?.review_status || 'pending'
  const isAccepted = reviewStatus === 'accepted'

  const handleEdit = () => {
    setEditData({
      definition: word.teacher_definition || word.ai_definition || '',
      example_1: word.teacher_example_1 || word.ai_example_1 || '',
      example_2: word.teacher_example_2 || word.ai_example_2 || ''
    })
    setShowEditDialog(true)
  }

  const submitEdit = () => {
    onEdit(editData)
    setShowEditDialog(false)
  }


  const currentDefinition = word.definition_source === 'teacher' 
    ? word.teacher_definition 
    : word.ai_definition

  const currentExample1 = word.examples_source === 'teacher'
    ? word.teacher_example_1
    : word.ai_example_1

  const currentExample2 = word.examples_source === 'teacher'
    ? word.teacher_example_2
    : word.ai_example_2

  return (
    <div className={`bg-white rounded-lg shadow-sm border-2 ${
      isAccepted ? 'border-green-200' : 'border-gray-200'
    } p-6`}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-xl font-semibold text-gray-900">{word.word}</h3>
          <div className="flex items-center mt-1 space-x-4">
            {isAccepted && (
              <span className="inline-flex items-center text-sm text-green-600">
                <CheckCircleIcon className="h-4 w-4 mr-1" />
                Accepted
              </span>
            )}
            {word.definition_source === 'teacher' && (
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                Teacher Provided
              </span>
            )}
            {word.definition_source === 'ai' && (
              <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
                AI Generated
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <h4 className="font-medium text-gray-700 mb-1">Definition</h4>
          <p className="text-gray-900">{currentDefinition || 'No definition available'}</p>
        </div>

        <div>
          <h4 className="font-medium text-gray-700 mb-1">Example Sentences</h4>
          <ol className="list-decimal list-inside space-y-1">
            <li className="text-gray-900">{currentExample1 || 'No example available'}</li>
            <li className="text-gray-900">{currentExample2 || 'No example available'}</li>
          </ol>
        </div>

      </div>

      {/* Action Buttons */}
      {!isAccepted && (
        <div className="mt-6 flex gap-3">
          <button
            onClick={onAccept}
            disabled={isProcessing}
            className="flex-1 inline-flex justify-center items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
          >
            <CheckIcon className="h-4 w-4 mr-2" />
            Accept
          </button>
          <button
            onClick={handleEdit}
            disabled={isProcessing}
            className="flex-1 inline-flex justify-center items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            <PencilIcon className="h-4 w-4 mr-2" />
            Edit
          </button>
        </div>
      )}

      {/* Edit Dialog */}
      {showEditDialog && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Edit Vocabulary Word
            </h3>
            <div className="space-y-4">
              <div className="mb-4">
                <h4 className="text-lg font-semibold text-gray-900">{word.word}</h4>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Definition
                </label>
                <textarea
                  value={editData.definition}
                  onChange={(e) => setEditData({ ...editData, definition: e.target.value })}
                  rows={3}
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Example Sentence 1
                </label>
                <input
                  type="text"
                  value={editData.example_1}
                  onChange={(e) => setEditData({ ...editData, example_1: e.target.value })}
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Example Sentence 2
                </label>
                <input
                  type="text"
                  value={editData.example_2}
                  onChange={(e) => setEditData({ ...editData, example_2: e.target.value })}
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                />
              </div>
            </div>
            <div className="mt-6 flex gap-3">
              <button
                onClick={() => setShowEditDialog(false)}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={submitEdit}
                disabled={
                  editData.definition.length < 10 ||
                  editData.example_1.length < 10 ||
                  editData.example_2.length < 10
                }
                className="flex-1 px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}

export default function VocabularyReviewPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [list, setList] = useState<VocabularyList | null>(null)
  const [progress, setProgress] = useState<VocabularyProgress | null>(null)
  const [currentWordIndex, setCurrentWordIndex] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadVocabularyList()
  }, [params.id])

  const loadVocabularyList = async () => {
    try {
      setIsLoading(true)
      const [listData, progressData] = await Promise.all([
        vocabularyApi.getList(params.id),
        vocabularyApi.getProgress(params.id)
      ])
      setList(listData)
      setProgress(progressData)
      
      // Find first pending word
      const firstPendingIndex = listData.words?.findIndex(
        w => w.review?.review_status === 'pending'
      ) ?? 0
      setCurrentWordIndex(firstPendingIndex >= 0 ? firstPendingIndex : 0)
    } catch (error) {
      console.error('Failed to load vocabulary list:', error)
      setError('Failed to load vocabulary list')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAccept = async (wordId: string) => {
    try {
      setIsProcessing(true)
      await vocabularyApi.reviewWord(wordId, { action: 'accept' })
      await loadVocabularyList()
      // Move to next pending word
      moveToNextPending()
    } catch (error) {
      console.error('Failed to accept word:', error)
      alert('Failed to accept word')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleWordEdit = async (wordId: string, data: VocabularyWordManualUpdate) => {
    try {
      setIsProcessing(true)
      await vocabularyApi.updateWordManually(wordId, data)
      await loadVocabularyList()
    } catch (error) {
      console.error('Failed to edit word:', error)
      alert('Failed to edit word')
    } finally {
      setIsProcessing(false)
    }
  }


  const handleRegenerate = async (wordId: string) => {
    try {
      setIsProcessing(true)
      await vocabularyApi.regenerateWordDefinition(wordId)
      await loadVocabularyList()
    } catch (error) {
      console.error('Failed to regenerate word:', error)
      alert('Failed to regenerate word')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleAcceptAll = async () => {
    if (!confirm('Are you sure you want to accept all remaining words?')) return
    
    try {
      setIsProcessing(true)
      await vocabularyApi.acceptAllPending(params.id)
      await loadVocabularyList()
    } catch (error) {
      console.error('Failed to accept all:', error)
      alert('Failed to accept all words')
    } finally {
      setIsProcessing(false)
    }
  }

  const handlePublish = async () => {
    if (!progress || progress.pending > 0) {
      alert('Please review all words before publishing')
      return
    }
    
    if (list?.status === 'published') {
      alert('This vocabulary list is already published')
      return
    }
    
    try {
      setIsProcessing(true)
      await vocabularyApi.publishList(params.id)
      
      // Update local state to reflect published status
      if (list) {
        setList({ ...list, status: 'published' })
      }
      
      // Show success message
      alert('Vocabulary list published successfully!')
      
      // Navigate back to the list after a short delay
      setTimeout(() => {
        router.push('/teacher/uma-vocab')
      }, 1000)
      
    } catch (error: any) {
      console.error('Failed to publish list:', error)
      
      // Show detailed error message
      let errorMessage = 'Failed to publish vocabulary list. '
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
      setIsProcessing(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this vocabulary list? This action cannot be undone.')) {
      return
    }
    
    try {
      setIsProcessing(true)
      await vocabularyApi.deleteList(params.id)
      router.push('/teacher/uma-vocab')
    } catch (error: any) {
      console.error('Failed to delete list:', error)
      
      // Check for 400 error with specific message about classrooms
      if (error.response?.status === 400 && error.response?.data?.detail) {
        alert(error.response.data.detail)
      } else if (error.response?.data?.message) {
        // Some error responses might use 'message' instead of 'detail'
        alert(error.response.data.message)
      } else {
        alert('Failed to delete list')
      }
    } finally {
      setIsProcessing(false)
    }
  }

  const handleListEdit = () => {
    // For now, redirect to create page with the list data
    // TODO: Implement proper edit page
    router.push(`/teacher/vocabulary/${params.id}/edit`)
  }

  const moveToNextPending = () => {
    if (!list?.words) return
    
    // Find next pending word after current index
    for (let i = currentWordIndex + 1; i < list.words.length; i++) {
      if (list.words[i].review?.review_status === 'pending') {
        setCurrentWordIndex(i)
        return
      }
    }
    
    // If no pending words after current, search from beginning
    for (let i = 0; i < currentWordIndex; i++) {
      if (list.words[i].review?.review_status === 'pending') {
        setCurrentWordIndex(i)
        return
      }
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error || !list) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error || 'Failed to load vocabulary list'}</p>
        </div>
      </div>
    )
  }

  const currentWord = list.words?.[currentWordIndex]
  const canPublish = progress && progress.pending === 0 && list?.status !== 'published'
  const isPublished = list?.status === 'published'

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="mb-4">
          <button
            onClick={() => router.push('/teacher/uma-vocab')}
            className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            Back to Vocabulary Lists
          </button>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{list.title}</h1>
            <p className="mt-1 text-sm text-gray-600">{list.context_description}</p>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={handleListEdit}
              disabled={isProcessing || list.status === 'published'}
              className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              <PencilIcon className="h-4 w-4 mr-1" />
              Edit
            </button>
            <button
              onClick={handleDelete}
              disabled={isProcessing}
              className="inline-flex items-center px-3 py-2 border border-red-300 rounded-md shadow-sm text-sm font-medium text-red-700 bg-white hover:bg-red-50 disabled:opacity-50"
            >
              <TrashIcon className="h-4 w-4 mr-1" />
              Delete
            </button>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              list.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
              list.status === 'reviewing' ? 'bg-blue-100 text-blue-800' :
              list.status === 'published' ? 'bg-green-100 text-green-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {list.status.charAt(0).toUpperCase() + list.status.slice(1)}
            </span>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      {progress && (
        <div className="mb-6 bg-white rounded-lg shadow p-4">
          <div className="flex justify-between items-center mb-2">
            <h2 className="text-lg font-medium">Review Progress</h2>
            <span className="text-sm text-gray-600">
              {progress.accepted + progress.rejected} / {progress.total} reviewed
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-primary-600 h-3 rounded-full transition-all duration-300"
              style={{ width: `${progress.progress_percentage}%` }}
            />
          </div>
          <div className="mt-2 flex justify-between text-xs text-gray-600">
            <span>{progress.accepted} accepted</span>
            <span>{progress.rejected} rejected</span>
            <span>{progress.pending} pending</span>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentWordIndex(Math.max(0, currentWordIndex - 1))}
            disabled={currentWordIndex === 0}
            className="p-2 rounded-md border border-gray-300 disabled:opacity-50"
          >
            <ChevronLeftIcon className="h-5 w-5" />
          </button>
          <span className="px-4 py-2 text-sm">
            Word {currentWordIndex + 1} of {list.words?.length || 0}
          </span>
          <button
            onClick={() => setCurrentWordIndex(Math.min((list.words?.length || 1) - 1, currentWordIndex + 1))}
            disabled={currentWordIndex >= (list.words?.length || 1) - 1}
            className="p-2 rounded-md border border-gray-300 disabled:opacity-50"
          >
            <ChevronRightIcon className="h-5 w-5" />
          </button>
        </div>
        
        <div className="flex gap-3">
          {progress && progress.pending > 0 && (
            <button
              onClick={handleAcceptAll}
              disabled={isProcessing}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              Accept All Remaining ({progress.pending})
            </button>
          )}
        </div>
      </div>

      {/* Current Word */}
      {currentWord && (
        <WordReviewCard
          word={currentWord}
          onAccept={() => handleAccept(currentWord.id)}
          onEdit={(data) => handleWordEdit(currentWord.id, data)}
          onRegenerate={() => handleRegenerate(currentWord.id)}
          isProcessing={isProcessing}
        />
      )}

      {/* Action Buttons */}
      <div className="mt-8 flex justify-between">
        <button
          onClick={() => router.push('/teacher/uma-vocab')}
          className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
        >
          Back to List
        </button>
        
        <button
          onClick={handlePublish}
          disabled={!canPublish || isProcessing}
          className={`px-6 py-2 rounded-md text-sm font-medium text-white ${
            canPublish 
              ? 'bg-green-600 hover:bg-green-700' 
              : 'bg-gray-400 cursor-not-allowed'
          } disabled:opacity-50`}
        >
          {isProcessing ? 'Publishing...' : 
           isPublished ? 'Already Published' :
           canPublish ? 'Publish List' : 
           `Review ${progress?.pending || 0} Remaining Words`}
        </button>
      </div>
    </div>
  )
}