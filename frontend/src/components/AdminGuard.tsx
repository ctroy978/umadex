'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';

interface AdminGuardProps {
  children: React.ReactNode;
}

export default function AdminGuard({ children }: AdminGuardProps) {
  const { user, isLoading: loading, loadUser } = useAuth();
  const router = useRouter();

  console.log('AdminGuard render:', { user, loading, is_admin: user?.is_admin });

  useEffect(() => {
    console.log('AdminGuard: Calling loadUser()');
    loadUser();
  }, [loadUser]);

  useEffect(() => {
    console.log('AdminGuard useEffect:', { loading, user, is_admin: user?.is_admin });
    if (!loading && (!user || !user.is_admin)) {
      console.log('AdminGuard: Redirecting to /dashboard');
      router.push('/dashboard');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!user || !user.is_admin) {
    return null;
  }

  return <>{children}</>;
}