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
  item_type: 'reading' | 'vocabulary'
  assigned_at: string
  start_date?: string
  end_date?: string
  display_order?: number
  status: 'not_started' | 'active' | 'expired'
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
  async validateAssignmentAccess(assignmentType: 'reading' | 'vocabulary', assignmentId: string): Promise<{
    access_granted: boolean
    classroom_id: string
    classroom_name: string
    assignment_type: string
    assignment_id: string
  }> {
    const response = await api.get(`/v1/student/assignment/${assignmentType}/${assignmentId}/validate`)
    return response.data
  }
}