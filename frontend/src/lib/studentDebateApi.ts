import { api } from './api'
import {
  DebateAssignmentCard,
  StudentDebate,
  DebateProgress,
  DebatePost,
  StudentPostCreate,
  ChallengeCreate,
  ChallengeResult,
  PositionSelection,
  AssignmentScore
} from '@/types/debate'

// Helper function to convert snake_case to camelCase
function toCamelCase(obj: any): any {
  if (obj === null || obj === undefined) return obj
  if (typeof obj !== 'object') return obj
  if (Array.isArray(obj)) return obj.map(toCamelCase)
  
  return Object.keys(obj).reduce((acc, key) => {
    const camelKey = key.replace(/_([a-z0-9])/g, (_, char) => char.toUpperCase())
    acc[camelKey] = toCamelCase(obj[key])
    return acc
  }, {} as any)
}

// Helper function to convert camelCase to snake_case
function toSnakeCase(obj: any): any {
  if (obj === null || obj === undefined) return obj
  if (typeof obj !== 'object') return obj
  if (Array.isArray(obj)) return obj.map(toSnakeCase)
  
  return Object.keys(obj).reduce((acc, key) => {
    const snakeKey = key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`)
    acc[snakeKey] = toSnakeCase(obj[key])
    return acc
  }, {} as any)
}

// Student Debate API
export const studentDebateApi = {
  // Get all available debate assignments
  async getAssignments(): Promise<DebateAssignmentCard[]> {
    const response = await api.get('/v1/student/debate/assignments')
    return toCamelCase(response.data)
  },

  // Get specific assignment details
  async getAssignment(assignmentId: string): Promise<DebateAssignmentCard> {
    const response = await api.get(`/v1/student/debate/${assignmentId}`)
    return toCamelCase(response.data)
  },

  // Start a debate assignment
  async startAssignment(assignmentId: string): Promise<StudentDebate> {
    const response = await api.post(`/v1/student/debate/${assignmentId}/start`)
    return toCamelCase(response.data)
  },

  // Get current debate state
  async getCurrentDebate(assignmentId: string): Promise<DebateProgress> {
    const response = await api.get(`/v1/student/debate/${assignmentId}/current`)
    const camelCased = toCamelCase(response.data)
    return camelCased
  },

  // Submit a student post
  async submitPost(assignmentId: string, post: StudentPostCreate): Promise<DebatePost> {
    try {
      const snakeCasePost = toSnakeCase(post)
      const response = await api.post(`/v1/student/debate/${assignmentId}/post`, snakeCasePost)
      return toCamelCase(response.data)
    } catch (error: any) {
      // Handle moderation pending case
      if (error.response?.status === 202) {
        throw new Error('Post submitted for review')
      }
      throw error
    }
  },

  // Submit a challenge
  async submitChallenge(assignmentId: string, challenge: ChallengeCreate): Promise<ChallengeResult> {
    const response = await api.post(`/v1/student/debate/${assignmentId}/challenge`, toSnakeCase(challenge))
    return toCamelCase(response.data)
  },

  // Select position for final debate
  async selectPosition(assignmentId: string, selection: PositionSelection): Promise<StudentDebate> {
    const response = await api.post(`/v1/student/debate/${assignmentId}/position`, toSnakeCase(selection))
    return toCamelCase(response.data)
  },

  // Get assignment scores
  async getScores(assignmentId: string): Promise<AssignmentScore> {
    const response = await api.get(`/v1/student/debate/${assignmentId}/scores`)
    return toCamelCase(response.data)
  },

  // Advance to next debate after viewing feedback
  async advanceDebate(assignmentId: string): Promise<StudentDebate> {
    const response = await api.post(`/v1/student/debate/${assignmentId}/advance`)
    return toCamelCase(response.data)
  },

  // Retry AI response generation
  async retryAiResponse(assignmentId: string): Promise<{ success: boolean; message: string }> {
    const response = await api.post(`/v1/student/debate/${assignmentId}/retry-ai-response`)
    return response.data
  },

  // Get rhetorical techniques for reference
  async getTechniques(): Promise<{proper: any[], improper: any[]}> {
    const response = await api.get('/v1/student/debate/techniques/list')
    return toCamelCase(response.data)
  },

  // Utility function to count words
  countWords(text: string): number {
    return text.trim().split(/\s+/).filter(word => word.length > 0).length
  },

  // Format time remaining
  formatTimeRemaining(seconds: number | null): string {
    if (!seconds || seconds <= 0) return 'Time expired'
    
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (hours > 0) {
      return `${hours}h ${minutes}m remaining`
    }
    return `${minutes}m remaining`
  },

  // Get position display text
  getPositionText(position: string | null): string {
    switch (position) {
      case 'pro':
        return 'PRO (Supporting)'
      case 'con':
        return 'CON (Opposing)'
      case 'choice':
        return 'Your Choice'
      default:
        return ''
    }
  },

  // Get debate status text
  getStatusText(status: string): string {
    switch (status) {
      case 'not_started':
        return 'Not Started'
      case 'debate_1':
        return 'Debate 1 in Progress'
      case 'debate_2':
        return 'Debate 2 in Progress'
      case 'debate_3':
        return 'Final Debate in Progress'
      case 'completed':
        return 'Completed'
      default:
        return status
    }
  }
}

export default studentDebateApi