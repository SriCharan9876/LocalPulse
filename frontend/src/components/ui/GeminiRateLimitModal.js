'use client';

import React, { useState, useEffect } from 'react';
import Modal from '@/components/ui/Modal';
import { GEMINI_RATE_LIMIT_EVENT } from '@/lib/geminiRateLimit';
import { Sparkles, Clock, AlertTriangle, ShieldCheck, Check } from 'lucide-react';

export default function GeminiRateLimitModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [info, setInfo] = useState({
    title: 'Gemini AI Limits Reached',
    message: 'The Gemini AI rate limit has been reached. Please wait and try after some time to explore AI capabilities.',
  });

  useEffect(() => {
    const handleEvent = (event) => {
      if (event?.detail) {
        setInfo((prev) => ({
          ...prev,
          ...event.detail,
        }));
      }
      setIsOpen(true);
    };

    if (typeof window !== 'undefined') {
      window.addEventListener(GEMINI_RATE_LIMIT_EVENT, handleEvent);
    }

    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener(GEMINI_RATE_LIMIT_EVENT, handleEvent);
      }
    };
  }, []);

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => setIsOpen(false)}
      title="Gemini AI Limit Reached"
      maxWidth="max-w-md"
    >
      <div className="space-y-4">
        {/* Warning Callout */}
        <div className="p-4 rounded-2xl bg-[#faeed6] border border-[#f2d8a5] text-[#8c5208] flex items-start gap-3">
          <div className="w-9 h-9 rounded-xl bg-[#8c5208] text-[#faeed6] flex items-center justify-center shrink-0 mt-0.5">
            <Clock className="w-5 h-5 animate-pulse" />
          </div>
          <div className="text-xs leading-relaxed">
            <div className="flex items-center gap-1.5 font-bold mb-1 text-[#6b3e06]">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Temporary AI Quota Exhausted</span>
            </div>
            <p>
              The Gemini API rate limit has been reached. Please wait a short while and try after some time to explore generative AI capabilities.
            </p>
          </div>
        </div>

        {/* Reassurance list */}
        <div className="p-3.5 rounded-2xl bg-[#f7f8f4] border border-stone-200/90 text-xs text-stone-600 space-y-2">
          <div className="flex items-center gap-2 font-bold text-[#16181a]">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Store Operations Remain Unaffected:</span>
          </div>
          <ul className="space-y-1.5 text-[11px] pl-6 list-disc text-stone-600">
            <li>Rule-based operational parsing & business tools remain active</li>
            <li>Inventory tracking, transactions, and product catalogs are uninterrupted</li>
            <li>Demand forecasting baselines and festival calendars continue working</li>
          </ul>
        </div>

        {/* Action button */}
        <div className="pt-2 flex justify-end">
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="w-full sm:w-auto px-6 py-2.5 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs flex items-center justify-center gap-1.5 shadow-xs transition-all cursor-pointer"
          >
            <Check className="w-3.5 h-3.5 text-[#e0fd53]" />
            <span>Understood</span>
          </button>
        </div>
      </div>
    </Modal>
  );
}
