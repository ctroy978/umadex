// Types for UMALecture Progress Tracking

export interface LectureProgressBadge {
  level: 'basic' | 'intermediate' | 'advanced' | 'expert';
  completed: boolean;
  questions_correct: number;
  total_questions: number;
}

export interface StudentLectureProgress {
  student_id: string;
  student_name: string;
  assignment_id: number;
  lecture_id: string;
  lecture_title: string;
  started_at: string | null;
  last_activity_at: string | null;
  current_topic: string | null;
  current_tab: string | null;
  topics_completed: number;
  total_topics: number;
  badges: LectureProgressBadge[];
  overall_progress: number;
  status: 'not_started' | 'in_progress' | 'completed';
}

export interface LectureSummary {
  total_students: number;
  students_started: number;
  students_completed: number;
  average_progress: number;
  badge_distribution: Record<string, number>;
}

export interface LectureReport {
  lecture_id: string;
  lecture_title: string;
  assignment_id: number;
  students: StudentLectureProgress[];
  summary: LectureSummary;
}

export interface LectureProgressResponse {
  classroom_id: string;
  classroom_name: string;
  lectures: LectureReport[];
  summary: LectureSummary;
}