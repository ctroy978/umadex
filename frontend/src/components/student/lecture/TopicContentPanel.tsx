import { useState } from 'react'
import { CheckCircle, Circle, Lock, X } from 'lucide-react'
import type { TopicContent } from '@/lib/umalectureApi'

interface TopicContentPanelProps {
  topic: TopicContent
  currentTab: 'basic' | 'intermediate' | 'advanced' | 'expert'
  onTabChange: (tab: 'basic' | 'intermediate' | 'advanced' | 'expert') => void
  completedTabs: string[]
  questionsCorrect: Record<string, boolean[]>
}

const TABS = [
  { id: 'basic', label: 'Basic', icon: '🌱' },
  { id: 'intermediate', label: 'Intermediate', icon: '🌿' },
  { id: 'advanced', label: 'Advanced', icon: '🌳' },
  { id: 'expert', label: 'Expert', icon: '🏆' },
] as const

export function TopicContentPanel({
  topic,
  currentTab,
  onTabChange,
  completedTabs,
  questionsCorrect,
}: TopicContentPanelProps) {
  const [expandedImage, setExpandedImage] = useState<string | null>(null)

  const getTabStatus = (tabId: string) => {
    if (completedTabs.includes(tabId)) return 'complete'
    if (questionsCorrect[tabId]?.some(correct => correct === true)) return 'in-progress'
    return 'not-started'
  }

  const isTabLocked = (tabId: string) => {
    // Basic is never locked
    if (tabId === 'basic') return false
    
    // Other tabs are locked until previous is complete
    const tabIndex = TABS.findIndex(t => t.id === tabId)
    if (tabIndex === -1) return true
    
    const previousTab = TABS[tabIndex - 1]
    return !completedTabs.includes(previousTab.id)
  }

  const renderContent = () => {
    const content = topic.difficulty_levels[currentTab]?.content
    if (!content) return <p className="text-gray-400">Content not available</p>

    // Split content into paragraphs and detect image placeholders
    const paragraphs = content.split('\n\n')
    const relevantImages = topic.images.filter(img => 
      topic.difficulty_levels[currentTab]?.content?.includes('[Image')
    )

    return (
      <div className="prose prose-invert max-w-none">
        {paragraphs.map((paragraph, index) => {
          // Check if paragraph references an image
          const imageMatch = paragraph.match(/\[Image (\d+)\]/)
          if (imageMatch && relevantImages[parseInt(imageMatch[1]) - 1]) {
            const image = relevantImages[parseInt(imageMatch[1]) - 1]
            return (
              <div key={index} className="my-6">
                <div 
                  className="cursor-pointer group"
                  onClick={() => setExpandedImage(image.display_url || image.original_url)}
                >
                  <img
                    src={image.thumbnail_url || image.original_url}
                    alt={image.teacher_description}
                    className="rounded-lg shadow-lg max-w-xs mx-auto group-hover:opacity-90 transition-opacity"
                  />
                  <p className="text-sm text-gray-400 mt-2 text-center italic">
                    {image.ai_description || image.teacher_description}
                  </p>
                  <p className="text-xs text-gray-500 text-center mt-1">
                    Click to enlarge
                  </p>
                </div>
              </div>
            )
          }

          return (
            <p key={index} className="mb-4 text-gray-300 leading-relaxed">
              {paragraph}
            </p>
          )
        })}

        {/* Show remaining images at the end if not already shown */}
        {topic.images.length > 0 && (
          <div className="mt-8 border-t border-gray-700 pt-6">
            <h3 className="text-lg font-medium text-white mb-4">Related Images</h3>
            <div className="grid grid-cols-2 gap-4">
              {topic.images.map((image, index) => (
                <div 
                  key={image.id}
                  className="cursor-pointer group"
                  onClick={() => setExpandedImage(image.display_url || image.original_url)}
                >
                  <img
                    src={image.thumbnail_url || image.original_url}
                    alt={image.teacher_description}
                    className="rounded-lg shadow-lg w-full h-32 object-cover group-hover:opacity-90 transition-opacity"
                  />
                  <p className="text-xs text-gray-400 mt-2 italic line-clamp-2">
                    {image.ai_description || image.teacher_description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Tab Navigation */}
      <div className="bg-gray-900 border-b border-gray-700 px-6 py-3">
        <h2 className="text-xl font-medium text-white mb-3">{topic.title}</h2>
        <div className="flex space-x-4">
          {TABS.map((tab) => {
            const status = getTabStatus(tab.id)
            const locked = isTabLocked(tab.id)
            
            return (
              <button
                key={tab.id}
                onClick={() => !locked && onTabChange(tab.id as any)}
                disabled={locked}
                className={`
                  px-4 py-2 rounded-lg flex items-center space-x-2 transition-all
                  ${currentTab === tab.id 
                    ? 'bg-blue-600 text-white' 
                    : locked
                    ? 'bg-gray-800 text-gray-600 cursor-not-allowed'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }
                `}
              >
                <span className="text-lg">{tab.icon}</span>
                <span>{tab.label}</span>
                {locked ? (
                  <Lock className="h-4 w-4" />
                ) : status === 'complete' ? (
                  <CheckCircle className="h-4 w-4 text-green-400" />
                ) : status === 'in-progress' ? (
                  <Circle className="h-4 w-4 text-yellow-400" />
                ) : null}
              </button>
            )
          })}
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {renderContent()}
      </div>

      {/* Image Modal */}
      {expandedImage && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-90 z-50 flex items-center justify-center p-4"
          onClick={() => setExpandedImage(null)}
        >
          <img
            src={expandedImage}
            alt="Expanded view"
            className="max-w-full max-h-full rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
          <button
            onClick={() => setExpandedImage(null)}
            className="absolute top-4 right-4 text-white bg-gray-800 rounded-full p-2 hover:bg-gray-700"
          >
            <X className="h-6 w-6" />
          </button>
        </div>
      )}
    </div>
  )
}