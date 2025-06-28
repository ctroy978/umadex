import { useState } from 'react'
import { XMarkIcon, CheckCircleIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { WritingTechnique } from '@/types/writing'

interface TechniquesPanelProps {
  isOpen: boolean
  onClose: () => void
  techniques: WritingTechnique[]
  selectedTechniques: string[]
  onTechniqueToggle: (technique: string) => void
}

export default function TechniquesPanel({
  isOpen,
  onClose,
  techniques,
  selectedTechniques,
  onTechniqueToggle
}: TechniquesPanelProps) {
  const [activeCategory, setActiveCategory] = useState<WritingTechnique['category']>('rhetorical')

  if (!isOpen) return null

  const categories = [
    { id: 'rhetorical', name: 'Rhetorical Devices', color: 'blue' },
    { id: 'narrative', name: 'Narrative Elements', color: 'purple' },
    { id: 'structural', name: 'Structural Elements', color: 'green' },
    { id: 'descriptive', name: 'Descriptive Techniques', color: 'yellow' },
    { id: 'persuasive', name: 'Persuasive Elements', color: 'red' }
  ]

  const filteredTechniques = techniques.filter(t => t.category === activeCategory)

  return (
    <>
      {/* Overlay */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 z-50 h-full w-full sm:w-[28rem] bg-white shadow-2xl flex flex-col">
        {/* Header */}
        <div className="bg-blue-600 text-white px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <SparklesIcon className="h-6 w-6 mr-2" />
              <h2 className="text-xl font-semibold">Writing Techniques</h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-blue-700 rounded-lg transition-colors"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
          <p className="text-sm text-blue-100 mt-2">
            Select up to 5 techniques to use in your writing for bonus points!
          </p>
        </div>

        {/* Selected count */}
        <div className="bg-gray-50 px-6 py-3 border-b">
          <p className="text-sm font-medium text-gray-700">
            Selected: {selectedTechniques.length} / 5 techniques
          </p>
        </div>

        {/* Category tabs */}
        <div className="flex border-b border-gray-200 overflow-x-auto">
          {categories.map((category) => (
            <button
              key={category.id}
              onClick={() => setActiveCategory(category.id as WritingTechnique['category'])}
              className={`
                px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors
                ${activeCategory === category.id
                  ? `text-${category.color}-600 border-b-2 border-${category.color}-600`
                  : 'text-gray-600 hover:text-gray-800'
                }
              `}
            >
              {category.name}
            </button>
          ))}
        </div>

        {/* Techniques list */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {filteredTechniques.map((technique) => {
            const isSelected = selectedTechniques.includes(technique.name)
            const isDisabled = !isSelected && selectedTechniques.length >= 5

            return (
              <div
                key={technique.name}
                className={`
                  rounded-lg p-4 border-2 transition-all cursor-pointer
                  ${isSelected
                    ? 'bg-blue-50 border-blue-300'
                    : isDisabled
                    ? 'bg-gray-50 border-gray-200 opacity-50 cursor-not-allowed'
                    : 'bg-white border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                  }
                `}
                onClick={() => !isDisabled && onTechniqueToggle(technique.name)}
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-gray-900">{technique.displayName}</h3>
                  {isSelected && (
                    <CheckCircleIcon className="h-5 w-5 text-blue-600 flex-shrink-0" />
                  )}
                </div>
                
                <p className="text-sm text-gray-700 mb-2">{technique.description}</p>
                
                <div className="bg-gray-100 rounded p-2 mb-2">
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Example:</span> {technique.example}
                  </p>
                </div>
                
                <div className="flex items-start">
                  <SparklesIcon className="h-4 w-4 text-yellow-500 mr-1 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Tip:</span> {technique.tipOrReason}
                  </p>
                </div>

                {isSelected && (
                  <div className="mt-3 p-2 bg-green-100 rounded text-sm text-green-800">
                    +5% bonus points when used effectively!
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Done Selecting
          </button>
        </div>
      </div>
    </>
  )
}