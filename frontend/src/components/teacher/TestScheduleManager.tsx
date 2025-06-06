import { useState, useEffect } from 'react'
import { 
  ClockIcon, 
  CalendarDaysIcon,
  PlusIcon,
  TrashIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XMarkIcon,
  DocumentDuplicateIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'
import { testScheduleApi } from '@/lib/testScheduleApi'
import type { 
  ClassroomTestSchedule, 
  ScheduleWindow, 
  ScheduleTemplate,
  TestAvailabilityStatus,
  OverrideCode
} from '@/types/testSchedule'

interface Props {
  classroomId: string
}

const DAYS_OF_WEEK = [
  { value: 'monday', label: 'Mon', fullLabel: 'Monday' },
  { value: 'tuesday', label: 'Tue', fullLabel: 'Tuesday' },
  { value: 'wednesday', label: 'Wed', fullLabel: 'Wednesday' },
  { value: 'thursday', label: 'Thu', fullLabel: 'Thursday' },
  { value: 'friday', label: 'Fri', fullLabel: 'Friday' },
  { value: 'saturday', label: 'Sat', fullLabel: 'Saturday' },
  { value: 'sunday', label: 'Sun', fullLabel: 'Sunday' }
]

const DEFAULT_COLORS = [
  '#3B82F6', // blue
  '#10B981', // green
  '#F59E0B', // amber
  '#8B5CF6', // violet
  '#EC4899', // pink
  '#14B8A6', // teal
]

export default function TestScheduleManager({ classroomId }: Props) {
  const [schedule, setSchedule] = useState<ClassroomTestSchedule | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [templates, setTemplates] = useState<ScheduleTemplate[]>([])
  const [currentStatus, setCurrentStatus] = useState<TestAvailabilityStatus | null>(null)
  const [overrideCodes, setOverrideCodes] = useState<OverrideCode[]>([])
  const [showTemplates, setShowTemplates] = useState(false)
  const [editingWindow, setEditingWindow] = useState<ScheduleWindow | null>(null)
  const [showOverrideForm, setShowOverrideForm] = useState(false)

  useEffect(() => {
    fetchScheduleData()
  }, [classroomId])

  const fetchScheduleData = async () => {
    try {
      setLoading(true)
      const [scheduleData, templatesData, statusData, overridesData] = await Promise.all([
        testScheduleApi.getClassroomSchedule(classroomId).catch(() => null),
        testScheduleApi.getScheduleTemplates(),
        testScheduleApi.checkAvailability(classroomId),
        testScheduleApi.getActiveOverrides(classroomId)
      ])

      if (scheduleData) {
        setSchedule(scheduleData)
      }
      setTemplates(templatesData)
      setCurrentStatus(statusData)
      setOverrideCodes(overridesData)
    } catch (error) {
      console.error('Failed to fetch schedule data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleSchedule = async () => {
    if (!schedule) return
    
    try {
      setSaving(true)
      await testScheduleApi.toggleSchedule(classroomId, !schedule.is_active)
      setSchedule({ ...schedule, is_active: !schedule.is_active })
      
      // Refresh status
      const newStatus = await testScheduleApi.checkAvailability(classroomId)
      setCurrentStatus(newStatus)
    } catch (error) {
      console.error('Failed to toggle schedule:', error)
      alert('Failed to toggle schedule. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleApplyTemplate = async (template: ScheduleTemplate) => {
    if (!confirm(`Apply "${template.name}" template to this classroom?`)) return

    try {
      setSaving(true)
      const newSchedule = await testScheduleApi.createOrUpdateSchedule(classroomId, {
        classroom_id: classroomId,
        is_active: true,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        grace_period_minutes: 30,
        schedule_data: template.schedule_data
      })
      
      setSchedule(newSchedule)
      setShowTemplates(false)
      
      // Refresh status
      const newStatus = await testScheduleApi.checkAvailability(classroomId)
      setCurrentStatus(newStatus)
    } catch (error) {
      console.error('Failed to apply template:', error)
      alert('Failed to apply template. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleAddWindow = () => {
    const newWindow: ScheduleWindow = {
      id: `window_${Date.now()}`,
      name: 'New Testing Window',
      days: ['monday'],
      start_time: '09:00',
      end_time: '10:00',
      color: DEFAULT_COLORS[schedule?.schedule_data.windows.length || 0 % DEFAULT_COLORS.length]
    }
    setEditingWindow(newWindow)
  }

  const handleSaveWindow = async (window: ScheduleWindow) => {
    if (!schedule) return

    try {
      setSaving(true)
      const updatedWindows = editingWindow && schedule.schedule_data.windows.find(w => w.id === editingWindow.id)
        ? schedule.schedule_data.windows.map(w => w.id === window.id ? window : w)
        : [...schedule.schedule_data.windows, window]

      const updatedSchedule = await testScheduleApi.createOrUpdateSchedule(classroomId, {
        ...schedule,
        schedule_data: {
          ...schedule.schedule_data,
          windows: updatedWindows
        }
      })

      setSchedule(updatedSchedule)
      setEditingWindow(null)
      
      // Refresh status
      const newStatus = await testScheduleApi.checkAvailability(classroomId)
      setCurrentStatus(newStatus)
    } catch (error) {
      console.error('Failed to save window:', error)
      alert('Failed to save window. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteWindow = async (windowId: string) => {
    if (!schedule || !confirm('Delete this testing window?')) return

    try {
      setSaving(true)
      const updatedWindows = schedule.schedule_data.windows.filter(w => w.id !== windowId)

      const updatedSchedule = await testScheduleApi.createOrUpdateSchedule(classroomId, {
        ...schedule,
        schedule_data: {
          ...schedule.schedule_data,
          windows: updatedWindows
        }
      })

      setSchedule(updatedSchedule)
    } catch (error) {
      console.error('Failed to delete window:', error)
      alert('Failed to delete window. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleGenerateOverride = async (data: { reason: string; expires_in_hours: number; max_uses: number }) => {
    try {
      const newOverride = await testScheduleApi.generateOverrideCode({
        classroom_id: classroomId,
        ...data
      })
      
      setOverrideCodes([newOverride, ...overrideCodes])
      setShowOverrideForm(false)
    } catch (error) {
      console.error('Failed to generate override code:', error)
      alert('Failed to generate override code. Please try again.')
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Current Status */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Test Schedule Status</h3>
          {schedule && (
            <button
              onClick={handleToggleSchedule}
              disabled={saving}
              className={`inline-flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                schedule.is_active
                  ? 'bg-red-100 text-red-700 hover:bg-red-200'
                  : 'bg-green-100 text-green-700 hover:bg-green-200'
              }`}
            >
              {schedule.is_active ? 'Disable Schedule' : 'Enable Schedule'}
            </button>
          )}
        </div>

        <div className="flex items-center space-x-4">
          {currentStatus?.allowed ? (
            <>
              <CheckCircleIcon className="h-8 w-8 text-green-500" />
              <div>
                <p className="text-lg font-medium text-green-700">Testing is currently available</p>
                {currentStatus.current_window_end && (
                  <p className="text-sm text-gray-600">
                    Until {new Date(currentStatus.current_window_end).toLocaleTimeString()}
                  </p>
                )}
              </div>
            </>
          ) : (
            <>
              <XMarkIcon className="h-8 w-8 text-red-500" />
              <div>
                <p className="text-lg font-medium text-red-700">Testing is not available</p>
                <p className="text-sm text-gray-600">{currentStatus?.message}</p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Schedule Configuration */}
      {!schedule ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <ClockIcon className="h-12 w-12 mx-auto mb-4 text-gray-400" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Test Schedule Configured</h3>
          <p className="text-gray-600 mb-6">
            Set up testing windows to control when students can take tests in this classroom.
          </p>
          <button
            onClick={() => setShowTemplates(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
          >
            <CalendarDaysIcon className="h-5 w-5 mr-2" />
            Choose a Template
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Testing Windows</h3>
            <div className="space-x-2">
              <button
                onClick={() => setShowTemplates(true)}
                className="inline-flex items-center px-3 py-1 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                <ArrowPathIcon className="h-4 w-4 mr-1" />
                Change Template
              </button>
              <button
                onClick={handleAddWindow}
                className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
              >
                <PlusIcon className="h-4 w-4 mr-1" />
                Add Window
              </button>
            </div>
          </div>

          {schedule.schedule_data.windows.length === 0 ? (
            <div className="text-center py-8 bg-gray-50 rounded-lg">
              <p className="text-gray-500">No testing windows configured</p>
              <button
                onClick={handleAddWindow}
                className="mt-2 text-primary-600 hover:text-primary-700 text-sm font-medium"
              >
                Add your first testing window
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {schedule.schedule_data.windows.map((window) => (
                <div
                  key={window.id}
                  className="border rounded-lg p-4 hover:bg-gray-50"
                  style={{ borderLeftColor: window.color, borderLeftWidth: '4px' }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900">{window.name}</h4>
                      <p className="text-sm text-gray-600 mt-1">
                        {window.days.map(d => DAYS_OF_WEEK.find(day => day.value === d)?.label).join(', ')}
                        {' • '}
                        {window.start_time} - {window.end_time}
                      </p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => setEditingWindow(window)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteWindow(window.id)}
                        className="text-red-400 hover:text-red-600"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Settings */}
          <div className="mt-6 pt-6 border-t">
            <h4 className="text-sm font-medium text-gray-900 mb-3">Schedule Settings</h4>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Grace Period</span>
                <span className="text-sm font-medium">{schedule.grace_period_minutes} minutes</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Timezone</span>
                <span className="text-sm font-medium">{schedule.timezone}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Emergency Override Codes */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Emergency Override Codes</h3>
            <p className="text-sm text-gray-600">Generate codes to allow testing outside scheduled windows</p>
          </div>
          <button
            onClick={() => setShowOverrideForm(true)}
            className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
          >
            <ExclamationTriangleIcon className="h-4 w-4 mr-1" />
            Generate Code
          </button>
        </div>

        {overrideCodes.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 rounded-lg">
            <p className="text-gray-500">No active override codes</p>
          </div>
        ) : (
          <div className="space-y-3">
            {overrideCodes.map((override) => (
              <div key={override.id} className="border rounded-lg p-4 bg-red-50 border-red-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-lg font-bold text-red-700">
                        {override.override_code}
                      </span>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(override.override_code)
                          alert('Code copied to clipboard!')
                        }}
                        className="text-red-600 hover:text-red-700"
                      >
                        <DocumentDuplicateIcon className="h-4 w-4" />
                      </button>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{override.reason}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      Uses: {override.current_uses}/{override.max_uses} • 
                      Expires: {new Date(override.expires_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Template Selection Modal */}
      {showTemplates && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Choose a Schedule Template</h3>
              <button
                onClick={() => setShowTemplates(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>
            
            <div className="grid gap-4">
              {templates.map((template) => (
                <button
                  key={template.id}
                  onClick={() => handleApplyTemplate(template)}
                  className="text-left border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                >
                  <h4 className="font-medium text-gray-900">{template.name}</h4>
                  <p className="text-sm text-gray-600 mt-1">{template.description}</p>
                  <div className="mt-2 text-xs text-gray-500">
                    {template.schedule_data.windows.map((w, i) => (
                      <span key={i}>
                        {i > 0 && ' • '}
                        {w.name}: {w.start_time}-{w.end_time}
                      </span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Window Editor Modal */}
      {editingWindow && (
        <WindowEditor
          window={editingWindow}
          onSave={handleSaveWindow}
          onCancel={() => setEditingWindow(null)}
        />
      )}

      {/* Override Form Modal */}
      {showOverrideForm && (
        <OverrideCodeForm
          onGenerate={handleGenerateOverride}
          onCancel={() => setShowOverrideForm(false)}
        />
      )}
    </div>
  )
}

// Window Editor Component
function WindowEditor({ 
  window, 
  onSave, 
  onCancel 
}: { 
  window: ScheduleWindow; 
  onSave: (window: ScheduleWindow) => void; 
  onCancel: () => void;
}) {
  const [editedWindow, setEditedWindow] = useState(window)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate times
    if (editedWindow.start_time >= editedWindow.end_time) {
      alert('End time must be after start time')
      return
    }
    
    // Validate days
    if (editedWindow.days.length === 0) {
      alert('Please select at least one day')
      return
    }
    
    onSave(editedWindow)
  }

  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Edit Testing Window
        </h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Window Name
            </label>
            <input
              type="text"
              value={editedWindow.name}
              onChange={(e) => setEditedWindow({ ...editedWindow, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Days
            </label>
            <div className="grid grid-cols-7 gap-2">
              {DAYS_OF_WEEK.map((day) => (
                <button
                  key={day.value}
                  type="button"
                  onClick={() => {
                    const days = editedWindow.days.includes(day.value)
                      ? editedWindow.days.filter(d => d !== day.value)
                      : [...editedWindow.days, day.value]
                    setEditedWindow({ ...editedWindow, days })
                  }}
                  className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    editedWindow.days.includes(day.value)
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {day.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Start Time
              </label>
              <input
                type="time"
                value={editedWindow.start_time}
                onChange={(e) => setEditedWindow({ ...editedWindow, start_time: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                End Time
              </label>
              <input
                type="time"
                value={editedWindow.end_time}
                onChange={(e) => setEditedWindow({ ...editedWindow, end_time: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Color
            </label>
            <div className="flex space-x-2">
              {DEFAULT_COLORS.map((color) => (
                <button
                  key={color}
                  type="button"
                  onClick={() => setEditedWindow({ ...editedWindow, color })}
                  className={`w-8 h-8 rounded-full border-2 ${
                    editedWindow.color === color ? 'border-gray-900' : 'border-transparent'
                  }`}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
            >
              Save Window
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Override Code Form Component
function OverrideCodeForm({ 
  onGenerate, 
  onCancel 
}: { 
  onGenerate: (data: { reason: string; expires_in_hours: number; max_uses: number }) => void;
  onCancel: () => void;
}) {
  const [reason, setReason] = useState('')
  const [expiresIn, setExpiresIn] = useState(24)
  const [maxUses, setMaxUses] = useState(1)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onGenerate({
      reason,
      expires_in_hours: expiresIn,
      max_uses: maxUses
    })
  }

  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Generate Emergency Override Code
        </h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Reason for Override
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
              rows={3}
              required
              placeholder="e.g., Student was sick during regular testing window"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Expires After (hours)
            </label>
            <select
              value={expiresIn}
              onChange={(e) => setExpiresIn(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              <option value={1}>1 hour</option>
              <option value={6}>6 hours</option>
              <option value={24}>24 hours</option>
              <option value={48}>48 hours</option>
              <option value={72}>72 hours</option>
              <option value={168}>1 week</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Maximum Uses
            </label>
            <input
              type="number"
              value={maxUses}
              onChange={(e) => setMaxUses(Number(e.target.value))}
              min={1}
              max={100}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-red-600 hover:bg-red-700"
            >
              Generate Code
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}