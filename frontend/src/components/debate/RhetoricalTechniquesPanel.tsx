'use client'

import { useState, useEffect } from 'react'
import { ChevronDownIcon, ChevronUpIcon, BookOpenIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { studentDebateApi } from '@/lib/studentDebateApi'
import { RhetoricalTechniques } from '@/types/debate'

export default function RhetoricalTechniquesPanel() {
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'proper' | 'improper'>('proper')
  const [techniques, setTechniques] = useState<RhetoricalTechniques | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen && !techniques) {
      loadTechniques()
    }
  }, [isOpen, techniques])

  const loadTechniques = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await studentDebateApi.getTechniques()
      setTechniques(data)
    } catch (err) {
      setError('Failed to load rhetorical techniques')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative">
      {/* Collapsed State - Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed right-4 top-24 z-40 flex items-center px-3 py-2 bg-blue-600 text-white rounded-lg shadow-lg hover:bg-blue-700 transition-colors duration-200"
        >
          <BookOpenIcon className="h-5 w-5 mr-2" />
          <span className="text-sm font-medium">Rhetorical Techniques</span>
          <ChevronDownIcon className="h-4 w-4 ml-2" />
        </button>
      )}

      {/* Expanded State - Panel */}
      {isOpen && (
        <div className="fixed right-0 top-0 z-50 h-full w-full sm:w-96 bg-white shadow-2xl overflow-hidden flex flex-col">
          {/* Header */}
          <div className="bg-blue-600 text-white px-4 py-3 flex items-center justify-between">
            <div className="flex items-center">
              <BookOpenIcon className="h-5 w-5 mr-2" />
              <h2 className="text-lg font-semibold">Rhetorical Techniques Reference</h2>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 hover:bg-blue-700 rounded-md transition-colors"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab('proper')}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === 'proper'
                  ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                  : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
              }`}
            >
              Proper Techniques
            </button>
            <button
              onClick={() => setActiveTab('improper')}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === 'improper'
                  ? 'text-red-600 border-b-2 border-red-600 bg-red-50'
                  : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
              }`}
            >
              Improper Techniques
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {loading && (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
                {error}
              </div>
            )}

            {techniques && !loading && (
              <div className="space-y-4">
                {activeTab === 'proper' && techniques.proper.map((technique, index) => (
                  <div key={technique.name} className="bg-blue-50 rounded-lg p-4 space-y-2">
                    <h3 className="font-semibold text-blue-900">{technique.displayName}</h3>
                    <p className="text-sm text-gray-700">{technique.description}</p>
                    <div className="bg-white rounded p-2 border border-blue-200">
                      <p className="text-sm text-gray-600">
                        <span className="font-medium">Example:</span> {technique.example}
                      </p>
                    </div>
                    <p className="text-sm text-blue-700">
                      <span className="font-medium">Tip:</span> {technique.tipOrReason}
                    </p>
                  </div>
                ))}

                {activeTab === 'improper' && techniques.improper.map((technique, index) => (
                  <div key={technique.name} className="bg-red-50 rounded-lg p-4 space-y-2">
                    <h3 className="font-semibold text-red-900">{technique.displayName}</h3>
                    <p className="text-sm text-gray-700">{technique.description}</p>
                    <div className="bg-white rounded p-2 border border-red-200">
                      <p className="text-sm text-gray-600">
                        <span className="font-medium">Example:</span> {technique.example}
                      </p>
                    </div>
                    <p className="text-sm text-red-700">
                      <span className="font-medium">Why it's unfair:</span> {technique.tipOrReason}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-gray-200 px-4 py-3 bg-gray-50">
            <p className="text-xs text-gray-600 text-center">
              Use these techniques to strengthen your arguments and identify weaknesses in opposing arguments.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}