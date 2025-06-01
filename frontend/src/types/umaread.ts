// UMARead types for TypeScript

export interface AssignmentStartResponse {
  assignment_id: string;
  title: string;
  author?: string;
  total_chunks: number;
  current_chunk: number;
  difficulty_level: number;
  status: string;
}

export interface ChunkContent {
  chunk_number: number;
  total_chunks: number;
  content: string;
  images: ChunkImage[];
  has_next: boolean;
  has_previous: boolean;
}

export interface ChunkImage {
  url: string;
  thumbnail_url?: string;
  description?: string;
  image_tag?: string;
}

export interface Question {
  question_id?: string;
  question_text: string;
  question_type: 'summary' | 'comprehension';
  difficulty_level?: number;
  attempt_number: number;
  previous_feedback?: string;
}

export interface SubmitAnswerRequest {
  answer_text: string;
  time_spent_seconds: number;
}

export interface SubmitAnswerResponse {
  is_correct: boolean;
  feedback: string;
  can_proceed: boolean;
  next_question_type?: 'summary' | 'comprehension';
  difficulty_changed: boolean;
  new_difficulty_level?: number;
}

export interface StudentProgress {
  assignment_id: string;
  student_id: string;
  current_chunk: number;
  total_chunks: number;
  difficulty_level: number;
  chunks_completed: number[];
  chunk_scores: Record<string, ChunkProgress>;
  status: string;
  last_activity: string;
}

export interface ChunkProgress {
  chunk_number: number;
  summary_completed: boolean;
  comprehension_completed: boolean;
  summary_attempts: number;
  comprehension_attempts: number;
  time_spent_seconds: number;
}