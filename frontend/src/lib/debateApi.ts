import { api } from './api'
import type {
  DebateAssignmentCreate,
  DebateAssignmentUpdate,
  DebateAssignment,
  DebateAssignmentListResponse,
  ContentFlag,
  ContentFlagUpdate
} from '@/types/debate'

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

// Helper function to convert snake_case to camelCase
function toCamelCase(obj: any): any {
  if (obj === null || obj === undefined) return obj
  if (typeof obj !== 'object') return obj
  if (Array.isArray(obj)) return obj.map(toCamelCase)
  
  return Object.keys(obj).reduce((acc, key) => {
    const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
    acc[camelKey] = toCamelCase(obj[key])
    return acc
  }, {} as any)
}

export const debateApi = {
  // Assignment CRUD operations
  async createAssignment(data: DebateAssignmentCreate): Promise<DebateAssignment> {
    // Convert camelCase to snake_case for backend
    const snakeCaseData = toSnakeCase(data)
    const response = await api.post('/v1/teacher/debate/assignments', snakeCaseData)
    return toCamelCase(response.data)
  },

  async listAssignments(params: {
    page?: number
    per_page?: number
    search?: string
    grade_level?: string
    subject?: string
    date_from?: string
    date_to?: string
    include_archived?: boolean
  } = {}): Promise<DebateAssignmentListResponse> {
    const response = await api.get('/v1/teacher/debate/assignments', { params })
    return toCamelCase(response.data)
  },

  async getAssignment(id: string): Promise<DebateAssignment> {
    const response = await api.get(`/v1/teacher/debate/assignments/${id}`)
    return toCamelCase(response.data)
  },

  async updateAssignment(id: string, data: DebateAssignmentUpdate): Promise<DebateAssignment> {
    const snakeCaseData = toSnakeCase(data)
    const response = await api.put(`/v1/teacher/debate/assignments/${id}`, snakeCaseData)
    return toCamelCase(response.data)
  },

  async archiveAssignment(id: string): Promise<void> {
    await api.delete(`/v1/teacher/debate/assignments/${id}`)
  },

  async restoreAssignment(id: string): Promise<void> {
    await api.post(`/v1/teacher/debate/assignments/${id}/restore`)
  },

  // Content moderation
  async getContentFlags(status?: string): Promise<ContentFlag[]> {
    const params = status ? { status } : {}
    const response = await api.get('/v1/teacher/debate/content-flags', { params })
    return toCamelCase(response.data)
  },

  async updateContentFlag(flagId: string, data: ContentFlagUpdate): Promise<ContentFlag> {
    const snakeCaseData = toSnakeCase(data)
    const response = await api.put(`/v1/teacher/debate/content-flags/${flagId}`, snakeCaseData)
    return toCamelCase(response.data)
  },

  // Topic validation (for assignment creation)
  async validateTopic(topic: string): Promise<{
    isValid: boolean
    confidence: number
    suggestions: string[]
  }> {
    // This will be implemented when AI validation is added
    // For now, return a mock response
    return {
      isValid: true,
      confidence: 0.95,
      suggestions: []
    }
  }
}