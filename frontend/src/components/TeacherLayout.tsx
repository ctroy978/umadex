'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import TokenExpiryWarning from '@/components/TokenExpiryWarning'
import { 
  HomeIcon,
  BookOpenIcon,
  ChatBubbleLeftRightIcon,
  LanguageIcon,
  PencilSquareIcon,
  AcademicCapIcon,
  UserGroupIcon,
  UsersIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  ArrowLeftOnRectangleIcon
} from '@heroicons/react/24/outline'

const navigation = [
  { name: 'Dashboard', href: '/teacher/dashboard', icon: HomeIcon },
  { name: 'uMaRead', href: '/teacher/uma-read', icon: BookOpenIcon },
  { name: 'uMaDebate', href: '/teacher/uma-debate', icon: ChatBubbleLeftRightIcon },
  { name: 'uMaVocab', href: '/teacher/uma-vocab', icon: LanguageIcon },
  { name: 'uMaWrite', href: '/teacher/uma-write', icon: PencilSquareIcon },
  { name: 'uMaLecture', href: '/teacher/uma-lecture', icon: AcademicCapIcon },
]

const utilities = [
  { name: 'Classrooms', href: '/teacher/classrooms', icon: UserGroupIcon },
  { name: 'Students', href: '/teacher/students', icon: UsersIcon },
  { name: 'Reports', href: '/teacher/reports', icon: ChartBarIcon },
  { name: 'Settings', href: '/teacher/settings', icon: Cog6ToothIcon },
]

export default function TeacherLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuth()

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <TokenExpiryWarning />
      <div className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        <div className="hidden md:flex md:flex-shrink-0">
          <div className="flex flex-col w-64">
            <div className="flex flex-col flex-grow pt-5 pb-4 overflow-y-auto bg-white border-r border-gray-200">
              <div className="flex items-center flex-shrink-0 px-4">
                <h1 className="text-2xl font-bold text-primary-600">UmaDex</h1>
              </div>
              <div className="mt-8 flex-grow flex flex-col">
                <nav className="flex-1 px-2 space-y-8">
                  <div>
                    <h3 className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Modules
                    </h3>
                    <div className="mt-2 space-y-1">
                      {navigation.map((item) => {
                        const isActive = pathname === item.href
                        return (
                          <Link
                            key={item.name}
                            href={item.href}
                            className={`
                              group flex items-center px-2 py-2 text-sm font-medium rounded-md
                              ${isActive
                                ? 'bg-primary-100 text-primary-900'
                                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                              }
                            `}
                          >
                            <item.icon
                              className={`
                                mr-3 flex-shrink-0 h-6 w-6
                                ${isActive ? 'text-primary-600' : 'text-gray-400 group-hover:text-gray-500'}
                              `}
                              aria-hidden="true"
                            />
                            {item.name}
                          </Link>
                        )
                      })}
                    </div>
                  </div>
                  <div>
                    <h3 className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Utilities
                    </h3>
                    <div className="mt-2 space-y-1">
                      {utilities.map((item) => {
                        const isActive = pathname === item.href
                        return (
                          <Link
                            key={item.name}
                            href={item.href}
                            className={`
                              group flex items-center px-2 py-2 text-sm font-medium rounded-md
                              ${isActive
                                ? 'bg-primary-100 text-primary-900'
                                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                              }
                            `}
                          >
                            <item.icon
                              className={`
                                mr-3 flex-shrink-0 h-6 w-6
                                ${isActive ? 'text-primary-600' : 'text-gray-400 group-hover:text-gray-500'}
                              `}
                              aria-hidden="true"
                            />
                            {item.name}
                          </Link>
                        )
                      })}
                    </div>
                  </div>
                </nav>
              </div>
              <div className="flex-shrink-0 flex border-t border-gray-200 p-4">
                <div className="flex items-center w-full">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">
                      {user?.first_name} {user?.last_name}
                    </p>
                    <p className="text-xs text-gray-500">{user?.email}</p>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="ml-3 p-1 text-gray-400 hover:text-gray-500"
                  >
                    <ArrowLeftOnRectangleIcon className="h-6 w-6" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="flex flex-col flex-1 overflow-hidden">
          <main className="flex-1 relative overflow-y-auto focus:outline-none">
            {children}
          </main>
        </div>
      </div>
    </div>
  )
}