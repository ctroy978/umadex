'use client'

import ComingSoon from '@/components/ComingSoon'
import { LanguageIcon } from '@heroicons/react/24/outline'

export default function UmaVocabPage() {
  return (
    <ComingSoon 
      title="uMaVocab Module"
      description="Build comprehensive vocabulary exercises with flashcards, word games, and contextual learning activities to expand your students' language skills."
      icon={LanguageIcon}
      color="bg-purple-500"
    />
  )
}