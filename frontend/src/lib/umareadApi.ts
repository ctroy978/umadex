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
    const response = await api.get(`/v1/student/umaread/v2/assignments/${assignmentId}/start`);
    return response.data;
  },

  // Get chunk content
  getChunk: async (assignmentId: string, chunkNumber: number): Promise<ChunkContent> => {
    const response = await api.get(
      `/v1/student/umaread/v2/assignments/${assignmentId}/chunks/${chunkNumber}`
    );
    return response.data;
  },

  // Get current question for a chunk
  getCurrentQuestion: async (assignmentId: string, chunkNumber: number): Promise<Question> => {
    const response = await api.get(
      `/v1/student/umaread/v2/assignments/${assignmentId}/chunks/${chunkNumber}/question`
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
      `/v1/student/umaread/v2/assignments/${assignmentId}/chunks/${chunkNumber}/answer`,
      data
    );
    return response.data;
  },

  // Get student progress
  getProgress: async (assignmentId: string): Promise<StudentProgress> => {
    const response = await api.get(`/v1/student/umaread/v2/assignments/${assignmentId}/progress`);
    return response.data;
  },

  // Request a simpler question (reduce difficulty)
  requestSimplerQuestion: async (
    assignmentId: string, 
    chunkNumber: number
  ): Promise<Question> => {
    const response = await api.post(
      `/v1/student/umaread/v2/assignments/${assignmentId}/chunks/${chunkNumber}/simpler`
    );
    return response.data;
  },

  // Get simplified text for chunk (Crunch Text feature)
  crunchText: async (
    assignmentId: string,
    chunkNumber: number
  ): Promise<{
    simplified_text: string;
    chunk_number: number;
    message: string;
  }> => {
    const response = await api.post(
      `/v1/student/umaread/v2/assignments/${assignmentId}/chunks/${chunkNumber}/crunch`
    );
    return response.data;
  }
};