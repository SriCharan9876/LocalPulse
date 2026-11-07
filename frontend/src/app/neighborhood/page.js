'use client';

import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import AppLayout from '@/components/layout/AppLayout';
import Modal from '@/components/ui/Modal';
import Badge from '@/components/ui/Badge';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import {
  MapPin,
  Store,
  Calendar,
  Sparkles,
  TrendingUp,
  RefreshCw,
  Navigation,
  ArrowRight,
  ShieldAlert,
  Loader2,
  CheckCircle2,
  Phone,
  Layers,
  Compass,
  Handshake,
  ShieldCheck,
} from 'lucide-react';
import NeighborhoodCalendar from '@/components/calendar/NeighborhoodCalendar';
import EventActionPlan from '@/components/actions/EventActionPlan';
import ProposalModal from '@/components/collab/ProposalModal';

// Dynamically import Leaflet Map to avoid SSR window errors
const NeighborhoodMap = dynamic(
  () => import('@/components/map/NeighborhoodMap'),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-[460px] rounded-[28px] bg-stone-100 border border-stone-200/90 flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-7 h-7 text-[#16181a] animate-spin" />
        <p className="text-xs font-semibold text-stone-600">Initializing neighborhood spatial map...</p>
      </div>
    ),
  }
);

export default function NeighborhoodPage() {
  const { merchant } = useAuth();
  const [nearbyMerchants, setNearbyMerchants] = useState([]);
  const [events, setEvents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeDirectoryTab, setActiveDirectoryTab] = useState('stores'); // 'stores' | 'proposals'

  // Selection states
  const [selectedMerchantId, setSelectedMerchantId] = useState(null);
  const [selectedEventId, setSelectedEventId] = useState(null);
  // Occasion whose action plan popup is open
  const [planEvent, setPlanEvent] = useState(null);

  // Bundle proposal popup (opens here; the merchant stays on this page)
  const [collabPartner, setCollabPartner] = useState(null);
  const [collabData, setCollabData] = useState(null); // { partners, myProducts }, loaded on first use
  const [collabLoadingId, setCollabLoadingId] = useState(null);
  const [collabNotice, setCollabNotice] = useState('');

  // Reset Data Modal state
  const [showResetModal, setShowResetModal] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetSuccessNotice, setResetSuccessNotice] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [merchantsRes, eventsRes, summaryRes, proposalsRes] = await Promise.all([
        api.get('/neighborhood/merchants').catch((e) => { console.error('merchants:', e.message); return { data: [] }; }),
        api.get('/neighborhood/events').catch((e) => { console.error('events:', e.message); return { data: [] }; }),
        api.get('/neighborhood/summary').catch((e) => { console.error('summary:', e.message); return { data: null }; }),
        api.get('/collaborations/proposals').catch(() => ({ data: [] })),
      ]);
      setNearbyMerchants(merchantsRes.data || []);
      setEvents(eventsRes.data || []);
      setSummary(summaryRes.data);
      setProposals(proposalsRes.data || []);
    } catch (err) {
      console.error('Failed to load neighborhood data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [merchant?.merchant_id]);

  // Open the joint-bundle popup for one nearby shop without leaving the map page
  const openCollab = async (partnerId) => {
    if (!partnerId) return;
    setCollabLoadingId(partnerId);
    try {
      let data = collabData;
      if (!data) {
        const [discoverRes, productsRes] = await Promise.all([
          api.get('/collaborations/discover'),
          api.get('/products'),
        ]);
        data = { partners: discoverRes.data, myProducts: productsRes.data };
        setCollabData(data);
      }
      const partner = data.partners.find((p) => p.merchant_id === partnerId);
      if (partner) {
        setPlanEvent(null); // one popup at a time
        setCollabPartner(partner);
      } else {
        setCollabNotice('This shop is not available for a bundle right now.');
        setTimeout(() => setCollabNotice(''), 5000);
      }
    } catch (err) {
      console.error('Failed to open bundle popup:', err);
      alert('Could not load bundle details. Please ensure backend is running.');
    } finally {
      setCollabLoadingId(null);
    }
  };

  // Handle URL deep links (?partner=... or ?tab=proposals) — must be after openCollab
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const partnerId = params.get('partner');
      const tab = params.get('tab');
      if (tab === 'proposals') {
        setActiveDirectoryTab('proposals');
      }
      if (partnerId) {
        window.history.replaceState(null, '', window.location.pathname);
        openCollab(partnerId);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    const onClick = (e) => {
      const el = e.target.closest?.('[data-collab-partner]');
      if (!el) return;
      e.preventDefault();
      openCollab(el.getAttribute('data-collab-partner'));
    };
    document.addEventListener('click', onClick, true); // capture: runs before Leaflet's popup handlers
    return () => document.removeEventListener('click', onClick, true);
  });

  // Approve / Reject a collaboration proposal
  const handleRespondProposal = async (proposalId, action) => {
    try {
      await api.post(`/collaborations/proposals/${proposalId}/respond?action=${action}`);
      await loadData();
      setCollabNotice(
        action === 'APPROVE'
          ? 'Collaboration proposal approved! Joint bundle is now active.'
          : 'Proposal rejected.'
      );
      setTimeout(() => setCollabNotice(''), 6000);
    } catch (err) {
      console.error('Failed to update proposal response:', err);
      alert(err.response?.data?.detail || 'Failed to update proposal response.');
    }
  };

  const handleResetEntireData = async () => {
    setResetting(true);
    try {
      const res = await api.post('/seed/reset');
      setShowResetModal(false);
      setCollabData(null);
      setResetSuccessNotice('Entire database successfully reset to default demo records with full coordinates and baseline catalogs!');
      setTimeout(() => setResetSuccessNotice(''), 6000);
      await loadData();
    } catch (err) {
      console.error('Database reset failed:', err);
      alert('Failed to reset database. Please ensure backend is running.');
    } finally {
      setResetting(false);
    }
  };

  const currLat = merchant?.latitude || summary?.current_coordinates?.lat || 12.920737;
  const currLng = merchant?.longitude || summary?.current_coordinates?.lng || 77.668710;

  return (
    <AppLayout
      title="Local Map & Community Events"
      subtitle="Geographical merchant clusters, proximity radar, demand events, and joint bundle collaborations"
    >
      {/* Top Banner and Quick Reset Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-stone-200/90 bg-white text-stone-700 text-xs font-semibold shadow-2xs">
            <Compass className="w-3.5 h-3.5 text-[#16181a]" />
            <span>Local Retail Cluster ({currLat.toFixed(4)}° N, {currLng.toFixed(4)}° E)</span>
          </div>
          {summary?.events_source && (
            <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-stone-200/90 bg-[#f7f8f4] text-stone-800 text-xs font-bold shadow-2xs">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              <span>{summary.events_source}</span>
            </div>
          )}
        </div>

        {/* Global Reset Entire Data Button */}
        <button
          onClick={() => setShowResetModal(true)}
          className="px-4 py-2 rounded-full bg-white hover:bg-stone-50 border border-stone-200/90 text-stone-800 text-xs font-bold flex items-center gap-2 shadow-2xs transition-all cursor-pointer hover:border-stone-400 self-start sm:self-auto"
          title="Reset all store records, inventory, sales, and events back to fresh demo defaults"
        >
          <RefreshCw className="w-3.5 h-3.5 text-stone-600" />
          <span>Reset Entire Data</span>
        </button>
      </div>

      {collabNotice && (
        <div className="p-3.5 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center gap-2.5 animate-in fade-in shadow-2xs font-medium">
          <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
          <span>{collabNotice}</span>
        </div>
      )}

      {/* Success Notification Banner */}
      {resetSuccessNotice && (
        <div className="p-3.5 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center gap-2.5 animate-in fade-in shadow-2xs font-medium">
          <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
          <span>{resetSuccessNotice}</span>
        </div>
      )}

      {/* Hero Metric Cards (Dribbble 3-card layout) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: My Shop Geolocation */}
        <div className="bg-white rounded-[28px] border border-stone-200/90 p-5 shadow-[0_4px_24px_rgba(20,24,20,0.04)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] uppercase font-bold text-stone-500 tracking-wider">
                Store Geolocation
              </span>
              <span className="w-2.5 h-2.5 rounded-full bg-[#e0fd53] border border-[#16181a]" />
            </div>
            <h3 className="text-base font-extrabold text-[#16181a] tracking-tight">
              {merchant?.business_name || 'My Store'}
            </h3>
            <p className="text-xs text-stone-500 font-medium mt-1 leading-relaxed">
              {merchant?.address || 'Indiranagar, Bengaluru'}
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-stone-100 flex items-center justify-between text-xs font-mono font-bold text-stone-700">
            <span>Coordinates:</span>
            <span className="text-[#16181a] bg-[#f7f8f4] px-2.5 py-1 rounded-full border border-stone-200/80">
              {currLat.toFixed(4)}°, {currLng.toFixed(4)}°
            </span>
          </div>
        </div>

        {/* Card 2: Neighboring Merchants Network */}
        <div className="bg-white rounded-[28px] border border-stone-200/90 p-5 shadow-[0_4px_24px_rgba(20,24,20,0.04)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] uppercase font-bold text-stone-500 tracking-wider">
                Neighborhood Cluster
              </span>
              <span className="px-2 py-0.5 rounded-full bg-[#f7f8f4] border border-stone-200/90 text-[10px] font-bold text-stone-700">
                1.5km Radius
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-black text-[#16181a] tracking-tight">
                {nearbyMerchants.length}
              </span>
              <span className="text-xs font-semibold text-stone-500">Adjacent Merchants</span>
            </div>
            <p className="text-xs text-stone-500 mt-1">
              Nearest Partner: <strong className="text-stone-800">{summary?.nearest_partner_name || 'Nearby Store'}</strong>
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-stone-100 flex items-center justify-between text-xs text-stone-700 font-medium">
            <span>Proximity Range:</span>
            <span className="font-bold text-[#16181a]">
              {summary?.nearest_partner_distance_km ? `${Math.round(summary.nearest_partner_distance_km * 1000)}m` : '200m'} - 1.1 km
            </span>
          </div>
        </div>

        {/* Card 3: Demand Pipeline Events */}
        <div className="bg-[#16181a] text-white rounded-[28px] p-5 shadow-[0_4px_24px_rgba(0,0,0,0.12)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] uppercase font-bold text-stone-400 tracking-wider">
                Demand Catalysts
              </span>
              <span className="px-2 py-0.5 rounded-full bg-[#e0fd53] text-[#16181a] text-[10px] font-black">
                {events.length} ACTIVE
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-black text-[#e0fd53] tracking-tight">
                +180%
              </span>
              <span className="text-xs font-semibold text-stone-300">Peak Demand Surge</span>
            </div>
            <p className="text-xs text-stone-300 mt-1">
              Google Calendar: Festivals, gazetted holidays & cultural observances in India
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-stone-800 flex items-center justify-between text-xs text-stone-400 font-medium">
            <span>Occasion Demand:</span>
            <span className="font-bold text-[#e0fd53]">Sweets, Gifting & Staples</span>
          </div>
        </div>
      </div>

      {/* Main Grid: Interactive Map (Left/Top) + Retail Calendar (Right/Bottom) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Column: Interactive Map & Nearby Merchant Cards (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          {/* Map Container */}
          <div className="bg-white rounded-[28px] border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)] p-4 md:p-5">
            <div className="flex items-center justify-between mb-3 px-1">
              <div>
                <h3 className="text-base font-extrabold text-[#16181a] tracking-tight flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-[#16181a]" />
                  <span>Interactive Store Map</span>
                </h3>
                <p className="text-[11px] text-stone-500 font-medium">
                  Live merchant shop pins & neighborhood partner network
                </p>
              </div>
            </div>

            <div className="h-[460px] w-full">
              <NeighborhoodMap
                currentMerchant={merchant}
                nearbyMerchants={nearbyMerchants}
                selectedMerchantId={selectedMerchantId}
                onSelectMerchant={(id) => setSelectedMerchantId(id)}
              />
            </div>
          </div>

          {/* Nearby Merchant Directory + Bundle Proposals (tabbed) */}
          <div className="bg-white rounded-[28px] border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)] p-5 md:p-6 space-y-4">
            {/* Tab Header */}
            <div className="flex items-center justify-between pb-3 border-b border-stone-100">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveDirectoryTab('stores')}
                  className={`px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                    activeDirectoryTab === 'stores'
                      ? 'bg-[#16181a] text-white shadow-xs font-bold'
                      : 'bg-white hover:bg-stone-50 text-stone-700 border border-stone-200/90 shadow-2xs'
                  }`}
                >
                  Nearby Stores ({nearbyMerchants.length})
                </button>
                <button
                  onClick={() => setActiveDirectoryTab('proposals')}
                  className={`px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${
                    activeDirectoryTab === 'proposals'
                      ? 'bg-[#16181a] text-white shadow-xs font-bold'
                      : 'bg-white hover:bg-stone-50 text-stone-700 border border-stone-200/90 shadow-2xs'
                  }`}
                >
                  <span>Bundle Proposals ({proposals.length})</span>
                  {proposals.some(
                    (p) =>
                      p.status === 'PENDING_APPROVAL' &&
                      ((p.partner_merchant_id === merchant?.merchant_id && !p.partner_approved) ||
                        (p.initiator_merchant_id === merchant?.merchant_id && !p.initiator_approved))
                  ) && (
                    <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" />
                  )}
                </button>
              </div>
              {activeDirectoryTab === 'stores' && (
                <span className="text-xs font-mono font-bold text-stone-400">
                  by walking distance
                </span>
              )}
              {activeDirectoryTab === 'proposals' && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-stone-200/90 bg-[#f7f8f4] text-[10px] font-bold text-stone-600">
                  <ShieldCheck className="w-3 h-3 text-[#16181a]" />
                  <span>12% Min Margin</span>
                </div>
              )}
            </div>

            {/* ── Tab: Nearby Stores ── */}
            {activeDirectoryTab === 'stores' && (
              <div className="space-y-3">
                {nearbyMerchants.map((m) => {
                  const isSelected = selectedMerchantId === m.merchant_id;
                  const distLabel = m.distance_meters ? `${m.distance_meters}m` : `${m.distance_km}km`;

                  return (
                    <div
                      key={m.merchant_id}
                      onClick={() => setSelectedMerchantId(m.merchant_id)}
                      className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                        isSelected
                          ? 'bg-[#16181a] text-white border-stone-800 shadow-md ring-2 ring-[#e0fd53]/40'
                          : 'bg-white hover:bg-[#fafaf7] border-stone-200/90 text-stone-800 shadow-2xs'
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                              isSelected
                                ? 'bg-stone-800 text-[#e0fd53] border border-stone-700'
                                : 'bg-[#f7f8f4] text-stone-700 border border-stone-200/90'
                            }`}
                          >
                            {m.category}
                          </span>
                          <span
                            className={`text-xs font-mono font-bold ${
                              isSelected ? 'text-[#e0fd53]' : 'text-stone-500'
                            }`}
                          >
                            {distLabel} away
                          </span>
                        </div>

                        <h4
                          className={`text-sm font-extrabold tracking-tight ${
                            isSelected ? 'text-white' : 'text-[#16181a]'
                          }`}
                        >
                          {m.business_name}
                        </h4>

                        <p
                          className={`text-xs leading-relaxed ${
                            isSelected ? 'text-stone-300' : 'text-stone-500'
                          }`}
                        >
                          {m.address}
                        </p>

                        {m.synergy_score && m.has_bundle && (
                          <div className="pt-1 flex items-center gap-1.5 text-[11px] font-medium">
                            <Sparkles
                              className={`w-3 h-3 ${
                                isSelected ? 'text-[#e0fd53]' : 'text-stone-700'
                              }`}
                            />
                            <span className={isSelected ? 'text-stone-200' : 'text-stone-700'}>
                              <strong>{m.synergy_score}% Synergy:</strong> {m.synergy_type}
                            </span>
                          </div>
                        )}
                        {m.has_bundle && m.synergy_rationale && (
                          <p className={`text-[11px] leading-snug ${isSelected ? 'text-stone-300' : 'text-stone-500'}`}>
                            {m.synergy_rationale}
                          </p>
                        )}
                        {!m.has_bundle && (
                          <p className={`text-[11px] leading-snug text-stone-400`}>
                            No natural product pairing with your shop right now.
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            openCollab(m.merchant_id);
                          }}
                          disabled={collabLoadingId === m.merchant_id}
                          title={m.has_bundle ? 'Open the suggested bundle (you review it before sending)' : 'Build a bundle with this shop'}
                          className={`px-3.5 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 shadow-2xs cursor-pointer disabled:opacity-60 ${
                            isSelected
                              ? 'bg-[#e0fd53] text-[#16181a] hover:bg-[#d6f447]'
                              : 'bg-[#16181a] text-white hover:bg-stone-800'
                          }`}
                        >
                          <span>
                            {collabLoadingId === m.merchant_id ? 'Opening…' : m.has_bundle ? 'Review Bundle' : 'Collaborate'}
                          </span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* ── Tab: Bundle Proposals ── */}
            {activeDirectoryTab === 'proposals' && (
              <div className="space-y-3">
                {proposals.length === 0 ? (
                  <div className="p-8 text-center bg-[#f7f8f4] rounded-2xl border border-dashed border-stone-200">
                    <Handshake className="w-8 h-8 text-stone-400 mx-auto mb-2" />
                    <p className="text-xs font-bold text-[#16181a]">No Proposals Yet</p>
                    <p className="text-[11px] text-stone-500 mt-0.5">
                      Switch to Nearby Stores and click "Collaborate" to propose your first joint bundle.
                    </p>
                  </div>
                ) : (
                  proposals.map((prop) => {
                    const isInitiator = prop.initiator_merchant_id === merchant?.merchant_id;
                    const isPartner = prop.partner_merchant_id === merchant?.merchant_id;
                    const canRespond =
                      prop.status === 'PENDING_APPROVAL' &&
                      ((isPartner && !prop.partner_approved) ||
                        (isInitiator && !prop.initiator_approved));

                    return (
                      <div
                        key={prop.proposal_id}
                        className="p-5 rounded-2xl border border-stone-200/90 hover:border-stone-300 transition-colors bg-[#fbfbf9] space-y-3"
                      >
                        {/* Title row */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
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
                                {prop.status.replace('_', ' ')}
                              </Badge>
                            </div>
                            <p className="text-xs text-stone-500 mt-0.5">{prop.bundle_description}</p>
                          </div>
                          <div className="text-right shrink-0">
                            <p className="text-xs text-stone-400 line-through">₹{prop.original_bundle_price}</p>
                            <p className="text-base font-black text-[#16181a]">₹{prop.discounted_bundle_price}</p>
                          </div>
                        </div>

                        {/* Participant margin cards */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-stone-200/60 text-xs">
                          <div className="p-3 rounded-xl bg-white border border-stone-200/80 flex items-center justify-between">
                            <div>
                              <p className="font-bold text-[#16181a]">{prop.initiator_merchant_name}</p>
                              <p className="text-[11px] text-stone-500">{prop.initiator_product_name} (-{prop.initiator_discount_pct}%)</p>
                              <p className="text-[10px] text-emerald-700 font-bold mt-0.5">Margin: {prop.initiator_margin_pct}%</p>
                            </div>
                            <Badge variant={prop.initiator_approved ? 'success' : 'warning'} size="sm">
                              {prop.initiator_approved ? 'Approved' : 'Pending'}
                            </Badge>
                          </div>
                          <div className="p-3 rounded-xl bg-white border border-stone-200/80 flex items-center justify-between">
                            <div>
                              <p className="font-bold text-[#16181a]">{prop.partner_merchant_name}</p>
                              <p className="text-[11px] text-stone-500">{prop.partner_product_name} (-{prop.partner_discount_pct}%)</p>
                              <p className="text-[10px] text-emerald-700 font-bold mt-0.5">Margin: {prop.partner_margin_pct}%</p>
                            </div>
                            <Badge variant={prop.partner_approved ? 'success' : 'warning'} size="sm">
                              {prop.partner_approved ? 'Approved' : 'Awaiting'}
                            </Badge>
                          </div>
                        </div>

                        {/* Action buttons */}
                        {canRespond && (
                          <div className="pt-2 flex items-center justify-between bg-white p-3 rounded-xl border border-stone-200">
                            <span className="text-[11px] font-semibold text-stone-700">
                              {isPartner ? 'You are the invited partner.' : 'Your confirmation requested.'}
                            </span>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleRespondProposal(prop.proposal_id, 'REJECT')}
                                className="px-3.5 py-1.5 rounded-full border border-stone-200 text-stone-700 hover:bg-stone-50 text-xs font-semibold cursor-pointer"
                              >
                                Reject
                              </button>
                              <button
                                onClick={() => handleRespondProposal(prop.proposal_id, 'APPROVE')}
                                className="px-4 py-1.5 rounded-full bg-[#16181a] hover:bg-stone-800 text-white text-xs font-bold flex items-center gap-1.5 shadow-2xs cursor-pointer"
                              >
                                <CheckCircle2 className="w-3.5 h-3.5 text-[#e0fd53]" />
                                <span>Approve</span>
                              </button>
                            </div>
                          </div>
                        )}
                        {!canRespond && prop.status === 'PENDING_APPROVAL' && (
                          <div className="text-[11px] text-stone-400 bg-white px-3 py-2 rounded-xl border border-stone-200/80">
                            Awaiting partner confirmation. Switch merchant accounts in the header to test approving.
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Interactive Demand Calendar (5 cols) */}
        <div className="lg:col-span-5">
          <NeighborhoodCalendar
            events={events}
            selectedEventId={selectedEventId}
            onSelectEvent={(id) => {
              setSelectedEventId((prev) => (prev === id ? null : id));
            }}
            onPlanEvent={(ev) => setPlanEvent(ev)}
          />
        </div>
      </div>

      {/* Action plan for a clicked occasion (drafts are applied only on confirm) */}
      <EventActionPlan event={planEvent} onClose={() => setPlanEvent(null)} onIdea={openCollab} />

      {/* Joint-bundle popup: opens on this page, nothing is sent until "Submit" */}
      <ProposalModal
        partner={collabPartner}
        myProducts={collabData?.myProducts || []}
        merchant={merchant}
        source="Local Map"
        onClose={() => setCollabPartner(null)}
        onSubmitted={(p) => {
          setCollabPartner(null);
          setCollabNotice(`Bundle proposal sent to ${p.business_name}. They'll see it in Bundle Proposals and can accept or decline.`);
          setTimeout(() => setCollabNotice(''), 7000);
          loadData(); // refresh proposals list
          setActiveDirectoryTab('proposals'); // jump to proposals tab
        }}
      />

      {/* Reset Entire Database Modal */}
      <Modal
        isOpen={showResetModal}
        onClose={() => !resetting && setShowResetModal(false)}
        title="Reset Entire Database to Defaults?"
        size="md"
      >
        <div className="space-y-4">
          <div className="p-4 rounded-2xl bg-[#fbe8e4] border border-[#f3c5bd] text-xs text-[#a43b27] flex items-start gap-2.5">
            <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5 text-[#a43b27]" />
            <div className="leading-relaxed">
              <strong className="font-bold">Administrative Environment Reset:</strong>
              <p className="mt-1">
                This will reset MongoDB collections across all 6 Indiranagar demo merchants, realign all exact shop coordinates, restore 90-day transaction histories, reset product stock levels to baseline thresholds, and regenerate fresh community calendar events.
              </p>
            </div>
          </div>

          <div className="space-y-2 text-xs text-stone-600 bg-[#f7f8f4] p-3.5 rounded-2xl border border-stone-200/90 font-medium">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#16181a]" />
              <span>Restores 6 merchants with exact coordinates ({currLat.toFixed(4)}° N, {currLng.toFixed(4)}° E)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#16181a]" />
              <span>Re-seeds 19 products, 1,700+ transactions & 7 retail demand events</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#16181a]" />
              <span>Clears transient copilot conversation logs</span>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-stone-100">
            <button
              type="button"
              onClick={() => setShowResetModal(false)}
              disabled={resetting}
              className="px-4 py-2 rounded-full border border-stone-200/90 text-stone-700 hover:bg-stone-50 font-bold text-xs transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleResetEntireData}
              disabled={resetting}
              className="px-5 py-2 rounded-full bg-[#c25e4e] hover:bg-[#a43b27] text-white font-bold text-xs flex items-center gap-2 shadow-xs transition-all cursor-pointer disabled:opacity-50"
            >
              {resetting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
                  <span>Re-seeding Database...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="w-3.5 h-3.5 text-white" />
                  <span>Confirm Reset</span>
                </>
              )}
            </button>
          </div>
        </div>
      </Modal>
    </AppLayout>
  );
}
