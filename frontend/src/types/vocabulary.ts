export enum VocabularyStatus {
  DRAFT = 'draft',
  PROCESSING = 'processing',
  REVIEWING = 'reviewing',
  PUBLISHED = 'published',
  ARCHIVED = 'archived'
}

export enum DefinitionSource {
  PENDING = 'pending',
  AI = 'ai',
  TEACHER = 'teacher'
}

export enum ReviewStatus {
  PENDING = 'pending',
  ACCEPTED = 'accepted',
  REJECTED_ONCE = 'rejected_once',
  REJECTED_TWICE = 'rejected_twice'
}

export interface VocabularyWordCreate {
  word: string
  teacher_definition?: string
  teacher_example_1?: string
  teacher_example_2?: string
}

export interface VocabularyListCreate {
  title: string
  context_description: string
  grade_level: string
  subject_area: string
  words: VocabularyWordCreate[]
}

export interface VocabularyListUpdate {
  title?: string
  context_description?: string
  grade_level?: string
  subject_area?: string
  status?: VocabularyStatus
}

export interface VocabularyWordReviewRequest {
  action: 'accept' | 'reject'
  rejection_feedback?: string
}

export interface VocabularyWordManualUpdate {
  definition: string
  example_1: string
  example_2: string
}

export interface VocabularyWordReview {
  id: string
  word_id: string
  review_status: ReviewStatus
  rejection_feedback: string | null
  reviewed_at: string | null
  created_at: string
}

export interface VocabularyWord {
  id: string
  list_id: string
  word: string
  teacher_definition: string | null
  teacher_example_1: string | null
  teacher_example_2: string | null
  ai_definition: string | null
  ai_example_1: string | null
  ai_example_2: string | null
  definition_source: DefinitionSource
  examples_source: DefinitionSource
  position: number
  created_at: string
  updated_at: string
  review?: VocabularyWordReview
}

export interface VocabularyList {
  id: string
  teacher_id: string
  title: string
  context_description: string
  grade_level: string
  subject_area: string
  status: VocabularyStatus
  created_at: string
  updated_at: string
  deleted_at: string | null
  words?: VocabularyWord[]
  word_count?: number
}

export interface VocabularyListSummary {
  id: string
  title: string
  grade_level: string
  subject_area: string
  status: VocabularyStatus
  word_count: number
  review_progress: number
  created_at: string
  updated_at: string
}

export interface VocabularyListPagination {
  items: VocabularyListSummary[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface VocabularyProgress {
  total: number
  accepted: number
  rejected: number
  pending: number
  progress_percentage: number
}

export interface VocabularyExportFormat {
  format: 'pdf' | 'csv'
}