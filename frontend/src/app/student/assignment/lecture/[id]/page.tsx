'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams, useSearchParams } from 'next/navigation'
import { ChevronLeft, X, CheckCircle, Circle, RotateCcw } from 'lucide-react'
import { umalectureApi } from '@/lib/umalectureApi'
import { TopicContentPanel } from '@/components/student/lecture/TopicContentPanel'
import { QuestionPanel } from '@/components/student/lecture/QuestionPanel'
import { TopicNavigation } from '@/components/student/lecture/TopicNavigation'
import type { LectureData, TopicContent } from '@/lib/umalectureApi'

export default function StudentLecturePage() {
  const router = useRouter()
  const params = useParams()
  const searchParams = useSearchParams()
  const assignmentId = params.id as string
  const classroomId = searchParams.get('classroomId')
  
  const [lectureData, setLectureData] = useState<LectureData | null>(null)
  const [currentTopic, setCurrentTopic] = useState<string | null>(null)
  const [currentTab, setCurrentTab] = useState<'basic' | 'intermediate' | 'advanced' | 'expert'>('basic')
  const [topicContent, setTopicContent] = useState<TopicContent | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [exitConfirm, setExitConfirm] = useState(false)

  useEffect(() => {
    fetchLectureData()
  }, [assignmentId])

  useEffect(() => {
    if (currentTopic && lectureData) {
      fetchTopicContent()
    }
  }, [currentTopic, lectureData])

  const fetchLectureData = async () => {
    try {
      setLoading(true)
      // Start the assignment to get/create progress
      const progress = await umalectureApi.startLectureAssignment(assignmentId)
      
      // Get full lecture data for student view
      const data = await umalectureApi.getLectureStudentView(
        progress.lecture_id,
        assignmentId
      )
      
      setLectureData(data)
      
      // Resume from last position or start with first topic
      const resumeTopic = data.progress_metadata?.current_topic || 
        Object.keys(data.lecture_structure?.topics || {})[0]
      const resumeTab = data.progress_metadata?.current_tab || 'basic'
      
      setCurrentTopic(resumeTopic)
      setCurrentTab(resumeTab as any)
    } catch (err) {
      console.error('Failed to load lecture:', err)
      setError('Failed to load lecture. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const fetchTopicContent = async () => {
    if (!currentTopic || !lectureData) return
    
    try {
      const content = await umalectureApi.getTopicAllContent(
        lectureData.id,
        currentTopic,
        assignmentId
      )
      setTopicContent(content)
      
      // Update current position
      await umalectureApi.updateCurrentPosition(assignmentId, {
        current_topic: currentTopic,
        current_tab: currentTab
      })
    } catch (err) {
      console.error('Failed to load topic content:', err)
    }
  }

  const handleTopicChange = async (topicId: string) => {
    // If changing topics, refresh the current topic data to ensure progress is saved
    if (currentTopic && currentTopic !== topicId) {
      await fetchTopicContent()
    }
    
    setCurrentTopic(topicId)
    // Reset to basic tab when changing topics
    setCurrentTab('basic')
  }

  const handleTabChange = async (tab: typeof currentTab) => {
    setCurrentTab(tab)
    
    // Update position
    if (lectureData) {
      await umalectureApi.updateCurrentPosition(assignmentId, {
        current_topic: currentTopic || undefined,
        current_tab: tab
      })
    }
  }

  const handleQuestionComplete = async (
    questionIndex: number,
    isCorrect: boolean
  ) => {
    if (!currentTopic) return
    
    // Update progress
    await umalectureApi.updateProgress({
      assignment_id: assignmentId,
      topic_id: currentTopic,
      tab: currentTab,
      question_index: questionIndex,
      is_correct: isCorrect
    })
    
    // Update local state instead of refetching to preserve feedback
    if (topicContent) {
      const updatedContent = { ...topicContent }
      if (!updatedContent.questions_correct) {
        updatedContent.questions_correct = {}
      }
      if (!updatedContent.questions_correct[currentTab]) {
        updatedContent.questions_correct[currentTab] = []
      }
      updatedContent.questions_correct[currentTab][questionIndex] = isCorrect
      setTopicContent(updatedContent)
    }
  }

  const handleAllQuestionsComplete = async () => {
    if (!topicContent || !currentTopic) return
    
    // Mark current tab as completed
    const updatedContent = { ...topicContent }
    if (!updatedContent.completed_tabs) {
      updatedContent.completed_tabs = []
    }
    if (!updatedContent.completed_tabs.includes(currentTab)) {
      updatedContent.completed_tabs.push(currentTab)
    }
    setTopicContent(updatedContent)
    
    // Find the next available tab
    const tabs: Array<'basic' | 'intermediate' | 'advanced' | 'expert'> = ['basic', 'intermediate', 'advanced', 'expert']
    const currentIndex = tabs.indexOf(currentTab)
    
    // Check if there's a next tab that's not completed
    for (let i = currentIndex + 1; i < tabs.length; i++) {
      const nextTab = tabs[i]
      
      // Check if this tab should be unlocked (previous tab is completed)
      const previousTab = tabs[i - 1]
      const isPreviousCompleted = updatedContent.completed_tabs.includes(previousTab)
      
      if (isPreviousCompleted && !updatedContent.completed_tabs.includes(nextTab)) {
        // Automatically switch to the next tab
        await handleTabChange(nextTab)
        break
      }
    }
  }

  const handleExit = () => {
    if (exitConfirm) {
      router.push(classroomId 
        ? `/student/classrooms/${classroomId}` 
        : '/student/dashboard'
      )
    } else {
      setExitConfirm(true)
      setTimeout(() => setExitConfirm(false), 3000)
    }
  }

  const getTopicCompletionStatus = (topicId: string) => {
    const topicProgress = lectureData?.progress_metadata?.topic_completion?.[topicId]
    if (!topicProgress) return 'not-started'
    
    if (topicProgress.completed_tabs?.length > 0) {
      // Check if all tabs have been completed
      const allTabs = ['basic', 'intermediate', 'advanced', 'expert']
      const allCompleted = allTabs.every(tab => 
        topicProgress.completed_tabs.includes(tab)
      )
      return allCompleted ? 'fully-complete' : 'complete'
    }
    
    if (topicProgress.questions_correct && 
        Object.keys(topicProgress.questions_correct).length > 0) {
      return 'in-progress'
    }
    
    return 'not-started'
  }

  const calculateOverallProgress = () => {
    if (!lectureData?.lecture_structure?.topics) return { completed: 0, total: 0 }
    
    const topics = Object.keys(lectureData.lecture_structure.topics)
    const completedTopics = topics.filter(topicId => {
      const status = getTopicCompletionStatus(topicId)
      return status === 'complete' || status === 'fully-complete'
    })
    
    return {
      completed: completedTopics.length,
      total: topics.length
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto"></div>
          <p className="mt-4 text-gray-400">Loading lecture...</p>
        </div>
      </div>
    )
  }

  if (error || !lectureData) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error || 'Failed to load lecture'}</p>
          <button
            onClick={() => router.push(classroomId 
              ? `/student/classrooms/${classroomId}` 
              : '/student/dashboard'
            )}
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  const progress = calculateOverallProgress()

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      {/* Header Bar */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-white font-medium">{lectureData.title}</h1>
          <div className="flex items-center space-x-2 text-sm text-gray-400">
            <span>{progress.completed} of {progress.total} topics complete</span>
            <div className="w-32 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div 
                className="h-full bg-green-500 transition-all duration-300"
                style={{ width: `${(progress.completed / progress.total) * 100}%` }}
              />
            </div>
          </div>
        </div>
        <button
          onClick={handleExit}
          className="text-gray-400 hover:text-white transition-colors"
        >
          {exitConfirm ? (
            <span className="text-sm">Click again to exit</span>
          ) : (
            <X className="h-5 w-5" />
          )}
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Tabbed Content */}
        <div className="flex-1 bg-gray-800">
          {currentTopic && topicContent && (
            <TopicContentPanel
              topic={topicContent}
              currentTab={currentTab}
              onTabChange={handleTabChange}
              completedTabs={topicContent.completed_tabs || []}
              questionsCorrect={topicContent.questions_correct || {}}
            />
          )}
        </div>

        {/* Right Panel - Questions */}
        <div className="w-[480px] bg-gray-850 border-l border-gray-700">
          {currentTopic && topicContent && (
            <QuestionPanel
              key={`${currentTopic}-${currentTab}`}
              questions={topicContent.difficulty_levels[currentTab]?.questions || []}
              difficulty={currentTab}
              topicId={currentTopic}
              assignmentId={assignmentId}
              lectureId={lectureData.id}
              questionsCorrect={topicContent.questions_correct?.[currentTab] || []}
              images={topicContent.images}
              onQuestionComplete={handleQuestionComplete}
              onAllQuestionsComplete={handleAllQuestionsComplete}
            />
          )}
        </div>
      </div>

      {/* Bottom Navigation */}
      <div className="bg-gray-800 border-t border-gray-700 px-6 py-4">
        {lectureData.lecture_structure?.topics && (
          <TopicNavigation
            topics={lectureData.lecture_structure.topics}
            currentTopic={currentTopic}
            onTopicChange={handleTopicChange}
            getCompletionStatus={getTopicCompletionStatus}
          />
        )}
      </div>
    </div>
  )
}