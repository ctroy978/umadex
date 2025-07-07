/**
 * Assignment Type Mapping Utilities
 * 
 * This module provides consistent mapping between frontend display names
 * and backend/database storage names for all assignment types.
 */

// Frontend display types (what users see)
export type FrontendAssignmentType = 'UMARead' | 'UMAVocab' | 'UMADebate' | 'UMAWrite' | 'UMALecture' | 'UMATest';

// Backend/database types (what the API expects)
export type BackendAssignmentType = 'reading' | 'vocabulary' | 'debate' | 'writing' | 'lecture' | 'test';

// Item types used in some contexts
export type ItemType = 'reading' | 'vocabulary' | 'debate' | 'writing' | 'lecture' | 'test';

// Mapping from frontend to backend types
const FRONTEND_TO_BACKEND_MAP: Record<FrontendAssignmentType, BackendAssignmentType> = {
  'UMARead': 'reading',
  'UMAVocab': 'vocabulary',
  'UMADebate': 'debate',
  'UMAWrite': 'writing',
  'UMALecture': 'lecture',
  'UMATest': 'test'
};

// Mapping from backend to frontend types
const BACKEND_TO_FRONTEND_MAP: Record<BackendAssignmentType, FrontendAssignmentType> = {
  'reading': 'UMARead',
  'vocabulary': 'UMAVocab',
  'debate': 'UMADebate',
  'writing': 'UMAWrite',
  'lecture': 'UMALecture',
  'test': 'UMATest'
};

// Mapping from item type to backend type
const ITEM_TYPE_TO_BACKEND_MAP: Record<ItemType, BackendAssignmentType> = {
  'reading': 'reading',
  'vocabulary': 'vocabulary',
  'debate': 'debate',
  'writing': 'writing',
  'lecture': 'lecture',
  'test': 'test'
};

/**
 * Convert frontend assignment type to backend type
 */
export function toBackendType(frontendType: FrontendAssignmentType | string): BackendAssignmentType {
  // Handle the case where backend type is already passed
  if (isBackendType(frontendType)) {
    return frontendType as BackendAssignmentType;
  }
  
  const mapped = FRONTEND_TO_BACKEND_MAP[frontendType as FrontendAssignmentType];
  if (!mapped) {
    console.warn(`Unknown frontend assignment type: ${frontendType}, defaulting to 'reading'`);
    return 'reading';
  }
  return mapped;
}

/**
 * Convert backend assignment type to frontend type
 */
export function toFrontendType(backendType: BackendAssignmentType | string): FrontendAssignmentType {
  // Handle the case where frontend type is already passed
  if (isFrontendType(backendType)) {
    return backendType as FrontendAssignmentType;
  }
  
  const mapped = BACKEND_TO_FRONTEND_MAP[backendType as BackendAssignmentType];
  if (!mapped) {
    console.warn(`Unknown backend assignment type: ${backendType}, defaulting to 'UMARead'`);
    return 'UMARead';
  }
  return mapped;
}

/**
 * Convert item type to backend type
 */
export function itemTypeToBackendType(itemType: ItemType | string): BackendAssignmentType {
  const mapped = ITEM_TYPE_TO_BACKEND_MAP[itemType as ItemType];
  if (!mapped) {
    console.warn(`Unknown item type: ${itemType}, defaulting to 'reading'`);
    return 'reading';
  }
  return mapped;
}

/**
 * Get the backend type from various possible inputs
 */
export function getBackendType(assignment: {
  assignment_type?: string;
  item_type?: string;
  type?: string;
}): BackendAssignmentType {
  // Priority order: assignment_type > item_type > type
  if (assignment.assignment_type) {
    return toBackendType(assignment.assignment_type);
  }
  if (assignment.item_type) {
    return itemTypeToBackendType(assignment.item_type);
  }
  if (assignment.type) {
    return toBackendType(assignment.type);
  }
  
  console.warn('No type information found in assignment, defaulting to reading');
  return 'reading';
}

/**
 * Check if a string is a valid backend type
 */
export function isBackendType(type: string): type is BackendAssignmentType {
  return ['reading', 'vocabulary', 'debate', 'writing', 'lecture', 'test'].includes(type);
}

/**
 * Check if a string is a valid frontend type
 */
export function isFrontendType(type: string): type is FrontendAssignmentType {
  return ['UMARead', 'UMAVocab', 'UMADebate', 'UMAWrite', 'UMALecture', 'UMATest'].includes(type);
}

/**
 * Check if assignment uses vocabulary_list_id instead of assignment_id
 */
export function usesVocabularyListId(type: BackendAssignmentType | FrontendAssignmentType | string): boolean {
  const backendType = isBackendType(type) ? type : toBackendType(type);
  return backendType === 'vocabulary';
}

/**
 * Get the correct ID field name for an assignment type
 */
export function getIdFieldName(type: BackendAssignmentType | FrontendAssignmentType | string): 'assignment_id' | 'vocabulary_list_id' {
  return usesVocabularyListId(type) ? 'vocabulary_list_id' : 'assignment_id';
}

/**
 * Format assignment data for API submission
 */
export function formatAssignmentForAPI(
  assignmentId: string,
  frontendType: FrontendAssignmentType | string,
  startDate?: string | null,
  endDate?: string | null
): any {
  const backendType = toBackendType(frontendType);
  
  const data: any = {
    assignment_type: backendType,
    start_date: startDate || null,
    end_date: endDate || null
  };
  
  // Always include assignment_id for API compatibility
  data.assignment_id = assignmentId;
  
  return data;
}