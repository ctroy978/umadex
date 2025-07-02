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
}

// Student endpoints
export const umalectureStudentApi = {
  startAssignment: (assignmentId: string) =>
    apiRequest<LectureStudentProgress>(
      `/v1/umalecture/assignments/${assignmentId}/start`
    ),

  getTopics: (assignmentId: string) =>
    apiRequest<any[]>(`/v1/umalecture/assignments/${assignmentId}/topics`),

  getTopicContent: (
    assignmentId: string,
    topicId: string,
    difficulty: string
  ) => {
    const params = new URLSearchParams({ difficulty })
    return apiRequest<LectureTopicContent>(
      `/v1/umalecture/assignments/${assignmentId}/topics/${topicId}/content?${params}`
    )
  },

  submitAnswer: (
    assignmentId: string,
    topicId: string,
    difficulty: string,
    questionIndex: number,
    answer: string
  ) =>
    apiRequest(`/v1/umalecture/assignments/${assignmentId}/topics/${topicId}/answer`, {
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
}