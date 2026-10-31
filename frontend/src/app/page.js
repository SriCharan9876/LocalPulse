'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import {
  Layers,
  ArrowRight,
  TrendingUp,
  Sparkles,
  Handshake,
  ShieldCheck,
  Store,
} from 'lucide-react';

export default function EntryPage() {
  const { isAuthenticated, loading, demoMerchants, switchDemoMerchant } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [loading, isAuthenticated, router]);

  const handleQuickDemoLaunch = async (merchantId) => {
    try {
      await switchDemoMerchant(merchantId);
      router.push('/dashboard');
    } catch (err) {
      console.error('Demo launch error:', err);
    }
  };

  return (
    <div className="min-h-screen bg-[#eef1f6] text-slate-900 flex flex-col">
      {/* Top Navigation */}
      <header className="max-w-7xl mx-auto w-full px-6 h-20 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/30">
            <Layers className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-bold text-lg text-slate-900 tracking-tight flex items-center gap-1.5">
              LocalPulse <span className="text-indigo-600 font-semibold text-xs px-2 py-0.5 rounded-full bg-indigo-50 border border-indigo-200/80">AI</span>
            </span>
            <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider block">Merchant Growth Platform</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="text-xs font-semibold text-slate-600 hover:text-slate-900 px-4 py-2 rounded-full hover:bg-white/80 transition-all"
          >
            Sign In
          </Link>
          <Link
            href="/login"
            className="px-5 py-2 rounded-full bg-[#0f172a] hover:bg-slate-800 text-white font-semibold text-xs transition-all shadow-xs"
          >
            Launch Prototype
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-10 md:py-16 flex flex-col items-center text-center">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-white border border-slate-200/80 text-slate-700 text-xs font-medium mb-6 shadow-2xs">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Paytm Build for India Hackathon • Merchant Growth Track</span>
        </div>

        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900 max-w-3xl leading-tight">
          Intelligent Demand & Growth Engine for <span className="text-indigo-600">Local Merchants</span>
        </h1>

        <p className="mt-4 text-sm md:text-base text-slate-500 max-w-2xl leading-relaxed">
          Empowering Indian MSMEs with weekday-aware 7-day demand forecasting, stockout runway prevention,
          audited replenishment workflows, and deterministic margin partner bundles.
        </p>

        {/* Feature Highlights Grid */}
        <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-4 w-full text-left">
          <div className="p-6 rounded-3xl bg-white border border-slate-200/80 shadow-[0_2px_12px_rgba(15,23,42,0.03)]">
            <div className="w-9 h-9 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4">
              <TrendingUp className="w-4 h-4" />
            </div>
            <h3 className="font-bold text-slate-900 text-sm tracking-tight">Transparent Demand Modeling</h3>
            <p className="mt-2 text-xs text-slate-500 leading-relaxed">
              7-day product-level demand baseline using historical weekday stratification. Transparent formulas with zero fabricated metrics.
            </p>
          </div>

          <div className="p-6 rounded-3xl bg-white border border-slate-200/80 shadow-[0_2px_12px_rgba(15,23,42,0.03)]">
            <div className="w-9 h-9 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4">
              <Sparkles className="w-4 h-4" />
            </div>
            <h3 className="font-bold text-slate-900 text-sm tracking-tight">AI Business Copilot</h3>
            <p className="mt-2 text-xs text-slate-500 leading-relaxed">
              Ask strategic business questions grounded strictly in live database sales. Drafts write actions requiring explicit merchant confirmation.
            </p>
          </div>

          <div className="p-6 rounded-3xl bg-white border border-slate-200/80 shadow-[0_2px_12px_rgba(15,23,42,0.03)]">
            <div className="w-9 h-9 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4">
              <Handshake className="w-4 h-4" />
            </div>
            <h3 className="font-bold text-slate-900 text-sm tracking-tight">Collaborative Bundles</h3>
            <p className="mt-2 text-xs text-slate-500 leading-relaxed">
              Discover complementary neighborhood merchants. Run deterministic margin validation enforcing minimum profit thresholds.
            </p>
          </div>
        </div>

        {/* Quick Launch Demo Merchants */}
        <div className="mt-8 w-full p-6 md:p-8 rounded-3xl bg-white border border-slate-200/80 text-left shadow-[0_2px_12px_rgba(15,23,42,0.04)]">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-4 border-b border-slate-100">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Store className="w-4 h-4 text-indigo-600" />
                Quick-Start Prototype: Select Demo Merchant
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Instantly launch with pre-seeded 90-day transactions, inventory records, and active collaboration proposals.
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-indigo-700 font-semibold bg-indigo-50 border border-indigo-200/80 px-3 py-1 rounded-full shrink-0">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Full JWT Server Auth</span>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {demoMerchants.slice(0, 6).map((m) => (
              <button
                key={m.merchant_id}
                onClick={() => handleQuickDemoLaunch(m.merchant_id)}
                className="p-4 rounded-2xl bg-slate-50/70 border border-slate-200/80 hover:border-indigo-500 hover:bg-white text-left transition-all group flex flex-col justify-between shadow-2xs"
              >
                <div>
                  <p className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors">
                    {m.business_name}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {m.owner_name} • <span className="text-indigo-600 font-medium">{m.category}</span>
                  </p>
                </div>
                <div className="mt-3 flex items-center justify-between pt-2 border-t border-slate-200/60 text-[11px] text-slate-500 group-hover:text-slate-900 font-medium">
                  <span>Enter Workspace</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform text-indigo-600" />
                </div>
              </button>
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="h-16 border-t border-slate-200/80 text-center text-xs text-slate-400 flex items-center justify-center">
        LocalPulse AI Platform • Built for Paytm Build for India AI Hackathon • MSME Observability Design
      </footer>
    </div>
  );
}
