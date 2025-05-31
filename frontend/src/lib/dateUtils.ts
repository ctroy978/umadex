import { formatDistanceToNow, format, isAfter, isBefore, differenceInDays, differenceInHours } from 'date-fns'

export function formatAssignmentDate(date: string | Date | null | undefined): string {
  if (!date) return ''
  
  const dateObj = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diffDays = differenceInDays(dateObj, now)
  const diffHours = differenceInHours(dateObj, now)
  
  // For dates within 7 days, use relative format
  if (Math.abs(diffDays) <= 7) {
    if (diffDays === 0) {
      if (diffHours === 0) return 'Now'
      if (diffHours > 0) return `in ${diffHours} hour${diffHours === 1 ? '' : 's'}`
      return `${Math.abs(diffHours)} hour${Math.abs(diffHours) === 1 ? '' : 's'} ago`
    }
    if (diffDays === 1) return 'Tomorrow'
    if (diffDays === -1) return 'Yesterday'
    if (diffDays > 0) return `in ${diffDays} days`
    return `${Math.abs(diffDays)} days ago`
  }
  
  // For dates further out, use absolute format
  return format(dateObj, 'MMM d, yyyy')
}

export function formatDateRange(startDate?: string | null, endDate?: string | null): string {
  if (!startDate && !endDate) return 'Always available'
  
  const now = new Date()
  const start = startDate ? new Date(startDate) : null
  const end = endDate ? new Date(endDate) : null
  
  if (start && isBefore(now, start)) {
    return `Starts ${formatAssignmentDate(start)}`
  }
  
  if (end && isAfter(now, end)) {
    return `Ended ${formatAssignmentDate(end)}`
  }
  
  if (end) {
    return `Due ${formatAssignmentDate(end)}`
  }
  
  return 'Available now'
}

export function getTimeRemaining(endDate: string | null | undefined): string | null {
  if (!endDate) return null
  
  const end = new Date(endDate)
  const now = new Date()
  
  if (isBefore(end, now)) return null
  
  const diffDays = differenceInDays(end, now)
  const diffHours = differenceInHours(end, now) % 24
  
  if (diffDays > 0) {
    return `${diffDays} day${diffDays === 1 ? '' : 's'} remaining`
  }
  
  if (diffHours > 0) {
    return `${diffHours} hour${diffHours === 1 ? '' : 's'} remaining`
  }
  
  return 'Due soon'
}

export function getStatusColor(status: 'not_started' | 'active' | 'expired'): {
  bg: string
  text: string
  border: string
} {
  switch (status) {
    case 'not_started':
      return {
        bg: 'bg-gray-50',
        text: 'text-gray-600',
        border: 'border-gray-200'
      }
    case 'active':
      return {
        bg: 'bg-green-50',
        text: 'text-green-700',
        border: 'border-green-200'
      }
    case 'expired':
      return {
        bg: 'bg-red-50',
        text: 'text-red-700',
        border: 'border-red-200'
      }
  }
}

export function getStatusIcon(status: 'not_started' | 'active' | 'expired'): string {
  switch (status) {
    case 'not_started':
      return 'ClockIcon'
    case 'active':
      return 'PlayCircleIcon'
    case 'expired':
      return 'XCircleIcon'
  }
}