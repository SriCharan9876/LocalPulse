'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import {
  ArrowRight,
  TrendingUp,
  Sparkles,
  Handshake,
  ShieldCheck,
  Store,
  MapPin,
  Mic,
  Calendar,
  IndianRupee,
  Activity,
  ChevronRight,
  Cpu,
  BarChart3,
  Package,
  Layers,
  Compass,
  CheckCircle2,
  Volume2,
  Bot,
  RotateCcw,
  Percent,
} from 'lucide-react';
import { LogoMark } from '@/components/ui/Logo';

export default function EntryPage() {
  const { isAuthenticated, demoMerchants, switchDemoMerchant, user } = useAuth();
  const router = useRouter();
  const [activeCategoryTab, setActiveCategoryTab] = useState(0);

  const handleQuickDemoLaunch = async (merchantId) => {
    try {
      await switchDemoMerchant(merchantId);
      router.push('/dashboard');
    } catch (err) {
      console.error('Demo launch error:', err);
    }
  };

  const copilotShowcase = [
    {
      category: 'Map & Stores',
      icon: MapPin,
      badge: 'Spatial Radar',
      query: 'Who are the closest stores near me within 1 km?',
      response: 'Found 3 nearby stores: Chai Point (420m away), Modern Threads (200m away), and Sanjeevani Wellness (400m away). You have high complementary synergy with Chai Point for bakery combos.',
    },
    {
      category: 'Collaborations',
      icon: Handshake,
      badge: '6-Factor Synergy',
      query: 'Propose a joint combo bundle with Krishna Bakery',
      response: 'Drafted "Morning Tea & Rusk Combo" with 10% discount on both sides. Both shops maintain verified 14% margins (safely above the 12% floor). Ready for mutual sign-off.',
    },
    {
      category: 'Forecasting',
      icon: TrendingUp,
      badge: 'Weekday AI',
      query: 'Show 7-day demand forecast and stockout risks',
      response: 'Amul Taaza Milk has 9 cartons remaining with 1.3 days of runway. Predicted weekend surge requires 50 cartons replenishment before Friday evening.',
    },
    {
      category: 'Restock & Loss',
      icon: Package,
      badge: 'Audit Ledger',
      query: 'Record 5 units of Bread damaged as loss',
      response: 'Prepared AUDIT_CORRECTION draft to deduct 5 units of Whole Wheat Bread with audit logging. Stock will update from 28 to 23 upon confirmation.',
    },
    {
      category: 'Sales Analytics',
      icon: BarChart3,
      badge: 'Telemetry',
      query: 'What are my top selling products this week?',
      response: 'Top performers: 1. Amul Taaza Milk (₹13,440 · 182 units), 2. Tata Tea Gold (₹9,800 · 35 units), 3. Aashirvaad Atta (₹8,750 · 25 units). Gross revenue up +14.2% vs previous period.',
    },
    {
      category: 'Campaigns & Catalog',
      icon: Percent,
      badge: 'Growth Engine',
      query: 'Recommend clearance discounts for excess stock',
      response: 'Identified Fortune Sunflower Oil (45 units, 38 days cover). Recommended 10% weekend promotional discount to lift turnover while locking in a 14.8% profit margin.',
    },
  ];

  return (
    <div className="min-h-screen bg-[#edece4] text-[#16181a] flex flex-col font-sans selection:bg-[#e0fd53] selection:text-[#16181a]">
      {/* Top Floating Navigation */}
      <header className="max-w-7xl mx-auto w-full px-6 py-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <LogoMark size={40} className="shadow-md shadow-stone-900/10" />
          <div>
            <span className="font-extrabold text-lg text-[#16181a] tracking-tight flex items-center gap-2">
              LocalPulse
              <span className="text-[#16181a] font-bold text-[10px] uppercase px-2 py-0.5 rounded-full bg-[#e0fd53] border border-[#16181a]/20">
                AI Platform
              </span>
            </span>
            <span className="text-[10px] text-stone-500 font-bold uppercase tracking-wider block">
              MSME Demand &amp; Merchant Growth Engine
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <Link
              href="/dashboard"
              className="px-5 py-2.5 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs transition-all shadow-sm flex items-center gap-1.5 group"
            >
              <span>Go to Dashboard</span>
              <ArrowRight className="w-3.5 h-3.5 text-[#e0fd53] group-hover:translate-x-0.5 transition-transform" />
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="text-xs font-bold text-stone-600 hover:text-[#16181a] px-4 py-2 rounded-full hover:bg-stone-200/50 transition-all"
              >
                Sign In
              </Link>
              <Link
                href="/signup"
                className="px-5 py-2.5 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs transition-all shadow-sm flex items-center gap-1.5 group"
              >
                <span>Register Merchant</span>
                <ArrowRight className="w-3.5 h-3.5 text-[#e0fd53] group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8 md:py-12 flex flex-col items-center text-center">
        {/* Hackathon Pill */}
        <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-white border border-stone-200/90 text-[#16181a] text-xs font-semibold mb-6 shadow-2xs">
          <span className="w-2 h-2 rounded-full bg-[#e0fd53] ring-4 ring-[#e0fd53]/30" />
          <span className="text-[11px] uppercase tracking-wider text-stone-500">Paytm Build for India AI Hackathon</span>
          <span className="w-1 h-1 rounded-full bg-stone-300" />
          <span className="text-xs font-bold text-[#16181a]">Autonomous MSME Retail Suite</span>
        </div>

        <h1 className="text-4xl md:text-6xl font-black tracking-tight text-[#16181a] max-w-4xl leading-[1.12]">
          Hyperlocal Demand Intelligence &amp; Autonomous Growth for{' '}
          <span className="relative inline-block px-2">
            <span className="relative z-10 text-[#16181a] underline decoration-[#e0fd53] decoration-8 underline-offset-4">
              Local Merchants
            </span>
          </span>
        </h1>

        <p className="mt-5 text-sm md:text-base text-stone-600 max-w-3xl leading-relaxed font-medium">
          Zero-guesswork retail operations for Indian neighborhood stores: weekday-stratified demand modeling, 18-tool Indic voice copilot (Sarvam AI + Gemini 3.8 Flash), deterministic 12% margin protection, and real-time proximity map collaboration.
        </p>

        {/* Core Pillars Grid */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 w-full text-left">
          {/* Card 1: Demand Modeling */}
          <div className="p-6 rounded-[28px] bg-white border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)] flex flex-col justify-between hover:border-[#16181a] transition-all">
            <div>
              <div className="w-10 h-10 rounded-2xl bg-[#edece4] text-[#16181a] flex items-center justify-center mb-4 font-bold">
                <TrendingUp className="w-5 h-5 text-[#16181a]" />
              </div>
              <span className="text-[10px] uppercase tracking-widest font-extrabold text-stone-400">Pillar 01</span>
              <h3 className="font-extrabold text-[#16181a] text-base tracking-tight mt-1">
                Weekday Demand Modeling
              </h3>
              <p className="mt-2 text-xs text-stone-500 leading-relaxed font-medium">
                7-day rolling forecast stratified by day-of-week sales patterns. Predicts stockout runway dates and sizes replenishment batches without fabricated metrics.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-stone-100 flex items-center justify-between text-[11px] font-bold text-[#16181a]">
              <span>Runway &amp; Restock Alerts</span>
              <Activity className="w-3.5 h-3.5 text-stone-400" />
            </div>
          </div>

          {/* Card 2: 18-Tool Voice Copilot */}
          <div className="p-6 rounded-[28px] bg-white border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)] flex flex-col justify-between hover:border-[#16181a] transition-all">
            <div>
              <div className="w-10 h-10 rounded-2xl bg-[#16181a] text-[#e0fd53] flex items-center justify-center mb-4">
                <Bot className="w-5 h-5" />
              </div>
              <span className="text-[10px] uppercase tracking-widest font-extrabold text-stone-400">Pillar 02</span>
              <h3 className="font-extrabold text-[#16181a] text-base tracking-tight mt-1">
                18-Tool Indic Voice Copilot
              </h3>
              <p className="mt-2 text-xs text-stone-500 leading-relaxed font-medium">
                Sarvam AI speech recognition across Hindi, Tamil, Telugu, and English paired with 18 autonomous function-calling tools and audited two-tier confirmation drafts.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-stone-100 flex items-center justify-between text-[11px] font-bold text-[#16181a]">
              <span>10+ Indic Languages</span>
              <Sparkles className="w-3.5 h-3.5 text-[#16181a]" />
            </div>
          </div>

          {/* Card 3: Proximity Map & Events */}
          <div className="p-6 rounded-[28px] bg-white border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)] flex flex-col justify-between hover:border-[#16181a] transition-all">
            <div>
              <div className="w-10 h-10 rounded-2xl bg-[#edece4] text-[#16181a] flex items-center justify-center mb-4 font-bold">
                <MapPin className="w-5 h-5 text-[#16181a]" />
              </div>
              <span className="text-[10px] uppercase tracking-widest font-extrabold text-stone-400">Pillar 03</span>
              <h3 className="font-extrabold text-[#16181a] text-base tracking-tight mt-1">
                Spatial Radar &amp; Events
              </h3>
              <p className="mt-2 text-xs text-stone-500 leading-relaxed font-medium">
                Haversine distance clustering on OpenStreetMap for neighborhood peers. Live All-India Google Calendar feed with event multipliers and instant bundle proposing.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-stone-100 flex items-center justify-between text-[11px] font-bold text-[#16181a]">
              <span>Retail Footfall Radar</span>
              <Calendar className="w-3.5 h-3.5 text-stone-400" />
            </div>
          </div>

          {/* Card 4: 6-Factor Collaborations */}
          <div className="p-6 rounded-[28px] bg-white border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)] flex flex-col justify-between hover:border-[#16181a] transition-all">
            <div>
              <div className="w-10 h-10 rounded-2xl bg-[#edece4] text-[#16181a] flex items-center justify-center mb-4 font-bold">
                <Handshake className="w-5 h-5 text-[#16181a]" />
              </div>
              <span className="text-[10px] uppercase tracking-widest font-extrabold text-stone-400">Pillar 04</span>
              <h3 className="font-extrabold text-[#16181a] text-base tracking-tight mt-1">
                6-Factor Synergy Bundles
              </h3>
              <p className="mt-2 text-xs text-stone-500 leading-relaxed font-medium">
                Mathematical synergy scoring combining customer link, stock surplus, partner pull, price balance, festival surge, and distance with a strict 12% margin invariant.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-stone-100 flex items-center justify-between text-[11px] font-bold text-[#16181a]">
              <span>12% Profit Invariant</span>
              <IndianRupee className="w-3.5 h-3.5 text-stone-400" />
            </div>
          </div>
        </div>

        {/* Interactive Capability Showcase: Copilot & Autonomous Tools */}
        <div className="mt-12 w-full p-6 md:p-8 rounded-[32px] bg-white border border-stone-200/90 text-left shadow-[0_4px_30px_rgba(20,24,20,0.05)]">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-6 border-b border-stone-100">
            <div>
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-[#16181a] text-[#e0fd53] flex items-center justify-center">
                  <Mic className="w-4 h-4" />
                </div>
                <h2 className="text-lg font-black text-[#16181a] tracking-tight">
                  Autonomous Copilot: 6 Operational Query Categories
                </h2>
              </div>
              <p className="text-xs text-stone-500 mt-1 font-medium">
                Backed by 18 function-calling tools, natural language date-range resolution, and seamless fallback to deterministic offline rules.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs text-[#16181a] font-bold bg-[#edece4] border border-stone-300/80 px-3.5 py-1.5 rounded-full shrink-0">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Two-Tier Confirmation Guardrails</span>
            </div>
          </div>

          {/* Category Tabs */}
          <div className="mt-6 flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
            {copilotShowcase.map((item, idx) => {
              const Icon = item.icon;
              const isActive = activeCategoryTab === idx;
              return (
                <button
                  key={idx}
                  onClick={() => setActiveCategoryTab(idx)}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer whitespace-nowrap shrink-0 ${
                    isActive
                      ? 'bg-[#16181a] text-[#e0fd53] shadow-xs'
                      : 'bg-stone-50 text-stone-600 hover:bg-stone-100 border border-stone-200/80'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5 shrink-0" />
                  <span>{item.category}</span>
                </button>
              );
            })}
          </div>

          {/* Active Category Preview Card */}
          <div className="mt-4 p-5 rounded-2xl bg-[#f7f8f4] border border-stone-200/80 flex flex-col md:flex-row gap-5 items-start justify-between">
            <div className="space-y-3 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black uppercase tracking-wider text-[#16181a] bg-[#e0fd53] px-2.5 py-0.5 rounded-full">
                  {copilotShowcase[activeCategoryTab].badge}
                </span>
                <span className="text-xs text-stone-400 font-mono">Sample Operational Voice/Text Query</span>
              </div>
              <p className="text-sm font-extrabold text-[#16181a]">
                "{copilotShowcase[activeCategoryTab].query}"
              </p>
              <div className="p-3.5 rounded-xl bg-white border border-stone-200/90 text-xs text-stone-600 font-medium leading-relaxed flex items-start gap-2.5">
                <Bot className="w-4 h-4 text-[#16181a] shrink-0 mt-0.5" />
                <p>{copilotShowcase[activeCategoryTab].response}</p>
              </div>
            </div>
            <div className="w-full md:w-56 shrink-0 flex flex-col justify-between p-4 rounded-xl bg-white border border-stone-200/90 text-xs space-y-2">
              <span className="text-[10px] uppercase font-bold text-stone-400 tracking-wider">Tool Capabilities</span>
              <div className="space-y-1.5 text-[11px] text-stone-600 font-medium">
                <div className="flex items-center gap-1.5 text-stone-800 font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <span>Zero fabricated metrics</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <span>10+ Indic voice languages</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <span>Audited inventory ledger</span>
                </div>
              </div>
              <Link
                href="/copilot"
                className="mt-2 text-[11px] font-bold text-[#16181a] hover:underline flex items-center gap-1 pt-2 border-t border-stone-100"
              >
                <span>Try in Copilot Console</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        </div>

        {/* 1-Click Prototype Launcher: Select a Demo Merchant */}
        <div className="mt-10 w-full p-6 md:p-8 rounded-[32px] bg-white border border-stone-200/90 text-left shadow-[0_4px_30px_rgba(20,24,20,0.05)]">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-6 border-b border-stone-100">
            <div>
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-[#16181a] text-[#e0fd53] flex items-center justify-center">
                  <Store className="w-4 h-4" />
                </div>
                <h2 className="text-lg font-black text-[#16181a] tracking-tight">
                  1-Click Prototype Launcher: Select a Demo Merchant
                </h2>
              </div>
              <p className="text-xs text-stone-500 mt-1 font-medium">
                Instantly jump into a production-grade merchant workspace with 90 days of transactions, inventory catalogs, dynamic pricing, and active collaboration proposals.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs text-[#16181a] font-bold bg-[#edece4] border border-stone-300/80 px-3.5 py-1.5 rounded-full shrink-0">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Full JWT &amp; Role-Gated Sessions</span>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {demoMerchants.slice(0, 6).map((m) => (
              <button
                key={m.merchant_id}
                onClick={() => handleQuickDemoLaunch(m.merchant_id)}
                className="p-4 rounded-2xl bg-[#f7f8f4] border border-stone-200/80 hover:border-[#16181a] hover:bg-white text-left transition-all group flex flex-col justify-between shadow-2xs cursor-pointer"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="text-[10px] font-black uppercase tracking-wider text-[#16181a] bg-[#e0fd53] px-2.5 py-0.5 rounded-full">
                      {m.category?.split('&')[0]?.trim() || 'Store'}
                    </span>
                    <span className="text-[10px] text-stone-400 font-mono">
                      {m.merchant_id}
                    </span>
                  </div>
                  <p className="text-sm font-extrabold text-[#16181a] group-hover:text-black transition-colors line-clamp-1">
                    {m.business_name}
                  </p>
                  <p className="text-xs text-stone-500 mt-0.5 font-medium">
                    Owner: <span className="text-stone-700">{m.owner_name}</span>
                  </p>
                  <p className="text-[11px] text-stone-400 mt-1 line-clamp-1 flex items-center gap-1">
                    <MapPin className="w-3 h-3 shrink-0 text-stone-400" />
                    <span>{m.address || 'Bengaluru Retail Cluster'}</span>
                  </p>
                </div>

                <div className="mt-4 pt-2.5 border-t border-stone-200/70 flex items-center justify-between text-xs text-stone-700 group-hover:text-[#16181a] font-bold">
                  <span>Open Merchant Dashboard</span>
                  <div className="w-6 h-6 rounded-full bg-stone-200/70 group-hover:bg-[#16181a] group-hover:text-[#e0fd53] flex items-center justify-center transition-colors">
                    <ChevronRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </button>
            ))}
          </div>

          <div className="mt-6 pt-5 border-t border-stone-100 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-stone-500">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-stone-400" />
              <span>All 6 demo accounts pre-configured with GPS coordinates, inventory levels, and live AI context.</span>
            </div>
            <Link
              href="/signup"
              className="text-xs font-bold text-[#16181a] hover:underline flex items-center gap-1"
            >
              <span>Or register a custom merchant store</span>
              <ArrowRight className="w-3.5 h-3.5 text-[#16181a]" />
            </Link>
          </div>
        </div>

        {/* Architectural Highlights / Trust Grid */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4 w-full text-left">
          <div className="p-5 rounded-2xl bg-white border border-stone-200/90 text-xs space-y-2">
            <div className="flex items-center gap-2 font-bold text-[#16181a]">
              <Compass className="w-4 h-4 text-stone-600" />
              <span>Store Profile &amp; Leaflet GPS</span>
            </div>
            <p className="text-stone-500 font-medium leading-relaxed">
              Every merchant can manage precise storefront coordinates using the interactive map or browser geolocation, automatically updating neighborhood radar distances.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white border border-stone-200/90 text-xs space-y-2">
            <div className="flex items-center gap-2 font-bold text-[#16181a]">
              <RotateCcw className="w-4 h-4 text-stone-600" />
              <span>Dual-Engine Offline Fallback</span>
            </div>
            <p className="text-stone-500 font-medium leading-relaxed">
              If external LLM rate limits (429) or internet drops occur, the platform automatically falls back to deterministic rule algorithms with zero system downtime.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white border border-stone-200/90 text-xs space-y-2">
            <div className="flex items-center gap-2 font-bold text-[#16181a]">
              <IndianRupee className="w-4 h-4 text-stone-600" />
              <span>Audited 3-Tier Catalog Pricing</span>
            </div>
            <p className="text-stone-500 font-medium leading-relaxed">
              Cost price, baseline retail price, and promotional effective selling price are tracked independently so profit margins remain mathematically protected at all times.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-stone-200/80 bg-white/50 backdrop-blur-xs py-6 text-center text-xs text-stone-500 flex flex-col sm:flex-row items-center justify-between px-6 max-w-7xl mx-auto w-full">
        <div className="flex items-center gap-2 font-bold text-[#16181a]">
          <LogoMark size={18} />
          <span>LocalPulse AI</span>
          <span className="text-stone-400 font-normal">• MSME Observability Design</span>
        </div>
        <div className="mt-2 sm:mt-0 text-[11px] text-stone-400 font-medium">
          Built for Paytm Build for India AI Hackathon • Bengaluru Retail Cluster Coordinates (12.920737, 77.668710)
        </div>
      </footer>
    </div>
  );
}