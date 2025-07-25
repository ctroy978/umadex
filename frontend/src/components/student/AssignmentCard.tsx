import { StudentAssignment } from '@/lib/studentApi'
import { formatDateRange, getTimeRemaining, getStatusColor } from '@/lib/dateUtils'
import { 
  ClockIcon, 
  PlayCircleIcon, 
  XCircleIcon,
  BookOpenIcon,
  LanguageIcon,
  ArrowRightIcon,
  CalendarIcon,
  UserIcon,
  CheckCircleIcon,
  DocumentCheckIcon,
  DocumentCheckIcon as FileCheckIcon,
  LockClosedIcon,
  ExclamationTriangleIcon,
  AcademicCapIcon
} from '@heroicons/react/24/outline'
import { useRouter } from 'next/navigation'
import { useTestAvailability } from '@/hooks/useTestAvailability'

interface AssignmentCardProps {
  assignment: StudentAssignment
  classroomId: string
}

export default function AssignmentCard({ assignment, classroomId }: AssignmentCardProps) {
  const router = useRouter()
  const statusColors = getStatusColor(assignment.status)
  const timeRemaining = assignment.status === 'active' ? getTimeRemaining(assignment.end_date) : null
  
  // Check test availability if this is a completed assignment with a test or a UMATest assignment
  const shouldCheckAvailability = (assignment.is_completed && assignment.has_test) || assignment.type === 'UMATest'
  const { availability } = useTestAvailability(shouldCheckAvailability ? classroomId : null)

  const handleAssignmentClick = () => {
    if (assignment.status === 'active') {
      if (assignment.type === 'UMADebate') {
        // Navigate to debate assignment page
        router.push(`/student/debate/${assignment.id}`)
      } else if (assignment.type === 'UMAWrite') {
        if (assignment.is_completed) {
          // Navigate to writing results page for completed assignments
          router.push(`/student/assignments/umawrite/${assignment.id}?view=results`)
        } else {
          // Navigate to writing assignment page
          router.push(`/student/assignments/umawrite/${assignment.id}`)
        }
      } else if (assignment.type === 'UMALecture') {
        // Navigate to lecture assignment page
        router.push(`/student/assignment/lecture/${assignment.id}?classroomId=${classroomId}`)
      } else if (assignment.type === 'UMATest') {
        // Navigate to UMATest page for UMATest assignments
        if (assignment.test_completed && assignment.test_attempt_id) {
          // Navigate to UMATest results for completed tests
          router.push(`/student/umatest/results/${assignment.test_attempt_id}`)
        } else {
          // Navigate to UMATest page
          router.push(`/student/umatest/${assignment.id}`)
        }
      } else if (assignment.is_completed && assignment.has_test) {
        if (assignment.test_completed && assignment.test_attempt_id) {
          // Navigate to test results for completed tests
          router.push(`/student/test/results/${assignment.test_attempt_id}`)
        } else {
          // Navigate to test page for incomplete tests
          router.push(`/student/test/${assignment.id}`)
        }
      } else if (!assignment.is_completed) {
        // Navigate to assignment page for incomplete assignments
        router.push(`/student/assignment/${assignment.item_type}/${assignment.id}?classroomId=${classroomId}`)
      }
    }
  }

  const getStatusIcon = () => {
    switch (assignment.status) {
      case 'not_started':
        return <ClockIcon className="h-5 w-5" />
      case 'active':
        return <PlayCircleIcon className="h-5 w-5" />
      case 'expired':
        return <XCircleIcon className="h-5 w-5" />
    }
  }

  const getTypeIcon = () => {
    switch (assignment.item_type) {
      case 'reading':
        return <BookOpenIcon className="h-5 w-5 text-blue-600" />
      case 'vocabulary':
        return <LanguageIcon className="h-5 w-5 text-purple-600" />
      case 'debate':
        return <UserIcon className="h-5 w-5 text-green-600" />
      case 'writing':
        return <DocumentCheckIcon className="h-5 w-5 text-amber-600" />
      case 'lecture':
        return <AcademicCapIcon className="h-5 w-5 text-indigo-600" />
      case 'test':
        return <DocumentCheckIcon className="h-5 w-5 text-red-600" />
      default:
        return <BookOpenIcon className="h-5 w-5 text-gray-600" />
    }
  }

  const getButtonText = () => {
    switch (assignment.status) {
      case 'not_started':
        return 'Not Available Yet'
      case 'active':
        if (assignment.type === 'UMADebate') {
          if (assignment.is_completed) {
            return 'View Debate Results'
          }
          return 'Continue Debate'
        }
        if (assignment.type === 'UMAWrite') {
          if (assignment.is_completed) {
            return 'View Results'
          }
          return 'Start Assignment'
        }
        if (assignment.type === 'UMALecture') {
          if (assignment.is_completed) {
            return 'Review Lecture'
          }
          if (assignment.has_started) {
            return 'Continue Learning'
          }
          return 'Start Lecture'
        }
        if (assignment.type === 'UMAVocab') {
          if (assignment.is_completed) {
            return 'View Results'
          }
          if (assignment.has_started) {
            return 'Continue'
          }
          return 'Start Assignment'
        }
        if (assignment.type === 'UMARead') {
          if (assignment.is_completed) {
            if (assignment.has_test) {
              if (assignment.test_completed) {
                return 'View Results'
              }
              // Check test availability
              if (availability && !availability.allowed) {
                return 'Test Locked'
              }
              return 'Start Completion Test'
            }
            return 'Completed'
          }
          if (assignment.has_started) {
            return 'Continue'
          }
          return 'Start Assignment'
        }
        if (assignment.type === 'UMATest') {
          if (assignment.test_completed) {
            return 'View Results'
          }
          // Check test availability
          if (availability && !availability.allowed) {
            return 'Test Locked'
          }
          return 'Start Test'
        }
        if (assignment.is_completed) {
          if (assignment.has_test) {
            if (assignment.test_completed) {
              return 'View Results'
            }
            // Check test availability
            if (availability && !availability.allowed) {
              return 'Test Locked'
            }
            return 'Start Completion Test'
          }
          return 'Completed'
        }
        return 'Start Assignment'
      case 'expired':
        return 'Assignment Ended'
    }
  }
  
  const canStartTest = () => {
    // For UMATest, check availability directly
    if (assignment.type === 'UMATest') {
      if (assignment.test_completed) return true // Always allow viewing results
      if (!availability) return true // Default to allowing if no schedule info
      return availability.allowed
    }
    if (!assignment.is_completed) return false
    // For UMAWrite, always allow viewing results when completed
    if (assignment.type === 'UMAWrite') return true
    if (!assignment.has_test) return false
    if (assignment.test_completed) return true // Always allow viewing results
    if (!availability) return true // Default to allowing if no schedule info
    return availability.allowed
  }

  return (
    <div className={`bg-white rounded-lg shadow hover:shadow-md transition-shadow border ${
      assignment.is_completed ? 'border-green-300 bg-green-50/30' : statusColors.border
    }`}>
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start space-x-3 flex-1">
            <div className={`p-2 rounded-lg ${
              assignment.item_type === 'reading' ? 'bg-blue-100' : 
              assignment.item_type === 'vocabulary' ? 'bg-purple-100' :
              assignment.item_type === 'debate' ? 'bg-green-100' :
              assignment.item_type === 'writing' ? 'bg-amber-100' :
              assignment.item_type === 'lecture' ? 'bg-indigo-100' :
              assignment.item_type === 'test' ? 'bg-red-100' :
              'bg-gray-100'
            }`}>
              {getTypeIcon()}
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                {assignment.title}
              </h3>
              {assignment.work_title && (
                <p className="text-sm text-gray-600 mb-1">
                  {assignment.work_title}
                </p>
              )}
              {assignment.author && (
                <p className="text-sm text-gray-500 flex items-center">
                  <UserIcon className="h-4 w-4 mr-1" />
                  {assignment.author}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {assignment.is_completed && (
              <div className="flex items-center space-x-1 px-3 py-1 rounded-full text-sm bg-green-100 text-green-800">
                <CheckCircleIcon className="h-5 w-5" />
                <span>Completed</span>
              </div>
            )}
            <div className={`flex items-center space-x-1 px-3 py-1 rounded-full text-sm ${statusColors.bg} ${statusColors.text}`}>
              {getStatusIcon()}
              <span className="capitalize">{assignment.status.replace('_', ' ')}</span>
            </div>
          </div>
        </div>

        {/* Metadata */}
        <div className="space-y-2 mb-4">
          <div className="flex items-center text-sm text-gray-600">
            <CalendarIcon className="h-4 w-4 mr-2" />
            <span>{formatDateRange(assignment.start_date, assignment.end_date)}</span>
          </div>
          
          {timeRemaining && (
            <div className="flex items-center text-sm font-medium text-amber-600">
              <ClockIcon className="h-4 w-4 mr-2" />
              <span>{timeRemaining}</span>
            </div>
          )}

          {assignment.grade_level && (
            <div className="flex items-center text-sm text-gray-500">
              <span className="mr-2">Grade Level:</span>
              <span>{assignment.grade_level}</span>
            </div>
          )}
          
          {assignment.type === 'UMADebate' && assignment.is_completed && (
            <div className="flex items-center text-sm text-green-600">
              <CheckCircleIcon className="h-4 w-4 mr-2" />
              <span>All debates completed</span>
            </div>
          )}
        </div>

        {/* Test Availability Notice */}
        {((assignment.is_completed && assignment.has_test) || assignment.type === 'UMATest') && availability && !availability.allowed && (
          <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-start space-x-2">
              <ExclamationTriangleIcon className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-amber-800">Test Currently Unavailable</p>
                <p className="text-sm text-amber-700">{availability.message}</p>
                {availability.next_window && (
                  <p className="text-xs text-amber-600 mt-1">
                    Next available: {new Date(availability.next_window).toLocaleString()}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Type Badge */}
        <div className="flex items-center justify-between">
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
            assignment.type === 'UMARead' ? 'bg-blue-100 text-blue-800' :
            assignment.type === 'UMAVocab' ? 'bg-purple-100 text-purple-800' :
            assignment.type === 'UMADebate' ? 'bg-green-100 text-green-800' :
            assignment.type === 'UMAWrite' ? 'bg-amber-100 text-amber-800' :
            assignment.type === 'UMALecture' ? 'bg-indigo-100 text-indigo-800' :
            assignment.type === 'UMATest' ? 'bg-red-100 text-red-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {assignment.type}
          </span>

          <button
            onClick={handleAssignmentClick}
            disabled={assignment.status !== 'active' || ((assignment.is_completed || assignment.type === 'UMATest') && !canStartTest())}
            className={`flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              assignment.status === 'active'
                ? assignment.type === 'UMATest'
                  ? assignment.test_completed
                    ? 'bg-blue-600 text-white hover:bg-blue-700'  // Blue for View Results
                    : canStartTest()
                      ? 'bg-red-600 text-white hover:bg-red-700'  // Red for Start Test (UMATest)
                      : 'bg-red-100 text-red-800 cursor-not-allowed'
                  : assignment.is_completed
                    ? assignment.type === 'UMAWrite'
                      ? 'bg-blue-600 text-white hover:bg-blue-700'  // Blue for View Results (UMAWrite)
                      : assignment.has_test
                        ? assignment.test_completed
                          ? 'bg-blue-600 text-white hover:bg-blue-700'  // Blue for View Results
                          : canStartTest()
                            ? 'bg-green-600 text-white hover:bg-green-700'  // Green for Start Test
                            : 'bg-red-100 text-red-800 cursor-not-allowed'
                        : 'bg-green-100 text-green-800 cursor-not-allowed'
                    : 'bg-primary-600 text-white hover:bg-primary-700'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            {getButtonText()}
            {assignment.status === 'active' && (!assignment.is_completed || canStartTest()) && (
              assignment.type === 'UMAWrite' && assignment.is_completed
                ? <CheckCircleIcon className="h-4 w-4 ml-2" />  // Check icon for view results (UMAWrite)
                : assignment.has_test && assignment.is_completed 
                  ? assignment.test_completed
                    ? <CheckCircleIcon className="h-4 w-4 ml-2" />  // Check icon for view results
                    : canStartTest()
                      ? <FileCheckIcon className="h-4 w-4 ml-2" />  // Test icon for start test
                      : <LockClosedIcon className="h-4 w-4 ml-2" />  // Lock icon for locked test
                  : <ArrowRightIcon className="h-4 w-4 ml-2" />  // Arrow for start assignment
            )}
          </button>
        </div>
      </div>
    </div>
  )
}