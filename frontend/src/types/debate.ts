export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced'
export type FallacyFrequency = 'every_1_2' | 'every_2_3' | 'every_3_4' | 'disabled'
export type FlagType = 'profanity' | 'inappropriate' | 'off_topic' | 'spam'
export type FlagStatus = 'pending' | 'approved' | 'rejected' | 'escalated'

export interface DebateAssignmentMetadata {
  title: string
  topic: string
  description?: string
  gradeLevel: string
  subject: string
}

export interface DebateConfiguration {
  roundsPerDebate: number
  debateCount: number
  timeLimitHours: number
  difficultyLevel: DifficultyLevel
  fallacyFrequency: FallacyFrequency
  aiPersonalitiesEnabled: boolean
  contentModerationEnabled: boolean
  autoFlagOffTopic: boolean
}

export interface DebateAssignmentCreate extends DebateAssignmentMetadata, DebateConfiguration {}

export interface DebateAssignmentUpdate {
  title?: string
  topic?: string
  description?: string
  gradeLevel?: string
  subject?: string
  roundsPerDebate?: number
  debateCount?: number
  timeLimitHours?: number
  difficultyLevel?: DifficultyLevel
  fallacyFrequency?: FallacyFrequency
  aiPersonalitiesEnabled?: boolean
  contentModerationEnabled?: boolean
  autoFlagOffTopic?: boolean
}

export interface DebateAssignment {
  id: string
  teacherId: string
  title: string
  topic: string
  description?: string
  gradeLevel: string
  subject: string
  roundsPerDebate: number
  debateCount: number
  timeLimitHours: number
  difficultyLevel: DifficultyLevel
  fallacyFrequency: FallacyFrequency
  aiPersonalitiesEnabled: boolean
  contentModerationEnabled: boolean
  autoFlagOffTopic: boolean
  createdAt: string
  updatedAt: string
  deletedAt?: string
}

export interface DebateAssignmentSummary {
  id: string
  title: string
  topic: string
  gradeLevel: string
  subject: string
  roundsPerDebate: number
  debateCount: number
  timeLimitHours: number
  createdAt: string
  deletedAt?: string
  studentCount: number
  completionRate: number
}

export interface DebateAssignmentListResponse {
  assignments: DebateAssignmentSummary[]
  total: number
  filtered: number
  page: number
  per_page: number
}

export interface DebateAssignmentFilters {
  search?: string
  gradeLevel?: string
  subject?: string
  dateFrom?: string
  dateTo?: string
  includeArchived?: boolean
}

export interface ContentFlag {
  id: string
  postId?: string
  studentId: string
  teacherId: string
  assignmentId: string
  flagType: FlagType
  flagReason?: string
  autoFlagged: boolean
  confidenceScore?: number
  status: FlagStatus
  teacherAction?: string
  teacherNotes?: string
  createdAt: string
  resolvedAt?: string
  studentName?: string
  assignmentTitle?: string
}

export interface ContentFlagUpdate {
  status: FlagStatus
  teacherAction?: string
  teacherNotes?: string
}