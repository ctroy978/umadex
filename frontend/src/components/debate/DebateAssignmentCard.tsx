'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Clock, MessageSquare, Users } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { formatDistanceToNow } from 'date-fns'
import { DebateAssignmentCard as DebateCardType } from '@/types/debate'
import { studentDebateApi } from '@/lib/studentDebateApi'

interface DebateAssignmentCardProps {
  assignment: DebateCardType
}

export default function DebateAssignmentCard({ assignment }: DebateAssignmentCardProps) {
  const router = useRouter()

  const handleClick = () => {
    router.push(`/student/debate/${assignment.assignment_id}`)
  }

  const getStatusBadge = () => {
    switch (assignment.status) {
      case 'not_started':
        return <Badge variant="outline">Not Started</Badge>
      case 'completed':
        return <Badge variant="default" className="bg-green-600">Completed</Badge>
      default:
        return (
          <Badge variant="secondary">
            Debate {assignment.current_debate_position ? assignment.debates_completed + 1 : assignment.debates_completed}/3
          </Badge>
        )
    }
  }

  const getProgressText = () => {
    if (assignment.status === 'not_started') {
      return 'Ready to start'
    } else if (assignment.status === 'completed') {
      return 'All debates completed'
    } else {
      const currentDebate = assignment.debates_completed + 1
      return `Round ${assignment.current_debate_position ? '1' : '0'}/${assignment.debate_format.rounds_per_debate}`
    }
  }

  const getTimeDisplay = () => {
    if (assignment.time_remaining) {
      return studentDebateApi.formatTimeRemaining(assignment.time_remaining)
    }
    
    const dueDate = new Date(assignment.due_date)
    const now = new Date()
    
    if (now > dueDate) {
      return 'Overdue'
    }
    
    return `Due ${formatDistanceToNow(dueDate, { addSuffix: true })}`
  }

  return (
    <Card 
      className="hover:shadow-md transition-shadow cursor-pointer"
      onClick={handleClick}
    >
      <CardHeader>
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <CardTitle className="text-lg">{assignment.title}</CardTitle>
            <CardDescription className="mt-1 line-clamp-2">
              {assignment.topic}
            </CardDescription>
          </div>
          {getStatusBadge()}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {/* Current Position */}
          {assignment.current_debate_position && (
            <div className="flex items-center text-sm text-muted-foreground">
              <Users className="mr-2 h-4 w-4" />
              <span>
                Current Position: <strong>{studentDebateApi.getPositionText(assignment.current_debate_position)}</strong>
              </span>
            </div>
          )}
          
          {/* Progress */}
          <div className="flex items-center text-sm text-muted-foreground">
            <MessageSquare className="mr-2 h-4 w-4" />
            <span>{getProgressText()}</span>
          </div>
          
          {/* Time */}
          <div className="flex items-center text-sm">
            <Clock className="mr-2 h-4 w-4" />
            <span className={assignment.time_remaining && assignment.time_remaining < 3600 ? 'text-orange-600' : 'text-muted-foreground'}>
              {getTimeDisplay()}
            </span>
          </div>
        </div>
        
        {assignment.can_start && assignment.status === 'not_started' && (
          <Button 
            className="w-full mt-4" 
            onClick={(e) => {
              e.stopPropagation()
              handleClick()
            }}
          >
            Start Debate
          </Button>
        )}
        
        {assignment.status !== 'not_started' && assignment.status !== 'completed' && (
          <Button 
            className="w-full mt-4" 
            variant="outline"
            onClick={(e) => {
              e.stopPropagation()
              handleClick()
            }}
          >
            Continue Debate
          </Button>
        )}
        
        {assignment.status === 'completed' && (
          <Button 
            className="w-full mt-4" 
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation()
              handleClick()
            }}
          >
            View Results
          </Button>
        )}
      </CardContent>
    </Card>
  )
}