'use client'

import ComingSoon from '@/components/ComingSoon'
import { ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline'

export default function UmaDebatePage() {
  return (
    <ComingSoon 
      title="uMaDebate Module"
      description="Create structured debate activities where students can engage in thoughtful discussions, present arguments, and develop critical thinking skills."
      icon={ChatBubbleLeftRightIcon}
      color="bg-green-500"
    />
  )
}