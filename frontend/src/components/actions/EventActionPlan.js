'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import Modal from '@/components/ui/Modal';
import ActionDraftCard from '@/components/actions/ActionDraftCard';
import { Loader2, Lightbulb, Info, ArrowRight, BarChart3 } from 'lucide-react';

/*
 * Popup with concrete actions for one occasion (restock drafts, a small festival offer,
 * partner bundle ideas). Each draft is applied only when the merchant confirms it.
 */
export default function EventActionPlan({ event, onClose }) {
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!event) return;
    setPlan(null);
    setError('');
    api
      .post('/neighborhood/events/action-plan', {
        event_id: event.event_id,
        title: event.title,
        start_date: event.start_date,
        end_date: event.end_date,
        severity: event.severity,
        category_impacts: event.category_impacts || [],
      })
      .then((res) => setPlan(res.data))
      .catch((err) => setError(err.response?.data?.detail || 'Could not build an action plan for this occasion.'));
  }, [event]);

  const shortTitle = (event?.title || '').split(/[/(]/)[0].trim();

  return (
    <Modal isOpen={Boolean(event)} onClose={onClose} title={`Action plan: ${shortTitle}`} maxWidth="max-w-xl">
      <div className="space-y-3 max-h-[70vh] overflow-y-auto pr-1">
        {!plan && !error && (
          <div className="py-8 flex items-center justify-center gap-2 text-xs text-stone-500">
            <Loader2 className="w-4 h-4 animate-spin" /> Checking your stock and forecast…
          </div>
        )}
        {error && <p className="text-xs text-[#a43b27]">{error}</p>}

        {plan && (
          <>
            <p className="text-[13px] font-semibold text-[#16181a] leading-snug">{plan.headline}</p>

            {plan.notes?.map((n, i) => (
              <div key={i} className="flex items-start gap-1.5 text-[11px] text-stone-600">
                <Info className="w-3.5 h-3.5 shrink-0 mt-0.5 text-stone-400" />
                <span>{n}</span>
              </div>
            ))}

            {/* Findings: how a past occasion went, or expected demand for the next one */}
            {plan.insights?.map((block, i) => (
              <div key={i} className="p-3 rounded-2xl bg-[#f7f8f4] border border-stone-200/80">
                <p className="text-[11px] font-bold text-[#16181a] flex items-center gap-1.5 mb-1.5">
                  <BarChart3 className="w-3.5 h-3.5" />
                  {block.title}
                </p>
                <ul className="space-y-1">
                  {block.lines.map((line, j) => (
                    <li key={j} className="text-[11px] text-stone-700 leading-snug flex gap-1.5">
                      <span className="shrink-0">•</span>
                      <span>{line}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}

            {plan.drafts?.length > 0 && (
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400">
                  Suggested actions · nothing is applied until you confirm
                </p>
                {plan.drafts.map((d, i) => (
                  <ActionDraftCard key={i} draft={d} source={`${shortTitle} plan`} />
                ))}
              </div>
            )}

            {plan.ideas?.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400">Partner ideas</p>
                {plan.ideas.map((idea, i) => (
                  <Link
                    key={i}
                    href={idea.href}
                    className="p-2.5 rounded-xl bg-[#f7f8f4] border border-stone-200/80 text-[11px] text-stone-700 flex items-start gap-2 hover:bg-[#e0fd53]/25"
                  >
                    <Lightbulb className="w-3.5 h-3.5 shrink-0 mt-0.5 text-[#16181a]" />
                    <span className="flex-1">{idea.text}</span>
                    <ArrowRight className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  </Link>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}
