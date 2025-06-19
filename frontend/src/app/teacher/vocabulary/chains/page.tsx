'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { vocabularyChainApi, VocabularyChainSummary } from '@/lib/vocabularyChainApi'
import {
  ArrowLeftIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  LinkIcon,
  AdjustmentsHorizontalIcon
} from '@heroicons/react/24/outline'

export default function VocabularyChainManagementPage() {
  const router = useRouter()
  const [chains, setChains] = useState<VocabularyChainSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newChainName, setNewChainName] = useState('')
  const [newChainDescription, setNewChainDescription] = useState('')
  const [newChainReviewWords, setNewChainReviewWords] = useState(3)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    loadChains()
  }, [])

  const loadChains = async () => {
    try {
      setIsLoading(true)
      const response = await vocabularyChainApi.listChains({
        per_page: 100,
        include_inactive: false
      })
      setChains(response.items)
    } catch (error) {
      console.error('Failed to load chains:', error)
      setError('Failed to load vocabulary chains')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateChain = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newChainName.trim()) return

    try {
      setCreating(true)
      setError('')
      await vocabularyChainApi.createChain({
        name: newChainName,
        description: newChainDescription || undefined,
        total_review_words: newChainReviewWords
      })
      
      // Reset form and reload
      setNewChainName('')
      setNewChainDescription('')
      setNewChainReviewWords(3)
      setShowCreateModal(false)
      await loadChains()
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to create chain')
    } finally {
      setCreating(false)
    }
  }

  const handleDeleteChain = async (chainId: string, chainName: string) => {
    if (!confirm(`Are you sure you want to delete the chain "${chainName}"? This will not delete the vocabulary lists, only the chain configuration.`)) {
      return
    }

    try {
      await vocabularyChainApi.deleteChain(chainId)
      await loadChains()
    } catch (error) {
      console.error('Failed to delete chain:', error)
      alert('Failed to delete chain')
    }
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.push('/teacher/uma-vocab')}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-5 w-5 mr-2" />
          Back to Vocabulary Lists
        </button>
        
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Vocabulary Test Chains</h1>
            <p className="mt-1 text-sm text-gray-600">
              Create named chains to group vocabulary lists for spaced repetition in tests
            </p>
          </div>
          
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
            Create Chain
          </button>
        </div>
      </div>

      {/* Chains List */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading chains...</p>
          </div>
        ) : chains.length === 0 ? (
          <div className="p-8 text-center">
            <LinkIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No vocabulary chains</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by creating a chain to group vocabulary lists for testing.
            </p>
            <div className="mt-6">
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
              >
                <PlusIcon className="h-5 w-5 mr-2" />
                Create Your First Chain
              </button>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Chain Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Description
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Lists
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Review Words
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {chains.map((chain) => (
                  <tr key={chain.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {chain.name}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-500">
                        {chain.description || '—'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {chain.member_count} {chain.member_count === 1 ? 'list' : 'lists'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {chain.total_review_words} words
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(chain.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center space-x-3">
                        <Link
                          href={`/teacher/vocabulary/chains/${chain.id}`}
                          className="text-primary-600 hover:text-primary-900"
                        >
                          <AdjustmentsHorizontalIcon className="h-5 w-5" />
                        </Link>
                        <button
                          onClick={() => handleDeleteChain(chain.id, chain.name)}
                          className="text-red-600 hover:text-red-900"
                        >
                          <TrashIcon className="h-5 w-5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Chain Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Create Vocabulary Chain
            </h3>
            
            {error && (
              <div className="mb-4 bg-red-50 border border-red-200 rounded-md p-4">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}

            <form onSubmit={handleCreateChain}>
              <div className="space-y-4">
                <div>
                  <label htmlFor="chain-name" className="block text-sm font-medium text-gray-700">
                    Chain Name *
                  </label>
                  <input
                    type="text"
                    id="chain-name"
                    value={newChainName}
                    onChange={(e) => setNewChainName(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                    placeholder="e.g., Weekly Vocabulary Review"
                    required
                  />
                </div>

                <div>
                  <label htmlFor="chain-description" className="block text-sm font-medium text-gray-700">
                    Description (Optional)
                  </label>
                  <textarea
                    id="chain-description"
                    rows={3}
                    value={newChainDescription}
                    onChange={(e) => setNewChainDescription(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                    placeholder="Describe the purpose of this chain..."
                  />
                </div>

                <div>
                  <label htmlFor="review-words" className="block text-sm font-medium text-gray-700">
                    Review Words per Test
                  </label>
                  <select
                    id="review-words"
                    value={newChainReviewWords}
                    onChange={(e) => setNewChainReviewWords(parseInt(e.target.value))}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                  >
                    <option value={1}>1 review word</option>
                    <option value={2}>2 review words</option>
                    <option value={3}>3 review words</option>
                    <option value={4}>4 review words</option>
                  </select>
                  <p className="mt-1 text-xs text-gray-500">
                    Number of words to randomly select from chained lists for review
                  </p>
                </div>
              </div>

              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false)
                    setError('')
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50"
                >
                  {creating ? 'Creating...' : 'Create Chain'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}