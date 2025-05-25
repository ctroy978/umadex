export interface ReadingAssignmentMetadata {
  assignment_title: string;
  work_title: string;
  author?: string;
  grade_level: 'K-2' | '3-5' | '6-8' | '9-10' | '11-12' | 'College' | 'Adult Education';
  work_type: 'fiction' | 'non-fiction';
  literary_form: 'prose' | 'poetry' | 'drama' | 'mixed';
  genre: 
    | 'Adventure' 
    | 'Fantasy' 
    | 'Historical' 
    | 'Mystery' 
    | 'Mythology'
    | 'Realistic Fiction' 
    | 'Science Fiction' 
    | 'Biography' 
    | 'Essay'
    | 'Informational' 
    | 'Science' 
    | 'Other';
  subject: 'English Literature' | 'History' | 'Science' | 'Social Studies' | 'ESL/ELL' | 'Other';
}

export interface ReadingAssignmentCreate extends ReadingAssignmentMetadata {
  raw_content: string;
}

export interface ReadingAssignmentUpdate {
  assignment_title?: string;
  work_title?: string;
  author?: string;
  grade_level?: ReadingAssignmentMetadata['grade_level'];
  work_type?: ReadingAssignmentMetadata['work_type'];
  literary_form?: ReadingAssignmentMetadata['literary_form'];
  genre?: ReadingAssignmentMetadata['genre'];
  subject?: ReadingAssignmentMetadata['subject'];
  raw_content?: string;
}

export interface AssignmentImage {
  id: string;
  image_key: string;
  custom_name?: string;
  file_url: string;
  file_size?: number;
  mime_type?: string;
  uploaded_at: string;
}

export interface ReadingChunk {
  id: string;
  chunk_order: number;
  content: string;
  has_important_sections: boolean;
  created_at: string;
}

export interface ReadingAssignment {
  id: string;
  teacher_id: string;
  assignment_title: string;
  work_title: string;
  author?: string;
  grade_level: string;
  work_type: string;
  literary_form: string;
  genre: string;
  subject: string;
  raw_content: string;
  total_chunks?: number;
  status: string;
  created_at: string;
  updated_at: string;
  chunks: ReadingChunk[];
  images: AssignmentImage[];
}

export interface ReadingAssignmentList {
  id: string;
  assignment_title: string;
  work_title: string;
  author?: string;
  grade_level: string;
  subject: string;
  status: string;
  total_chunks?: number;
  created_at: string;
  updated_at: string;
}

export interface MarkupValidationResult {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  chunk_count: number;
  image_references: string[];
}

export interface PublishResult {
  success: boolean;
  message: string;
  chunk_count?: number;
}