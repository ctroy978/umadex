'use client'

import ComingSoon from '@/components/ComingSoon'
import { PencilSquareIcon } from '@heroicons/react/24/outline'

export default function UmaWritePage() {
  return (
    <ComingSoon 
      title="uMaWrite Module"
      description="Design creative writing assignments with prompts, rubrics, and peer review features to help students develop their writing skills."
      icon={PencilSquareIcon}
      color="bg-orange-500"
    />
  )
}