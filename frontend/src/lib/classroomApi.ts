import api from './api';
import type {
  Classroom,
  ClassroomDetail,
  ClassroomCreateRequest,
  ClassroomUpdateRequest,
  JoinClassroomRequest,
  JoinClassroomResponse,
  UpdateClassroomAssignmentsRequest,
  UpdateClassroomAssignmentsResponse,
  AvailableAssignment,
  AvailableAssignmentsResponse,
  AssignmentInClassroom,
  StudentInClassroom,
  CheckAssignmentRemovalResponse,
  VocabularySettingsResponse,
  VocabularySettingsUpdate
} from '@/types/classroom';

// Teacher APIs
export const teacherClassroomApi = {
  // Classroom CRUD
  async listClassrooms(): Promise<Classroom[]> {
    const response = await api.get('/v1/teacher/classrooms');
    return response.data;
  },

  async getClassroom(id: string): Promise<ClassroomDetail> {
    const response = await api.get(`/v1/teacher/classrooms/${id}`);
    return response.data;
  },

  async createClassroom(data: ClassroomCreateRequest): Promise<Classroom> {
    const response = await api.post('/v1/teacher/classrooms', data);
    return response.data;
  },

  async updateClassroom(id: string, data: ClassroomUpdateRequest): Promise<Classroom> {
    const response = await api.put(`/v1/teacher/classrooms/${id}`, data);
    return response.data;
  },

  async deleteClassroom(id: string): Promise<void> {
    await api.delete(`/v1/teacher/classrooms/${id}`);
  },

  // Student management
  async getClassroomStudents(classroomId: string): Promise<StudentInClassroom[]> {
    const response = await api.get(`/v1/teacher/classrooms/${classroomId}/students`);
    return response.data;
  },

  async removeStudent(classroomId: string, studentId: string): Promise<void> {
    await api.delete(`/v1/teacher/classrooms/${classroomId}/students/${studentId}`);
  },

  // Assignment management
  async getClassroomAssignments(classroomId: string): Promise<AssignmentInClassroom[]> {
    const response = await api.get(`/v1/teacher/classrooms/${classroomId}/assignments/all`);
    return response.data;
  },

  async updateClassroomAssignments(
    classroomId: string,
    data: UpdateClassroomAssignmentsRequest
  ): Promise<UpdateClassroomAssignmentsResponse> {
    const response = await api.put(`/v1/teacher/classrooms/${classroomId}/assignments`, data);
    return response.data;
  },

  async getAvailableAssignments(classroomId?: string): Promise<AvailableAssignment[]> {
    const params = classroomId ? { classroom_id: classroomId } : {};
    const response = await api.get('/v1/teacher/assignments/available', { params });
    return response.data;
  },

  async getClassroomAvailableAssignments(
    classroomId: string,
    params?: {
      search?: string;
      assignment_type?: string;
      grade_level?: string;
      status?: string;
      page?: number;
      per_page?: number;
    }
  ): Promise<AvailableAssignmentsResponse> {
    const response = await api.get(`/v1/teacher/classrooms/${classroomId}/assignments/available/all`, { params });
    return response.data;
  },

  async updateClassroomAssignmentsAll(
    classroomId: string,
    data: UpdateClassroomAssignmentsRequest
  ): Promise<UpdateClassroomAssignmentsResponse> {
    const response = await api.put(`/v1/teacher/classrooms/${classroomId}/assignments/all`, data);
    return response.data;
  },

  async checkAssignmentRemoval(
    classroomId: string,
    data: UpdateClassroomAssignmentsRequest
  ): Promise<CheckAssignmentRemovalResponse> {
    const response = await api.post(`/v1/teacher/classrooms/${classroomId}/assignments/check-removal`, data);
    return response.data;
  },

  // Vocabulary settings
  async getVocabularySettings(
    classroomId: string,
    assignmentId: number
  ): Promise<VocabularySettingsResponse> {
    const response = await api.get(`/v1/teacher/classrooms/${classroomId}/vocabulary/${assignmentId}/settings`);
    return response.data;
  },

  async updateVocabularySettings(
    classroomId: string,
    assignmentId: number,
    settings: VocabularySettingsUpdate
  ): Promise<VocabularySettingsResponse> {
    const response = await api.put(`/v1/teacher/classrooms/${classroomId}/vocabulary/${assignmentId}/settings`, settings);
    return response.data;
  },

  async releaseVocabularyGroup(
    classroomId: string,
    assignmentId: number,
    groupNumber: number
  ): Promise<any> {
    const response = await api.post(`/v1/teacher/classrooms/${classroomId}/vocabulary/${assignmentId}/release-group?group_number=${groupNumber}`);
    return response.data;
  }
};

// Student APIs
export const studentClassroomApi = {
  async joinClassroom(data: JoinClassroomRequest): Promise<JoinClassroomResponse> {
    const response = await api.post('/v1/student/join-classroom', data);
    return response.data;
  },

  async listMyClassrooms(): Promise<Classroom[]> {
    const response = await api.get('/v1/student/classrooms');
    return response.data;
  },

  async leaveClassroom(classroomId: string): Promise<void> {
    await api.delete(`/v1/student/classrooms/${classroomId}/leave`);
  },

  async getClassroomAssignments(classroomId: string): Promise<AssignmentInClassroom[]> {
    const response = await api.get(`/v1/student/classrooms/${classroomId}/assignments`);
    return response.data;
  }
};