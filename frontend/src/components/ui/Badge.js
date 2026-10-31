'use client';

import React from 'react';

export default function Badge({
  children,
  variant = 'default',
  size = 'md',
  dot = false,
}) {
  const variantStyles = {
    default: 'bg-stone-100 text-stone-700 border-stone-200/90',
    primary: 'bg-[#16181a] text-white border-[#16181a]',
    lime: 'bg-[#e0fd53] text-[#16181a] border-[#d8f547] font-bold',
    success: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
    warning: 'bg-[#faeed6] text-[#8c5208] border-[#f2d8a5]',
    danger: 'bg-[#fbe8e4] text-[#a43b27] border-[#f3c5bd]',
    purple: 'bg-purple-50 text-purple-700 border-purple-200/80',
    dark: 'bg-[#16181a] text-white border-stone-800',
  };

  const dotColors = {
    default: 'bg-stone-400',
    primary: 'bg-white',
    lime: 'bg-[#16181a]',
    success: 'bg-emerald-600',
    warning: 'bg-[#b45309]',
    danger: 'bg-[#c25e4e]',
    purple: 'bg-purple-500',
    dark: 'bg-[#e0fd53]',
  };

  const sizeStyles = {
    sm: 'text-[10px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-0.5',
    lg: 'text-xs px-3 py-1 font-semibold',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium border ${
        variantStyles[variant] || variantStyles.default
      } ${sizeStyles[size] || sizeStyles.md}`}
    >
      {dot && (
        <span
          className={`w-1.5 h-1.5 rounded-full shrink-0 ${
            dotColors[variant] || 'bg-slate-400'
          }`}
        />
      )}
      {children}
    </span>
  );
}

