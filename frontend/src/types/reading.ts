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
  start_date?: string | null;
  end_date?: string | null;
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
  start_date?: string | null;
  end_date?: string | null;
}

export interface AssignmentImage {
  id: string;
  image_tag: string;  // 'image-1', 'image-2', etc.
  image_key: string;  // Unique file identifier
  file_name?: string;  // Original filename
  original_url: string;  // 2000x2000 max
  display_url: string;   // 800x600 max
  thumbnail_url: string;  // 200x150 max
  image_url: string;  // Backward compatibility (same as display_url)
  width: number;  // Original dimensions
  height: number;
  ai_description?: string;  // AI-generated description
  description_generated_at?: string;
  file_size: number;  // In bytes
  mime_type: string;
  created_at: string;
  uploaded_at: string;  // Backward compatibility
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
  start_date?: string | null;
  end_date?: string | null;
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
  start_date?: string | null;
  end_date?: string | null;
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