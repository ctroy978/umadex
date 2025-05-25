'use client'

import ComingSoon from '@/components/ComingSoon'
import { AcademicCapIcon } from '@heroicons/react/24/outline'

export default function UmaLecturePage() {
  return (
    <ComingSoon 
      title="uMaLecture Module"
      description="Create interactive lectures with multimedia content, quizzes, and engagement tools to make learning more dynamic and effective."
      icon={AcademicCapIcon}
      color="bg-red-500"
    />
  )
}