'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthSupabase } from '@/hooks/useAuthSupabase';

interface AdminGuardProps {
  children: React.ReactNode;
}

export default function AdminGuard({ children }: AdminGuardProps) {
  const { user, isLoading: loading, loadUser } = useAuthSupabase();
  const router = useRouter();

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  useEffect(() => {
    console.log('AdminGuard - loading:', loading, 'user:', user);
    if (!loading && (!user || !user.is_admin)) {
      console.log('AdminGuard - Redirecting: user not admin');
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