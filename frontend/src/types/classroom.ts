export interface Classroom {
  id: string;
  name: string;
  teacher_id: string;
  class_code: string;
  created_at: string;
  deleted_at?: string;
  student_count: number;
  assignment_count: number;
}

export interface ClassroomDetail extends Classroom {
  students: StudentInClassroom[];
  assignments: AssignmentInClassroom[];
}

export interface StudentInClassroom {
  id: string;
  email: string;
  full_name: string;
  joined_at: string;
  removed_at?: string;
}

export interface AssignmentInClassroom {
  id: number;  // classroom_assignment.id
  assignment_id: string;
  title: string;
  assignment_type: string;
  assigned_at: string;
  display_order?: number;
  start_date?: string;
  end_date?: string;
}

export interface ClassroomCreateRequest {
  name: string;
}

export interface ClassroomUpdateRequest {
  name?: string;
}

export interface JoinClassroomRequest {
  class_code: string;
}

export interface JoinClassroomResponse {
  classroom: Classroom;
  message: string;
}

export interface AssignmentSchedule {
  assignment_id: string;
  assignment_type?: string;  // "reading" or "vocabulary"
  start_date?: string | null;
  end_date?: string | null;
}

export interface UpdateClassroomAssignmentsRequest {
  assignments: AssignmentSchedule[];
}

export interface UpdateClassroomAssignmentsResponse {
  added: string[];
  removed: string[];
  total: number;
}

export interface CurrentSchedule {
  start_date?: string | null;
  end_date?: string | null;
}

export interface AvailableAssignment {
  id: string;
  assignment_title: string;
  work_title: string;
  author: string;
  assignment_type: string;
  grade_level: string;
  work_type: string;
  status: string;
  created_at: string;
  is_assigned: boolean;
  is_archived?: boolean;
  current_schedule?: CurrentSchedule;
  item_type?: string;  // "reading", "vocabulary", or "lecture"
  word_count?: number;  // For vocabulary lists
}

export interface AvailableAssignmentsResponse {
  assignments: AvailableAssignment[];
  total_count: number;
  page: number;
  per_page: number;
}

export interface AssignmentWithStudents {
  assignment_id: string;
  assignment_type: string;
  assignment_title: string;
  student_count: number;
}

export interface CheckAssignmentRemovalResponse {
  assignments_with_students: AssignmentWithStudents[];
  total_students_affected: number;
}

// Vocabulary settings types
export type VocabularyDeliveryMode = "all_at_once" | "in_groups" | "teacher_controlled"
export type VocabularyReleaseCondition = "immediate" | "after_test"

export interface VocabularySettings {
  delivery_mode: VocabularyDeliveryMode
  group_size?: number
  release_condition?: VocabularyReleaseCondition
  allow_test_retakes: boolean
  max_test_attempts: number
  released_groups: number[]
}

export interface VocabularySettingsUpdate {
  delivery_mode?: VocabularyDeliveryMode
  group_size?: number
  release_condition?: VocabularyReleaseCondition
  allow_test_retakes?: boolean
  max_test_attempts?: number
}

export interface VocabularySettingsResponse {
  assignment_id: number
  vocabulary_list_id: string
  settings: VocabularySettings
  total_words: number
  groups_count?: number
}