'use client'

import ComingSoon from '@/components/ComingSoon'
import { UsersIcon } from '@heroicons/react/24/outline'

export default function StudentsPage() {
  return (
    <ComingSoon 
      title="Student Management"
      description="View all your students across classrooms, track their progress, and manage enrollments from one central location."
      icon={UsersIcon}
      color="bg-pink-500"
    />
  )
}