'use client'

import { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import { XMarkIcon, InformationCircleIcon, Cog6ToothIcon, CheckIcon } from '@heroicons/react/24/outline'
import { vocabularyApi, VocabularyTestConfig } from '@/lib/vocabularyApi'
import { vocabularyChainApi, VocabularyChainSummary } from '@/lib/vocabularyChainApi'

interface VocabularyTestConfigModalProps {
  isOpen: boolean
  onClose: () => void
  vocabularyListId: string
  vocabularyTitle: string
}

export default function VocabularyTestConfigModal({
  isOpen,
  onClose,
  vocabularyListId,
  vocabularyTitle
}: VocabularyTestConfigModalProps) {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [availableChains, setAvailableChains] = useState<VocabularyChainSummary[]>([])
  const [config, setConfig] = useState<VocabularyTestConfig>({
    chain_enabled: false,
    chain_type: 'named_chain',
    weeks_to_include: 1,
    questions_per_week: 5,
    chained_list_ids: [],
    total_review_words: 3,
    current_week_questions: 10,
    max_attempts: 3,
    time_limit_minutes: 30
  })

  useEffect(() => {
    if (isOpen) {
      fetchConfig()
      fetchAvailableChains()
    }
  }, [isOpen])

  const fetchConfig = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await vocabularyApi.getTestConfig(vocabularyListId)
      setConfig({
        ...data,
        chain_type: data.chain_type || 'named_chain',
        chained_list_ids: data.chained_list_ids || [],
        total_review_words: data.total_review_words || 3
      })
    } catch (err) {
      // If no config exists, use defaults
      console.log('No test config found, using defaults')
    } finally {
      setLoading(false)
    }
  }


  const fetchAvailableChains = async () => {
    try {
      const response = await vocabularyChainApi.listChains({
        per_page: 100,
        include_inactive: false
      })
      setAvailableChains(response.items)
    } catch (err) {
      console.error('Failed to fetch chains:', err)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setError('')
      
      // Validate settings
      if (config.chain_enabled) {
        if (!config.chain_id) {
          setError('Please select a vocabulary chain')
          return
        }
      }

      if (config.current_week_questions < 8 || config.current_week_questions > 15) {
        setError('Current week questions must be between 8 and 15')
        return
      }

      if (config.time_limit_minutes < 10 || config.time_limit_minutes > 120) {
        setError('Time limit must be between 10 and 120 minutes')
        return
      }

      await vocabularyApi.updateTestConfig(vocabularyListId, config)
      onClose()
    } catch (err) {
      setError('Failed to save test configuration')
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const calculateTotalQuestions = () => {
    let total = config.current_week_questions
    if (config.chain_enabled && config.chain_id) {
      const chain = availableChains.find(c => c.id === config.chain_id)
      total += chain?.total_review_words || 0
    }
    return total
  }


  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-3xl transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                <Dialog.Title
                  as="div"
                  className="flex items-center justify-between mb-4"
                >
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                      <Cog6ToothIcon className="h-6 w-6 mr-2 text-blue-600" />
                      Vocabulary Test Configuration
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">{vocabularyTitle}</p>
                  </div>
                  <button
                    onClick={onClose}
                    className="rounded-md text-gray-400 hover:text-gray-500"
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </Dialog.Title>

                {loading ? (
                  <div className="flex justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {error && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                        <p className="text-sm text-red-800">{error}</p>
                      </div>
                    )}

                    {/* Test Preview */}
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <div className="flex items-center mb-2">
                        <InformationCircleIcon className="h-5 w-5 text-blue-600 mr-2" />
                        <span className="font-medium text-blue-900">Test Preview</span>
                      </div>
                      <div className="text-sm text-blue-800 space-y-1">
                        <p>Total questions: <strong>{calculateTotalQuestions()}</strong></p>
                        <p>Time limit: <strong>{config.time_limit_minutes} minutes</strong></p>
                        <p>Maximum attempts: <strong>{config.max_attempts}</strong></p>
                        {config.chain_enabled && config.chain_id && (
                          <p>Includes review words from chain: <strong>{availableChains.find(c => c.id === config.chain_id)?.name}</strong></p>
                        )}
                      </div>
                    </div>

                    {/* Test Chaining */}
                    <div>
                      <h4 className="text-base font-medium text-gray-900 mb-4">
                        Test Chaining (Spaced Repetition)
                      </h4>
                      
                      <div className="space-y-4">
                        <label className="flex items-start p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                          <input
                            type="checkbox"
                            checked={config.chain_enabled}
                            onChange={(e) => setConfig(prev => ({ ...prev, chain_enabled: e.target.checked }))}
                            className="mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500"
                          />
                          <div className="ml-3">
                            <div className="font-medium text-gray-900">Enable test chaining</div>
                            <div className="text-sm text-gray-600">
                              Include review words from previous vocabulary assignments to reinforce learning
                            </div>
                          </div>
                        </label>

                        {config.chain_enabled && (
                          <div className="ml-7 space-y-4 p-4 bg-gray-50 rounded-lg">


                            {/* Named Chain Configuration */}
                            {config.chain_enabled && (
                              <div className="space-y-4">
                                <div>
                                  <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Select a chain
                                  </label>
                                  <select
                                    value={config.chain_id || ''}
                                    onChange={(e) => setConfig(prev => ({ 
                                      ...prev, 
                                      chain_id: e.target.value || undefined
                                    }))}
                                    className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                  >
                                    <option value="">Choose a chain...</option>
                                    {availableChains.map(chain => (
                                      <option key={chain.id} value={chain.id}>
                                        {chain.name} ({chain.member_count} lists, {chain.total_review_words} review words)
                                      </option>
                                    ))}
                                  </select>
                                  {config.chain_id && (
                                    <p className="text-xs text-gray-500 mt-1">
                                      Review words will be randomly selected from all lists in this chain
                                    </p>
                                  )}
                                </div>
                              </div>
                            )}

                          </div>
                        )}
                      </div>
                    </div>

                    {/* Question Settings */}
                    <div>
                      <h4 className="text-base font-medium text-gray-900 mb-4">
                        Question Settings
                      </h4>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Current week questions
                          </label>
                          <select
                            value={config.current_week_questions}
                            onChange={(e) => setConfig(prev => ({ 
                              ...prev, 
                              current_week_questions: parseInt(e.target.value) 
                            }))}
                            className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                          >
                            {[...Array(8)].map((_, i) => (
                              <option key={i + 8} value={i + 8}>
                                {i + 8} questions
                              </option>
                            ))}
                          </select>
                          <p className="text-xs text-gray-500 mt-1">
                            Questions from the current vocabulary assignment
                          </p>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Time limit (minutes)
                          </label>
                          <select
                            value={config.time_limit_minutes}
                            onChange={(e) => setConfig(prev => ({ 
                              ...prev, 
                              time_limit_minutes: parseInt(e.target.value) 
                            }))}
                            className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                          >
                            {[10, 15, 20, 25, 30, 40, 45, 60, 90, 120].map(mins => (
                              <option key={mins} value={mins}>
                                {mins} minutes
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    </div>

                    {/* Test Attempts */}
                    <div>
                      <h4 className="text-base font-medium text-gray-900 mb-4">
                        Test Attempts
                      </h4>
                      
                      <div className="max-w-sm">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Maximum attempts allowed
                        </label>
                        <select
                          value={config.max_attempts}
                          onChange={(e) => setConfig(prev => ({ 
                            ...prev, 
                            max_attempts: parseInt(e.target.value) 
                          }))}
                          className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                        >
                          {[1, 2, 3, 4, 5].map(num => (
                            <option key={num} value={num}>
                              {num} attempt{num > 1 ? 's' : ''}
                            </option>
                          ))}
                        </select>
                        <p className="text-xs text-gray-500 mt-1">
                          Students can retake the test if they score below the passing threshold
                        </p>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex justify-end space-x-3 pt-4 border-t">
                      <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                        disabled={saving}
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleSave}
                        disabled={saving}
                        className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50"
                      >
                        {saving ? 'Saving...' : 'Save Configuration'}
                      </button>
                    </div>
                  </div>
                )}
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}