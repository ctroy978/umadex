'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { vocabularyChainApi, VocabularyChain, VocabularyChainMember } from '@/lib/vocabularyChainApi'
import { vocabularyApi } from '@/lib/vocabularyApi'
import type { VocabularyListSummary } from '@/types/vocabulary'
import {
  ArrowLeftIcon,
  PlusIcon,
  TrashIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  CheckIcon
} from '@heroicons/react/24/outline'

export default function VocabularyChainDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [chain, setChain] = useState<VocabularyChain | null>(null)
  const [availableLists, setAvailableLists] = useState<VocabularyListSummary[]>([])
  const [selectedLists, setSelectedLists] = useState<Set<string>>(new Set())
  const [isLoading, setIsLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    loadChainAndLists()
  }, [params.id])

  const loadChainAndLists = async () => {
    try {
      setIsLoading(true)
      
      // Load chain with members
      const chainData = await vocabularyChainApi.getChain(params.id, true)
      setChain(chainData)
      
      // Load available vocabulary lists
      const listsResponse = await vocabularyApi.getLists({
        status: 'published',
        per_page: 100
      })
      
      // Filter out lists already in the chain
      const memberIds = new Set(chainData.members?.map(m => m.vocabulary_list_id) || [])
      const available = listsResponse.items.filter(list => !memberIds.has(list.id))
      setAvailableLists(available)
    } catch (error) {
      console.error('Failed to load chain:', error)
      setError('Failed to load chain details')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAddLists = async () => {
    if (selectedLists.size === 0) return

    try {
      setUpdating(true)
      setError('')
      
      await vocabularyChainApi.addMembers(params.id, {
        vocabulary_list_ids: Array.from(selectedLists)
      })
      
      // Reset and reload
      setSelectedLists(new Set())
      setShowAddModal(false)
      await loadChainAndLists()
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to add lists to chain')
    } finally {
      setUpdating(false)
    }
  }

  const handleRemoveMember = async (vocabularyListId: string, title: string) => {
    if (!confirm(`Remove "${title}" from this chain?`)) return

    try {
      await vocabularyChainApi.removeMember(params.id, vocabularyListId)
      await loadChainAndLists()
    } catch (error) {
      console.error('Failed to remove member:', error)
      alert('Failed to remove list from chain')
    }
  }

  const handleReorderMember = async (vocabularyListId: string, currentPosition: number, direction: 'up' | 'down') => {
    if (!chain?.members) return

    const newPosition = direction === 'up' ? currentPosition - 1 : currentPosition + 1
    if (newPosition < 0 || newPosition >= chain.members.length) return

    try {
      await vocabularyChainApi.reorderMember(params.id, {
        vocabulary_list_id: vocabularyListId,
        new_position: newPosition
      })
      await loadChainAndLists()
    } catch (error) {
      console.error('Failed to reorder member:', error)
      alert('Failed to reorder list')
    }
  }

  const handleUpdateReviewWords = async (newValue: number) => {
    if (!chain) return

    try {
      await vocabularyChainApi.updateChain(params.id, {
        total_review_words: newValue
      })
      setChain({ ...chain, total_review_words: newValue })
    } catch (error) {
      console.error('Failed to update review words:', error)
      alert('Failed to update review words')
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!chain) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error || 'Chain not found'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.push('/teacher/vocabulary/chains')}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-5 w-5 mr-2" />
          Back to Chains
        </button>
        
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{chain.name}</h1>
            {chain.description && (
              <p className="mt-1 text-sm text-gray-600">{chain.description}</p>
            )}
            <div className="mt-2 flex items-center gap-4 text-sm text-gray-500">
              <span>{chain.member_count || 0} vocabulary lists</span>
              <span>•</span>
              <div className="flex items-center gap-2">
                <span>Review words per test:</span>
                <select
                  value={chain.total_review_words}
                  onChange={(e) => handleUpdateReviewWords(parseInt(e.target.value))}
                  className="text-sm rounded border-gray-300 py-1"
                >
                  <option value={1}>1</option>
                  <option value={2}>2</option>
                  <option value={3}>3</option>
                  <option value={4}>4</option>
                </select>
              </div>
            </div>
          </div>
          
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
            Add Lists
          </button>
        </div>
      </div>

      {/* Chain Members */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Vocabulary Lists in Chain</h2>
          <p className="mt-1 text-sm text-gray-500">
            Drag to reorder or remove lists from this chain. Lists appear in test order.
          </p>
        </div>
        
        {!chain.members || chain.members.length === 0 ? (
          <div className="p-8 text-center">
            <PlusIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No lists in chain</h3>
            <p className="mt-1 text-sm text-gray-500">
              Add vocabulary lists to start building your test chain.
            </p>
            <div className="mt-6">
              <button
                onClick={() => setShowAddModal(true)}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
              >
                <PlusIcon className="h-5 w-5 mr-2" />
                Add Lists
              </button>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {chain.members.map((member, index) => (
              <div key={member.id} className="px-6 py-4 flex items-center justify-between hover:bg-gray-50">
                <div className="flex items-center space-x-4">
                  <span className="text-sm font-medium text-gray-500 w-8">
                    {index + 1}.
                  </span>
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {member.vocabulary_list?.title || 'Unknown List'}
                    </p>
                    <p className="text-sm text-gray-500">
                      {member.vocabulary_list?.grade_level} • {member.vocabulary_list?.subject_area} • {member.vocabulary_list?.word_count} words
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleReorderMember(member.vocabulary_list_id, index, 'up')}
                    disabled={index === 0}
                    className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ArrowUpIcon className="h-5 w-5" />
                  </button>
                  <button
                    onClick={() => handleReorderMember(member.vocabulary_list_id, index, 'down')}
                    disabled={index === chain.members.length - 1}
                    className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ArrowDownIcon className="h-5 w-5" />
                  </button>
                  <button
                    onClick={() => handleRemoveMember(
                      member.vocabulary_list_id,
                      member.vocabulary_list?.title || 'this list'
                    )}
                    className="p-1 text-red-400 hover:text-red-600"
                  >
                    <TrashIcon className="h-5 w-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Lists Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">
                Add Vocabulary Lists to Chain
              </h3>
            </div>
            
            {error && (
              <div className="mx-6 mt-4 bg-red-50 border border-red-200 rounded-md p-4">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}

            <div className="flex-1 overflow-y-auto p-6">
              {availableLists.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-8">
                  No published vocabulary lists available to add.
                </p>
              ) : (
                <div className="space-y-2">
                  {availableLists.map((list) => (
                    <label
                      key={list.id}
                      className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50"
                    >
                      <input
                        type="checkbox"
                        checked={selectedLists.has(list.id)}
                        onChange={(e) => {
                          const newSelected = new Set(selectedLists)
                          if (e.target.checked) {
                            newSelected.add(list.id)
                          } else {
                            newSelected.delete(list.id)
                          }
                          setSelectedLists(newSelected)
                        }}
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500"
                      />
                      <div className="ml-3 flex-1">
                        <p className="text-sm font-medium text-gray-900">{list.title}</p>
                        <p className="text-sm text-gray-500">
                          {list.grade_level} • {list.subject_area} • {list.word_count} words
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex justify-between items-center">
              <p className="text-sm text-gray-500">
                {selectedLists.size} {selectedLists.size === 1 ? 'list' : 'lists'} selected
              </p>
              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false)
                    setSelectedLists(new Set())
                    setError('')
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddLists}
                  disabled={updating || selectedLists.size === 0}
                  className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50"
                >
                  {updating ? 'Adding...' : `Add ${selectedLists.size} ${selectedLists.size === 1 ? 'List' : 'Lists'}`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}