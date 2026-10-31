'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import AppLayout from '@/components/layout/AppLayout';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';
import api from '@/lib/api';
import {
  IndianRupee,
  ShoppingBag,
  AlertTriangle,
  Sparkles,
  TrendingUp,
  ArrowUpRight,
  Package,
  Calendar,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Tag,
  Percent,
  Store,
  BarChart3,
  SlidersHorizontal,
  ChevronRight,
  MoreVertical,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('Overview');

  // Quick Restock Modal state
  const [selectedStockItem, setSelectedStockItem] = useState(null);
  const [restockQty, setRestockQty] = useState(20);
  const [restocking, setRestocking] = useState(false);
  const [actionSuccess, setActionSuccess] = useState('');

  const fetchDashboardData = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/dashboard/summary');
      setData(res.data);
    } catch (err) {
      console.error('Error fetching dashboard summary:', err);
      setError('Failed to fetch dashboard metrics. Please ensure backend is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleRestockSubmit = async (e) => {
    e.preventDefault();
    if (!selectedStockItem) return;
    setRestocking(true);
    setActionSuccess('');
    try {
      await api.post(`/products/${selectedStockItem.product_id}/adjust-inventory`, {
        adjustment_type: 'RESTOCK',
        quantity: parseInt(restockQty, 10),
        notes: 'Replenished from Dashboard stock warning queue',
      });
      setActionSuccess(`Successfully replenished ${restockQty} units of ${selectedStockItem.product_name}!`);
      setTimeout(() => {
        setSelectedStockItem(null);
        setActionSuccess('');
        fetchDashboardData();
      }, 1200);
    } catch (err) {
      console.error(err);
      alert('Failed to restock inventory.');
    } finally {
      setRestocking(false);
    }
  };

  if (loading) {
    return (
      <AppLayout title="Merchant Intelligence" subtitle="Live store performance, inventory runway, and demand pulse">
        <div className="h-96 flex flex-col items-center justify-center gap-3">
          <Loader2 className="w-7 h-7 text-[#16181a] animate-spin" />
          <p className="text-xs font-semibold text-stone-600">Aggregating live store metrics and forecasting signals...</p>
        </div>
      </AppLayout>
    );
  }

  if (error || !data) {
    return (
      <AppLayout title="Merchant Intelligence" subtitle="Live store performance, inventory runway, and demand pulse">
        <div className="p-8 rounded-3xl bg-white border border-[#f3c5bd] text-center shadow-xs">
          <AlertTriangle className="w-9 h-9 text-[#c25e4e] mx-auto mb-2" />
          <h3 className="text-sm font-bold text-[#16181a]">Service Unavailable</h3>
          <p className="text-xs text-stone-500 mt-1 max-w-md mx-auto">{error}</p>
          <button
            onClick={fetchDashboardData}
            className="mt-4 px-5 py-2 rounded-full bg-[#16181a] text-white text-xs font-semibold hover:bg-stone-800 inline-flex items-center gap-2 shadow-xs transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Connection</span>
          </button>
        </div>
      </AppLayout>
    );
  }

  const {
    total_revenue_30d = 0,
    revenue_growth_pct = 0,
    total_orders_30d = 0,
    avg_order_value = 0,
    low_stock_items_count = 0,
    growth_health_score = 0,
    sales_history_30d = [],
    seven_day_forecast_summary = [],
    stock_warnings = [],
    top_recommendations = [],
  } = data;

  // Calculate capsule segments (8 capsules total, inspired by Dribbble screenshot)
  const operationsRatio = Math.min(100, Math.max(10, Math.round(growth_health_score || 82)));
  const operationsFilledCapsules = Math.max(1, Math.min(8, Math.round((operationsRatio / 100) * 8)));

  const revenueTargetRatio = Math.min(100, Math.max(15, Math.round((total_orders_30d / 500) * 100)));
  const revenueFilledCapsules = Math.max(1, Math.min(8, Math.round((revenueTargetRatio / 100) * 8)));

  return (
    <AppLayout
      title={`Managing ${data.business_name}`}
      subtitle={`Hyper-local demand telemetry, inventory health, and margins for ${data.category}`}
    >
      {/* Top Dribbble-Style Title & Category Chip Navigation */}
      <div className="space-y-3 pt-1">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-2xl md:text-3xl font-black text-[#16181a] tracking-tight">
              Managing
            </span>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-stone-200/90 text-xs font-bold text-stone-800 shadow-2xs">
              <Store className="w-3.5 h-3.5 text-[#16181a]" />
              <span>{data.business_name}</span>
            </div>
            <span className="text-2xl md:text-3xl font-black text-[#16181a] tracking-tight">
              and
            </span>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#e0fd53] border border-[#d5f347] text-xs font-black text-[#16181a] shadow-2xs">
              <Sparkles className="w-3.5 h-3.5 text-[#16181a]" />
              <span>Workflows</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchDashboardData}
              className="w-9 h-9 rounded-full bg-white border border-stone-200/90 flex items-center justify-center text-stone-700 hover:bg-stone-50 shadow-2xs transition-all"
              title="Refresh live metrics"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
            <Link
              href="/copilot"
              className="px-4 py-2 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs shadow-xs inline-flex items-center gap-2 transition-all"
            >
              <Sparkles className="w-3.5 h-3.5 text-[#e0fd53]" />
              <span>Launch Copilot</span>
            </Link>
          </div>
        </div>

        {/* Horizontal Category Pill Tabs (Directly from Dribbble layout) */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
          {['Overview', 'Operations', 'Demand Pulse', 'Replenishment', 'Promotions'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                activeTab === tab
                  ? 'bg-[#16181a] text-white shadow-xs font-bold'
                  : 'bg-white hover:bg-stone-50 text-stone-700 border border-stone-200/90 shadow-2xs'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* 3 HERO METRIC CARDS (Direct Dribbble Shot Reproduction) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
        {/* Card 1: Operations / Health Card (Clean White) */}
        <div className="p-6 rounded-[28px] bg-white border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full border border-stone-200/90 bg-stone-50 flex items-center justify-center text-[#16181a]">
                  <SlidersHorizontal className="w-4 h-4" />
                </div>
                <span className="text-xs font-bold text-[#16181a] tracking-tight">
                  Operations & Health
                </span>
              </div>
              <button
                onClick={fetchDashboardData}
                className="text-stone-400 hover:text-stone-700 p-1"
                title="Options"
              >
                <MoreVertical className="w-4 h-4" />
              </button>
            </div>

            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-3xl md:text-4xl font-black text-[#16181a] tracking-tight">
                {growth_health_score}
              </span>
              <span className="text-xs font-bold text-stone-400">
                / 100 Score
              </span>
              <span className="ml-auto text-[11px] font-bold px-2 py-0.5 rounded-full bg-[#f6f6f0] border border-stone-200/90 text-stone-700 inline-flex items-center gap-1">
                <span>{growth_health_score}%</span>
                <span className="w-1.5 h-1.5 rounded-full bg-[#16181a]" />
              </span>
            </div>
            <p className="text-[11px] text-stone-500 font-medium">
              {low_stock_items_count > 0
                ? `${low_stock_items_count} inventory lines require replenishment`
                : 'All catalog lines within safe runway buffer'}
            </p>
          </div>

          {/* Dribbble Segmented Capsule Indicator Bar */}
          <div className="mt-5 pt-4 border-t border-stone-100">
            <div className="flex items-center gap-1.5">
              {[...Array(8)].map((_, i) => {
                const isFilled = i < operationsFilledCapsules;
                return (
                  <div
                    key={i}
                    className={`flex-1 h-7 rounded-full transition-all duration-300 ${
                      isFilled
                        ? 'bg-[#16181a]'
                        : 'border border-dashed border-stone-300 bg-transparent'
                    }`}
                  />
                );
              })}
            </div>
          </div>
        </div>

        {/* Card 2: Electric Chartreuse / Neon Lime Hero Card */}
        <div className="p-6 rounded-[28px] bg-[#e0fd53] text-[#16181a] border border-[#d6f447] shadow-[0_4px_24px_rgba(224,253,83,0.22)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full border border-[#16181a]/15 bg-white/40 flex items-center justify-center text-[#16181a]">
                  <TrendingUp className="w-4 h-4 stroke-[2.5]" />
                </div>
                <span className="text-xs font-bold text-[#16181a] tracking-tight">
                  Demand Pulse & Revenue
                </span>
              </div>
              <div className="text-[11px] font-black px-2 py-0.5 rounded-full bg-white/70 text-[#16181a] border border-black/10">
                {revenue_growth_pct >= 0 ? `+${revenue_growth_pct}%` : `${revenue_growth_pct}%`}
              </div>
            </div>

            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-3xl md:text-4xl font-black text-[#16181a] tracking-tight">
                ₹{total_revenue_30d.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </span>
            </div>
            <p className="text-[11px] text-[#16181a]/80 font-medium">
              30-day gross receipts • {total_orders_30d.toLocaleString('en-IN')} units delivered
            </p>
          </div>

          {/* Dribbble Segmented Capsule Indicator Bar on Lime Background */}
          <div className="mt-5 pt-4 border-t border-[#16181a]/15">
            <div className="flex items-center gap-1.5">
              {[...Array(8)].map((_, i) => {
                const isFilled = i < revenueFilledCapsules;
                return (
                  <div
                    key={i}
                    className={`flex-1 h-7 rounded-full transition-all duration-300 ${
                      isFilled
                        ? 'bg-[#16181a]'
                        : 'border border-dashed border-[#16181a]/40 bg-transparent'
                    }`}
                  />
                );
              })}
            </div>
          </div>
        </div>

        {/* Card 3: Deep Onyx Promo & Copilot Card */}
        <div className="p-6 rounded-[28px] bg-[#16181a] text-white border border-stone-800 shadow-[0_4px_24px_rgba(0,0,0,0.18)] flex flex-col justify-between relative overflow-hidden">
          <div className="relative z-10">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] uppercase font-bold tracking-wider text-[#e0fd53] bg-white/10 px-2 py-0.5 rounded-full border border-white/10">
                Autonomous AI Agent
              </span>
              <Sparkles className="w-4 h-4 text-[#e0fd53]" />
            </div>

            <h3 className="text-lg md:text-xl font-bold text-white tracking-tight leading-snug">
              Take Your Store Automation to the Next Level
            </h3>
            <p className="text-xs text-stone-300 mt-2 leading-relaxed">
              Use voice or text to audit catalog margins, draft promotional campaigns, and trigger restocks.
            </p>
          </div>

          <div className="mt-5 pt-3 border-t border-white/10 relative z-10 flex items-center justify-between">
            <Link
              href="/copilot"
              className="w-full py-2.5 px-4 rounded-full bg-white hover:bg-stone-100 text-[#16181a] font-bold text-xs text-center inline-flex items-center justify-center gap-2 transition-all shadow-xs"
            >
              <span>Open AI Copilot</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* Main Statistics Card (Dual Visual Language: 30D Sales & 7D Demand) */}
      <div className="p-6 rounded-[28px] bg-white border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full border border-stone-200/90 bg-stone-50 flex items-center justify-center text-[#16181a]">
              <BarChart3 className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#16181a] tracking-tight">
                Statistics & Forecasting Telemetry
              </h2>
              <p className="text-[11px] text-stone-400 font-medium">
                Daily recorded sales against 7-day predicted unit requirements
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-3 text-xs font-semibold text-stone-600">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#16181a]" />
                <span>Historical Sales</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#e0fd53] border border-stone-400" />
                <span>Projected Demand</span>
              </span>
            </div>

            <span className="text-xs font-bold text-[#16181a] bg-[#f6f6f0] px-3 py-1 rounded-full border border-stone-200/90">
              Active Horizon
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 30-Day Sales Trend with Dribbble Charcoal Palette */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-stone-700">30-Day Revenue Trend</span>
              <span className="text-xs font-bold text-[#16181a]">
                ₹{total_revenue_30d.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </span>
            </div>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={sales_history_30d} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="charcoalGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#16181a" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#16181a" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="2 2" vertical={false} stroke="#f0f2eb" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(val) => val.slice(5)}
                    tick={{ fontSize: 10, fill: '#8c9288' }}
                    tickLine={false}
                    axisLine={{ stroke: '#e2e5dc' }}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: '#8c9288' }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(val) => `₹${val >= 1000 ? (val / 1000).toFixed(0) + 'k' : val}`}
                  />
                  <Tooltip
                    cursor={{ stroke: '#16181a', strokeWidth: 1.5, strokeDasharray: '3 3' }}
                    content={({ active, payload }) => {
                      if (!active || !payload || !payload.length) return null;
                      const pt = payload[0].payload;
                      const rev = Number(pt.revenue || 0);
                      return (
                        <div className="bg-[#16181a] border border-stone-700/80 p-3 rounded-2xl shadow-xl text-white text-xs select-none min-w-[150px] z-50">
                          <p className="text-[10px] uppercase font-bold text-stone-400 tracking-wider mb-1">
                            {pt.date}
                          </p>
                          <div className="flex items-baseline gap-1.5">
                            <span className="text-sm font-black text-[#e0fd53]">
                              ₹{rev.toLocaleString('en-IN')}
                            </span>
                            <span className="text-[10px] text-stone-400">sales</span>
                          </div>
                          <p className="text-[10px] text-stone-300 mt-0.5">
                            Actual Daily Store Receipts
                          </p>
                        </div>
                      );
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke="#16181a"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#charcoalGrad)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 7-Day Forecast with Capsule Bars */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-stone-700">7-Day Projected Unit Demand</span>
              <Link
                href="/demand"
                className="text-xs font-bold text-stone-700 hover:text-[#16181a] inline-flex items-center gap-1"
              >
                <span>Product Breakdown</span>
                <ArrowUpRight className="w-3 h-3" />
              </Link>
            </div>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={seven_day_forecast_summary} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="2 2" vertical={false} stroke="#f0f2eb" />
                  <XAxis
                    dataKey="day_name"
                    tickFormatter={(val) => val.slice(0, 3)}
                    tick={{ fontSize: 10, fill: '#8c9288' }}
                    tickLine={false}
                    axisLine={{ stroke: '#e2e5dc' }}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: '#8c9288' }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    cursor={{ fill: 'rgba(224, 253, 83, 0.15)', radius: 8 }}
                    content={({ active, payload }) => {
                      if (!active || !payload || !payload.length) return null;
                      const pt = payload[0].payload;
                      const units = pt.predicted_units;
                      const rev = Number(pt.projected_revenue || 0);
                      return (
                        <div className="bg-[#16181a] border border-stone-700/80 p-3 rounded-2xl shadow-xl text-white text-xs select-none min-w-[160px] z-50">
                          <div className="flex items-center justify-between gap-2 mb-1 border-b border-stone-800 pb-1">
                            <p className="text-xs font-bold text-[#e0fd53]">
                              {pt.day_name}
                            </p>
                            {pt.date && (
                              <span className="text-[10px] text-stone-400 font-mono">{pt.date}</span>
                            )}
                          </div>
                          <div className="space-y-1 mt-1">
                            <p className="text-xs text-stone-200">
                              Projected Demand: <strong className="text-white font-bold">{units} Units</strong>
                            </p>
                            <p className="text-xs text-stone-200">
                              Est. Revenue: <strong className="text-[#e0fd53] font-bold">₹{rev.toLocaleString('en-IN')}</strong>
                            </p>
                          </div>
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="predicted_units" fill="#16181a" radius={[12, 12, 4, 4]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Recommended Actions by Category */}
      {top_recommendations && top_recommendations.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-[#16181a] tracking-tight">
                Recommended Actions by Category
              </h2>
              <span className="text-[10px] font-bold text-stone-600 bg-white border border-stone-200/90 px-2.5 py-0.5 rounded-full shadow-2xs">
                Top Guidance
              </span>
            </div>
            <span className="text-[11px] text-stone-400 font-medium hidden sm:inline">
              Deterministic replenishment and margin-safe promotional lift
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {top_recommendations.map((rec) => {
              const isRestock = rec.category_type === 'RESTOCK_PRIORITY';
              const isClearance = rec.category_type === 'CLEARANCE_DISCOUNT';

              const badgeStyle = isRestock
                ? 'bg-[#fbe8e4] text-[#a43b27] border-[#f3c5bd]'
                : isClearance
                ? 'bg-[#e0fd53]/30 text-[#16181a] border-[#e0fd53]'
                : 'bg-emerald-50 text-emerald-800 border-emerald-200';

              const IconComponent = isRestock ? AlertTriangle : isClearance ? Tag : Percent;
              const actionLabel = isRestock ? 'Restock Item' : isClearance ? 'Launch Offer' : 'Apply Promo';

              // The target page opens its popup pre-filled with these recommended values.
              // Nothing is applied until the merchant reviews and confirms there.
              const recParams = new URLSearchParams({
                rec: isRestock ? 'restock' : 'campaign',
                product_id: rec.product_id,
                product_name: rec.product_name,
                reason: rec.badge_label,
              });
              if (isRestock && rec.recommended_quantity) recParams.set('qty', String(rec.recommended_quantity));
              if (!isRestock && rec.suggested_discount_pct) recParams.set('discount', String(rec.suggested_discount_pct));
              if (!isRestock) recParams.set('kind', isClearance ? 'clearance' : 'promo');
              const actionHref = `${rec.action_url || (isRestock ? '/demand' : '/campaigns')}?${recParams.toString()}`;

              return (
                <div
                  key={rec.recommendation_id}
                  className="p-5 rounded-[26px] bg-white border border-stone-200/90 shadow-[0_4px_20px_rgba(20,24,20,0.03)] flex flex-col justify-between hover:border-stone-400 transition-all gap-4"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className={`text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full border ${badgeStyle}`}>
                        {rec.badge_label}
                      </span>
                      <span className="text-[10px] text-stone-400 font-medium">
                        {rec.current_stock} in stock
                      </span>
                    </div>

                    <h3 className="text-sm font-bold text-[#16181a] tracking-tight line-clamp-1" title={rec.title}>
                      {rec.title}
                    </h3>

                    <div className="mt-2.5 p-2 rounded-xl bg-[#f7f8f4] border border-stone-200/70 flex items-center gap-2">
                      <div className="w-6 h-6 rounded-lg bg-white border border-stone-200 flex items-center justify-center shrink-0 text-[#16181a]">
                        <IconComponent className="w-3.5 h-3.5" />
                      </div>
                      <p className="text-[11px] font-semibold text-stone-800 truncate">
                        {rec.metric_highlight}
                      </p>
                    </div>

                    <p className="mt-2.5 text-xs text-stone-500 line-clamp-2 leading-relaxed">
                      {rec.summary}
                    </p>
                  </div>

                  <div className="pt-3 border-t border-stone-100 flex items-center justify-between gap-2">
                    <div>
                      <p className="text-[9px] uppercase tracking-wider text-stone-400 font-medium">Est. Revenue Lift</p>
                      <p className="text-xs font-bold text-emerald-700">
                        +₹{rec.projected_revenue_lift.toLocaleString('en-IN')}
                      </p>
                    </div>

                    <Link
                      href={actionHref}
                      className="px-4 py-1.5 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-semibold text-xs transition-all shadow-2xs inline-flex items-center gap-1.5 shrink-0"
                    >
                      <span>{actionLabel}</span>
                      <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Stock Warnings Table */}
      <div className="p-6 rounded-[28px] bg-white border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm md:text-base font-bold text-[#16181a] tracking-tight">
              Stockout Warnings & Replenishment Queue
            </h3>
            <p className="text-[11px] text-stone-400 mt-0.5">
              Catalog lines with safety threshold deficits requiring active replenishment
            </p>
          </div>
          <Link
            href="/demand"
            className="text-xs font-semibold text-stone-800 hover:text-[#16181a] flex items-center gap-1"
          >
            <span>Manage All Catalog</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {stock_warnings.length === 0 ? (
          <div className="p-8 text-center bg-[#f7f8f4] rounded-2xl border border-dashed border-stone-200">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
            <p className="text-xs font-bold text-[#16181a]">All Inventory Healthy</p>
            <p className="text-[11px] text-stone-500 mt-0.5">Zero stockout risks identified on live 7-day forecast.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-stone-100 text-stone-400 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="pb-3 pl-2">Product Name</th>
                  <th className="pb-3">Category</th>
                  <th className="pb-3 text-right">Current Stock</th>
                  <th className="pb-3 text-right">Threshold</th>
                  <th className="pb-3 text-right">Runway</th>
                  <th className="pb-3 text-center">Status</th>
                  <th className="pb-3 text-right pr-2">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100 text-stone-700">
                {stock_warnings.map((item) => (
                  <tr key={item.product_id} className="hover:bg-stone-50/80 transition-colors">
                    <td className="py-3 pl-2 font-semibold text-[#16181a] flex items-center gap-2">
                      <div className="w-6 h-6 rounded-lg bg-stone-100 flex items-center justify-center shrink-0">
                        <Package className="w-3.5 h-3.5 text-stone-500" />
                      </div>
                      <span>{item.product_name}</span>
                    </td>
                    <td className="py-3 text-stone-500">{item.category}</td>
                    <td className="py-3 text-right font-bold text-[#16181a]">{item.current_stock}</td>
                    <td className="py-3 text-right text-stone-500">{item.reorder_threshold}</td>
                    <td className="py-3 text-right">
                      <span className="font-semibold text-[#8c5208] bg-[#faeed6] border border-[#f2d8a5] px-2 py-0.5 rounded-full text-[11px]">
                        {item.days_of_stock_left} days left
                      </span>
                    </td>
                    <td className="py-3 text-center">
                      <Badge
                        variant={item.severity === 'CRITICAL' ? 'danger' : 'warning'}
                        dot
                        size="sm"
                      >
                        {item.severity}
                      </Badge>
                    </td>
                    <td className="py-3 text-right pr-2">
                      <button
                        onClick={() => {
                          setSelectedStockItem(item);
                          setRestockQty(item.recommended_reorder || 20);
                        }}
                        className="px-3.5 py-1 rounded-full bg-white hover:bg-[#16181a] hover:text-white text-stone-800 font-semibold text-[11px] transition-all border border-stone-200/90 shadow-2xs"
                      >
                        Restock (+{item.recommended_reorder})
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick Restock Modal */}
      <Modal
        isOpen={!!selectedStockItem}
        onClose={() => setSelectedStockItem(null)}
        title={selectedStockItem ? `Restock: ${selectedStockItem.product_name}` : 'Restock Inventory'}
      >
        {actionSuccess ? (
          <div className="p-4 rounded-2xl bg-emerald-50 text-emerald-900 text-xs font-semibold flex items-center gap-2 border border-emerald-200">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <span>{actionSuccess}</span>
          </div>
        ) : (
          <form onSubmit={handleRestockSubmit} className="space-y-4">
            <div className="p-3 bg-[#f7f8f4] rounded-2xl text-xs text-stone-700 space-y-1 border border-stone-200/70">
              <p>Current On-Hand Stock: <strong>{selectedStockItem?.current_stock}</strong></p>
              <p>Safety Reorder Threshold: <strong>{selectedStockItem?.reorder_threshold}</strong></p>
              <p>Recommended Replenishment: <strong className="text-[#16181a]">+{selectedStockItem?.recommended_reorder} units</strong></p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Quantity to Add to Inventory
              </label>
              <input
                type="number"
                min="1"
                required
                value={restockQty}
                onChange={(e) => setRestockQty(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-sm focus:outline-hidden focus:ring-2 focus:ring-[#16181a]"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setSelectedStockItem(null)}
                className="px-4 py-2 rounded-full border border-stone-200 text-xs font-semibold text-stone-600 hover:bg-stone-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={restocking}
                className="px-5 py-2 rounded-full bg-[#16181a] hover:bg-stone-800 text-white text-xs font-semibold flex items-center gap-2 shadow-xs transition-all"
              >
                {restocking ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Confirm Replenishment'}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </AppLayout>
  );
}
