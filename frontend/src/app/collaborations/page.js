'use client';

import React, { useState, useEffect } from 'react';
import AppLayout from '@/components/layout/AppLayout';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';
import RecommendationBanner from '@/components/ui/RecommendationBanner';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import {
  Handshake,
  Store,
  MapPin,
  Sparkles,
  Percent,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  Loader2,
  ShieldCheck,
  ChevronRight,
  TrendingUp,
  ArrowUpRight,
} from 'lucide-react';

export default function CollaborationsPage() {
  const { merchant } = useAuth();
  const [partners, setPartners] = useState([]);
  const [proposals, setProposals] = useState([]);
  const [myProducts, setMyProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('proposals');

  // Proposal Creator modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedPartner, setSelectedPartner] = useState(null);
  const [proposalForm, setProposalForm] = useState({
    initiator_product_id: '',
    initiator_discount_pct: 10,
    partner_product_id: '',
    partner_discount_pct: 10,
    bundle_name: '',
    bundle_description: '',
  });

  // Set when the proposal popup was pre-filled with the suggested bundle
  const [prefillInfo, setPrefillInfo] = useState(null);

  // Live Margin Validation state
  const [validationResult, setValidationResult] = useState(null);
  const [validating, setValidating] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [partnersRes, proposalsRes, prodsRes] = await Promise.all([
        api.get('/collaborations/discover'),
        api.get('/collaborations/proposals'),
        api.get('/products'),
      ]);
      setPartners(partnersRes.data);
      setProposals(proposalsRes.data);
      setMyProducts(prodsRes.data);

      if (prodsRes.data.length > 0) {
        // Default only when nothing is chosen yet (checked on the latest state, so a
        // pre-filled suggested bundle is never overwritten when data reloads)
        setProposalForm((prev) =>
          prev.initiator_product_id ? prev : { ...prev, initiator_product_id: prodsRes.data[0].product_id }
        );
      }

      // Arrived from the Local Map ("Collaborate" on a nearby shop): open that partner's
      // proposal pre-filled with the suggested bundle. Nothing is sent until "Submit".
      if (typeof window !== 'undefined') {
        const params = new URLSearchParams(window.location.search);
        const partnerId = params.get('partner');
        if (partnerId) {
          window.history.replaceState(null, '', window.location.pathname);
          const target = partnersRes.data.find((p) => p.merchant_id === partnerId);
          if (target) {
            setActiveTab('partners');
            openProposalModal(target, prodsRes.data, 'Local Map');
          }
        }
      }
    } catch (err) {
      console.error('Failed to load collaborations data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openProposalModal = (partner, productsList = myProducts, from = null) => {
    setSelectedPartner(partner);
    const b = partner.suggested_bundle;
    if (b) {
      // Pre-fill the suggested bundle (products + cost-safe discounts); the merchant can edit
      setProposalForm({
        initiator_product_id: b.initiator_product_id,
        initiator_discount_pct: b.initiator_discount_pct,
        partner_product_id: b.partner_product_id,
        partner_discount_pct: b.partner_discount_pct,
        bundle_name: b.bundle_name,
        bundle_description: b.pitch,
      });
      setPrefillInfo({
        source: from ? `${from} · ${partner.suggestion_source || 'LocalPulse'}` : partner.suggestion_source || 'LocalPulse',
        reason: b.theme,
        summary: `${b.initiator_discount_pct}% off your ${b.initiator_product_name} + ${b.partner_discount_pct}% off their ${b.partner_product_name}: ₹${Math.round(b.discounted_bundle_price).toLocaleString('en-IN')} instead of ₹${Math.round(b.original_bundle_price).toLocaleString('en-IN')}.`,
      });
    } else {
      setProposalForm({
        initiator_product_id: productsList[0]?.product_id || '',
        initiator_discount_pct: 10,
        partner_product_id: partner.top_products?.[0]?.product_id || '',
        partner_discount_pct: 10,
        bundle_name: `${merchant?.business_name} & ${partner.business_name} Combo`,
        bundle_description: `Cross-promoted neighborhood bundle offering exclusive discounts on complementary items.`,
      });
      setPrefillInfo(null);
    }
    setValidationResult(null);
    setShowCreateModal(true);
  };

  // Run deterministic margin validation
  const runValidation = async () => {
    if (!selectedPartner || !proposalForm.initiator_product_id || !proposalForm.partner_product_id) {
      return;
    }
    setValidating(true);
    try {
      const res = await api.post('/collaborations/validate-margins', {
        partner_merchant_id: selectedPartner.merchant_id,
        initiator_product_id: proposalForm.initiator_product_id,
        initiator_discount_pct: parseFloat(proposalForm.initiator_discount_pct),
        partner_product_id: proposalForm.partner_product_id,
        partner_discount_pct: parseFloat(proposalForm.partner_discount_pct),
        bundle_name: proposalForm.bundle_name || 'Joint Bundle',
      });
      setValidationResult(res.data);
    } catch (err) {
      console.error('Validation error:', err);
    } finally {
      setValidating(false);
    }
  };

  useEffect(() => {
    if (showCreateModal && selectedPartner) {
      runValidation();
    }
  }, [
    showCreateModal,
    proposalForm.initiator_product_id,
    proposalForm.initiator_discount_pct,
    proposalForm.partner_product_id,
    proposalForm.partner_discount_pct,
  ]);

  const handleCreateProposal = async (e) => {
    e.preventDefault();
    if (!validationResult?.is_financially_viable) {
      alert('Cannot propose bundle: Minimum 12% profit margin rule violated.');
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/collaborations/proposals', {
        partner_merchant_id: selectedPartner.merchant_id,
        initiator_product_id: proposalForm.initiator_product_id,
        initiator_discount_pct: parseFloat(proposalForm.initiator_discount_pct),
        partner_product_id: proposalForm.partner_product_id,
        partner_discount_pct: parseFloat(proposalForm.partner_discount_pct),
        bundle_name: proposalForm.bundle_name,
        bundle_description: proposalForm.bundle_description,
      });
      setShowCreateModal(false);
      setPrefillInfo(null);
      loadData();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || 'Failed to submit proposal.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRespondProposal = async (proposalId, action) => {
    try {
      await api.post(`/collaborations/proposals/${proposalId}/respond?action=${action}`);
      loadData();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || 'Failed to update proposal response.');
    }
  };

  return (
    <AppLayout
      title="Merchant Collaborations"
      subtitle="Discover local MSME partners, construct complementary bundles, and validate unit margins"
    >
      {/* Top Banner & Context Pill */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-stone-200/90 bg-white text-stone-700 text-xs font-semibold shadow-2xs">
            <ShieldCheck className="w-3.5 h-3.5 text-[#16181a]" />
            <span>Deterministic Margin Protection (12% Min)</span>
          </div>
          <span className="text-xs text-stone-400 font-medium hidden sm:inline">
            Active: {merchant?.business_name}
          </span>
        </div>
      </div>

      {/* Dribbble-style Category Navigation Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
        <button
          onClick={() => setActiveTab('proposals')}
          className={`px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
            activeTab === 'proposals'
              ? 'bg-[#16181a] text-white shadow-xs font-bold'
              : 'bg-white hover:bg-stone-50 text-stone-700 border border-stone-200/90 shadow-2xs'
          }`}
        >
          Active Proposals ({proposals.length})
        </button>
        <button
          onClick={() => setActiveTab('partners')}
          className={`px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
            activeTab === 'partners'
              ? 'bg-[#16181a] text-white shadow-xs font-bold'
              : 'bg-white hover:bg-stone-50 text-stone-700 border border-stone-200/90 shadow-2xs'
          }`}
        >
          Nearby Store Partners ({partners.length})
        </button>
      </div>

      {/* Proposals Tracker Section */}
      <div className="bg-white rounded-[28px] border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)] p-6">
        <div className="flex items-center justify-between pb-3.5 border-b border-stone-100 mb-4">
          <div>
            <h3 className="text-sm md:text-base font-bold text-[#16181a] tracking-tight">
              Active Collaboration Proposals & Approvals
            </h3>
            <p className="text-[11px] text-stone-400 mt-0.5">
              Multi-merchant mutual signoffs for neighborhood retail combos
            </p>
          </div>
          <span className="text-xs font-mono text-stone-400">
            {proposals.length} recorded
          </span>
        </div>

        {proposals.length === 0 ? (
          <div className="p-8 text-center bg-[#f7f8f4] rounded-2xl border border-dashed border-stone-200">
            <Handshake className="w-8 h-8 text-stone-400 mx-auto mb-2" />
            <p className="text-xs font-bold text-[#16181a]">No Proposals Yet</p>
            <p className="text-[11px] text-stone-500 mt-0.5">Explore nearby partners below to construct your first joint bundle.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {proposals.map((prop) => {
              const isInitiator = prop.initiator_merchant_id === merchant?.merchant_id;
              const isPartner = prop.partner_merchant_id === merchant?.merchant_id;
              const canRespond = (isPartner && !prop.partner_approved) || (isInitiator && !prop.initiator_approved);

              return (
                <div
                  key={prop.proposal_id}
                  className="p-5 rounded-2xl border border-stone-200/90 hover:border-stone-400 transition-colors bg-[#fbfbf9] space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-bold text-[#16181a]">{prop.bundle_name}</h4>
                        <Badge
                          variant={
                            prop.status === 'APPROVED'
                              ? 'success'
                              : prop.status === 'REJECTED'
                              ? 'danger'
                              : 'warning'
                          }
                          size="sm"
                        >
                          {prop.status}
                        </Badge>
                      </div>
                      <p className="text-xs text-stone-500 mt-0.5">{prop.bundle_description}</p>
                    </div>

                    <div className="text-right shrink-0">
                      <p className="text-xs text-stone-400 line-through">₹{prop.original_bundle_price}</p>
                      <p className="text-base font-black text-[#16181a]">₹{prop.discounted_bundle_price}</p>
                    </div>
                  </div>

                  {/* Merchant Participant Margin Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-stone-200/60 text-xs">
                    {/* Initiator Info */}
                    <div className="p-3 rounded-xl bg-white border border-stone-200/80 flex items-center justify-between">
                      <div>
                        <p className="font-bold text-[#16181a]">{prop.initiator_merchant_name}</p>
                        <p className="text-[11px] text-stone-500">{prop.initiator_product_name} (-{prop.initiator_discount_pct}%)</p>
                        <p className="text-[10px] text-emerald-700 font-bold mt-0.5">Unit Margin: {prop.initiator_margin_pct}%</p>
                      </div>
                      <div className="text-right">
                        {prop.initiator_approved ? (
                          <Badge variant="success" size="sm">Initiator Approved</Badge>
                        ) : (
                          <Badge variant="warning" size="sm">Pending</Badge>
                        )}
                      </div>
                    </div>

                    {/* Partner Info */}
                    <div className="p-3 rounded-xl bg-white border border-stone-200/80 flex items-center justify-between">
                      <div>
                        <p className="font-bold text-[#16181a]">{prop.partner_merchant_name}</p>
                        <p className="text-[11px] text-stone-500">{prop.partner_product_name} (-{prop.partner_discount_pct}%)</p>
                        <p className="text-[10px] text-emerald-700 font-bold mt-0.5">Unit Margin: {prop.partner_margin_pct}%</p>
                      </div>
                      <div className="text-right">
                        {prop.partner_approved ? (
                          <Badge variant="success" size="sm">Partner Approved</Badge>
                        ) : (
                          <Badge variant="warning" size="sm">Awaiting Review</Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Participant Action Buttons */}
                  {canRespond && prop.status === 'PENDING_APPROVAL' && (
                    <div className="pt-2 flex items-center justify-between bg-white p-3 rounded-xl border border-stone-200">
                      <span className="text-[11px] font-semibold text-stone-700">
                        {isPartner ? 'You are the invited partner for this proposal.' : 'Your confirmation requested.'}
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleRespondProposal(prop.proposal_id, 'REJECT')}
                          className="px-3.5 py-1.5 rounded-full border border-stone-200 text-stone-700 hover:bg-stone-50 text-xs font-semibold"
                        >
                          Reject
                        </button>
                        <button
                          onClick={() => handleRespondProposal(prop.proposal_id, 'APPROVE')}
                          className="px-4 py-1.5 rounded-full bg-[#16181a] hover:bg-stone-800 text-white text-xs font-bold flex items-center gap-1.5 shadow-2xs"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5 text-[#e0fd53]" />
                          <span>Approve Collaboration</span>
                        </button>
                      </div>
                    </div>
                  )}

                  {!canRespond && prop.status === 'PENDING_APPROVAL' && (
                    <div className="text-[11px] text-stone-400 bg-white px-3 py-2 rounded-xl border border-stone-200/80 flex items-center justify-between">
                      <span>Awaiting partner confirmation. Tip: Use the top Header demo switcher to switch accounts and test approving this proposal.</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Discover Nearby Merchants Grid */}
      <div className="bg-white rounded-[28px] border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)] p-6">
        <div className="flex items-center justify-between pb-3.5 border-b border-stone-100 mb-4">
          <div>
            <h2 className="text-sm md:text-base font-bold text-[#16181a] flex items-center gap-2">
              <Store className="w-4 h-4 text-stone-600" />
              <span>Discover Nearby MSME Partners</span>
            </h2>
            <p className="text-[11px] text-stone-400">Stores located within 1 km for complementary co-marketing bundles</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {partners.map((partner) => (
            <div
              key={partner.merchant_id}
              className="p-5 rounded-[24px] border border-stone-200/90 hover:border-stone-400 transition-all bg-[#fbfbf9] flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-bold text-[#16181a] text-sm">{partner.business_name}</h3>
                    <p className="text-xs text-stone-500 font-semibold">{partner.category}</p>
                  </div>
                  {partner.suggested_bundle ? (
                    <div className="px-2.5 py-0.5 rounded-full bg-[#e0fd53] text-[#16181a] text-[10px] font-black shrink-0">
                      {partner.complementary_score}% Synergy
                    </div>
                  ) : (
                    <div className="px-2.5 py-0.5 rounded-full bg-stone-100 border border-stone-200 text-stone-500 text-[10px] font-bold shrink-0">
                      No natural match
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-1 text-[11px] text-stone-500 mt-2">
                  <MapPin className="w-3.5 h-3.5 text-stone-400 shrink-0" />
                  <span className="truncate">{partner.distance_km} km • {partner.address}</span>
                </div>

                <div className="mt-3 p-2.5 rounded-xl bg-white border border-stone-200/80">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[10px] font-bold text-stone-400 uppercase">{partner.synergy_type}</p>
                    {partner.suggestion_source && (
                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-[#f7f8f4] border border-stone-200 text-stone-500 shrink-0">
                        {partner.suggestion_source}
                      </span>
                    )}
                  </div>
                  {partner.suggested_bundle ? (
                    <>
                      <p className="text-[11.5px] text-[#16181a] font-semibold mt-1 leading-snug">
                        {partner.suggested_bundle.initiator_product_name} ({partner.suggested_bundle.initiator_discount_pct}% off)
                        {' + '}
                        {partner.suggested_bundle.partner_product_name} ({partner.suggested_bundle.partner_discount_pct}% off)
                      </p>
                      <ul className="mt-1.5 space-y-1">
                        {(partner.suggestion_reasons || []).slice(0, 4).map((r, i) => (
                          <li key={i} className="text-[10.5px] text-stone-600 leading-snug flex gap-1.5">
                            <span className="text-[#16181a] shrink-0">•</span>
                            <span>{r}</span>
                          </li>
                        ))}
                      </ul>
                    </>
                  ) : (
                    <p className="text-[11px] text-stone-700 mt-0.5 leading-relaxed">{partner.synergy_rationale}</p>
                  )}
                </div>

                <div className="mt-3">
                  <p className="text-[10px] font-semibold text-stone-400 uppercase">Available Catalog Items:</p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {partner.top_products.map((p) => (
                      <span key={p.product_id} className="text-[10px] bg-white border border-stone-200 px-2 py-0.5 rounded-full text-stone-700">
                        {p.name} (₹{p.selling_price})
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-stone-200/70">
                <button
                  onClick={() => openProposalModal(partner)}
                  className="w-full py-2.5 px-3 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs transition-colors flex items-center justify-center gap-1.5 shadow-2xs"
                >
                  <span>{partner.suggested_bundle ? 'Review Suggested Bundle' : 'Build Joint Bundle'}</span>
                  <ArrowUpRight className="w-3.5 h-3.5 text-[#e0fd53]" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Proposal & Margin Validator Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => {
          setShowCreateModal(false);
          setPrefillInfo(null);
        }}
        title={selectedPartner ? `Construct Joint Bundle with ${selectedPartner.business_name}` : 'Construct Bundle'}
        maxWidth="max-w-2xl"
      >
        <form onSubmit={handleCreateProposal} className="space-y-4">
          {prefillInfo && (
            <RecommendationBanner source={prefillInfo.source} reason={prefillInfo.reason}>
              {prefillInfo.summary} Your partner still has to approve it.
            </RecommendationBanner>
          )}
          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-1">Bundle Name</label>
            <input
              type="text"
              required
              value={proposalForm.bundle_name}
              onChange={(e) => setProposalForm({ ...proposalForm, bundle_name: e.target.value })}
              className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
              placeholder="e.g. Indiranagar Breakfast Hamper"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-1">Bundle Description / Marketing Pitch</label>
            <textarea
              rows={2}
              required
              value={proposalForm.bundle_description}
              onChange={(e) => setProposalForm({ ...proposalForm, bundle_description: e.target.value })}
              className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-2xl bg-[#f7f8f4] border border-stone-200">
            {/* Your Product Choice */}
            <div>
              <p className="text-xs font-bold text-stone-800 mb-2">Your Product ({merchant?.business_name})</p>
              <select
                value={proposalForm.initiator_product_id}
                onChange={(e) => setProposalForm({ ...proposalForm, initiator_product_id: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs bg-white mb-2"
              >
                {myProducts.map((p) => (
                  <option key={p.product_id} value={p.product_id}>
                    {p.name} (₹{p.selling_price})
                  </option>
                ))}
              </select>

              <label className="block text-[11px] font-semibold text-stone-600 mb-1">
                Your Discount Contribution (%): {proposalForm.initiator_discount_pct}%
              </label>
              <input
                type="range"
                min="0"
                max="35"
                step="1"
                value={proposalForm.initiator_discount_pct}
                onChange={(e) => setProposalForm({ ...proposalForm, initiator_discount_pct: e.target.value })}
                className="w-full accent-[#16181a]"
              />
            </div>

            {/* Partner Product Choice */}
            <div>
              <p className="text-xs font-bold text-stone-800 mb-2">Partner Product ({selectedPartner?.business_name})</p>
              <select
                value={proposalForm.partner_product_id}
                onChange={(e) => setProposalForm({ ...proposalForm, partner_product_id: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs bg-white mb-2"
              >
                {selectedPartner?.top_products.map((p) => (
                  <option key={p.product_id} value={p.product_id}>
                    {p.name} (₹{p.selling_price})
                  </option>
                ))}
              </select>

              <label className="block text-[11px] font-semibold text-stone-600 mb-1">
                Partner Discount Contribution (%): {proposalForm.partner_discount_pct}%
              </label>
              <input
                type="range"
                min="0"
                max="35"
                step="1"
                value={proposalForm.partner_discount_pct}
                onChange={(e) => setProposalForm({ ...proposalForm, partner_discount_pct: e.target.value })}
                className="w-full accent-[#16181a]"
              />
            </div>
          </div>

          {/* Real-time Deterministic Margin Validation Box */}
          {validationResult && (
            <div className={`p-4 rounded-2xl border text-xs ${
              validationResult.is_financially_viable
                ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                : 'bg-[#faeed6] border-[#f2d8a5] text-[#8c5208]'
            }`}>
              <div className="flex items-center justify-between mb-2 font-bold">
                <span className="flex items-center gap-1.5">
                  {validationResult.is_financially_viable ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-[#8c5208]" />
                  )}
                  <span>{validationResult.is_financially_viable ? 'Financially Viable Bundle' : 'Margin Safety Threshold Violated'}</span>
                </span>
                <span className="text-[11px]">
                  Effective Discount: <strong>{validationResult.effective_bundle_discount_pct}%</strong>
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 text-[11px] mb-2 bg-white p-2.5 rounded-xl border border-stone-200 text-stone-800">
                <div>
                  <p className="font-semibold text-stone-600">Your Unit Margin:</p>
                  <p className="font-bold text-sm">{validationResult.initiator_margin_pct}% (₹{validationResult.initiator_profit_per_unit} profit)</p>
                </div>
                <div>
                  <p className="font-semibold text-stone-600">Partner Unit Margin:</p>
                  <p className="font-bold text-sm">{validationResult.partner_margin_pct}% (₹{validationResult.partner_profit_per_unit} profit)</p>
                </div>
              </div>

              <p className="text-[11px]">{validationResult.status_reason}</p>
            </div>
          )}

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
              disabled={submitting || !validationResult?.is_financially_viable}
              className="px-5 py-2 rounded-full bg-[#16181a] hover:bg-stone-800 text-white text-xs font-bold shadow-xs transition-all disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : 'Submit Proposal to Partner'}
            </button>
          </div>
        </form>
      </Modal>
    </AppLayout>
  );
}
