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
  assignment_id: string;
  title: string;
  assignment_type: string;
  assigned_at: string;
  display_order?: number;
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

export interface UpdateClassroomAssignmentsRequest {
  assignment_ids: string[];
}

export interface UpdateClassroomAssignmentsResponse {
  added: string[];
  removed: string[];
  total: number;
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
}

export interface AvailableAssignmentsResponse {
  assignments: AvailableAssignment[];
  total_count: number;
  page: number;
  per_page: number;
}