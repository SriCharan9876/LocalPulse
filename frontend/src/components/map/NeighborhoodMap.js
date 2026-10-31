'use client';

import React, { useEffect, useRef, useState } from 'react';
import 'leaflet/dist/leaflet.css';
import {
  Navigation,
  Store,
  Calendar,
  Layers,
  MapPin,
  ExternalLink,
  Phone,
  Sparkles,
  Maximize2
} from 'lucide-react';

export default function NeighborhoodMap({
  currentMerchant,
  nearbyMerchants = [],
  events = [],
  selectedMerchantId = null,
  onSelectMerchant = null,
  selectedEventId = null,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({});
  const [filterType, setFilterType] = useState('all'); // all, merchants, events
  const [mapReady, setMapReady] = useState(false);

  // Initialize Leaflet Map
  useEffect(() => {
    let isMounted = true;

    async function initMap() {
      if (!mapContainerRef.current) return;
      if (mapInstanceRef.current) return;

      const L = (await import('leaflet')).default;

      if (!isMounted || !mapContainerRef.current) return;

      const centerLat = currentMerchant?.latitude || currentMerchant?.coordinates?.lat || 12.9716;
      const centerLng = currentMerchant?.longitude || currentMerchant?.coordinates?.lng || 77.6412;

      const map = L.map(mapContainerRef.current, {
        center: [centerLat, centerLng],
        zoom: 15,
        zoomControl: false,
      });

      // Sleek, clean OpenStreetMap tiles
      L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19,
      }).addTo(map);

      // Custom Zoom Control at bottom right
      L.control.zoom({ position: 'bottomright' }).addTo(map);

      mapInstanceRef.current = map;
      setMapReady(true);
    }

    initMap();

    return () => {
      isMounted = false;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update Markers when map is ready or data / filter changes
  useEffect(() => {
    if (!mapReady || !mapInstanceRef.current) return;

    let isMounted = true;

    async function updateMarkers() {
      const L = (await import('leaflet')).default;
      if (!isMounted || !mapInstanceRef.current) return;

      const map = mapInstanceRef.current;

      // Clear existing markers
      Object.values(markersRef.current).forEach((marker) => {
        map.removeLayer(marker);
      });
      markersRef.current = {};

      const currLat = currentMerchant?.latitude || currentMerchant?.coordinates?.lat || 12.9716;
      const currLng = currentMerchant?.longitude || currentMerchant?.coordinates?.lng || 77.6412;

      // 1. Current Merchant Marker (Prominent Dark Charcoal with Pulse Ring)
      const currentIcon = L.divIcon({
        className: 'custom-map-marker',
        html: `
          <div class="relative flex items-center justify-center">
            <div class="absolute w-10 h-10 rounded-full bg-[#16181a]/15 animate-ping"></div>
            <div class="relative w-8 h-8 rounded-full bg-[#16181a] border-2 border-[#e0fd53] shadow-lg flex items-center justify-center text-white">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#e0fd53" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            </div>
            <div class="absolute -bottom-5 bg-[#16181a] text-[#e0fd53] font-black text-[9px] px-2 py-0.5 rounded-full border border-stone-800 shadow-md whitespace-nowrap">
              YOUR STORE
            </div>
          </div>
        `,
        iconSize: [36, 36],
        iconAnchor: [18, 18],
        popupAnchor: [0, -22],
      });

      const currentMarker = L.marker([currLat, currLng], { icon: currentIcon }).addTo(map);
      currentMarker.bindPopup(`
        <div style="font-family: inherit; min-width: 180px; padding: 4px;">
          <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
            <span style="background: #16181a; color: #e0fd53; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 9999px;">CURRENT CONTEXT</span>
          </div>
          <h4 style="font-size: 13px; font-weight: 800; color: #16181a; margin: 0 0 2px 0;">${currentMerchant?.business_name || 'My Shop'}</h4>
          <p style="font-size: 11px; color: #666; margin: 0 0 6px 0;">${currentMerchant?.category || 'Retail Store'}</p>
          <div style="font-size: 10px; color: #888; border-top: 1px solid #eee; padding-top: 6px;">
            Coordinates: ${currLat.toFixed(4)}° N, ${currLng.toFixed(4)}° E
          </div>
        </div>
      `);
      markersRef.current['current'] = currentMarker;

      // 2. Neighboring Merchant Markers
      if (filterType === 'all' || filterType === 'merchants') {
        nearbyMerchants.forEach((m) => {
          const lat = m.latitude || m.coordinates?.lat;
          const lng = m.longitude || m.coordinates?.lng;
          if (!lat || !lng) return;

          const isSelected = selectedMerchantId === m.merchant_id;
          const distLabel = m.distance_meters ? `${m.distance_meters}m` : `${m.distance_km}km`;

          const neighborIcon = L.divIcon({
            className: 'custom-map-marker',
            html: `
              <div class="relative flex flex-col items-center">
                <div class="w-7 h-7 rounded-full ${isSelected ? 'bg-[#e0fd53] text-[#16181a] ring-4 ring-[#16181a]/20 scale-125' : 'bg-white text-[#16181a]'} border-2 border-[#16181a] shadow-md flex items-center justify-center transition-transform">
                  <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m2 7 4.41-4.41A2 2 0 0 1 7.83 2h8.34a2 2 0 0 1 1.42.59L22 7"/><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="M15 22v-4a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4"/><path d="M2 7h20"/></svg>
                </div>
                <div class="bg-white text-stone-800 font-bold text-[8.5px] px-1.5 py-0.2 rounded-full border border-stone-300 shadow-xs whitespace-nowrap mt-0.5">
                  ${distLabel}
                </div>
              </div>
            `,
            iconSize: [32, 36],
            iconAnchor: [16, 18],
            popupAnchor: [0, -20],
          });

          const marker = L.marker([lat, lng], { icon: neighborIcon }).addTo(map);

          marker.bindPopup(`
            <div style="font-family: inherit; min-width: 200px; padding: 4px;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                <span style="background: #f4f4f0; color: #444; font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 9999px;">${m.category}</span>
                <span style="font-size: 10px; font-weight: 800; color: #16181a;">${distLabel} away</span>
              </div>
              <h4 style="font-size: 13px; font-weight: 800; color: #16181a; margin: 0 0 2px 0;">${m.business_name}</h4>
              <p style="font-size: 10.5px; color: #666; margin: 0 0 6px 0;">${m.address}</p>
              ${m.synergy_score ? `
                <div style="background: #f7f9f2; border: 1px solid #e2e8d8; padding: 4px 6px; border-radius: 8px; margin-bottom: 6px; font-size: 10px; color: #333;">
                  <strong>${m.synergy_score}% Synergy:</strong> ${m.synergy_type || 'Neighborhood Partner'}
                </div>
              ` : ''}
              <div style="display: flex; gap: 6px; margin-top: 6px;">
                <a href="/collaborations" style="display: inline-block; background: #16181a; color: #fff; text-decoration: none; font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 9999px;">Propose Bundle</a>
              </div>
            </div>
          `);

          marker.on('click', () => {
            if (onSelectMerchant) onSelectMerchant(m.merchant_id);
          });

          markersRef.current[`merchant-${m.merchant_id}`] = marker;
        });
      }

      // 3. Community Event Markers
      if (filterType === 'all' || filterType === 'events') {
        events.forEach((ev) => {
          const lat = ev.coordinates?.lat;
          const lng = ev.coordinates?.lng;
          if (!lat || !lng) return;

          const isSelected = selectedEventId === ev.event_id;

          const eventIcon = L.divIcon({
            className: 'custom-map-marker',
            html: `
              <div class="relative flex flex-col items-center">
                <div class="w-7 h-7 rounded-full ${isSelected ? 'bg-[#16181a] text-[#e0fd53] ring-4 ring-[#16181a]/20 scale-125' : 'bg-[#e0fd53] text-[#16181a]'} border-2 border-[#16181a] shadow-md flex items-center justify-center transition-transform">
                  <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/><path d="m9 16 2 2 4-4"/></svg>
                </div>
                <div class="bg-[#16181a] text-[#e0fd53] font-bold text-[8.5px] px-1.5 py-0.2 rounded-full border border-stone-800 shadow-xs whitespace-nowrap mt-0.5">
                  EVENT
                </div>
              </div>
            `,
            iconSize: [32, 36],
            iconAnchor: [16, 18],
            popupAnchor: [0, -20],
          });

          const marker = L.marker([lat, lng], { icon: eventIcon }).addTo(map);

          const impactBadges = (ev.category_impacts || [])
            .map((imp) => `<span style="background: #edece4; padding: 2px 6px; border-radius: 4px; font-size: 9.5px; font-weight: 700; color: #16181a; margin-right: 4px;">${imp.category} +${imp.projected_demand_change_pct}%</span>`)
            .join(' ');

          marker.bindPopup(`
            <div style="font-family: inherit; min-width: 220px; padding: 4px;">
              <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                <span style="background: #e0fd53; color: #16181a; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 9999px;">LOCAL EVENT</span>
                <span style="font-size: 10px; color: #666;">${ev.start_date}</span>
              </div>
              <h4 style="font-size: 13px; font-weight: 800; color: #16181a; margin: 0 0 2px 0;">${ev.title}</h4>
              <p style="font-size: 10.5px; color: #666; margin: 0 0 6px 0;">${ev.location_name}</p>
              <div style="margin-bottom: 6px;">
                ${impactBadges}
              </div>
              <p style="font-size: 10px; color: #444; border-top: 1px solid #eee; padding-top: 4px; margin: 0;">
                ${ev.recommended_action}
              </p>
            </div>
          `);

          markersRef.current[`event-${ev.event_id}`] = marker;
        });
      }
    }

    updateMarkers();

    return () => {
      isMounted = false;
    };
  }, [mapReady, currentMerchant, nearbyMerchants, events, filterType, selectedMerchantId, selectedEventId]);

  // Center on selected merchant
  useEffect(() => {
    if (!mapInstanceRef.current || !selectedMerchantId) return;
    const target = nearbyMerchants.find((m) => m.merchant_id === selectedMerchantId);
    if (target?.latitude && target?.longitude) {
      mapInstanceRef.current.setView([target.latitude, target.longitude], 16, { animate: true });
      const marker = markersRef.current[`merchant-${selectedMerchantId}`];
      if (marker) marker.openPopup();
    }
  }, [selectedMerchantId, nearbyMerchants]);

  // Center on selected event
  useEffect(() => {
    if (!mapInstanceRef.current || !selectedEventId) return;
    const target = events.find((e) => e.event_id === selectedEventId);
    if (target?.coordinates?.lat && target?.coordinates?.lng) {
      mapInstanceRef.current.setView([target.coordinates.lat, target.coordinates.lng], 16, { animate: true });
      const marker = markersRef.current[`event-${selectedEventId}`];
      if (marker) marker.openPopup();
    }
  }, [selectedEventId, events]);

  const handleCenterOnMe = () => {
    if (!mapInstanceRef.current) return;
    const lat = currentMerchant?.latitude || 12.9716;
    const lng = currentMerchant?.longitude || 77.6412;
    mapInstanceRef.current.setView([lat, lng], 15, { animate: true });
    const marker = markersRef.current['current'];
    if (marker) marker.openPopup();
  };

  return (
    <div className="relative w-full h-full min-h-[460px] rounded-[28px] overflow-hidden border border-stone-200/90 shadow-sm bg-stone-100 flex flex-col">
      {/* Floating Map Controls Toolbar */}
      <div className="absolute top-3 left-3 z-[1000] flex flex-wrap items-center gap-1.5 bg-white/95 backdrop-blur-md p-1.5 rounded-2xl border border-stone-200/90 shadow-sm">
        <button
          onClick={() => setFilterType('all')}
          className={`px-3 py-1 rounded-xl text-[11px] font-semibold transition-all cursor-pointer ${
            filterType === 'all'
              ? 'bg-[#16181a] text-white shadow-2xs font-bold'
              : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'
          }`}
        >
          All Pins ({nearbyMerchants.length + events.length})
        </button>
        <button
          onClick={() => setFilterType('merchants')}
          className={`px-3 py-1 rounded-xl text-[11px] font-semibold transition-all cursor-pointer flex items-center gap-1 ${
            filterType === 'merchants'
              ? 'bg-[#16181a] text-white shadow-2xs font-bold'
              : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'
          }`}
        >
          <Store className="w-3 h-3" />
          <span>Merchants ({nearbyMerchants.length})</span>
        </button>
        <button
          onClick={() => setFilterType('events')}
          className={`px-3 py-1 rounded-xl text-[11px] font-semibold transition-all cursor-pointer flex items-center gap-1 ${
            filterType === 'events'
              ? 'bg-[#16181a] text-white shadow-2xs font-bold'
              : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'
          }`}
        >
          <Calendar className="w-3 h-3" />
          <span>Events ({events.length})</span>
        </button>
      </div>

      {/* Recenter My Store Button */}
      <div className="absolute top-3 right-3 z-[1000]">
        <button
          onClick={handleCenterOnMe}
          className="px-3.5 py-1.5 bg-[#16181a] hover:bg-stone-800 text-white rounded-full text-xs font-bold flex items-center gap-1.5 shadow-md transition-all cursor-pointer border border-stone-700"
          title="Recenter map on your shop location"
        >
          <Navigation className="w-3.5 h-3.5 text-[#e0fd53]" />
          <span>Center My Shop</span>
        </button>
      </div>

      {/* Leaflet Map Canvas */}
      <div ref={mapContainerRef} className="w-full flex-1 min-h-[460px] z-0" />
    </div>
  );
}
