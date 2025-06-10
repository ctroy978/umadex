'use client'

import { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import { XMarkIcon, InformationCircleIcon } from '@heroicons/react/24/outline'
import { teacherClassroomApi } from '@/lib/classroomApi'
import type { 
  VocabularySettings, 
  VocabularySettingsResponse,
  VocabularyDeliveryMode
} from '@/types/classroom'

interface VocabularySettingsModalProps {
  isOpen: boolean
  onClose: () => void
  classroomId: string
  assignmentId: number
  assignmentTitle: string
}


export default function VocabularySettingsModal({
  isOpen,
  onClose,
  classroomId,
  assignmentId,
  assignmentTitle
}: VocabularySettingsModalProps) {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [settingsData, setSettingsData] = useState<VocabularySettingsResponse | null>(null)
  const [settings, setSettings] = useState<VocabularySettings>({
    delivery_mode: 'all_at_once',
    allow_test_retakes: true,
    max_test_attempts: 2,
    released_groups: []
  })

  useEffect(() => {
    if (isOpen) {
      fetchSettings()
    }
  }, [isOpen])

  const fetchSettings = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await teacherClassroomApi.getVocabularySettings(classroomId, assignmentId)
      setSettingsData(data)
      setSettings(data.settings)
    } catch (err) {
      setError('Failed to load vocabulary settings')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setError('')
      
      // Validate settings
      if (settings.delivery_mode !== 'all_at_once' && !settings.group_size) {
        setError('Please select a group size')
        return
      }
      
      if (settings.delivery_mode === 'in_groups' && !settings.release_condition) {
        setError('Please select a release condition')
        return
      }

      await teacherClassroomApi.updateVocabularySettings(classroomId, assignmentId, settings)
      onClose()
    } catch (err) {
      setError('Failed to save settings')
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const handleDeliveryModeChange = (mode: VocabularyDeliveryMode) => {
    setSettings(prev => ({
      ...prev,
      delivery_mode: mode,
      // Reset mode-specific fields
      group_size: mode === 'all_at_once' ? undefined : prev.group_size,
      release_condition: mode === 'in_groups' ? 'immediate' : undefined
    }))
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
                    <h3 className="text-lg font-semibold text-gray-900">
                      Vocabulary Settings
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">{assignmentTitle}</p>
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
                ) : error ? (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                    <p className="text-sm text-red-800">{error}</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Delivery Options */}
                    <div>
                      <h4 className="text-base font-medium text-gray-900 mb-4">
                        How should students receive vocabulary words?
                      </h4>
                      
                      {settingsData && (
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                          <p className="text-sm text-blue-800">
                            Total words in this list: <strong>{settingsData.total_words}</strong>
                          </p>
                        </div>
                      )}

                      <div className="space-y-3">
                        {/* Option 1: All at once */}
                        <label className="flex items-start p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                          <input
                            type="radio"
                            name="delivery_mode"
                            value="all_at_once"
                            checked={settings.delivery_mode === 'all_at_once'}
                            onChange={() => handleDeliveryModeChange('all_at_once')}
                            className="mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500"
                          />
                          <div className="ml-3">
                            <div className="font-medium text-gray-900">All at once</div>
                            <div className="text-sm text-gray-600">
                              Students get all {settingsData?.total_words || 'X'} words to study, then test
                            </div>
                          </div>
                        </label>

                        {/* Option 2: In small groups */}
                        <label className="flex items-start p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                          <input
                            type="radio"
                            name="delivery_mode"
                            value="in_groups"
                            checked={settings.delivery_mode === 'in_groups'}
                            onChange={() => handleDeliveryModeChange('in_groups')}
                            className="mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500"
                          />
                          <div className="ml-3 flex-1">
                            <div className="font-medium text-gray-900">In small groups</div>
                            <div className="text-sm text-gray-600 mb-3">
                              Break vocabulary into smaller chunks for easier learning
                            </div>
                            
                            {settings.delivery_mode === 'in_groups' && (
                              <div className="space-y-3 mt-3 pl-6 border-l-2 border-gray-200">
                                <div>
                                  <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Group size
                                  </label>
                                  <select
                                    value={settings.group_size || ''}
                                    onChange={(e) => setSettings(prev => ({ 
                                      ...prev, 
                                      group_size: parseInt(e.target.value) 
                                    }))}
                                    className="block w-32 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                                  >
                                    <option value="">Select...</option>
                                    {[5, 6, 7, 8].map(size => (
                                      <option key={size} value={size}>
                                        {size} words
                                      </option>
                                    ))}
                                  </select>
                                  {settings.group_size && settingsData && (
                                    <p className="text-xs text-gray-500 mt-1">
                                      This will create {Math.ceil(settingsData.total_words / settings.group_size)} groups
                                    </p>
                                  )}
                                </div>

                                <div>
                                  <label className="block text-sm font-medium text-gray-700 mb-1">
                                    When to release next group
                                  </label>
                                  <div className="space-y-2">
                                    <label className="flex items-center">
                                      <input
                                        type="radio"
                                        name="release_condition"
                                        value="immediate"
                                        checked={settings.release_condition === 'immediate'}
                                        onChange={() => setSettings(prev => ({ 
                                          ...prev, 
                                          release_condition: 'immediate' 
                                        }))}
                                        className="h-4 w-4 text-primary-600 focus:ring-primary-500"
                                      />
                                      <span className="ml-2 text-sm text-gray-700">
                                        Immediately after completing previous group
                                      </span>
                                    </label>
                                    <label className="flex items-center">
                                      <input
                                        type="radio"
                                        name="release_condition"
                                        value="after_test"
                                        checked={settings.release_condition === 'after_test'}
                                        onChange={() => setSettings(prev => ({ 
                                          ...prev, 
                                          release_condition: 'after_test' 
                                        }))}
                                        className="h-4 w-4 text-primary-600 focus:ring-primary-500"
                                      />
                                      <span className="ml-2 text-sm text-gray-700">
                                        After passing mini-test on previous group
                                      </span>
                                    </label>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        </label>

                        {/* Option 3: Teacher controlled */}
                        <label className="flex items-start p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                          <input
                            type="radio"
                            name="delivery_mode"
                            value="teacher_controlled"
                            checked={settings.delivery_mode === 'teacher_controlled'}
                            onChange={() => handleDeliveryModeChange('teacher_controlled')}
                            className="mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500"
                          />
                          <div className="ml-3 flex-1">
                            <div className="font-medium text-gray-900">Teacher controlled release</div>
                            <div className="text-sm text-gray-600">
                              You'll manually release each group when ready
                            </div>
                            
                            {settings.delivery_mode === 'teacher_controlled' && (
                              <div className="mt-3 pl-6 border-l-2 border-gray-200">
                                <div>
                                  <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Group size
                                  </label>
                                  <select
                                    value={settings.group_size || ''}
                                    onChange={(e) => setSettings(prev => ({ 
                                      ...prev, 
                                      group_size: parseInt(e.target.value) 
                                    }))}
                                    className="block w-32 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                                  >
                                    <option value="">Select...</option>
                                    {[5, 6, 7, 8].map(size => (
                                      <option key={size} value={size}>
                                        {size} words
                                      </option>
                                    ))}
                                  </select>
                                  {settings.group_size && settingsData && (
                                    <p className="text-xs text-gray-500 mt-1">
                                      This will create {Math.ceil(settingsData.total_words / settings.group_size)} groups
                                    </p>
                                  )}
                                </div>
                                
                                {settings.released_groups.length > 0 && (
                                  <div className="mt-3">
                                    <p className="text-sm text-gray-700">
                                      Released groups: {settings.released_groups.join(', ')}
                                    </p>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        </label>
                      </div>
                    </div>

                    {/* Test Settings */}
                    <div className="border-t pt-6">
                      <h4 className="text-base font-medium text-gray-900 mb-4">
                        Test Configuration
                      </h4>

                      <div className="space-y-4">
                        {/* Test Retakes */}
                        <div className="flex items-start">
                          <input
                            type="checkbox"
                            id="allow_retakes"
                            checked={settings.allow_test_retakes}
                            onChange={(e) => setSettings(prev => ({ 
                              ...prev, 
                              allow_test_retakes: e.target.checked 
                            }))}
                            className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded mt-1"
                          />
                          <div className="ml-3">
                            <label htmlFor="allow_retakes" className="font-medium text-gray-700">
                              Allow test retakes
                            </label>
                            {settings.allow_test_retakes && (
                              <div className="mt-2 flex items-center">
                                <label className="text-sm text-gray-600 mr-2">
                                  Maximum attempts:
                                </label>
                                <input
                                  type="number"
                                  min="1"
                                  max="5"
                                  value={settings.max_test_attempts}
                                  onChange={(e) => setSettings(prev => ({ 
                                    ...prev, 
                                    max_test_attempts: parseInt(e.target.value) || 2 
                                  }))}
                                  className="w-16 px-2 py-1 border border-gray-300 rounded-md text-sm"
                                />
                              </div>
                            )}
                          </div>
                        </div>

                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex justify-end gap-3 pt-6 border-t">
                      <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={handleSave}
                        disabled={saving}
                        className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50"
                      >
                        {saving ? 'Saving...' : 'Save Settings'}
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