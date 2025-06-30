import api from './api'
import { 
  TestStartResponse, 
  TestProgressResponse, 
  ReadingContentResponse,
  SaveAnswerRequest,
  SecurityIncidentRequest,
  SecurityStatusResponse 
} from '@/types/test'

export const testApi = {
  // Start or resume a test
  async startTest(assignmentId: string): Promise<TestStartResponse> {
    const response = await api.get(`/v1/student/tests/${assignmentId}/start`)
    return response.data
  },

  // Start test with override code
  async startTestWithOverride(assignmentId: string, overrideCode: string): Promise<TestStartResponse> {
    const response = await api.get(`/v1/student/tests/${assignmentId}/start?override_code=${encodeURIComponent(overrideCode)}`)
    return response.data
  },

  // Save answer for a question
  async saveAnswer(testAttemptId: string, data: SaveAnswerRequest): Promise<{ success: boolean; message: string }> {
    const response = await api.post(`/v1/student/tests/${testAttemptId}/save-answer`, data)
    return response.data
  },

  // Get test progress
  async getProgress(testId: string): Promise<TestProgressResponse> {
    const response = await api.get(`/v1/student/tests/${testId}/progress`)
    return response.data
  },

  // Submit test for grading
  async submitTest(testAttemptId: string): Promise<{ success: boolean; message: string; attempt_id: string }> {
    console.log('=== TEST API: submitTest called with testAttemptId:', testAttemptId)
    // Use a longer timeout for test submission since AI evaluation can take time
    const response = await api.post(`/v1/student/tests/${testAttemptId}/submit`, {}, {
      timeout: 120000 // 2 minute timeout for AI evaluation
    })
    console.log('=== TEST API: submitTest response:', response.data)
    return response.data
  },

  // Get reading content for reference
  async getReadingContent(assignmentId: string): Promise<ReadingContentResponse> {
    const response = await api.get(`/v1/student/tests/${assignmentId}/reading-content`)
    return response.data
  },

  // Get test questions
  async getTestQuestions(testId: string): Promise<{ questions: any[]; total_questions: number }> {
    const response = await api.get(`/v1/student/tests/${testId}/questions`)
    return response.data
  },

  // Security-related endpoints
  async logSecurityIncident(testId: string, data: SecurityIncidentRequest): Promise<{
    violation_count: number;
    warning_issued: boolean;
    test_locked: boolean;
  }> {
    const response = await api.post(`/v1/student/tests/${testId}/security-incident`, data)
    return response.data
  },

  async lockTest(testId: string, reason: string): Promise<{
    success: boolean;
    message: string;
    locked_at: string;
  }> {
    const response = await api.post(`/v1/student/tests/${testId}/lock`, { reason })
    return response.data
  },

  async getSecurityStatus(testId: string): Promise<SecurityStatusResponse> {
    const response = await api.get(`/v1/student/tests/${testId}/security-status`)
    return response.data
  },

  async unlockWithBypassCode(testAttemptId: string, bypassCode: string): Promise<{
    success: boolean;
    message: string;
    test_attempt_id: string;
    bypass_type: string;
  }> {
    const response = await api.post(`/v1/student/tests/tests/${testAttemptId}/unlock`, {
      unlock_code: bypassCode.trim()
    })
    return response.data
  }
}