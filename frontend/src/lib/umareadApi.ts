// API client for UMARead endpoints

import { api } from './api';
import type {
  AssignmentStartResponse,
  ChunkContent,
  Question,
  SubmitAnswerRequest,
  SubmitAnswerResponse,
  StudentProgress
} from '@/types/umaread';

export const umareadApi = {
  // Start or resume an assignment
  startAssignment: async (assignmentId: string): Promise<AssignmentStartResponse> => {
    const response = await api.get(`/v1/student/umaread/assignments/${assignmentId}/start`);
    return response.data;
  },

  // Get chunk content
  getChunk: async (assignmentId: string, chunkNumber: number): Promise<ChunkContent> => {
    const response = await api.get(
      `/v1/student/umaread/assignments/${assignmentId}/chunks/${chunkNumber}`
    );
    return response.data;
  },

  // Get current question for a chunk
  getCurrentQuestion: async (assignmentId: string, chunkNumber: number): Promise<Question> => {
    const response = await api.get(
      `/v1/student/umaread/assignments/${assignmentId}/chunks/${chunkNumber}/question`
    );
    return response.data;
  },

  // Submit an answer
  submitAnswer: async (
    assignmentId: string,
    chunkNumber: number,
    data: SubmitAnswerRequest
  ): Promise<SubmitAnswerResponse> => {
    const response = await api.post(
      `/v1/student/umaread/assignments/${assignmentId}/chunks/${chunkNumber}/answer`,
      data
    );
    return response.data;
  },

  // Get student progress
  getProgress: async (assignmentId: string): Promise<StudentProgress> => {
    const response = await api.get(`/v1/student/umaread/assignments/${assignmentId}/progress`);
    return response.data;
  },

  // Teacher: Flush question cache
  flushQuestionCache: async (assignmentId: string, reason?: string) => {
    const response = await api.post(
      `/v1/student/umaread/assignments/${assignmentId}/cache/flush`,
      { reason }
    );
    return response.data;
  }
};