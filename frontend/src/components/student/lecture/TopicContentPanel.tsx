import { useState } from 'react'
import { CheckCircle, Circle, Lock, X } from 'lucide-react'
import { ExplorationContent } from './ExplorationContent'
import ImageModal from '../umaread/ImageModal'
import type { TopicContent } from '@/lib/umalectureApi'

interface TopicContentPanelProps {
  topic: TopicContent
  currentTab: 'basic' | 'intermediate' | 'advanced' | 'expert'
  onTabChange: (tab: 'basic' | 'intermediate' | 'advanced' | 'expert') => void
  completedTabs: string[]
  questionsCorrect: Record<string, boolean[]>
  lectureId: string
  gradeLevel: string
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
  lectureId,
  gradeLevel,
}: TopicContentPanelProps) {
  const [selectedImage, setSelectedImage] = useState<{ url: string; description: string } | null>(null)

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

    return (
      <>
        <div className="prose prose-invert max-w-none">
          <ExplorationContent
            content={content}
            topicId={topic.id}
            topicTitle={topic.title}
            difficultyLevel={currentTab}
            gradeLevel={gradeLevel}
            lectureId={lectureId}
          />
        </div>

        {/* Display images at the bottom if available */}
        {topic.images && topic.images.length > 0 && (
          <div className="mt-8 pt-6 border-t border-gray-700">
            <h3 className="text-lg font-medium text-white mb-4">Reference Images</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {topic.images.map((image, index) => (
                <button
                  key={image.id}
                  onClick={() => setSelectedImage({
                    url: image.display_url || image.original_url,
                    description: image.ai_description || image.teacher_description || ''
                  })}
                  className="relative group cursor-pointer overflow-hidden rounded-lg shadow-md hover:shadow-xl transition-all duration-200 bg-gray-800"
                >
                  <img
                    src={image.thumbnail_url || image.original_url}
                    alt={image.teacher_description}
                    className="w-full h-32 object-cover group-hover:opacity-90 transition-opacity"
                  />
                  <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-opacity flex items-center justify-center">
                    <span className="text-white opacity-0 group-hover:opacity-100 transition-opacity bg-black bg-opacity-70 px-3 py-1 rounded text-sm">
                      Click to view
                    </span>
                  </div>
                  <div className="p-2">
                    <p className="text-xs text-gray-400 line-clamp-2">
                      {image.teacher_description}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </>
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
      {selectedImage && (
        <ImageModal
          imageUrl={selectedImage.url}
          altText={selectedImage.description}
          onClose={() => setSelectedImage(null)}
        />
      )}
    </div>
  )
}