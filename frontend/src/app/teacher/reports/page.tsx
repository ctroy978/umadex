'use client'

import ComingSoon from '@/components/ComingSoon'
import { ChartBarIcon } from '@heroicons/react/24/outline'

export default function ReportsPage() {
  return (
    <ComingSoon 
      title="Reports & Analytics"
      description="Access detailed reports on student performance, assignment completion rates, and classroom analytics to track progress and identify areas for improvement."
      icon={ChartBarIcon}
      color="bg-teal-500"
    />
  )
}