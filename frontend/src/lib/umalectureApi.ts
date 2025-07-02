/**
 * UMALecture API client
 */
import { apiRequest } from './api'

export interface LectureAssignment {
  id: string
  teacher_id: string
  title: string
  subject: string
  grade_level: string
  learning_objectives: string[]
  topic_outline?: string
  lecture_structure?: any
  status: 'draft' | 'processing' | 'published' | 'archived'
  processing_started_at?: string
  processing_completed_at?: string
  processing_error?: string
  created_at: string
  updated_at: string
  deleted_at?: string
}

export interface LectureAssignmentCreate {
  title: string
  subject: string
  grade_level: string
  learning_objectives: string[]
}

export interface LectureAssignmentUpdate {
  title?: string
  subject?: string
  grade_level?: string
  learning_objectives?: string[]
  topic_outline?: string
  lecture_structure?: any
}

export interface LectureImage {
  id: string
  lecture_id: string
  filename: string
  teacher_description: string
  ai_description?: string
  node_id: string
  position: number
  original_url: string
  display_url?: string
  thumbnail_url?: string
  file_size?: number
  mime_type?: string
  created_at: string
}

export interface LectureProcessingStatus {
  lecture_id: string
  status: string
  processing_started_at?: string
  processing_completed_at?: string
  processing_error?: string
}

export interface LectureTopicContent {
  topic_id: string
  difficulty_level: string
  content: string
  images: LectureImage[]
  questions: any[]
  next_difficulties: string[]
  next_topics: string[]
}

export interface LectureTopicResponse {
  topic_id: string
  title: string
  available_difficulties: string[]
  completed_difficulties: string[]
}

export interface LectureStudentProgress {
  assignment_id: string
  lecture_id: string
  current_topic?: string
  current_difficulty?: string
  topics_completed: string[]
  topic_progress: Record<string, string[]>
  total_points: number
  last_activity_at?: string
  started_at: string
  completed_at?: string
  title?: string
  subject?: string
  grade_level?: string
  learning_objectives?: string[]
  total_topics?: number
  total_questions?: number
  questions_answered?: number
}

export interface LectureData {
  id: string
  title: string
  subject: string
  grade_level: string
  learning_objectives: string[]
  lecture_structure?: {
    topics: Record<string, {
      title: string
      difficulty_levels: Record<string, {
        content: string
        questions: any[]
      }>
    }>
  }
  images_by_topic: Record<string, LectureImage[]>
  progress_metadata?: {
    topic_completion: Record<string, {
      completed_tabs: string[]
      completed_at?: string
      questions_correct: Record<string, boolean[]>
    }>
    current_topic?: string
    current_tab?: string
    lecture_complete: boolean
  }
}

export interface TopicContent {
  topic_id: string
  title: string
  difficulty_levels: Record<string, {
    content: string
    questions: any[]
  }>
  images: LectureImage[]
  completed_tabs: string[]
  questions_correct: Record<string, boolean[]>
}

// Teacher endpoints
export const umalectureApi = {
  // Lecture CRUD
  createLecture: (data: LectureAssignmentCreate) =>
    apiRequest<LectureAssignment>('/v1/umalecture/lectures', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  listLectures: (params?: {
    skip?: number
    limit?: number
    status?: string
    search?: string
  }) => {
    const queryParams = new URLSearchParams()
    if (params?.skip) queryParams.append('skip', params.skip.toString())
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    if (params?.status) queryParams.append('status', params.status)
    if (params?.search) queryParams.append('search', params.search)
    
    const queryString = queryParams.toString()
    return apiRequest<LectureAssignment[]>(
      `/v1/umalecture/lectures${queryString ? `?${queryString}` : ''}`
    )
  },

  getLecture: (lectureId: string) =>
    apiRequest<LectureAssignment>(`/v1/umalecture/lectures/${lectureId}`),

  updateLecture: (lectureId: string, data: LectureAssignmentUpdate) =>
    apiRequest<LectureAssignment>(`/v1/umalecture/lectures/${lectureId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteLecture: (lectureId: string) =>
    apiRequest(`/v1/umalecture/lectures/${lectureId}`, {
      method: 'DELETE',
    }),

  restoreLecture: (lectureId: string) =>
    apiRequest(`/v1/umalecture/lectures/${lectureId}/restore`, {
      method: 'POST',
    }),

  // Image management
  uploadImage: (lectureId: string, formData: FormData) =>
    apiRequest<LectureImage>(`/v1/umalecture/lectures/${lectureId}/images`, {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set multipart headers
    }),

  listImages: (lectureId: string) =>
    apiRequest<LectureImage[]>(`/v1/umalecture/lectures/${lectureId}/images`),

  deleteImage: (lectureId: string, imageId: string) =>
    apiRequest(`/v1/umalecture/lectures/${lectureId}/images/${imageId}`, {
      method: 'DELETE',
    }),

  // AI processing
  processLecture: (lectureId: string) =>
    apiRequest(`/v1/umalecture/lectures/${lectureId}/process`, {
      method: 'POST',
    }),

  getProcessingStatus: (lectureId: string) =>
    apiRequest<LectureProcessingStatus>(
      `/v1/umalecture/lectures/${lectureId}/processing-status`
    ),

  updateLectureStructure: (lectureId: string, structure: any) =>
    apiRequest(`/v1/umalecture/lectures/${lectureId}/structure`, {
      method: 'PUT',
      body: JSON.stringify(structure),
    }),

  publishLecture: (lectureId: string) =>
    apiRequest(`/v1/umalecture/lectures/${lectureId}/publish`, {
      method: 'POST',
    }),

  // Classroom assignment
  assignToClassrooms: (lectureId: string, classroomIds: string[]) =>
    apiRequest(`/v1/umalecture/lectures/${lectureId}/assign`, {
      method: 'POST',
      body: JSON.stringify({ classroom_ids: classroomIds }),
    }),

  // Student endpoints
  startLectureAssignment: (assignmentId: string) =>
    apiRequest<LectureStudentProgress>(
      `/v1/umalecture/assignments/${assignmentId}/start`
    ),

  getLectureTopics: (assignmentId: string) =>
    apiRequest<LectureTopicResponse[]>(`/v1/umalecture/assignments/${assignmentId}/topics`),

  getTopicContent: (
    assignmentId: string,
    topicId: string,
    difficulty: string
  ) => {
    const params = new URLSearchParams({ difficulty })
    return apiRequest<LectureTopicContent>(
      `/v1/umalecture/assignments/${assignmentId}/topics/${encodeURIComponent(topicId)}/content?${params}`
    )
  },

  submitAnswer: (
    assignmentId: string,
    topicId: string,
    difficulty: string,
    questionIndex: number,
    answer: string
  ) =>
    apiRequest(`/v1/umalecture/assignments/${assignmentId}/topics/${encodeURIComponent(topicId)}/answer`, {
      method: 'POST',
      body: JSON.stringify({
        difficulty,
        question_index: questionIndex,
        answer,
      }),
    }),

  getProgress: (assignmentId: string) =>
    apiRequest<LectureStudentProgress>(
      `/v1/umalecture/assignments/${assignmentId}/progress`
    ),

  // New student view endpoints
  getLectureStudentView: (lectureId: string, assignmentId: string) =>
    apiRequest<LectureData>(
      `/v1/umalecture/lectures/${lectureId}/student-view?assignment_id=${assignmentId}`
    ),

  getTopicAllContent: (lectureId: string, topicId: string, assignmentId: string) =>
    apiRequest<TopicContent>(
      `/v1/umalecture/lectures/${lectureId}/topic/${encodeURIComponent(topicId)}/content?assignment_id=${assignmentId}`
    ),

  getLectureImage: (lectureId: string, imageId: string, assignmentId: string) =>
    apiRequest<LectureImage>(
      `/v1/umalecture/lectures/${lectureId}/images/${imageId}?assignment_id=${assignmentId}`
    ),

  updateProgress: (data: {
    assignment_id: string
    topic_id: string
    tab: string
    question_index?: number
    is_correct?: boolean
  }) =>
    apiRequest('/v1/umalecture/lectures/progress/update', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  evaluateResponse: (data: {
    assignment_id: string
    topic_id: string
    difficulty: string
    question_text: string
    student_answer: string
    expected_answer?: string
    includes_images?: boolean
    image_descriptions?: string[]
  }) =>
    apiRequest<{
      is_correct: boolean
      feedback: string
      points_earned: number
    }>('/v1/umalecture/lectures/evaluate-response', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateCurrentPosition: (assignmentId: string, position: {
    current_topic?: string
    current_tab?: string
  }) =>
    apiRequest(`/v1/umalecture/lectures/progress/${assignmentId}/current-position`, {
      method: 'PUT',
      body: JSON.stringify(position),
    }),
}