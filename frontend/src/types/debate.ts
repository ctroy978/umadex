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

// Student Debate Types (Phase 2)
export type DebateStatus = 'not_started' | 'debate_1' | 'debate_2' | 'debate_3' | 'completed';
export type DebatePosition = 'pro' | 'con' | 'choice';
export type PostType = 'student' | 'ai';
export type ChallengeType = 'fallacy' | 'appeal';
export type ModerationStatus = 'pending' | 'approved' | 'rejected' | 'revision_requested';

// Assignment Overview for Students
export interface DebateAssignmentCard {
  assignmentId: string;
  title: string;
  topic: string;
  difficultyLevel: string;
  debateFormat: {
    roundsPerDebate: number;
    timeLimitHours: number;
    debateCount: number;
  };
  status: DebateStatus;
  debatesCompleted: number;
  currentDebatePosition: DebatePosition | null;
  timeRemaining: number | null; // seconds
  canStart: boolean;
  accessDate: string;
  dueDate: string;
}

// Student Debate Progress
export interface StudentDebate {
  id: string;
  studentId: string;
  assignmentId: string;
  classroomAssignmentId: string;
  status: DebateStatus;
  currentDebate: number;
  currentRound: number;
  
  debate_1Position: DebatePosition | null;
  debate_2Position: DebatePosition | null;
  debate_3Position: DebatePosition | null;
  
  fallacyCounter: number;
  fallacyScheduledDebate: number | null;
  fallacyScheduledRound: number | null;
  
  assignmentStartedAt: string | null;
  currentDebateStartedAt: string | null;
  currentDebateDeadline: string | null;
  
  debate_1Percentage: number | null;
  debate_2Percentage: number | null;
  debate_3Percentage: number | null;
  finalPercentage: number | null;
  
  createdAt: string;
  updatedAt: string;
}

// Debate Post
export interface DebatePost {
  id: string;
  student_debate_id: string;
  debate_number: number;
  round_number: number;
  statement_number?: number;
  post_type: PostType;
  
  content: string;
  word_count: number;
  
  ai_personality?: string;
  is_fallacy: boolean;
  fallacy_type?: string;
  
  clarity_score?: number;
  evidence_score?: number;
  logic_score?: number;
  persuasiveness_score?: number;
  rebuttal_score?: number;
  base_percentage?: number;
  bonus_points: number;
  final_percentage?: number;
  
  content_flagged: boolean;
  moderation_status: ModerationStatus;
  ai_feedback?: string;
  selected_technique?: string;
  
  created_at: string;
  
  // Frontend conversions
  postType?: PostType;
  aiPersonality?: string;
  statementNumber?: number;
  isFallacy?: boolean;
  fallacyType?: string;
  clarityScore?: number;
  evidenceScore?: number;
  logicScore?: number;
  persuasivenessScore?: number;
  rebuttalScore?: number;
  basePercentage?: number;
  bonusPoints?: number;
  finalPercentage?: number;
  contentFlagged?: boolean;
  moderationStatus?: ModerationStatus;
  aiFeedback?: string;
  selectedTechnique?: string;
  createdAt?: string;
}

// Challenge System
export interface ChallengeOption {
  type: ChallengeType;
  value: string;
  displayName: string;
  description: string;
}

export interface ChallengeCreate {
  postId: string;
  challengeType: ChallengeType;
  challengeValue: string;
  explanation?: string;
}

export interface ChallengeResult {
  is_correct: boolean;
  points_awarded: number;
  ai_feedback: string;
}

// Scoring
export interface PostScore {
  clarity: number;
  evidence: number;
  logic: number;
  persuasiveness: number;
  rebuttal: number;
  base_percentage: number;
  bonus_points: number;
  final_percentage: number;
  feedback: string;
}

export interface DebateScore {
  debate_number: number;
  posts: PostScore[];
  average_percentage: number;
  total_bonus_points: number;
  final_percentage: number;
}

export interface AssignmentScore {
  debate_1_score?: DebateScore;
  debate_2_score?: DebateScore;
  debate_3_score?: DebateScore;
  improvement_bonus: number;
  consistency_bonus: number;
  final_grade: number;
  finalGrade?: number; // Support both snake_case and camelCase
}

// Progress State
export interface DebateProgress {
  studentDebate: StudentDebate;
  currentPosts: DebatePost[];
  availableChallenges: ChallengeOption[];
  timeRemaining: number | null;
  canSubmitPost: boolean;
  nextAction: 'submit_post' | 'await_ai' | 'choose_position' | 'debate_complete' | 'assignment_complete';
}

// Position Selection
export interface PositionSelection {
  position: 'pro' | 'con';
  reason?: string;
}

// Post Creation
export interface StudentPostCreate {
  content: string;
  word_count: number;
  selectedTechnique?: string;
}

// Round Feedback
export interface RoundFeedback {
  id: string;
  student_debate_id: string;
  debate_number: number;
  coaching_feedback: string;
  strengths?: string;
  improvement_areas?: string;
  specific_suggestions?: string;
  round_completed_at: string;
}

// Available challenge options
export const CHALLENGE_OPTIONS: ChallengeOption[] = [
  { type: 'fallacy', value: 'ad_hominem', displayName: 'Ad Hominem', description: 'Attacks person, not argument' },
  { type: 'fallacy', value: 'strawman', displayName: 'Strawman', description: 'Misrepresents your position' },
  { type: 'fallacy', value: 'red_herring', displayName: 'Red Herring', description: 'Introduces irrelevant information' },
  { type: 'fallacy', value: 'false_dichotomy', displayName: 'False Dichotomy', description: 'Only two options presented' },
  { type: 'fallacy', value: 'slippery_slope', displayName: 'Slippery Slope', description: 'Extreme consequences assumed' },
  { type: 'appeal', value: 'ethos', displayName: 'Ethos (Credibility)', description: 'Uses authority/credibility' },
  { type: 'appeal', value: 'pathos', displayName: 'Pathos (Emotion)', description: 'Appeals to emotions' },
  { type: 'appeal', value: 'logos', displayName: 'Logos (Logic)', description: 'Uses logical reasoning' }
];

// Rhetorical Techniques
export interface RhetoricalTechnique {
  name: string;
  displayName: string;
  description: string;
  example: string;
  tipOrReason: string;
}

export interface RhetoricalTechniques {
  proper: RhetoricalTechnique[];
  improper: RhetoricalTechnique[];
}