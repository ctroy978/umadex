import { useState, useEffect } from 'react'
import { testScheduleApi } from '@/lib/testScheduleApi'
import type { TestAvailabilityStatus } from '@/types/testSchedule'

export function useTestAvailability(classroomId: string | null) {
  const [availability, setAvailability] = useState<TestAvailabilityStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!classroomId) return

    const checkAvailability = async () => {
      try {
        setLoading(true)
        setError(null)
        const status = await testScheduleApi.checkAvailability(classroomId)
        setAvailability(status)
      } catch (err) {
        console.error('Failed to check test availability:', err)
        setError('Failed to check test availability')
        // Default to available if check fails
        setAvailability({
          allowed: true,
          schedule_active: false,
          message: 'Schedule check unavailable',
          next_window: null,
          current_window_end: null,
          time_until_next: null
        })
      } finally {
        setLoading(false)
      }
    }

    checkAvailability()
    
    // Refresh availability every minute
    const interval = setInterval(checkAvailability, 60000)
    
    return () => clearInterval(interval)
  }, [classroomId])

  return { availability, loading, error }
}