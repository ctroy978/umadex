// UMATest Module Type Definitions
// Phase 1: Test Creation System

export interface TestAssignment {
  id: string;
  teacher_id: string;
  test_title: string;
  test_description: string | null;
  selected_lecture_ids: string[];
  time_limit_minutes: number | null;
  attempt_limit: number;
  randomize_questions: boolean;
  show_feedback_immediately: boolean;
  test_structure: TestStructure;
  status: 'draft' | 'published' | 'archived';
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface TestStructure {
  total_questions: number;
  topics: Record<string, TopicQuestions>;
  generation_metadata: GenerationMetadata;
}

export interface TopicQuestions {
  topic_title: string;
  source_lecture_id: string;
  source_lecture_title: string;
  questions: TestQuestion[];
}

export interface TestQuestion {
  id: string;
  question_text: string;
  difficulty_level: 'basic' | 'intermediate' | 'advanced' | 'expert';
  source_content: string;
  answer_key: AnswerKey;
}

export interface AnswerKey {
  correct_answer: string;
  explanation: string;
  evaluation_rubric: string;
}

export interface GenerationMetadata {
  generated_at: string;
  ai_model: string;
  distribution: {
    basic_intermediate: number;
    advanced: number;
    expert: number;
  };
}

export interface TestQuestionCache {
  id: string;
  lecture_id: string;
  topic_id: string;
  difficulty_level: 'basic' | 'intermediate' | 'advanced' | 'expert';
  content_hash: string;
  questions: CachedQuestion[];
  ai_model: string;
  generation_timestamp: string;
}

export interface CachedQuestion {
  question_text: string;
  answer_key: AnswerKey;
  source_excerpt: string;
}

export interface TestGenerationLog {
  id: string;
  test_assignment_id: string;
  started_at: string;
  completed_at: string | null;
  status: 'processing' | 'completed' | 'failed';
  error_message: string | null;
  total_topics_processed: number;
  total_questions_generated: number;
  cache_hits: number;
  cache_misses: number;
  ai_tokens_used: number;
  ai_model: string | null;
}

// API Request/Response Types

export interface CreateTestRequest {
  test_title: string;
  test_description?: string;
  selected_lecture_ids: string[];
  time_limit_minutes?: number;
  attempt_limit?: number;
  randomize_questions?: boolean;
  show_feedback_immediately?: boolean;
}

export interface UpdateTestRequest {
  test_title?: string;
  test_description?: string;
  time_limit_minutes?: number | null;
  attempt_limit?: number;
  randomize_questions?: boolean;
  show_feedback_immediately?: boolean;
  status?: 'draft' | 'published' | 'archived';
}

export interface GenerateTestQuestionsRequest {
  test_assignment_id: string;
  regenerate?: boolean; // Force regeneration even if questions exist
}

export interface TestListResponse {
  tests: TestAssignment[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface TestDetailResponse extends TestAssignment {
  selected_lectures?: LectureInfo[]; // Populated lecture information
}

export interface LectureInfo {
  id: string;
  title: string;
  subject: string;
  grade_level: string;
  topic_count: number;
}

export interface QuestionGenerationProgress {
  test_assignment_id: string;
  status: 'processing' | 'completed' | 'failed';
  progress: {
    current_topic: number;
    total_topics: number;
    current_topic_name?: string;
  };
  error?: string;
}

// Distribution configuration for question generation
export const QUESTION_DISTRIBUTION = {
  BASIC_INTERMEDIATE_PERCENT: 70,
  ADVANCED_PERCENT: 20,
  EXPERT_PERCENT: 10,
  QUESTIONS_PER_TOPIC: 10
} as const;

// Helper function to calculate question counts
export function calculateQuestionCounts(totalTopics: number) {
  const questionsPerTopic = QUESTION_DISTRIBUTION.QUESTIONS_PER_TOPIC;
  const total = totalTopics * questionsPerTopic;
  
  return {
    total,
    basicIntermediate: Math.round((total * QUESTION_DISTRIBUTION.BASIC_INTERMEDIATE_PERCENT) / 100),
    advanced: Math.round((total * QUESTION_DISTRIBUTION.ADVANCED_PERCENT) / 100),
    expert: Math.round((total * QUESTION_DISTRIBUTION.EXPERT_PERCENT) / 100),
    perTopic: {
      basicIntermediate: Math.round((questionsPerTopic * QUESTION_DISTRIBUTION.BASIC_INTERMEDIATE_PERCENT) / 100),
      advanced: Math.round((questionsPerTopic * QUESTION_DISTRIBUTION.ADVANCED_PERCENT) / 100),
      expert: Math.round((questionsPerTopic * QUESTION_DISTRIBUTION.EXPERT_PERCENT) / 100)
    }
  };
}