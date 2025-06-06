export interface TestQuestion {
  question: string
  answer_key?: string
  difficulty: number
  grading_context?: string
}

export interface TestStartResponse {
  test_id: string
  test_attempt_id: string
  assignment_id: string
  assignment_title: string
  total_questions: number
  time_limit_minutes?: number
  current_question: number
  status: string
  attempt_number: number
  saved_answers: Record<string, string>
}

export interface TestProgressResponse {
  current_question: number
  total_questions: number
  answered_questions: number[]
  time_spent_seconds: number
  status: string
  saved_answers: Record<string, string>
}

export interface ReadingChunk {
  chunk_number: number
  content: string
  has_image: boolean
  images?: {
    url: string
    thumbnail_url: string
    description?: string
    image_tag: string
  }[]
}

export interface ReadingContentResponse {
  chunks: ReadingChunk[]
  total_chunks: number
  assignment_title: string
}

export interface SaveAnswerRequest {
  question_index: number
  answer: string
  time_spent_seconds: number
}

export interface SecurityIncidentRequest {
  incident_type: 'focus_loss' | 'tab_switch' | 'navigation_attempt' | 'window_blur' | 'app_switch' | 'orientation_cheat'
  incident_data?: Record<string, any>
}

export interface SecurityStatusResponse {
  violation_count: number
  is_locked: boolean
  locked_at?: string
  locked_reason?: string
  warnings_given: number
}