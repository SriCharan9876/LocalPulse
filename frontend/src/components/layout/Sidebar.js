'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
  LayoutDashboard,
  TrendingUp,
  Sparkles,
  Megaphone,
  BookOpen,
  LogOut,
  MapPin,
  Store,
} from 'lucide-react';
import { LogoMark } from '@/components/ui/Logo';

export default function Sidebar() {
  const pathname = usePathname();
  const { merchant, logout } = useAuth();

  const OPERATE_ITEMS = [
    {
      name: 'Overview',
      href: '/dashboard',
      icon: LayoutDashboard,
      badge: null,
    },
    {
      name: 'Demand & Inventory',
      href: '/demand',
      icon: TrendingUp,
      badge: null,
    },
    {
      name: 'AI Business Copilot',
      href: '/copilot',
      icon: Sparkles,
      badge: 'Live',
    },
    {
      name: 'Local Map & Events',
      href: '/neighborhood',
      icon: MapPin,
      badge: 'New',
    },
    {
      name: 'Campaign',
      href: '/campaigns',
      icon: Megaphone,
      badge: null,
    },
    {
      name: 'Store Profile & Map',
      href: '/profile',
      icon: Store,
      badge: null,
    },
  ];


  const initials = merchant?.business_name
    ? merchant.business_name
      .split(' ')
      .map((w) => w[0])
      .slice(0, 2)
      .join('')
      .toUpperCase()
    : 'LP';

  return (
    <aside className="w-64 bg-[#151719] text-stone-200 rounded-[28px] border border-stone-800/80 shadow-[0_4px_24px_rgba(0,0,0,0.18)] flex flex-col shrink-0 overflow-hidden select-none">
      {/* Brand Header */}
      <div className="h-16 px-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <LogoMark size={36} />
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-base text-white tracking-tight">
              LocalPulse
            </span>
            <span className="text-[10px] font-black text-[#151719] bg-[#e0fd53] rounded-full px-2 py-0.5 tracking-wide">
              AI
            </span>
          </div>
        </div>
      </div>

      {/* Navigation Sections */}
      <nav className="flex-1 px-3 py-2 space-y-4 overflow-y-auto">
        {/* OPERATE SECTION */}
        <div>
          <div className="px-3 pb-1.5 text-[10px] font-bold text-stone-500 uppercase tracking-widest">
            Operate
          </div>
          <div className="space-y-1">
            {OPERATE_ITEMS.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-2xl text-xs md:text-sm font-semibold transition-all ${isActive
                      ? 'bg-[#e0fd53] text-[#151719] shadow-sm font-bold'
                      : 'text-stone-300 hover:text-white hover:bg-white/5'
                    }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon
                      className={`w-4 h-4 ${isActive ? 'text-[#151719]' : 'text-stone-400'
                        }`}
                    />
                    <span>{item.name}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-bold min-w-5 text-center ${isActive
                          ? 'bg-[#151719] text-[#e0fd53]'
                          : 'bg-[#25282d] text-stone-300 border border-white/5'
                        }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        </div>

      </nav>

      {/* Footer Links (Docs, Sign Out & Bottom User Pill) */}
      <div className="p-3 border-t border-white/5 space-y-1">
        <a
          href="https://github.com/SriCharan9876/LocalPulse"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-3 px-3.5 py-2 rounded-xl text-xs font-medium text-stone-400 hover:text-white hover:bg-white/5 transition-colors"
        >
          <BookOpen className="w-4 h-4 text-stone-500" />
          <span>Documentation</span>
        </a>
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3.5 py-2 rounded-xl text-xs font-medium text-stone-400 hover:text-[#d96b52] hover:bg-[#d96b52]/10 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>

      {/* Bottom Avatar Profile Bar */}
      <Link
        href="/profile"
        className="px-4 py-3 bg-[#111315] border-t border-white/5 flex items-center justify-between hover:bg-white/5 transition-colors cursor-pointer group"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-full bg-[#202327] border border-white/10 text-stone-200 font-bold text-xs flex items-center justify-center shrink-0 group-hover:border-[#e0fd53]/50">
            {initials}
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-white truncate group-hover:text-[#e0fd53]">
              {merchant?.owner_name || 'Store Owner'}
            </p>
            <p className="text-[10px] text-stone-400 truncate">
              {merchant?.business_name || 'Store Profile'}
            </p>
          </div>
        </div>
        <div className="w-2 h-2 rounded-full bg-[#e0fd53]" title="Online & Connected" />
      </Link>
    </aside>
  );
}

