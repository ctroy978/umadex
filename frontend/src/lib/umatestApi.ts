import api from './api'

export interface UMATestStartResponse {
  test_attempt_id: string
  test_id: string
  assignment_id: number  // ClassroomAssignment.id is an integer
  assignment_title: string
  test_title: string
  test_description?: string
  status: string
  current_question: number
  total_questions: number
  time_limit_minutes?: number
  attempt_number: number
  max_attempts: number
  saved_answers: Record<string, string>
  questions: UMATestQuestion[]
}

export interface UMATestQuestion {
  id: string
  question_text: string
  difficulty_level: string
  source_lecture_title: string
  topic_title: string
}

export interface SaveAnswerRequest {
  question_index: number
  answer: string
  time_spent_seconds?: number
}

export interface UMATestResultsResponse {
  test_attempt_id: string
  score: number
  status: string
  submitted_at: string
  evaluated_at?: string
  question_evaluations: QuestionEvaluation[]
  feedback?: string
}

export interface QuestionEvaluation {
  question_index: number
  rubric_score: number
  points_earned: number
  max_points: number
  scoring_rationale: string
  feedback?: string
  key_concepts_identified: string[]
  misconceptions_detected: string[]
}

export const umatestApi = {
  // Start or resume a UMATest
  startTest: async (assignmentId: string): Promise<UMATestStartResponse> => {
    const response = await api.post(`/v1/student/umatest/test/${assignmentId}/start`, {})
    return response.data
  },

  // Start test with override code
  startTestWithOverride: async (assignmentId: string, overrideCode: string): Promise<UMATestStartResponse> => {
    const response = await api.post(`/v1/student/umatest/test/${assignmentId}/start`, {}, {
      params: { override_code: overrideCode }
    })
    return response.data
  },

  // Save an answer
  saveAnswer: async (testAttemptId: string, data: SaveAnswerRequest): Promise<{ success: boolean }> => {
    const response = await api.post(`/v1/student/umatest/test/${testAttemptId}/save-answer`, data)
    return response.data
  },

  // Submit test for evaluation
  submitTest: async (testAttemptId: string): Promise<{ success: boolean; test_attempt_id: string }> => {
    const response = await api.post(`/v1/student/umatest/test/${testAttemptId}/submit`)
    return response.data
  },

  // Get test results
  getTestResults: async (testAttemptId: string): Promise<UMATestResultsResponse> => {
    const response = await api.get(`/v1/student/umatest/test/results/${testAttemptId}`)
    return response.data
  },

  // Log security incident
  logSecurityIncident: async (testAttemptId: string, data: {
    incident_type: 'focus_loss' | 'tab_switch' | 'navigation_attempt' | 'window_blur' | 'app_switch' | 'orientation_cheat';
    incident_data?: any;
  }): Promise<{ violation_count: number; warning_issued: boolean; test_locked: boolean }> => {
    const response = await api.post(`/v1/student/umatest/test/${testAttemptId}/security-incident`, data)
    return response.data
  },

  // Get security status
  getSecurityStatus: async (testAttemptId: string): Promise<{
    violation_count: number;
    is_locked: boolean;
    locked_at?: string;
    locked_reason?: string;
    warnings_given: number;
  }> => {
    const response = await api.get(`/v1/student/umatest/test/${testAttemptId}/security-status`)
    return response.data
  },

  // Unlock test with override code
  unlockTest: async (testAttemptId: string, unlockCode: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.post(`/v1/student/umatest/test/${testAttemptId}/unlock`, {
      unlock_code: unlockCode
    })
    return response.data
  }
}