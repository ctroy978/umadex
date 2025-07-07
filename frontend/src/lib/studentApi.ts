import api from './api'

export interface StudentClassroom {
  id: string
  name: string
  teacher_name: string
  teacher_id: string
  class_code: string
  joined_at: string
  assignment_count: number
  available_assignment_count: number
  created_at: string
}

export interface StudentAssignment {
  id: string
  title: string
  work_title?: string
  author?: string
  grade_level?: string
  type: string
  item_type: 'reading' | 'vocabulary' | 'debate' | 'writing' | 'lecture'
  assigned_at: string
  start_date?: string
  end_date?: string
  display_order?: number
  status: 'not_started' | 'active' | 'expired'
  is_completed: boolean
  has_started: boolean
  has_test: boolean
  test_completed: boolean
  test_attempt_id?: string
}

export interface StudentClassroomDetail {
  id: string
  name: string
  teacher_name: string
  teacher_id: string
  class_code: string
  joined_at: string
  created_at: string
  assignments: StudentAssignment[]
}

export interface JoinClassroomRequest {
  class_code: string
}

export interface JoinClassroomResponse {
  success: boolean
  message: string
  classroom?: {
    id: string
    name: string
    teacher_id: string
    teacher_name: string
    class_code: string
    created_at: string
    student_count: number
    assignment_count: number
  }
}

export const studentApi = {
  // Get all enrolled classrooms
  async getClassrooms(): Promise<StudentClassroom[]> {
    const response = await api.get('/v1/student/classrooms')
    return response.data
  },

  // Join a classroom using class code
  async joinClassroom(request: JoinClassroomRequest): Promise<JoinClassroomResponse> {
    const response = await api.post('/v1/student/join-classroom', request)
    return response.data
  },

  // Leave a classroom
  async leaveClassroom(classroomId: string): Promise<{ message: string }> {
    const response = await api.delete(`/v1/student/classrooms/${classroomId}/leave`)
    return response.data
  },

  // Get detailed classroom information
  async getClassroomDetail(classroomId: string): Promise<StudentClassroomDetail> {
    const response = await api.get(`/v1/student/classrooms/${classroomId}`)
    return response.data
  },

  // Get available assignments for a classroom
  async getClassroomAssignments(classroomId: string): Promise<any[]> {
    const response = await api.get(`/v1/student/classrooms/${classroomId}/assignments`)
    return response.data
  },

  // Validate assignment access
  async validateAssignmentAccess(assignmentType: 'reading' | 'vocabulary' | 'debate', assignmentId: string): Promise<{
    access_granted: boolean
    classroom_id: string
    classroom_name: string
    assignment_type: string
    assignment_id: string
  }> {
    const response = await api.get(`/v1/student/assignment/${assignmentType}/${assignmentId}/validate`)
    return response.data
  },

  // Get test status for an assignment
  async getAssignmentTestStatus(assignmentId: string): Promise<{ has_test: boolean; test_id?: string }> {
    const response = await api.get(`/v1/student/assignment/reading/${assignmentId}/test-status`)
    return response.data
  },

  // Get vocabulary assignment details
  async getVocabularyAssignment(assignmentId: string): Promise<any> {
    const response = await api.get(`/v1/student/vocabulary/${assignmentId}`)
    return response.data
  },

  // Vocabulary Practice Activities
  async getVocabularyPracticeStatus(assignmentId: string): Promise<VocabularyPracticeStatusResponse> {
    const response = await api.get(`/v1/student/vocabulary/${assignmentId}/practice/status`)
    return response.data
  },


  // Story Builder Activities
  async startStoryBuilder(assignmentId: string): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/${assignmentId}/practice/start-story-builder`)
    return response.data
  },

  async submitStory(storyAttemptId: string, data: {
    prompt_id: string
    story_text: string
    attempt_number: number
  }): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/practice/submit-story/${storyAttemptId}`, data)
    return response.data
  },

  async getNextStoryPrompt(storyAttemptId: string): Promise<any> {
    const response = await api.get(`/v1/student/vocabulary/practice/next-story-prompt/${storyAttemptId}`)
    return response.data
  },

  async confirmStoryCompletion(storyAttemptId: string): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/practice/confirm-story-completion/${storyAttemptId}`)
    return response.data
  },

  async declineStoryCompletion(storyAttemptId: string): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/practice/decline-story-completion/${storyAttemptId}`)
    return response.data
  },

  // Concept Mapping API methods
  async startConceptMapping(assignmentId: string): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/${assignmentId}/practice/start-concept-mapping`)
    return response.data
  },

  async submitConceptMap(conceptAttemptId: string, data: {
    word_id: string
    definition: string
    synonyms: string
    antonyms: string
    context_theme: string
    connotation: string
    example_sentence: string
    time_spent_seconds: number
  }): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/practice/submit-concept-map/${conceptAttemptId}`, data)
    return response.data
  },

  async getConceptMapProgress(conceptAttemptId: string): Promise<any> {
    const response = await api.get(`/v1/student/vocabulary/practice/concept-map-progress/${conceptAttemptId}`)
    return response.data
  },

  async finishConceptMappingEarly(conceptAttemptId: string): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/practice/finish-concept-mapping-early/${conceptAttemptId}`)
    return response.data
  },

  // Puzzle Path APIs
  async startPuzzlePath(assignmentId: string): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/${assignmentId}/practice/start-puzzle-path`)
    return response.data
  },

  async submitPuzzleAnswer(puzzleAttemptId: string, data: {
    puzzle_id: string
    student_answer: string
    time_spent_seconds: number
  }): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/practice/submit-puzzle-answer/${puzzleAttemptId}`, data)
    return response.data
  },

  async getPuzzlePathProgress(puzzleAttemptId: string): Promise<any> {
    const response = await api.get(`/v1/student/vocabulary/practice/puzzle-path-progress/${puzzleAttemptId}`)
    return response.data
  },

  async confirmPuzzleCompletion(puzzleAttemptId: string): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/practice/confirm-puzzle-completion/${puzzleAttemptId}`)
    return response.data
  },

  async declinePuzzleCompletion(puzzleAttemptId: string): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/practice/decline-puzzle-completion/${puzzleAttemptId}`)
    return response.data
  },

  async confirmConceptCompletion(conceptAttemptId: string): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/practice/confirm-concept-completion/${conceptAttemptId}`)
    return response.data
  },

  async declineConceptCompletion(conceptAttemptId: string): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/practice/decline-concept-completion/${conceptAttemptId}`)
    return response.data
  },

  // Fill-in-the-Blank APIs
  async startFillInBlank(assignmentId: string): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/${assignmentId}/practice/start-fill-in-blank`)
    return response.data
  },

  async submitFillInBlankAnswer(fillInBlankAttemptId: string, data: {
    sentence_id: string
    student_answer: string
    time_spent_seconds: number
  }): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/practice/submit-fill-in-blank-answer/${fillInBlankAttemptId}`, data)
    return response.data
  },

  async getFillInBlankProgress(fillInBlankAttemptId: string): Promise<any> {
    const response = await api.get(`/v1/student/vocabulary/practice/fill-in-blank-progress/${fillInBlankAttemptId}`)
    return response.data
  },

  async confirmFillInBlankCompletion(fillInBlankAttemptId: string): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/practice/confirm-fill-in-blank-completion/${fillInBlankAttemptId}`)
    return response.data
  },

  async declineFillInBlankCompletion(fillInBlankAttemptId: string): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/practice/decline-fill-in-blank-completion/${fillInBlankAttemptId}`)
    return response.data
  },

  // Vocabulary Test APIs
  async checkVocabularyTestEligibility(assignmentId: string): Promise<VocabularyTestEligibilityResponse> {
    const response = await api.get(`/v1/student/vocabulary/${assignmentId}/test/eligibility`)
    return response.data
  },

  async updateVocabularyProgress(assignmentId: string, data: {
    assignment_type: 'flashcards' | 'practice' | 'challenge' | 'sentences'
    completed: boolean
  }): Promise<any> {
    const response = await api.post(`/v1/student/vocabulary/${assignmentId}/test/progress`, data)
    return response.data
  },

  async startVocabularyTest(assignmentId: string, overrideCode?: string): Promise<VocabularyTestStartResponse> {
    const response = await api.post(`/v1/student/vocabulary/${assignmentId}/test/start`, null, {
      params: overrideCode ? { override_code: overrideCode } : {}
    })
    return response.data
  },

  async submitVocabularyTest(testAttemptId: string, responses: Record<string, string>): Promise<VocabularyTestAttemptResponse> {
    const response = await api.post(`/v1/student/vocabulary/test/submit/${testAttemptId}`, { responses })
    return response.data
  },

  async getVocabularyTestResults(testAttemptId: string): Promise<VocabularyTestAttemptResponse> {
    const response = await api.get(`/v1/student/vocabulary/test/results/${testAttemptId}`)
    return response.data
  }
}

// Vocabulary Test Types
export interface VocabularyTestEligibilityResponse {
  eligible: boolean
  reason?: string
  assignments_completed: number
  assignments_required: number
  progress_details: {
    story_builder_completed: boolean
    concept_mapping_completed: boolean
    puzzle_path_completed: boolean
    fill_in_blank_completed: boolean
  }
}

export interface VocabularyTestQuestion {
  id: string
  word: string
  example_sentence: string
  question_type: string
}

export interface VocabularyTestStartResponse {
  test_attempt_id: string
  questions: VocabularyTestQuestion[]
  total_questions: number
  time_limit_minutes: number
  started_at: string
}

export interface VocabularyTestAttemptResponse {
  test_attempt_id: string
  test_id: string
  score_percentage: number
  questions_correct: number
  total_questions: number
  time_spent_seconds?: number
  status: string
  started_at: string
  completed_at?: string
  detailed_results: Array<{
    question_id: string
    question_text: string
    correct_answer: string
    student_answer: string
    score: number
    is_correct: boolean
    explanation: string
  }>
}

export interface VocabularyPracticeStatusResponse {
  assignments: Array<{
    type: string
    name: string
    is_completed: boolean
    has_active_session: boolean
  }>
  completed_count: number
  required_count: number
  test_unlocked: boolean
  test_unlock_date?: string
  test_completed: boolean
  test_attempts_count: number
  max_test_attempts: number
  best_test_score?: number
  last_test_completed_at?: string
}