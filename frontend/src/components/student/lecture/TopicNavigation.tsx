import { CheckCircle, Circle, PlayCircle } from 'lucide-react'

interface TopicNavigationProps {
  topics: Record<string, { title: string }>
  currentTopic: string | null
  onTopicChange: (topicId: string) => void
  getCompletionStatus: (topicId: string) => 'not-started' | 'in-progress' | 'complete' | 'fully-complete'
}

export function TopicNavigation({
  topics,
  currentTopic,
  onTopicChange,
  getCompletionStatus,
}: TopicNavigationProps) {
  const topicEntries = Object.entries(topics)

  return (
    <div className="flex items-center justify-center space-x-4 overflow-x-auto">
      {topicEntries.map(([topicId, topic], index) => {
        const status = getCompletionStatus(topicId)
        const isActive = currentTopic === topicId

        const getIcon = () => {
          switch (status) {
            case 'fully-complete':
              return <CheckCircle className="h-5 w-5 text-green-400" />
            case 'complete':
              return <CheckCircle className="h-5 w-5 text-green-400" />
            case 'in-progress':
              return <Circle className="h-5 w-5 text-yellow-400" />
            default:
              return <PlayCircle className="h-5 w-5 text-gray-500" />
          }
        }

        const getButtonStyles = () => {
          if (isActive) {
            return 'bg-blue-600 text-white border-blue-500'
          }
          
          switch (status) {
            case 'fully-complete':
            case 'complete':
              return 'bg-green-900/30 text-green-400 border-green-600 hover:bg-green-900/50'
            case 'in-progress':
              return 'bg-yellow-900/30 text-yellow-400 border-yellow-600 hover:bg-yellow-900/50'
            default:
              return 'bg-gray-800 text-gray-400 border-gray-700 hover:bg-gray-700'
          }
        }

        const getTopicIcon = () => {
          // Assign different icons based on topic index or content
          const icons = ['📚', '🔬', '🌍', '⚡', '🎯', '🚀', '💡', '🔍']
          return icons[index % icons.length]
        }

        return (
          <button
            key={topicId}
            onClick={() => onTopicChange(topicId)}
            className={`
              flex items-center space-x-3 px-4 py-3 rounded-lg border-2 transition-all
              min-w-[200px] ${getButtonStyles()}
            `}
          >
            <span className="text-2xl">{getTopicIcon()}</span>
            <div className="flex-1 text-left">
              <p className="font-medium line-clamp-1">{topic.title}</p>
              <p className="text-xs opacity-75">
                {status === 'fully-complete' ? 'All levels complete' :
                 status === 'complete' ? 'Completed' :
                 status === 'in-progress' ? 'In Progress' :
                 'Not Started'}
              </p>
            </div>
            {getIcon()}
          </button>
        )
      })}
    </div>
  )
}