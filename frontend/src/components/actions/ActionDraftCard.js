'use client';

import { useState } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { Package, Tag, CheckCircle2, AlertTriangle, Loader2, PencilLine } from 'lucide-react';

/*
 * One confirmable action (same draft format the copilot uses).
 * - "Confirm & Apply" sends it to /copilot/confirm-action, which re-checks every safety rule.
 * - "Edit first" opens the full popup on the Demand / Campaigns page, pre-filled.
 * Nothing happens until the merchant clicks one of them.
 */

function editHref(draft, source) {
  const p = draft.payload || {};
  if (draft.action_type === 'RESTOCK_INVENTORY') {
    const q = new URLSearchParams({
      rec: 'restock',
      product_id: p.product_id || '',
      qty: String(p.quantity || 10),
      reason: source,
    });
    return `/demand?${q.toString()}`;
  }
  if (draft.action_type === 'CREATE_CAMPAIGN') {
    const q = new URLSearchParams({
      rec: 'campaign',
      product_id: (p.target_product_ids || [])[0] || '',
      discount: String(p.discount_pct || 5),
      title: p.title || '',
      start: p.start_date || '',
      end: p.end_date || '',
      campaign_type: p.campaign_type || 'Festival Discount',
      source,
      reason: draft.title,
    });
    return `/campaigns?${q.toString()}`;
  }
  return null;
}

export default function ActionDraftCard({ draft, source = 'Action plan', onApplied }) {
  const [state, setState] = useState('idle'); // idle | applying | done | error
  const [message, setMessage] = useState('');
  const isRestock = draft.action_type === 'RESTOCK_INVENTORY';
  const Icon = isRestock ? Package : Tag;
  const href = editHref(draft, source);

  const apply = async () => {
    setState('applying');
    try {
      const res = await api.post('/copilot/confirm-action', {
        action_type: draft.action_type,
        payload: draft.payload,
      });
      setMessage(res.data.message);
      setState(res.data.success ? 'done' : 'error');
      if (res.data.success && onApplied) onApplied(draft);
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Could not apply this action. Please try again.');
      setState('error');
    }
  };

  return (
    <div className="p-3.5 rounded-2xl border border-stone-200/90 bg-white">
      <div className="flex items-start gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-[#f7f8f4] border border-stone-200 flex items-center justify-center shrink-0 text-[#16181a]">
          <Icon className="w-3.5 h-3.5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-bold uppercase tracking-wider text-stone-400">
            {isRestock ? 'Restock' : 'Festival offer'}
          </p>
          <p className="text-xs font-bold text-[#16181a] leading-snug">{draft.title}</p>
          <p className="text-[11px] text-stone-600 mt-1 leading-relaxed">{draft.description}</p>
        </div>
      </div>

      {state === 'done' ? (
        <div className="mt-2.5 p-2 rounded-xl bg-emerald-50 border border-emerald-200 text-[11px] text-emerald-900 flex items-start gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>{message}</span>
        </div>
      ) : (
        <>
          {state === 'error' && (
            <div className="mt-2.5 p-2 rounded-xl bg-[#fbe8e4] border border-[#f3c5bd] text-[11px] text-[#a43b27] flex items-start gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>{message}</span>
            </div>
          )}
          <div className="mt-2.5 flex items-center justify-end gap-2">
            {href && (
              <Link
                href={href}
                className="px-3 py-1.5 rounded-full border border-stone-200 text-[11px] font-semibold text-stone-700 hover:bg-stone-50 inline-flex items-center gap-1"
              >
                <PencilLine className="w-3 h-3" />
                Edit first
              </Link>
            )}
            <button
              type="button"
              onClick={apply}
              disabled={state === 'applying'}
              className="px-3.5 py-1.5 rounded-full bg-[#16181a] hover:bg-stone-800 disabled:opacity-60 text-white text-[11px] font-bold inline-flex items-center gap-1.5 cursor-pointer"
            >
              {state === 'applying' && <Loader2 className="w-3 h-3 animate-spin" />}
              Confirm &amp; Apply
            </button>
          </div>
        </>
      )}
    </div>
  );
}
