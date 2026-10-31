'use client';

import { Sparkles } from 'lucide-react';

/*
 * Shown at the top of a popup that was opened from a recommendation and pre-filled
 * with recommended values. Makes clear nothing changes until the merchant confirms.
 */
export default function RecommendationBanner({ source = 'Overview', reason, children }) {
  return (
    <div className="p-3 rounded-2xl bg-[#e0fd53]/25 border border-[#d6f447] text-[11.5px] text-[#16181a] flex items-start gap-2">
      <Sparkles className="w-4 h-4 shrink-0 mt-0.5" />
      <div className="leading-relaxed">
        <p className="font-bold">
          Pre-filled from {source}
          {reason ? ` · ${reason}` : ''}
        </p>
        {children && <p className="text-stone-700">{children}</p>}
        <p className="text-stone-600">Review or change the values below. Nothing is applied until you confirm.</p>
      </div>
    </div>
  );
}

/**
 * Read recommendation values from the page URL once, then remove them from the URL
 * so a page refresh doesn't reopen the popup.
 */
export function takeRecommendationParams() {
  if (typeof window === 'undefined') return null;
  const params = new URLSearchParams(window.location.search);
  if (!params.get('rec')) return null;
  const values = Object.fromEntries(params.entries());
  window.history.replaceState(null, '', window.location.pathname);
  return values;
}
