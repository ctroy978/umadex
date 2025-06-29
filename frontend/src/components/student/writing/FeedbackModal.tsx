import { Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon, CheckCircleIcon, XCircleIcon, LightBulbIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import { WritingFeedback } from '@/types/writing'

interface FeedbackModalProps {
  isOpen: boolean
  onClose: () => void
  feedback: WritingFeedback
  canRevise: boolean
  onRevise: () => void
}

export default function FeedbackModal({
  isOpen,
  onClose,
  feedback,
  canRevise,
  onRevise
}: FeedbackModalProps) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getScoreBgColor = (score: number) => {
    if (score >= 80) return 'bg-green-100'
    if (score >= 60) return 'bg-yellow-100'
    return 'bg-red-100'
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
                <Dialog.Title as="div" className="flex items-center justify-between mb-6">
                  <h3 className="text-2xl font-bold text-gray-900">Writing Feedback</h3>
                  <button
                    onClick={onClose}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <XMarkIcon className="h-5 w-5 text-gray-400" />
                  </button>
                </Dialog.Title>

                {/* Overall Score */}
                <div className={`mb-8 p-6 rounded-xl ${getScoreBgColor(feedback.overall_score)}`}>
                  <div className="flex items-center justify-between">
                    <h4 className="text-lg font-semibold text-gray-900">Overall Score</h4>
                    <span className={`text-3xl font-bold ${getScoreColor(feedback.overall_score)}`}>
                      {Math.round(feedback.overall_score)}%
                    </span>
                  </div>
                  <p className="mt-2 text-gray-700">{feedback.general_feedback}</p>
                  {feedback.core_score !== undefined && feedback.bonus_points !== undefined && (
                    <div className="mt-3 text-sm text-gray-600">
                      Core: {feedback.core_score}/100 • Bonus: +{feedback.bonus_points}
                    </div>
                  )}
                </div>

                {/* Criteria Scores */}
                {feedback.criteria_scores && Object.keys(feedback.criteria_scores).length > 0 && (
                  <div className="mb-8">
                    <h4 className="text-lg font-semibold text-gray-900 mb-4">Criteria Evaluation</h4>
                    <div className="space-y-4">
                      {Object.entries(feedback.criteria_scores).map(([criterion, data]: [string, any]) => {
                        if (!data) return null
                        return (
                          <div key={criterion} className="bg-gray-50 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                              <h5 className="font-medium text-gray-900">
                                {criterion.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              </h5>
                              {data.score !== undefined && (
                                <span className={`font-semibold ${getScoreColor((data.score / 40) * 100)}`}>
                                  {data.score}/{criterion === 'content_purpose' ? 40 : criterion === 'teacher_criteria' ? 35 : 25}
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-gray-700 mb-2">{data.reasoning || data.feedback}</p>
                            {data.strengths && data.strengths.length > 0 && (
                              <div className="mt-2">
                                <p className="text-xs font-medium text-green-600 mb-1">Strengths:</p>
                                <ul className="text-xs text-gray-600 space-y-1">
                                  {data.strengths.map((strength: string, idx: number) => (
                                    <li key={idx} className="flex items-start">
                                      <CheckCircleIcon className="h-3 w-3 text-green-500 mr-1 flex-shrink-0 mt-0.5" />
                                      {strength}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {data.suggestions && data.suggestions.length > 0 && (
                              <div className="mt-2">
                                <p className="text-xs font-medium text-gray-600 mb-1">Suggestions:</p>
                                <ul className="text-xs text-gray-600 space-y-1">
                                  {data.suggestions.map((suggestion: string, idx: number) => (
                                    <li key={idx} className="flex items-start">
                                      <LightBulbIcon className="h-3 w-3 text-yellow-500 mr-1 flex-shrink-0 mt-0.5" />
                                      {suggestion}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* Technique Validation */}
                {feedback.technique_validation && (
                  feedback.technique_validation.techniques?.length > 0 ? (
                    <div className="mb-8">
                      <h4 className="text-lg font-semibold text-gray-900 mb-4">Technique Usage</h4>
                      <div className="space-y-3">
                        {feedback.technique_validation.techniques.map((technique: any) => (
                          <div key={technique.name} className={`rounded-lg p-4 border-2 ${
                            technique.found ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                          }`}>
                            <div className="flex items-center justify-between mb-2">
                              <h5 className="font-medium text-gray-900">{technique.name}</h5>
                              {technique.found ? (
                                <CheckCircleIcon className="h-5 w-5 text-green-600" />
                              ) : (
                                <XCircleIcon className="h-5 w-5 text-red-600" />
                              )}
                            </div>
                            <p className="text-sm text-gray-700">{technique.feedback}</p>
                            {technique.example && (
                              <div className="mt-2">
                                <p className="text-xs font-medium text-gray-600 mb-1">Example found:</p>
                                <p className="text-xs text-gray-600 italic">"{technique.example}"</p>
                              </div>
                            )}
                            {technique.found && technique.points_awarded > 0 && (
                              <div className="mt-2 text-sm font-medium text-green-700">
                                +{technique.points_awarded}% bonus points earned!
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : Object.keys(feedback.technique_validation).length > 0 && (
                    // Fallback for object-based technique validation
                    <div className="mb-8">
                      <h4 className="text-lg font-semibold text-gray-900 mb-4">Technique Usage</h4>
                      <div className="space-y-3">
                        {Object.entries(feedback.technique_validation).map(([technique, data]: [string, any]) => (
                          <div key={technique} className={`rounded-lg p-4 border-2 ${
                            data.found ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                          }`}>
                            <div className="flex items-center justify-between mb-2">
                              <h5 className="font-medium text-gray-900">{technique}</h5>
                              {data.found ? (
                                <CheckCircleIcon className="h-5 w-5 text-green-600" />
                              ) : (
                                <XCircleIcon className="h-5 w-5 text-red-600" />
                              )}
                            </div>
                            <p className="text-sm text-gray-700">{data.feedback}</p>
                            {data.examples && data.examples.length > 0 && (
                              <div className="mt-2">
                                <p className="text-xs font-medium text-gray-600 mb-1">Examples found:</p>
                                <ul className="text-xs text-gray-600 space-y-1">
                                  {data.examples.map((example: string, idx: number) => (
                                    <li key={idx} className="italic">"{example}"</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {data.found && (
                              <div className="mt-2 text-sm font-medium text-green-700">
                                +5% bonus points earned!
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                )}

                {/* Revision Suggestions */}
                {feedback.revision_suggestions.length > 0 && (
                  <div className="mb-8">
                    <h4 className="text-lg font-semibold text-gray-900 mb-4">Suggestions for Improvement</h4>
                    <ul className="space-y-2">
                      {feedback.revision_suggestions.map((suggestion, idx) => (
                        <li key={idx} className="flex items-start">
                          <ArrowPathIcon className="h-4 w-4 text-blue-500 mr-2 flex-shrink-0 mt-0.5" />
                          <span className="text-sm text-gray-700">{suggestion}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-4">
                  {canRevise && (
                    <button
                      onClick={onRevise}
                      className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      Revise My Response
                    </button>
                  )}
                  <button
                    onClick={onClose}
                    className={`px-6 py-3 ${canRevise ? 'flex-1' : 'w-full'} bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors`}
                  >
                    {canRevise ? 'Close' : 'Done'}
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}