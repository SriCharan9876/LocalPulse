'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import {
  ChevronDown,
  Check,
  Store,
  Loader2,
  MapPin
} from 'lucide-react';
import api from '@/lib/api';

export default function Header({ title, subtitle }) {
  const { merchant, demoMerchants, switchDemoMerchant } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [switching, setSwitching] = useState(false);

  const handleSelectDemo = async (mId) => {
    if (mId === merchant?.merchant_id) {
      setDropdownOpen(false);
      return;
    }
    setSwitching(true);
    setDropdownOpen(false);
    try {
      await switchDemoMerchant(mId);
    } catch (err) {
      console.error('Failed to switch demo merchant:', err);
      alert('Failed to switch merchant. Please check backend connection.');
    } finally {
      setSwitching(false);
    }
  };

  const initials = merchant?.business_name
    ? merchant.business_name
        .split(' ')
        .map((w) => w[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : 'SM';

  return (
    <header className="h-14 px-2 flex items-center justify-between shrink-0 mb-1 select-none">
      {/* Title & Subtitle with Dribbble Display Typography */}
      <div>
        <h1 className="text-lg md:text-xl font-extrabold text-[#16181a] tracking-tight leading-tight flex items-center gap-2">
          <span>{title}</span>
        </h1>
        {subtitle && (
          <p className="text-[11.5px] text-stone-500 font-medium truncate max-w-xl lg:max-w-2xl mt-0.5">
            {subtitle}
          </p>
        )}
      </div>

      {/* Right Controls: Functional Demo Merchant Switcher & Merchant Avatar */}
      <div className="flex items-center gap-2.5">
        {/* Working Demo Merchant Switcher Pill */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            disabled={switching}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full border bg-white hover:bg-stone-50 text-[#16181a] text-xs font-semibold shadow-2xs transition-all ${
              dropdownOpen
                ? 'border-[#16181a] ring-2 ring-[#16181a]/10'
                : 'border-stone-200/90'
            }`}
            title="Switch demo merchant account"
          >
            <div className="w-5 h-5 rounded-full bg-[#16181a] text-[#e0fd53] flex items-center justify-center shrink-0">
              <Store className="w-3 h-3" />
            </div>
            <span className="truncate max-w-[130px] sm:max-w-[180px]">
              {switching ? 'Switching...' : merchant?.business_name || 'Select Merchant'}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-stone-400" />
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-3xl shadow-xl border border-stone-200/90 p-2 z-50 animate-in fade-in slide-in-from-top-1">
              <div className="px-3 py-2 border-b border-stone-100">
                <p className="text-[10px] font-bold text-stone-400 uppercase tracking-wider">
                  Select Active MSME Context
                </p>
                <p className="text-[11px] text-stone-500">
                  Issues server JWT session token
                </p>
              </div>

              <div className="py-1 max-h-64 overflow-y-auto space-y-0.5">
                {demoMerchants.length === 0 ? (
                  <p className="text-xs text-stone-400 px-3 py-2">
                    No demo merchants found
                  </p>
                ) : (
                  demoMerchants.map((m) => {
                    const isSelected = m.merchant_id === merchant?.merchant_id;
                    return (
                      <button
                        key={m.merchant_id}
                        onClick={() => handleSelectDemo(m.merchant_id)}
                        className={`w-full text-left px-3 py-2 rounded-2xl flex items-center justify-between transition-colors ${
                          isSelected
                            ? 'bg-[#16181a] text-white font-semibold'
                            : 'hover:bg-stone-100 text-stone-800'
                        }`}
                      >
                        <div className="min-w-0 pr-2">
                          <p className="text-xs font-semibold truncate">
                            {m.business_name}
                          </p>
                          <p className={`text-[10px] truncate ${isSelected ? 'text-stone-300' : 'text-stone-400'}`}>
                            {m.owner_name} • {m.category}
                          </p>
                        </div>
                        {isSelected && (
                          <div className="w-5 h-5 rounded-full bg-[#e0fd53] text-[#16181a] flex items-center justify-center shrink-0">
                            <Check className="w-3 h-3 stroke-[3]" />
                          </div>
                        )}
                      </button>
                    );
                  })
                )}
              </div>

              {/* Store Profile Quick Action inside dropdown */}
              <div className="pt-2 px-1 border-t border-stone-100 space-y-1">
                <Link
                  href="/profile"
                  onClick={() => setDropdownOpen(false)}
                  className="w-full text-left px-3 py-2 rounded-2xl bg-stone-50 hover:bg-stone-100 text-stone-800 text-[11px] font-bold flex items-center justify-between transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-1.5">
                    <Store className="w-3.5 h-3.5 text-stone-600" />
                    <span>My Store Profile & Map</span>
                  </div>
                  <span className="text-[9.5px] uppercase font-bold text-stone-400">View</span>
                </Link>
              </div>

              <div className="pt-2 px-3 pb-1 text-[10px] text-stone-400 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#e0fd53] border border-[#16181a] inline-block" />
                  <span>Verified MSME merchant</span>
                </div>
                {merchant?.latitude && (
                  <span className="font-mono text-[9px] text-stone-400">
                    {merchant.latitude.toFixed(2)}°, {merchant.longitude?.toFixed(2)}°
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Avatar Circle with Merchant Initials */}
        <div
          title={`${merchant?.business_name || 'Merchant'} (${merchant?.category || ''}) - ${merchant?.latitude ? `${merchant.latitude.toFixed(4)}° N, ${merchant.longitude?.toFixed(4)}° E` : ''}`}
          className="w-8 h-8 rounded-full bg-[#16181a] text-[#e0fd53] font-bold text-xs flex items-center justify-center shadow-xs shrink-0 border border-stone-200"
        >
          {initials}
        </div>
      </div>
    </header>
  );
}
