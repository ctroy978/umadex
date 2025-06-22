'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import AdminGuard from '@/components/AdminGuard';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isLoading: loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user && !user.is_admin) {
      router.push('/dashboard');
    }
  }, [user, loading, router]);

  const handleExitAdmin = () => {
    // Exit admin mode and go to the user's normal dashboard
    if (user?.role === 'teacher') {
      router.push('/teacher/dashboard');
    } else if (user?.role === 'student') {
      router.push('/student/dashboard');
    } else {
      router.push('/dashboard');
    }
  };

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  return (
    <AdminGuard>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm border-b">
          <div className="container mx-auto px-4">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center space-x-8">
                <h1 className="text-xl font-semibold">Admin Panel</h1>
                <div className="flex space-x-4">
                  <a
                    href="/admin/dashboard"
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Dashboard
                  </a>
                  <a
                    href="/admin/users"
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Users
                  </a>
                  <a
                    href="/admin/audit-log"
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Audit Log
                  </a>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-500">
                  {user?.email}
                </span>
                <button
                  onClick={handleExitAdmin}
                  className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Exit Admin
                </button>
                <button
                  onClick={handleLogout}
                  className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </nav>
        <main>{children}</main>
      </div>
    </AdminGuard>
  );
}