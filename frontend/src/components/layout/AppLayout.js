'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import { Loader2 } from 'lucide-react';

export default function AppLayout({ children, title, subtitle, fullHeight = false }) {
  const { merchant, loading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login');
    }
  }, [loading, isAuthenticated, router]);

  if (loading || !isAuthenticated) {
    return (
      <div className="min-h-screen bg-[#edece4] flex flex-col items-center justify-center p-4">
        <div className="flex items-center gap-3 px-6 py-4 rounded-3xl bg-white border border-stone-200/90 shadow-sm">
          <Loader2 className="w-5 h-5 text-[#16181a] animate-spin" />
          <p className="text-sm font-medium text-stone-700">Loading merchant workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#edece4] p-2.5 md:p-3.5 gap-3 md:gap-3.5">
      {/* Floating Left Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header title={title} subtitle={subtitle} />
        
        <main
          className={`flex-1 min-w-0 ${
            fullHeight
              ? 'overflow-hidden flex flex-col pt-0 pb-0 px-1 md:px-2'
              : 'overflow-y-auto pt-1 pb-6 px-1 md:px-2'
          }`}
        >
          <div
            className={`max-w-7xl mx-auto w-full ${
              fullHeight ? 'flex-1 flex flex-col min-h-0' : 'space-y-4'
            }`}
          >
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
