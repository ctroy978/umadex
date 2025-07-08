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
  }
}