'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { 
  PlusIcon, 
  MagnifyingGlassIcon,
  DocumentCheckIcon,
  ClockIcon,
  EyeIcon,
  PencilIcon,
  TrashIcon,
  ArchiveBoxIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'
import { useAuthSupabase } from '@/hooks/useAuthSupabase'
import { api } from '@/lib/api'
import { toast } from 'react-hot-toast'
import { format } from 'date-fns'

interface TestAssignment {
  id: string
  test_title: string
  test_description: string | null
  selected_lecture_ids: string[]
  time_limit_minutes: number | null
  attempt_limit: number
  status: 'draft' | 'published' | 'archived'
  total_questions: number
  created_at: string
  updated_at: string
  is_archived?: boolean
}

interface TestListResponse {
  tests: TestAssignment[]
  total_count: number
  page: number
  page_size: number
}

export default function UMATestPage() {
  const { user } = useAuthSupabase()
  const router = useRouter()
  const [tests, setTests] = useState<TestAssignment[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  useEffect(() => {
    fetchTests()
  }, [page, statusFilter])

  const fetchTests = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20'
      })
      
      if (statusFilter !== 'all') {
        params.append('status', statusFilter)
      }
      
      if (searchTerm) {
        params.append('search', searchTerm)
      }

      const response = await api.get<TestListResponse>(`/v1/teacher/umatest/tests?${params}`)
      setTests(response.data.tests)
      setTotalPages(Math.ceil(response.data.total_count / response.data.page_size))
    } catch (error) {
      console.error('Error fetching tests:', error)
      toast.error('Failed to load tests')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    fetchTests()
  }

  const handleDelete = async (testId: string) => {
    if (!confirm('Are you sure you want to archive this test?')) return

    try {
      await api.delete(`/v1/teacher/umatest/tests/${testId}`)
      toast.success('Test archived successfully')
      fetchTests()
    } catch (error: any) {
      console.error('Error archiving test:', error)
      console.log('Full error response data:', JSON.stringify(error.response?.data))
      
      // Handle different error response structures
      let errorMessage = 'Failed to archive test'
      
      if (error.response?.data) {
        // FastAPI typically returns errors in {detail: "message"} format
        if (error.response.data.detail) {
          errorMessage = error.response.data.detail
        } else if (error.response.data.message) {
          errorMessage = error.response.data.message
        } else if (typeof error.response.data === 'string') {
          errorMessage = error.response.data
        }
      } else if (error.message) {
        errorMessage = error.message
      }
      
      // Log what we're about to show
      console.log('Showing error message:', errorMessage)
      toast.error(errorMessage)
    }
  }

  const handleRestore = async (testId: string) => {
    try {
      await api.post(`/v1/teacher/umatest/tests/${testId}/restore`)
      toast.success('Test restored successfully')
      // If we're viewing archived tests, switch to all tests after restore
      if (statusFilter === 'archived') {
        setStatusFilter('all')
      } else {
        fetchTests()
      }
    } catch (error) {
      console.error('Error restoring test:', error)
      toast.error('Failed to restore test')
    }
  }

  const getStatusBadge = (test: TestAssignment) => {
    const statusStyles = {
      draft: 'bg-gray-100 text-gray-800',
      published: 'bg-green-100 text-green-800',
      archived: 'bg-yellow-100 text-yellow-800'
    }

    const displayStatus = test.is_archived ? 'archived' : (test.status || 'draft')
    
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusStyles[displayStatus as keyof typeof statusStyles] || statusStyles.draft}`}>
        {displayStatus.charAt(0).toUpperCase() + displayStatus.slice(1)}
      </span>
    )
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">uMaTest</h1>
          <p className="mt-2 text-sm text-gray-700">
            Create comprehensive tests from your UMALecture assignments
          </p>
        </div>
        <div className="mt-4 sm:mt-0">
          <Link
            href="/teacher/uma-test/new"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            <PlusIcon className="-ml-1 mr-2 h-5 w-5" />
            Create New Test
          </Link>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="mt-8 flex flex-col sm:flex-row gap-4">
        <form onSubmit={handleSearch} className="flex-1">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              placeholder="Search tests..."
            />
          </div>
        </form>
        
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value)
            setPage(1)
          }}
          className="block w-full sm:w-auto pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm rounded-md"
        >
          <option value="all">All Status</option>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
        </select>
      </div>

      {/* Tests List */}
      {loading ? (
        <div className="mt-8 text-center">
          <div className="inline-flex items-center">
            <svg className="animate-spin h-5 w-5 mr-3 text-gray-500" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Loading tests...
          </div>
        </div>
      ) : tests.length === 0 ? (
        <div className="mt-8 text-center py-12">
          <DocumentCheckIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No tests found</h3>
          <p className="mt-1 text-sm text-gray-500">
            Get started by creating a new test from your UMALecture assignments.
          </p>
          <div className="mt-6">
            <Link
              href="/teacher/uma-test/new"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              <PlusIcon className="-ml-1 mr-2 h-5 w-5" />
              Create New Test
            </Link>
          </div>
        </div>
      ) : (
        <div className="mt-8 flex flex-col">
          <div className="-my-2 -mx-4 overflow-x-auto sm:-mx-6 lg:-mx-8">
            <div className="inline-block min-w-full py-2 align-middle md:px-6 lg:px-8">
              <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
                <table className="min-w-full divide-y divide-gray-300">
                  <thead className="bg-gray-50">
                    <tr>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                        Test Title
                      </th>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                        Questions
                      </th>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                        Time Limit
                      </th>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                        Status
                      </th>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                        Created
                      </th>
                      <th scope="col" className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 bg-white">
                    {tests.map((test) => (
                      <tr key={test.id}>
                        <td className="whitespace-nowrap px-3 py-4 text-sm">
                          <div>
                            <div className="font-medium text-gray-900">{test.test_title}</div>
                            {test.test_description && (
                              <div className="text-gray-500">{test.test_description}</div>
                            )}
                          </div>
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                          {test.total_questions || 0}
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                          {test.time_limit_minutes ? `${test.time_limit_minutes} min` : 'No limit'}
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm">
                          {getStatusBadge(test)}
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                          {format(new Date(test.created_at), 'MMM d, yyyy')}
                        </td>
                        <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                          <div className="flex items-center justify-end gap-2">
                            <Link
                              href={`/teacher/uma-test/${test.id}`}
                              className="text-gray-400 hover:text-gray-500"
                              title="View"
                            >
                              <EyeIcon className="h-5 w-5" />
                            </Link>
                            <Link
                              href={`/teacher/uma-test/${test.id}/edit`}
                              className="text-primary-600 hover:text-primary-900"
                              title="Edit"
                            >
                              <PencilIcon className="h-5 w-5" />
                            </Link>
                            {test.is_archived || statusFilter === 'archived' ? (
                              <button
                                onClick={() => handleRestore(test.id)}
                                className="text-yellow-600 hover:text-yellow-900"
                                title="Restore"
                              >
                                <ArrowPathIcon className="h-5 w-5" />
                              </button>
                            ) : (
                              <button
                                onClick={() => handleDelete(test.id)}
                                className="text-red-600 hover:text-red-900"
                                title="Archive"
                              >
                                <ArchiveBoxIcon className="h-5 w-5" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <div className="flex justify-between sm:hidden">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
              <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-gray-700">
                    Page <span className="font-medium">{page}</span> of{' '}
                    <span className="font-medium">{totalPages}</span>
                  </p>
                </div>
                <div>
                  <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                    >
                      Next
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}