import api from './api';
import { 
  ReadingAssignmentCreate, 
  ReadingAssignmentUpdate,
  ReadingAssignment,
  ReadingAssignmentList,
  ReadingAssignmentListResponse,
  AssignmentImage,
  MarkupValidationResult,
  PublishResult 
} from '@/types/reading';

export const readingApi = {
  // Create a new draft assignment
  createDraft: async (data: ReadingAssignmentCreate): Promise<ReadingAssignment> => {
    const response = await api.post('/v1/teacher/assignments/reading/draft', data);
    return response.data;
  },

  // Update an existing assignment
  updateAssignment: async (id: string, data: ReadingAssignmentUpdate): Promise<ReadingAssignment> => {
    const response = await api.put(`/v1/teacher/assignments/reading/${id}`, data);
    return response.data;
  },

  // Upload an image for an assignment
  uploadImage: async (assignmentId: string, file: File, customName?: string): Promise<AssignmentImage> => {
    const formData = new FormData();
    formData.append('file', file);
    if (customName) {
      formData.append('custom_name', customName);
    }

    const response = await api.post(
      `/v1/teacher/assignments/reading/${assignmentId}/images`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  // Delete an assignment image
  deleteImage: async (assignmentId: string, imageId: string): Promise<void> => {
    await api.delete(`/v1/teacher/assignments/reading/${assignmentId}/images/${imageId}`);
  },

  // Validate assignment markup
  validateMarkup: async (assignmentId: string): Promise<MarkupValidationResult> => {
    const response = await api.post(`/v1/teacher/assignments/reading/${assignmentId}/validate`);
    return response.data;
  },

  // Publish an assignment
  publishAssignment: async (assignmentId: string): Promise<PublishResult> => {
    const response = await api.post(`/v1/teacher/assignments/reading/${assignmentId}/publish`);
    return response.data;
  },

  // List teacher's assignments with search and filters
  listAssignments: async (params?: {
    skip?: number;
    limit?: number;
    search?: string;
    date_from?: string;
    date_to?: string;
    grade_level?: string;
    work_type?: string;
    include_archived?: boolean;
  }): Promise<ReadingAssignmentListResponse> => {
    const response = await api.get('/v1/teacher/assignments/reading', { params });
    return response.data;
  },

  // Get a specific assignment
  getAssignment: async (id: string): Promise<ReadingAssignment> => {
    const response = await api.get(`/v1/teacher/assignments/reading/${id}`);
    return response.data;
  },

  // Get assignment for editing
  getAssignmentForEdit: async (id: string): Promise<ReadingAssignment> => {
    const response = await api.get(`/v1/teacher/assignments/${id}/edit`);
    return response.data;
  },

  // Update assignment content
  updateAssignmentContent: async (id: string, data: { raw_content: string }): Promise<any> => {
    const response = await api.put(`/v1/teacher/assignments/${id}/content`, data);
    return response.data;
  },

  // Update image description
  updateImageDescription: async (assignmentId: string, imageId: string, data: { ai_description: string }): Promise<any> => {
    const response = await api.put(`/v1/teacher/assignments/${assignmentId}/images/${imageId}/description`, data);
    return response.data;
  },

  // Archive assignment (soft delete)
  archiveAssignment: async (id: string): Promise<any> => {
    const response = await api.delete(`/v1/teacher/assignments/${id}`);
    return response.data;
  },

  // Restore archived assignment
  restoreAssignment: async (id: string): Promise<any> => {
    const response = await api.post(`/v1/teacher/assignments/${id}/restore`);
    return response.data;
  },
};