'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { vocabularyApi } from '@/lib/vocabularyApi'
import {
  PlusIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  BookOpenIcon,
  ClockIcon,
  CheckCircleIcon,
  ArchiveBoxIcon,
  ArrowUturnLeftIcon
} from '@heroicons/react/24/outline'
import type { VocabularyListSummary, VocabularyStatus } from '@/types/vocabulary'

const STATUS_COLORS: Record<VocabularyStatus, { bg: string; text: string; icon: any }> = {
  draft: { bg: 'bg-gray-100', text: 'text-gray-800', icon: ClockIcon },
  processing: { bg: 'bg-yellow-100', text: 'text-yellow-800', icon: ClockIcon },
  reviewing: { bg: 'bg-blue-100', text: 'text-blue-800', icon: BookOpenIcon },
  published: { bg: 'bg-green-100', text: 'text-green-800', icon: CheckCircleIcon },
  archived: { bg: 'bg-gray-100', text: 'text-gray-600', icon: ArchiveBoxIcon }
}

export default function UmaVocabPage() {
  const router = useRouter()
  const [lists, setLists] = useState<VocabularyListSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<VocabularyStatus | 'all'>('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)

  useEffect(() => {
    loadVocabularyLists()
  }, [currentPage, statusFilter, searchTerm])

  const loadVocabularyLists = async () => {
    try {
      setIsLoading(true)
      const response = await vocabularyApi.getLists({
        page: currentPage,
        per_page: 20,
        status: statusFilter === 'all' ? undefined : statusFilter,
        search: searchTerm || undefined
      })
      
      setLists(response.items)
      setTotalPages(response.pages)
      setTotalCount(response.total)
    } catch (error) {
      console.error('Failed to load vocabulary lists:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setCurrentPage(1)
    loadVocabularyLists()
  }

  const handleUnarchive = async (listId: string) => {
    try {
      await vocabularyApi.updateList(listId, { 
        status: 'published' as VocabularyStatus 
      })
      // Refresh the list to show the updated status
      loadVocabularyLists()
    } catch (error) {
      console.error('Failed to unarchive vocabulary list:', error)
      alert('Failed to unarchive vocabulary list. Please try again.')
    }
  }

  const getStatusBadge = (status: VocabularyStatus) => {
    const config = STATUS_COLORS[status]
    const Icon = config.icon
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        <Icon className="w-3 h-3 mr-1" />
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Vocabulary Lists</h1>
            <p className="mt-1 text-sm text-gray-600">
              Create and manage vocabulary lists with AI-enhanced definitions
            </p>
          </div>
          <Link
            href="/teacher/vocabulary/chains"
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.102 1.101m4.899.758a4 4 0 01-5.656 0" />
            </svg>
            Manage Test Chains
          </Link>
        </div>
      </div>

      {/* Actions Bar */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search vocabulary lists..."
                className="pl-10 pr-3 py-2 w-full border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
            >
              Search
            </button>
          </form>
        </div>
        
        <div className="flex gap-2">
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as VocabularyStatus | 'all')
              setCurrentPage(1)
            }}
            className="px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="all">All Status</option>
            <option value="draft">Draft</option>
            <option value="processing">Processing</option>
            <option value="reviewing">Reviewing</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
          
          <Link
            href="/teacher/vocabulary/create?new=true"
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
            Create List
          </Link>
        </div>
      </div>

      {/* Lists Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading vocabulary lists...</p>
          </div>
        ) : lists.length === 0 ? (
          <div className="p-8 text-center">
            <BookOpenIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No vocabulary lists</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by creating a new vocabulary list.
            </p>
            <div className="mt-6">
              <Link
                href="/teacher/vocabulary/create?new=true"
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
              >
                <PlusIcon className="h-5 w-5 mr-2" />
                Create Your First List
              </Link>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Title
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Grade / Subject
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Words
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Review Progress
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
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
                {lists.map((list) => (
                  <tr key={list.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {list.title}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{list.grade_level}</div>
                      <div className="text-sm text-gray-500">{list.subject_area}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {list.word_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {list.status === 'reviewing' || list.status === 'published' ? (
                        <div className="flex items-center">
                          <div className="flex-1 bg-gray-200 rounded-full h-2 mr-2">
                            <div
                              className="bg-primary-600 h-2 rounded-full"
                              style={{ width: `${list.review_progress}%` }}
                            />
                          </div>
                          <span className="text-sm text-gray-600">
                            {list.review_progress}%
                          </span>
                        </div>
                      ) : (
                        <span className="text-sm text-gray-500">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(list.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(list.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      {list.status === 'reviewing' ? (
                        <Link
                          href={`/teacher/vocabulary/${list.id}/review`}
                          className="text-primary-600 hover:text-primary-900"
                        >
                          Review
                        </Link>
                      ) : list.status === 'published' ? (
                        <Link
                          href={`/teacher/vocabulary/${list.id}`}
                          className="text-primary-600 hover:text-primary-900"
                        >
                          View
                        </Link>
                      ) : list.status === 'archived' ? (
                        <button
                          onClick={() => handleUnarchive(list.id)}
                          className="inline-flex items-center text-green-600 hover:text-green-900"
                        >
                          <ArrowUturnLeftIcon className="h-4 w-4 mr-1" />
                          Unarchive
                        </button>
                      ) : list.status === 'draft' || list.status === 'processing' ? (
                        <span className="text-gray-400">Processing...</span>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Showing {(currentPage - 1) * 20 + 1} to {Math.min(currentPage * 20, totalCount)} of {totalCount} results
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}