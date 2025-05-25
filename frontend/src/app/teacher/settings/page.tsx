'use client'

import ComingSoon from '@/components/ComingSoon'
import { Cog6ToothIcon } from '@heroicons/react/24/outline'

export default function SettingsPage() {
  return (
    <ComingSoon 
      title="Settings"
      description="Configure your teaching preferences, notification settings, and customize your dashboard experience."
      icon={Cog6ToothIcon}
      color="bg-gray-500"
    />
  )
}