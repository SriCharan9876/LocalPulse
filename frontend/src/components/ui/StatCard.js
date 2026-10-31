'use client';

import React from 'react';

export default function StatCard({
  title,
  value,
  subvalue,
  icon: Icon,
  metricMeta,
  trend,
  trendPositive = true,
  alert = false,
  badgeText,
}) {
  return (
    <div
      className={`p-6 rounded-[26px] bg-white border transition-all duration-200 shadow-[0_4px_20px_rgba(20,24,20,0.03)] ${
        alert
          ? 'border-[#f2d8a5] ring-2 ring-[#faeed6]'
          : 'border-stone-200/90 hover:border-stone-300'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <span className="text-xs md:text-sm font-bold text-[#16181a] tracking-tight block">
            {title}
          </span>
          {metricMeta && (
            <span className="text-[10px] font-semibold text-stone-400">
              {metricMeta}
            </span>
          )}
        </div>
        {Icon ? (
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border border-stone-200/80 ${
              alert
                ? 'bg-[#faeed6] text-[#8c5208]'
                : 'bg-stone-50 text-stone-700'
            }`}
          >
            <Icon className="w-4 h-4" />
          </div>
        ) : badgeText ? (
          <span className="text-[10px] font-bold text-stone-600 bg-[#f7f8f4] border border-stone-200/90 px-2.5 py-0.5 rounded-full">
            {badgeText}
          </span>
        ) : null}
      </div>

      <div className="flex items-baseline justify-between gap-2">
        <span className="text-2xl md:text-3xl font-black text-[#16181a] tracking-tight font-sans">
          {value}
        </span>
        {trend && (
          <span
            className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full ${
              trendPositive
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200/80'
                : 'bg-[#fbe8e4] text-[#a43b27] border border-[#f3c5bd]'
            }`}
          >
            {trend}
          </span>
        )}
      </div>

      {subvalue && (
        <p className="mt-2.5 text-xs text-stone-500 font-medium">
          {subvalue}
        </p>
      )}
    </div>
  );
}

