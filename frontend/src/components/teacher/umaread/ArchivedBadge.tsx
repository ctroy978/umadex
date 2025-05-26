'use client';

import React from 'react';
import { ArchiveBoxIcon } from '@heroicons/react/24/outline';

interface ArchivedBadgeProps {
  className?: string;
}

export default function ArchivedBadge({ className = '' }: ArchivedBadgeProps) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 ${className}`}>
      <ArchiveBoxIcon className="w-3 h-3 mr-1" />
      Archived
    </span>
  );
}