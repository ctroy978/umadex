'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { vocabularyApi } from '@/lib/vocabularyApi'
import {
  ArrowLeftIcon,
  DocumentArrowDownIcon,
  PencilIcon,
  BookOpenIcon,
  PresentationChartBarIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline'
import type { VocabularyList, VocabularyWord } from '@/types/vocabulary'
import VocabularyTestConfigModal from '@/components/teacher/VocabularyTestConfigModal'

export default function VocabularyViewPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [list, setList] = useState<VocabularyList | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isExporting, setIsExporting] = useState(false)
  const [showInstructionsModal, setShowInstructionsModal] = useState(false)
  const [showTestConfigModal, setShowTestConfigModal] = useState(false)

  useEffect(() => {
    loadVocabularyList()
  }, [params.id])

  const loadVocabularyList = async () => {
    try {
      setIsLoading(true)
      const data = await vocabularyApi.getList(params.id)
      setList(data)
    } catch (error) {
      console.error('Failed to load vocabulary list:', error)
      setError('Failed to load vocabulary list')
    } finally {
      setIsLoading(false)
    }
  }

  const handleExport = async (format: 'pdf' | 'csv') => {
    try {
      setIsExporting(true)
      // Note: exportList method needs to be implemented in vocabularyApi
      alert(`Export as ${format.toUpperCase()} is not yet implemented`)
    } catch (error) {
      console.error('Failed to export list:', error)
      alert('Failed to export vocabulary list')
    } finally {
      setIsExporting(false)
    }
  }

  const handleExportPresentation = async () => {
    // Check if list is published
    if (list?.status !== 'published') {
      alert('Only published vocabulary lists can be exported as presentations')
      return
    }

    // Check minimum word count
    if (!list.words || list.words.length < 3) {
      alert('Vocabulary list must have at least 3 words to create a presentation')
      return
    }

    try {
      setIsExporting(true)
      const blob = await vocabularyApi.exportPresentation(params.id)
      
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const safeName = list.title.replace(/[^a-zA-Z0-9 -_]/g, '').replace(/ /g, '_').substring(0, 50)
      a.download = `vocab-presentation-${safeName}-${new Date().toISOString().split('T')[0]}.html`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      // Show instructions modal
      setShowInstructionsModal(true)
    } catch (error) {
      console.error('Failed to export presentation:', error)
      alert('Failed to export vocabulary presentation')
    } finally {
      setIsExporting(false)
      // Hide the dropdown
      document.getElementById('export-dropdown')?.classList.add('hidden')
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

  const sortedWords = list.words?.sort((a, b) => a.position - b.position) || []

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
            <div className="mt-2 flex items-center gap-4 text-sm text-gray-500">
              <span>Grade: {list.grade_level}</span>
              <span>•</span>
              <span>Subject: {list.subject_area}</span>
              <span>•</span>
              <span>{sortedWords.length} words</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <button
                onClick={() => {
                  const dropdown = document.getElementById('export-dropdown')
                  dropdown?.classList.toggle('hidden')
                }}
                disabled={isExporting}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                <DocumentArrowDownIcon className="h-4 w-4 mr-2" />
                Export
              </button>
              <div
                id="export-dropdown"
                className="hidden absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-10"
              >
                <div className="py-1">
                  <button
                    onClick={() => {
                      handleExport('pdf')
                      document.getElementById('export-dropdown')?.classList.add('hidden')
                    }}
                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    Export as PDF
                  </button>
                  <button
                    onClick={() => {
                      handleExport('csv')
                      document.getElementById('export-dropdown')?.classList.add('hidden')
                    }}
                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    Export as CSV
                  </button>
                  <div className="border-t border-gray-100"></div>
                  <button
                    onClick={handleExportPresentation}
                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    <div className="flex items-center">
                      <PresentationChartBarIcon className="h-4 w-4 mr-2" />
                      Export as Presentation
                    </div>
                  </button>
                </div>
              </div>
            </div>

            {list.status === 'published' && (
              <button
                onClick={() => setShowTestConfigModal(true)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                <Cog6ToothIcon className="h-4 w-4 mr-2" />
                Configure Test
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Status Badge */}
      <div className="mb-6">
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
          list.status === 'published' ? 'bg-green-100 text-green-800' :
          'bg-blue-100 text-blue-800'
        }`}>
          <BookOpenIcon className="w-4 h-4 mr-1" />
          {list.status.charAt(0).toUpperCase() + list.status.slice(1)}
        </span>
      </div>

      {/* Words List */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Vocabulary Words</h2>
        </div>
        <div className="divide-y divide-gray-200">
          {sortedWords.map((word, index) => (
            <div key={word.id} className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl font-bold text-gray-300">
                      {index + 1}.
                    </span>
                    <h3 className="text-lg font-semibold text-gray-900">
                      {word.word}
                    </h3>
                  </div>
                  
                  <div className="mt-3 ml-10 space-y-3">
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-1">Definition</h4>
                      <p className="text-gray-900">
                        {word.definition_source === 'teacher' 
                          ? word.teacher_definition 
                          : word.ai_definition}
                      </p>
                    </div>
                    
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-1">Example Sentences</h4>
                      <ol className="list-decimal list-inside space-y-1">
                        <li className="text-gray-900">
                          {word.examples_source === 'teacher'
                            ? word.teacher_example_1
                            : word.ai_example_1}
                        </li>
                        <li className="text-gray-900">
                          {word.examples_source === 'teacher'
                            ? word.teacher_example_2
                            : word.ai_example_2}
                        </li>
                      </ol>
                    </div>
                  </div>
                </div>
                
                <div className="ml-4">
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
          ))}
        </div>
      </div>

      {/* Timestamps */}
      <div className="mt-6 text-sm text-gray-500">
        <p>Created: {new Date(list.created_at).toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        })}</p>
        <p>Last Updated: {new Date(list.updated_at).toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        })}</p>
      </div>

      {/* Instructions Modal */}
      {showInstructionsModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  ✅ Presentation Downloaded Successfully!
                </h3>
                <button
                  onClick={() => setShowInstructionsModal(false)}
                  className="text-gray-400 hover:text-gray-500"
                >
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="prose prose-sm max-w-none">
                <p className="text-gray-600 mb-4">
                  Your vocabulary presentation has been saved to your Downloads folder.
                </p>
                
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                  <h4 className="font-semibold text-blue-900 mb-2">📋 How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-2 text-blue-800">
                    <li>Copy the HTML file to a USB drive or your classroom computer</li>
                    <li>Double-click the file to open in any web browser</li>
                    <li>Press F11 for full-screen mode</li>
                    <li>Use arrow keys to navigate between slides</li>
                    <li>Click buttons or press spacebar to reveal definitions and examples</li>
                  </ol>
                </div>
                
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <h4 className="font-semibold text-green-900 mb-2">💡 Tips:</h4>
                  <ul className="list-disc list-inside space-y-2 text-green-800">
                    <li>Works offline - no internet required</li>
                    <li>Compatible with any computer or tablet</li>
                    <li>Can be printed for student handouts</li>
                    <li>Perfect for substitute teachers</li>
                  </ul>
                </div>
                
                <p className="text-gray-600 mt-4 text-sm">
                  Need help? Contact your IT department or refer to the platform documentation.
                </p>
              </div>
              
              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setShowInstructionsModal(false)}
                  className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
                >
                  Got it!
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Test Configuration Modal */}
      {showTestConfigModal && list && (
        <VocabularyTestConfigModal
          isOpen={showTestConfigModal}
          onClose={() => setShowTestConfigModal(false)}
          vocabularyListId={params.id}
          vocabularyTitle={list.title}
        />
      )}
    </div>
  )
}