import api from './api';
import { 
  ReadingAssignmentCreate, 
  ReadingAssignmentUpdate,
  ReadingAssignment,
  ReadingAssignmentList,
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

  // List teacher's assignments
  listAssignments: async (skip?: number, limit?: number): Promise<ReadingAssignmentList[]> => {
    const response = await api.get('/v1/teacher/assignments/reading', {
      params: { skip, limit },
    });
    return response.data;
  },

  // Get a specific assignment
  getAssignment: async (id: string): Promise<ReadingAssignment> => {
    const response = await api.get(`/v1/teacher/assignments/reading/${id}`);
    return response.data;
  },
};