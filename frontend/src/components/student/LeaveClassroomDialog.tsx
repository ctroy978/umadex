import { Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'

interface LeaveClassroomDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  classroomName: string
  teacherName: string
  assignmentCount: number
}

export default function LeaveClassroomDialog({
  isOpen,
  onClose,
  onConfirm,
  classroomName,
  teacherName,
  assignmentCount
}: LeaveClassroomDialogProps) {
  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
                    <ExclamationTriangleIcon className="h-6 w-6 text-red-600" aria-hidden="true" />
                  </div>
                  <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                    <Dialog.Title as="h3" className="text-lg font-semibold leading-6 text-gray-900">
                      Are you sure you want to leave this classroom?
                    </Dialog.Title>
                    <div className="mt-4 space-y-3">
                      <div className="bg-red-50 border border-red-200 rounded-md p-3">
                        <p className="text-sm font-medium text-red-800">
                          Warning: This action cannot be undone!
                        </p>
                      </div>
                      
                      <p className="text-sm text-gray-600">
                        You are about to leave <span className="font-semibold">{classroomName}</span> taught by {teacherName}.
                      </p>

                      <div className="bg-gray-50 rounded-md p-3">
                        <p className="text-sm font-medium text-gray-900 mb-2">
                          If you leave this classroom:
                        </p>
                        <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
                          <li>You will lose access to all {assignmentCount} assignment{assignmentCount !== 1 ? 's' : ''} in this class</li>
                          <li>Your progress on any assignments will be lost</li>
                          <li>You will need a new class code from your teacher to rejoin</li>
                          <li>Your teacher will be notified that you left</li>
                        </ul>
                      </div>

                      <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
                        <p className="text-sm text-amber-800">
                          <span className="font-medium">Alternative:</span> If you're having issues with the class, 
                          consider talking to your teacher first before leaving.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="mt-5 sm:mt-6 sm:flex sm:flex-row-reverse gap-3">
                  <button
                    type="button"
                    className="inline-flex w-full justify-center rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500 sm:w-auto"
                    onClick={onConfirm}
                  >
                    Yes, Leave Classroom
                  </button>
                  <button
                    type="button"
                    className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:mt-0 sm:w-auto"
                    onClick={onClose}
                  >
                    Cancel, Stay in Class
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}