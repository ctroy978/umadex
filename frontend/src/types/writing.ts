export interface EvaluationCriteria {
  tone: string[]
  style: string[]
  perspective: string[]
  techniques: string[]
  structure: string[]
}

export interface WritingAssignment {
  id: string
  teacher_id: string
  title: string
  prompt_text: string
  word_count_min: number
  word_count_max: number
  evaluation_criteria: EvaluationCriteria
  instructions?: string
  grade_level?: string
  subject?: string
  created_at: string
  updated_at: string
  deleted_at?: string
  classroom_count: number
  is_archived: boolean
}

export interface WritingAssignmentCreate {
  title: string
  prompt_text: string
  word_count_min: number
  word_count_max: number
  evaluation_criteria: EvaluationCriteria
  instructions?: string
  grade_level?: string
  subject?: string
}

export interface WritingAssignmentUpdate {
  title?: string
  prompt_text?: string
  word_count_min?: number
  word_count_max?: number
  evaluation_criteria?: EvaluationCriteria
  instructions?: string
  grade_level?: string
  subject?: string
}

export interface WritingAssignmentListResponse {
  assignments: WritingAssignment[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface StudentWritingSubmission {
  id: string
  student_id: string
  assignment_id: string
  classroom_id: string
  submission_text: string
  word_count: number
  submitted_at: string
  updated_at: string
  evaluation_score?: Record<string, any>
  evaluation_feedback?: string
  evaluated_at?: string
}

export interface StudentWritingSubmissionCreate {
  assignment_id: string
  classroom_id: string
  submission_text: string
}

export interface StudentWritingSubmissionUpdate {
  submission_text?: string
}

export interface WritingAssignmentWithProgress extends WritingAssignment {
  submission?: StudentWritingSubmission
  is_submitted: boolean
}

// Evaluation criteria options
export const TONE_OPTIONS = ['Happy', 'Sad', 'Neutral', 'Hopeful', 'Serious']
export const STYLE_OPTIONS = ['Narrative', 'Descriptive', 'Persuasive', 'Instructive', 'Expository']
export const PERSPECTIVE_OPTIONS = ['First Person', 'Second Person', 'Third Person']
export const TECHNIQUE_OPTIONS = ['Metaphor', 'Simile', 'Dialogue', 'Imagery', 'Repetition']
export const STRUCTURE_OPTIONS = ['Varied Sentences', 'Paragraphs', 'Introduction/Conclusion']

// Grade level options (matching other modules)
export const GRADE_LEVELS = [
  'Elementary (K-2)',
  'Elementary (3-5)',
  'Middle School (6-8)',
  'High School (9-12)',
  'College/Adult'
]

// Subject area options (matching other modules)
export const SUBJECT_AREAS = [
  'English Language Arts',
  'Science',
  'Social Studies',
  'Mathematics',
  'Foreign Language',
  'Arts',
  'Other'
]