import { Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon, ChatBubbleLeftRightIcon, ClockIcon, AcademicCapIcon } from '@heroicons/react/24/outline'
import type { DebateAssignmentMetadata, DebateConfiguration } from '@/types/debate'

interface DebatePreviewProps {
  metadata: DebateAssignmentMetadata
  config: DebateConfiguration
  onClose: () => void
}

export default function DebatePreview({ metadata, config, onClose }: DebatePreviewProps) {
  const getDifficultyColor = (level: string) => {
    switch (level) {
      case 'beginner': return 'text-green-600'
      case 'intermediate': return 'text-yellow-600'
      case 'advanced': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  const getFallacyFrequencyLabel = (frequency: string) => {
    switch (frequency) {
      case 'every_1_2': return 'Frequent (every 1-2 rounds)'
      case 'every_2_3': return 'Moderate (every 2-3 rounds)'
      case 'every_3_4': return 'Occasional (every 3-4 rounds)'
      case 'disabled': return 'Disabled'
      default: return frequency
    }
  }

  return (
    <Transition.Root show={true} as={Fragment}>
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
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-2xl sm:p-6">
                <div className="absolute right-0 top-0 pr-4 pt-4">
                  <button
                    type="button"
                    className="rounded-md bg-white text-gray-400 hover:text-gray-500"
                    onClick={onClose}
                  >
                    <span className="sr-only">Close</span>
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </div>

                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 sm:mx-0 sm:h-10 sm:w-10">
                    <ChatBubbleLeftRightIcon className="h-6 w-6 text-blue-600" />
                  </div>
                  <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left w-full">
                    <Dialog.Title as="h3" className="text-lg font-semibold leading-6 text-gray-900">
                      Assignment Preview
                    </Dialog.Title>
                    
                    <div className="mt-4 space-y-4">
                      {/* Basic Information */}
                      <div className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-2">Basic Information</h4>
                        <dl className="space-y-1 text-sm">
                          <div>
                            <dt className="inline font-medium text-gray-500">Title:</dt>
                            <dd className="inline ml-2 text-gray-900">{metadata.title}</dd>
                          </div>
                          <div>
                            <dt className="inline font-medium text-gray-500">Topic:</dt>
                            <dd className="inline ml-2 text-gray-900">{metadata.topic}</dd>
                          </div>
                          {metadata.description && (
                            <div>
                              <dt className="font-medium text-gray-500">Description:</dt>
                              <dd className="mt-1 text-gray-900">{metadata.description}</dd>
                            </div>
                          )}
                          <div className="flex space-x-4 mt-2">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                              {metadata.gradeLevel}
                            </span>
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                              {metadata.subject}
                            </span>
                          </div>
                        </dl>
                      </div>


                      {/* Difficulty & AI Settings */}
                      <div className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-2">Difficulty & AI Settings</h4>
                        <dl className="space-y-2 text-sm">
                          <div className="flex items-center">
                            <dt className="text-gray-500">Difficulty Level:</dt>
                            <dd className={`ml-2 font-medium capitalize ${getDifficultyColor(config.difficultyLevel)}`}>
                              {config.difficultyLevel}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-gray-500">Logical Fallacies:</dt>
                            <dd className="ml-2">{getFallacyFrequencyLabel(config.fallacyFrequency)}</dd>
                          </div>
                          <div className="flex items-center">
                            <dt className="text-gray-500">AI Personalities:</dt>
                            <dd className="ml-2">
                              {config.aiPersonalitiesEnabled ? (
                                <span className="text-green-600">Enabled</span>
                              ) : (
                                <span className="text-gray-400">Disabled</span>
                              )}
                            </dd>
                          </div>
                        </dl>
                      </div>

                      {/* Moderation Settings */}
                      <div className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-2">Content Moderation</h4>
                        <dl className="space-y-2 text-sm">
                          <div className="flex items-center">
                            <dt className="text-gray-500">Content Moderation:</dt>
                            <dd className="ml-2">
                              {config.contentModerationEnabled ? (
                                <span className="text-green-600">Enabled</span>
                              ) : (
                                <span className="text-gray-400">Disabled</span>
                              )}
                            </dd>
                          </div>
                          {config.contentModerationEnabled && (
                            <div className="flex items-center">
                              <dt className="text-gray-500">Auto-flag Off-topic:</dt>
                              <dd className="ml-2">
                                {config.autoFlagOffTopic ? (
                                  <span className="text-green-600">Yes</span>
                                ) : (
                                  <span className="text-gray-400">No</span>
                                )}
                              </dd>
                            </div>
                          )}
                        </dl>
                      </div>

                      {/* Student Experience Preview */}
                      <div className="border-t pt-4">
                        <h4 className="font-medium text-gray-900 mb-2">Student Experience</h4>
                        <p className="text-sm text-gray-600">
                          Students will participate in debates on the topic: 
                          <span className="font-medium"> "{metadata.topic}"</span>
                        </p>
                        {config.aiPersonalitiesEnabled && (
                          <p className="text-sm text-gray-600 mt-2">
                            Students will face different AI opponents with unique debating styles.
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="mt-6 flex justify-end">
                      <button
                        type="button"
                        className="rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
                        onClick={onClose}
                      >
                        Close Preview
                      </button>
                    </div>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}