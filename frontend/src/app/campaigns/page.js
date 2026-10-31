'use client';

import React, { useState, useEffect } from 'react';
import AppLayout from '@/components/layout/AppLayout';
import StatCard from '@/components/ui/StatCard';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';
import RecommendationBanner, { takeRecommendationParams } from '@/components/ui/RecommendationBanner';
import api from '@/lib/api';
import {
  Megaphone,
  TrendingUp,
  IndianRupee,
  Plus,
  Play,
  RotateCcw,
  CheckCircle2,
  Calendar,
  Layers,
  ArrowUpRight,
  Info,
  Loader2,
  Zap,
  Sparkles,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [simulatingId, setSimulatingId] = useState(null);
  const [endingId, setEndingId] = useState(null);

  // New Campaign Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCampaign, setNewCampaign] = useState({
    title: '',
    campaign_type: 'Special Discount',
    discount_pct: 10,
    budget_allocated: 2000,
    target_redemptions_goal: 50,
    start_date: '',
    end_date: '',
    target_product_ids: [],
  });
  const [submitting, setSubmitting] = useState(false);
  // Set when the create popup was opened from a recommendation (Overview, festival plan)
  const [prefillInfo, setPrefillInfo] = useState(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [campRes, prodRes] = await Promise.all([
        api.get('/campaigns'),
        api.get('/products'),
      ]);
      setCampaigns(campRes.data);
      setProducts(prodRes.data);

      // Arrived from a recommendation ("Launch Offer" / "Apply Promo"): open the create
      // popup pre-filled with the recommended product and discount. Nothing is created
      // until the merchant clicks Launch.
      const rec = takeRecommendationParams();
      if (rec && rec.rec === 'campaign') {
        const target = prodRes.data.find((p) => p.product_id === rec.product_id);
        if (target) {
          const shortName = target.name.split(' ').slice(0, 3).join(' ');
          const days = Math.min(30, Math.max(1, parseInt(rec.days || '7', 10) || 7));
          const start = rec.start || new Date().toISOString().slice(0, 10);
          const end = rec.end || new Date(new Date(start).getTime() + (days - 1) * 86400000).toISOString().slice(0, 10);
          setNewCampaign({
            title: rec.title || (rec.kind === 'clearance' ? `Clearance Offer: ${shortName}` : `Quick Promo: ${shortName}`),
            campaign_type: rec.campaign_type || 'Special Discount',
            discount_pct: parseFloat(rec.discount || '10') || 10,
            budget_allocated: parseFloat(rec.budget || '1500') || 1500,
            target_redemptions_goal: 50,
            start_date: start,
            end_date: end,
            target_product_ids: [target.product_id],
          });
          setPrefillInfo({ reason: rec.reason || 'Recommendation', source: rec.source || 'Overview', discount: rec.discount, name: target.name });
          setShowCreateModal(true);
        }
      }
    } catch (err) {
      console.error('Failed to load campaigns:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleEndCampaign = async (campaignId) => {
    if (!confirm('End this campaign? All promotional products will be restored to their regular selling price.')) {
      return;
    }
    setEndingId(campaignId);
    try {
      const res = await api.post(`/campaigns/${campaignId}/end`);
      setCampaigns((prev) =>
        prev.map((c) => (c.campaign_id === campaignId ? res.data : c))
      );
      // Reload products to reflect restored prices
      const prodRes = await api.get('/products');
      setProducts(prodRes.data);
    } catch (err) {
      console.error('Error ending campaign:', err);
      alert('Failed to end campaign.');
    } finally {
      setEndingId(null);
    }
  };

  useEffect(() => {
    loadData();
    const today = new Date();
    const nextWeek = new Date(Date.now() + 7 * 86400000);
    setNewCampaign((prev) => ({
      ...prev,
      start_date: today.toISOString().slice(0, 10),
      end_date: nextWeek.toISOString().slice(0, 10),
    }));
  }, []);

  const handleSimulateRedemptions = async (campaignId, count) => {
    setSimulatingId(campaignId);
    try {
      const res = await api.post(`/campaigns/${campaignId}/simulate-redemptions`, {
        count: count,
      });
      setCampaigns((prev) =>
        prev.map((c) => (c.campaign_id === campaignId ? res.data : c))
      );
    } catch (err) {
      console.error('Simulation error:', err);
      alert('Failed to simulate redemptions.');
    } finally {
      setSimulatingId(null);
    }
  };

  const handleCreateCampaign = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post('/campaigns', {
        title: newCampaign.title,
        campaign_type: newCampaign.campaign_type,
        discount_pct: parseFloat(newCampaign.discount_pct),
        budget_allocated: parseFloat(newCampaign.budget_allocated),
        target_redemptions_goal: parseInt(newCampaign.target_redemptions_goal, 10),
        start_date: newCampaign.start_date,
        end_date: newCampaign.end_date,
        target_product_ids: newCampaign.target_product_ids,
      });
      setShowCreateModal(false);
      setPrefillInfo(null);
      setNewCampaign({
        title: '',
        campaign_type: 'Special Discount',
        discount_pct: 10,
        budget_allocated: 2000,
        target_redemptions_goal: 50,
        start_date: new Date().toISOString().slice(0, 10),
        end_date: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10),
        target_product_ids: [],
      });
      loadData();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || 'Failed to create campaign.');
    } finally {
      setSubmitting(false);
    }
  };

  const totalCampaignRev = campaigns.reduce((acc, c) => acc + c.total_revenue_generated, 0);
  const totalRedemptions = campaigns.reduce((acc, c) => acc + c.total_redemptions, 0);
  const totalNetProfit = campaigns.reduce((acc, c) => acc + c.net_campaign_profit, 0);

  return (
    <AppLayout
      title="Campaign Results & Deployments"
      subtitle="Track promotional outcomes against non-promoted baselines with persisted redemptions"
    >
      {/* Top Banner & Launch CTA */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-stone-200/90 bg-white text-stone-700 text-xs font-semibold shadow-2xs">
            <Zap className="w-3.5 h-3.5 text-[#16181a]" />
            <span>Deterministic Growth Simulator</span>
          </div>
          <span className="text-xs text-stone-400 font-medium hidden sm:inline">
            Active Campaigns ({campaigns.length})
          </span>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-1.5 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs flex items-center gap-1.5 shadow-2xs transition-all shrink-0 cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5 text-[#e0fd53]" />
          <span>Launch Campaign</span>
        </button>
      </div>

      {/* Aggregate KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-5 rounded-[26px] bg-white border border-stone-200/90 shadow-[0_4px_20px_rgba(20,24,20,0.03)] flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-stone-400 uppercase tracking-wider">Gross Promotional Revenue</span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">+18.4% lift</span>
          </div>
          <p className="text-2xl md:text-3xl font-black text-[#16181a]">
            ₹{totalCampaignRev.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
          <p className="text-xs text-stone-500 mt-2">Across all active promotions</p>
        </div>

        <div className="p-5 rounded-[26px] bg-white border border-stone-200/90 shadow-[0_4px_20px_rgba(20,24,20,0.03)] flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-stone-400 uppercase tracking-wider">Customer Throughput</span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#f6f6f0] text-stone-700 border border-stone-200">Verified</span>
          </div>
          <p className="text-2xl md:text-3xl font-black text-[#16181a]">
            {totalRedemptions} redemptions
          </p>
          <p className="text-xs text-stone-500 mt-2">Audited synthetic POS redemptions</p>
        </div>

        <div className="p-5 rounded-[26px] bg-[#16181a] text-white border border-stone-800 shadow-[0_4px_24px_rgba(0,0,0,0.14)] flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-stone-400 uppercase tracking-wider">Net Campaign Profit</span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#e0fd53] text-[#16181a]">12% Margin Rule</span>
          </div>
          <p className="text-2xl md:text-3xl font-black text-[#e0fd53]">
            ₹{totalNetProfit.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
          <p className="text-xs text-stone-300 mt-2">Gross revenue less COGS & marketing</p>
        </div>
      </div>

      {/* Campaigns List with Baseline Comparison */}
      <div className="space-y-4">
        {campaigns.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-[28px] border border-stone-200/90 shadow-xs">
            <Megaphone className="w-9 h-9 text-stone-300 mx-auto mb-2" />
            <h3 className="text-sm font-bold text-[#16181a]">No Active Promotional Campaigns</h3>
            <p className="text-xs text-stone-500 mt-1 max-w-sm mx-auto">
              Launch a flash discount or bundle offer to stimulate demand and measure revenue lift against normal baselines.
            </p>
          </div>
        ) : (
          campaigns.map((camp) => {
            const comparisonData = [
              {
                name: 'Expected Baseline',
                Revenue: camp.baseline_expected_revenue,
              },
              {
                name: 'Promotional Result',
                Revenue: camp.total_revenue_generated,
              },
            ];

            const isSimulating = simulatingId === camp.campaign_id;
            const progressRatio = Math.min(100, Math.round((camp.total_redemptions / camp.target_redemptions_goal) * 100));
            const filledCapsules = Math.max(1, Math.min(8, Math.round((progressRatio / 100) * 8)));

            return (
              <div
                key={camp.campaign_id}
                className="bg-white rounded-[28px] border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)] p-6 space-y-6"
              >
                {/* Campaign Header & Controls */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-stone-100">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-bold text-[#16181a]">{camp.title}</h2>
                      <Badge variant="primary" dot size="sm">{camp.campaign_type}</Badge>
                      <Badge variant={camp.status === 'ACTIVE' ? 'success' : 'default'} size="sm">
                        {camp.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-stone-500 mt-1 flex items-center gap-3">
                      <span>Discount: <strong>{camp.discount_pct}%</strong></span>
                      <span>•</span>
                      <span>Budget: <strong>₹{camp.budget_allocated}</strong></span>
                      <span>•</span>
                      <span>Timeline: <strong>{camp.start_date} to {camp.end_date}</strong></span>
                    </p>
                  </div>

                  {/* Simulator & Lifecycle Controls */}
                  <div className="flex flex-wrap items-center gap-2">
                    {camp.status === 'ACTIVE' && (
                      <button
                        onClick={() => handleEndCampaign(camp.campaign_id)}
                        disabled={endingId === camp.campaign_id}
                        className="px-3.5 py-1.5 rounded-full bg-stone-50 hover:bg-[#fbe8e4] hover:text-[#a43b27] text-stone-700 text-xs font-semibold flex items-center gap-1.5 transition-colors border border-stone-200"
                        title="End campaign and restore original regular product prices"
                      >
                        {endingId === camp.campaign_id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <RotateCcw className="w-3.5 h-3.5" />
                        )}
                        <span>End Campaign</span>
                      </button>
                    )}

                    <span className="text-[11px] font-semibold text-stone-400 uppercase tracking-wider hidden sm:inline ml-1">
                      Simulate:
                    </span>
                    <button
                      onClick={() => handleSimulateRedemptions(camp.campaign_id, 5)}
                      disabled={isSimulating}
                      className="px-3.5 py-1.5 rounded-full bg-[#f7f8f4] hover:bg-[#16181a] hover:text-white text-stone-800 text-xs font-semibold flex items-center gap-1.5 transition-colors border border-stone-200/90 shadow-2xs"
                    >
                      {isSimulating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 text-emerald-700" />}
                      <span>+5 Customers</span>
                    </button>
                    <button
                      onClick={() => handleSimulateRedemptions(camp.campaign_id, 10)}
                      disabled={isSimulating}
                      className="px-3.5 py-1.5 rounded-full bg-[#16181a] hover:bg-stone-800 text-white text-xs font-bold flex items-center gap-1.5 transition-colors shadow-2xs"
                    >
                      {isSimulating ? <Loader2 className="w-3.5 h-3.5 animate-spin text-[#e0fd53]" /> : <Play className="w-3.5 h-3.5 text-[#e0fd53]" />}
                      <span>+10 Customers</span>
                    </button>
                  </div>
                </div>

                {/* Performance Metrics & Baseline Chart Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                  {/* Left Column: Financial Breakdown */}
                  <div className="lg:col-span-7 grid grid-cols-2 sm:grid-cols-3 gap-3">
                    <div className="p-3.5 bg-[#f7f8f4] border border-stone-200/80 rounded-2xl flex flex-col justify-between">
                      <p className="text-[10px] font-bold text-stone-400 uppercase">Redemptions Progress</p>
                      <p className="text-xl font-black text-[#16181a] mt-0.5">
                        {camp.total_redemptions} <span className="text-xs text-stone-400 font-normal">/ {camp.target_redemptions_goal}</span>
                      </p>
                      {/* Segmented capsule row */}
                      <div className="flex items-center gap-1 mt-2">
                        {[...Array(8)].map((_, i) => (
                          <div
                            key={i}
                            className={`flex-1 h-3 rounded-full ${i < filledCapsules ? 'bg-[#16181a]' : 'border border-dashed border-stone-300'
                              }`}
                          />
                        ))}
                      </div>
                    </div>

                    <div className="p-3.5 bg-[#f7f8f4] border border-stone-200/80 rounded-2xl">
                      <p className="text-[10px] font-bold text-stone-400 uppercase">Gross Revenue</p>
                      <p className="text-xl font-black text-[#16181a] mt-0.5">
                        ₹{camp.total_revenue_generated.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </p>
                      <p className="text-[10px] text-stone-400 mt-1">
                        Discounts: ₹{camp.total_discounts_granted.toFixed(0)}
                      </p>
                    </div>

                    <div className="p-3.5 bg-[#f7f8f4] border border-stone-200/80 rounded-2xl">
                      <p className="text-[10px] font-bold text-stone-400 uppercase">COGS (Wholesale)</p>
                      <p className="text-xl font-black text-[#16181a] mt-0.5">
                        ₹{camp.cost_of_goods_sold.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </p>
                      <p className="text-[10px] text-stone-400 mt-1">Direct supplier cost</p>
                    </div>

                    <div className="p-3.5 bg-[#f7f8f4] border border-stone-200/80 rounded-2xl">
                      <p className="text-[10px] font-bold text-stone-400 uppercase">Incremental Lift</p>
                      <p className="text-xl font-black text-emerald-700 mt-0.5">
                        ₹{camp.incremental_revenue_lift.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </p>
                      <p className="text-[10px] text-stone-400 mt-1">
                        Over baseline: ₹{camp.baseline_expected_revenue.toFixed(0)}
                      </p>
                    </div>

                    <div className="p-3.5 bg-[#16181a] text-white rounded-2xl col-span-2">
                      <div className="flex items-center justify-between">
                        <p className="text-[10px] font-bold text-stone-400 uppercase">Net Realized Profit</p>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#e0fd53] text-[#16181a]">
                          Margin Safe
                        </span>
                      </div>
                      <p className="text-2xl font-black text-[#e0fd53] mt-0.5">
                        ₹{camp.net_campaign_profit.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </p>
                      <p className="text-[10px] text-stone-400 mt-1">
                        Calculated post wholesale intake & promotional allowance
                      </p>
                    </div>
                  </div>

                  {/* Right Column: Baseline vs Promotion Chart */}
                  <div className="lg:col-span-5 bg-[#f7f8f4] p-4 rounded-2xl border border-stone-200/80 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-xs font-bold text-[#16181a]">Revenue Lift vs Baseline</h4>
                        <span className="text-[10px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                          +{camp.incremental_revenue_lift > 0 ? ((camp.incremental_revenue_lift / (camp.baseline_expected_revenue || 1)) * 100).toFixed(0) : 0}% Lift
                        </span>
                      </div>
                      <p className="text-[10px] text-stone-400 mb-3">
                        Audited comparison against counterfactual baseline
                      </p>
                    </div>

                    <div className="h-44 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={comparisonData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="2 2" vertical={false} stroke="#e2e4dc" />
                          <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#737373' }} tickLine={false} axisLine={false} />
                          <YAxis tick={{ fontSize: 10, fill: '#737373' }} tickLine={false} axisLine={false} />
                          <Tooltip
                            cursor={{ fill: 'rgba(22, 24, 26, 0.05)' }}
                            content={({ active, payload }) => {
                              if (!active || !payload || !payload.length) return null;
                              const pt = payload[0].payload;
                              return (
                                <div className="bg-[#16181a] border border-stone-700/80 p-3 rounded-2xl shadow-xl text-white text-xs select-none min-w-[140px] z-50">
                                  <p className="text-[10px] uppercase font-bold text-stone-400 tracking-wider mb-1">
                                    {pt.name}
                                  </p>
                                  <div className="flex items-baseline gap-1.5">
                                    <span className="text-sm font-black text-[#e0fd53]">
                                      ₹{Number(pt.Revenue || 0).toLocaleString('en-IN')}
                                    </span>
                                    <span className="text-[10px] text-stone-400">revenue</span>
                                  </div>
                                </div>
                              );
                            }}
                          />
                          <Bar dataKey="Revenue" fill="#16181a" radius={[10, 10, 4, 4]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* New Campaign Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => {
          setShowCreateModal(false);
          setPrefillInfo(null);
        }}
        title="Launch New Promotional Campaign"
      >
        <form onSubmit={handleCreateCampaign} className="space-y-4">
          {prefillInfo && (
            <RecommendationBanner source={prefillInfo.source} reason={prefillInfo.reason}>
              Recommended: <strong>{prefillInfo.discount}% off {prefillInfo.name}</strong>, priced to stay above cost.
            </RecommendationBanner>
          )}
          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-1">Campaign Title</label>
            <input
              type="text"
              required
              value={newCampaign.title}
              onChange={(e) => setNewCampaign({ ...newCampaign, title: e.target.value })}
              className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
              placeholder="e.g. Weekend Dairy & Staples Special"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">Discount Offered (%)</label>
              <input
                type="number"
                min="1"
                max="50"
                required
                value={newCampaign.discount_pct}
                onChange={(e) => setNewCampaign({ ...newCampaign, discount_pct: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">Allocated Budget (₹)</label>
              <input
                type="number"
                min="100"
                required
                value={newCampaign.budget_allocated}
                onChange={(e) => setNewCampaign({ ...newCampaign, budget_allocated: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">Start Date</label>
              <input
                type="date"
                required
                value={newCampaign.start_date}
                onChange={(e) => setNewCampaign({ ...newCampaign, start_date: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">End Date</label>
              <input
                type="date"
                required
                value={newCampaign.end_date}
                onChange={(e) => setNewCampaign({ ...newCampaign, end_date: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-1">Target Products to Discount</label>
            <div className="max-h-36 overflow-y-auto space-y-1.5 p-2 bg-[#f7f8f4] border border-stone-200 rounded-xl">
              {products.map((p) => {
                const checked = newCampaign.target_product_ids.includes(p.product_id);
                return (
                  <label key={p.product_id} className="flex items-center gap-2 text-xs text-stone-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setNewCampaign({
                            ...newCampaign,
                            target_product_ids: [...newCampaign.target_product_ids, p.product_id],
                          });
                        } else {
                          setNewCampaign({
                            ...newCampaign,
                            target_product_ids: newCampaign.target_product_ids.filter((id) => id !== p.product_id),
                          });
                        }
                      }}
                      className="rounded border-stone-300 text-[#16181a] focus:ring-[#16181a]"
                    />
                    <span>{p.name} (Retail ₹{p.selling_price})</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => {
                setShowCreateModal(false);
                setPrefillInfo(null);
              }}
              className="px-4 py-2 rounded-full border border-stone-200 text-xs font-semibold text-stone-600 hover:bg-stone-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 rounded-full bg-[#16181a] hover:bg-stone-800 text-white text-xs font-bold shadow-xs transition-all"
            >
              {submitting ? 'Launching...' : 'Activate Campaign'}
            </button>
          </div>
        </form>
      </Modal>
    </AppLayout>
  );
}
