import api from './api';
import { WritingAssignment, StudentWritingDraft, StudentWritingSubmission, StudentWritingProgress } from '@/types/writing';

export const studentWritingApi = {
  // Get a specific writing assignment
  getAssignment: async (assignmentId: string): Promise<WritingAssignment> => {
    const response = await api.get(`/v1/writing/student/assignments/${assignmentId}`);
    return response.data;
  },

  // Start working on an assignment
  startAssignment: async (assignmentId: string) => {
    const response = await api.post(`/v1/writing/student/assignments/${assignmentId}/start`);
    return response.data;
  },

  // Save a draft
  saveDraft: async (assignmentId: string, draft: StudentWritingDraft) => {
    const response = await api.put(`/v1/writing/student/assignments/${assignmentId}/draft`, draft);
    return response.data;
  },

  // Update selected techniques
  updateTechniques: async (assignmentId: string, techniques: string[]) => {
    const response = await api.post(`/v1/writing/student/assignments/${assignmentId}/techniques`, techniques);
    return response.data;
  },

  // Submit final response
  submitAssignment: async (assignmentId: string, submission: StudentWritingSubmission) => {
    const response = await api.post(`/v1/writing/student/assignments/${assignmentId}/submit`, submission);
    return response.data;
  },

  // Trigger evaluation for a submission
  evaluateSubmission: async (submissionId: string) => {
    const response = await api.post(`/v1/writing/student/submissions/${submissionId}/evaluate`);
    return response.data;
  },

  // Get feedback
  getFeedback: async (assignmentId: string, submissionId?: string) => {
    const params = submissionId ? { submission_id: submissionId } : {};
    const response = await api.get(`/v1/writing/student/assignments/${assignmentId}/feedback`, { params });
    return response.data;
  },

  // Get progress
  getProgress: async (assignmentId: string): Promise<StudentWritingProgress> => {
    const response = await api.get(`/v1/writing/student/assignments/${assignmentId}/progress`);
    return response.data;
  }
};