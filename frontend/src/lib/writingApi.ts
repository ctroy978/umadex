import api from './api'
import { 
  WritingAssignment, 
  WritingAssignmentCreate, 
  WritingAssignmentUpdate,
  WritingAssignmentListResponse,
  StudentWritingSubmission,
  StudentWritingSubmissionCreate,
  StudentWritingSubmissionUpdate
} from '@/types/writing'

export const writingApi = {
  // Teacher endpoints
  async createAssignment(data: WritingAssignmentCreate): Promise<WritingAssignment> {
    const response = await api.post('/v1/writing/assignments', data)
    return response.data
  },

  async getAssignments(params?: {
    page?: number
    per_page?: number
    search?: string
    grade_level?: string
    subject?: string
    archived?: boolean
  }): Promise<WritingAssignmentListResponse> {
    const response = await api.get('/v1/writing/assignments', { params })
    return response.data
  },

  async getAssignment(id: string): Promise<WritingAssignment> {
    const response = await api.get(`/v1/writing/assignments/${id}`)
    return response.data
  },

  async updateAssignment(id: string, data: WritingAssignmentUpdate): Promise<WritingAssignment> {
    const response = await api.put(`/v1/writing/assignments/${id}`, data)
    return response.data
  },

  async archiveAssignment(id: string): Promise<void> {
    await api.delete(`/v1/writing/assignments/${id}`)
  },

  async restoreAssignment(id: string): Promise<void> {
    await api.post(`/v1/writing/assignments/${id}/restore`)
  },

  // Student endpoints (to be implemented)
  async submitWriting(data: StudentWritingSubmissionCreate): Promise<StudentWritingSubmission> {
    const response = await api.post('/v1/student/writing/submit', data)
    return response.data
  },

  async updateSubmission(id: string, data: StudentWritingSubmissionUpdate): Promise<StudentWritingSubmission> {
    const response = await api.put(`/v1/student/writing/submissions/${id}`, data)
    return response.data
  },

  async getStudentAssignment(assignmentId: string, classroomId: string): Promise<WritingAssignment> {
    const response = await api.get(`/v1/student/writing/assignments/${assignmentId}`, {
      params: { classroom_id: classroomId }
    })
    return response.data
  },

  async getStudentSubmission(assignmentId: string, classroomId: string): Promise<StudentWritingSubmission | null> {
    try {
      const response = await api.get(`/v1/student/writing/submissions/${assignmentId}`, {
        params: { classroom_id: classroomId }
      })
      return response.data
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null
      }
      throw error
    }
  }
}