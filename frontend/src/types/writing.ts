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
  content: string
  selected_techniques: string[]
  word_count: number
  is_final: boolean
}

export interface StudentWritingDraft {
  content: string
  selected_techniques: string[]
  word_count: number
}

export interface StudentWritingProgress {
  student_assignment_id: string | null
  draft_content: string
  selected_techniques: string[]
  word_count: number
  last_saved_at?: string
  status: string
  submission_count: number
}

export interface WritingSubmissionResponse {
  id: string
  student_assignment_id: string
  writing_assignment_id: string
  student_id: string
  response_text: string
  selected_techniques: string[]
  word_count: number
  submission_attempt: number
  is_final_submission: boolean
  submitted_at: string
  score?: number
  ai_feedback?: WritingFeedback
}

export interface WritingFeedback {
  overall_score: number
  core_score: number
  bonus_points: number
  criteria_scores: {
    content_purpose?: any
    teacher_criteria?: any
    conventions_clarity?: any
  }
  technique_validation: {
    total_bonus?: number
    techniques?: Array<{
      name: string
      found: boolean
      example?: string
      effectiveness?: string
      points_awarded: number
      feedback: string
    }>
  } | {
    [technique: string]: {
      found: boolean
      examples?: string[]
      feedback: string
    }
  }
  general_feedback: string
  revision_suggestions: string[]
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

// Writing technique definitions for students
export interface WritingTechnique {
  name: string
  displayName: string
  category: 'rhetorical' | 'narrative' | 'structural' | 'descriptive' | 'persuasive'
  description: string
  example: string
  tipOrReason: string
}

export const WRITING_TECHNIQUES: WritingTechnique[] = [
  // Rhetorical Devices
  {
    name: 'metaphor',
    displayName: 'Metaphor',
    category: 'rhetorical',
    description: 'Comparing two things without using "like" or "as"',
    example: 'Her voice was music to his ears.',
    tipOrReason: 'Use metaphors to create vivid imagery and help readers understand complex ideas through familiar comparisons.'
  },
  {
    name: 'simile',
    displayName: 'Simile',
    category: 'rhetorical',
    description: 'Comparing two things using "like" or "as"',
    example: 'She ran like the wind.',
    tipOrReason: 'Similes make descriptions more relatable and easier to visualize for your readers.'
  },
  {
    name: 'personification',
    displayName: 'Personification',
    category: 'rhetorical',
    description: 'Giving human qualities to non-human things',
    example: 'The wind whispered through the trees.',
    tipOrReason: 'Personification brings life to your writing and helps readers connect emotionally with objects or concepts.'
  },
  {
    name: 'alliteration',
    displayName: 'Alliteration',
    category: 'rhetorical',
    description: 'Repeating the same sound at the beginning of words',
    example: 'Peter Piper picked a peck of pickled peppers.',
    tipOrReason: 'Alliteration makes your writing more memorable and creates a rhythmic quality.'
  },
  {
    name: 'hyperbole',
    displayName: 'Hyperbole',
    category: 'rhetorical',
    description: 'Extreme exaggeration for effect',
    example: 'I\'ve told you a million times!',
    tipOrReason: 'Hyperbole adds humor or emphasis to make your point more dramatically.'
  },
  
  // Narrative Elements
  {
    name: 'dialogue',
    displayName: 'Dialogue',
    category: 'narrative',
    description: 'Characters speaking to each other in quotation marks',
    example: '"Where are you going?" she asked.',
    tipOrReason: 'Dialogue brings characters to life and advances the story through conversation.'
  },
  {
    name: 'flashback',
    displayName: 'Flashback',
    category: 'narrative',
    description: 'A scene that takes place before the main story',
    example: 'She remembered the day they first met...',
    tipOrReason: 'Flashbacks provide important background information and add depth to your story.'
  },
  {
    name: 'foreshadowing',
    displayName: 'Foreshadowing',
    category: 'narrative',
    description: 'Hints about what will happen later in the story',
    example: 'Little did she know, this would be the last time they spoke.',
    tipOrReason: 'Foreshadowing creates suspense and keeps readers engaged.'
  },
  
  // Structural Elements
  {
    name: 'varied_sentences',
    displayName: 'Varied Sentence Length',
    category: 'structural',
    description: 'Using both short and long sentences for rhythm',
    example: 'The storm hit hard. Thunder crashed and lightning split the sky as rain pounded against the windows.',
    tipOrReason: 'Varying sentence length creates rhythm and keeps readers interested.'
  },
  {
    name: 'parallelism',
    displayName: 'Parallelism',
    category: 'structural',
    description: 'Using the same pattern of words or phrases',
    example: 'She likes reading, writing, and painting.',
    tipOrReason: 'Parallelism makes your writing clearer and more balanced.'
  },
  {
    name: 'transitions',
    displayName: 'Transitions',
    category: 'structural',
    description: 'Words or phrases that connect ideas',
    example: 'Furthermore, the evidence suggests...',
    tipOrReason: 'Transitions guide readers smoothly from one idea to the next.'
  },
  
  // Descriptive Techniques
  {
    name: 'imagery',
    displayName: 'Imagery',
    category: 'descriptive',
    description: 'Vivid descriptive language that appeals to the senses',
    example: 'The crimson sunset painted the sky like watercolors.',
    tipOrReason: 'Imagery helps readers visualize and experience your writing.'
  },
  {
    name: 'sensory_details',
    displayName: 'Sensory Details',
    category: 'descriptive',
    description: 'Details that appeal to sight, sound, smell, taste, or touch',
    example: 'The sweet aroma of fresh-baked cookies filled the kitchen.',
    tipOrReason: 'Sensory details make your writing more immersive and memorable.'
  },
  
  // Persuasive Elements
  {
    name: 'evidence',
    displayName: 'Evidence',
    category: 'persuasive',
    description: 'Facts, statistics, or examples that support your argument',
    example: 'Studies show that 90% of students improve with practice.',
    tipOrReason: 'Evidence makes your arguments more convincing and credible.'
  },
  {
    name: 'rhetorical_questions',
    displayName: 'Rhetorical Questions',
    category: 'persuasive',
    description: 'Questions asked for effect, not expecting an answer',
    example: 'Isn\'t it time we made a change?',
    tipOrReason: 'Rhetorical questions engage readers and make them think about your point.'
  }
]