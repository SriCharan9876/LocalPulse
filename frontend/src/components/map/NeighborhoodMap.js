'use client';

import React, { useEffect, useRef, useState } from 'react';
import 'leaflet/dist/leaflet.css';
import {
  Navigation,
  Store,
  MapPin,
  ExternalLink,
  Phone,
  Sparkles,
} from 'lucide-react';

export default function NeighborhoodMap({
  currentMerchant,
  nearbyMerchants = [],
  selectedMerchantId = null,
  onSelectMerchant = null,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({});
  const [mapReady, setMapReady] = useState(false);

  // Initialize Leaflet Map with Standard OpenStreetMap
  useEffect(() => {
    let isMounted = true;

    async function initMap() {
      if (!mapContainerRef.current) return;
      if (mapInstanceRef.current) return;

      const L = (await import('leaflet')).default;

      if (!isMounted || !mapContainerRef.current) return;

      const centerLat = currentMerchant?.latitude || currentMerchant?.coordinates?.lat || 12.920737;
      const centerLng = currentMerchant?.longitude || currentMerchant?.coordinates?.lng || 77.668710;

      const map = L.map(mapContainerRef.current, {
        center: [centerLat, centerLng],
        zoom: 15,
        zoomControl: false,
      });

      // Standard OpenStreetMap Tile Layer (100% Free, No API Key Required)
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
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

      const currLat = currentMerchant?.latitude || currentMerchant?.coordinates?.lat || 12.920737;
      const currLng = currentMerchant?.longitude || currentMerchant?.coordinates?.lng || 77.668710;

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
              ${m.synergy_score && m.has_bundle ? `
                <div style="background: #f7f9f2; border: 1px solid #e2e8d8; padding: 4px 6px; border-radius: 8px; margin-bottom: 6px; font-size: 10px; color: #333;">
                  <strong>${m.synergy_score}% Synergy:</strong> ${m.synergy_type || 'Neighborhood Partner'}
                </div>
              ` : ''}
              <div style="display: flex; gap: 6px; margin-top: 6px;">
                <a href="/collaborations?partner=${encodeURIComponent(m.merchant_id)}" style="display: inline-block; background: #16181a; color: #fff; text-decoration: none; font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 9999px;">${m.has_bundle ? 'Review Bundle' : 'Propose Bundle'}</a>
              </div>
            </div>
          `);

          marker.on('click', () => {
            if (onSelectMerchant) onSelectMerchant(m.merchant_id);
          });

          markersRef.current[`merchant-${m.merchant_id}`] = marker;
        });

      // Auto-center on merchant if no specific item is currently selected
      if (!selectedMerchantId) {
        map.setView([currLat, currLng], 15, { animate: true });
      }
    }

    updateMarkers();

    return () => {
      isMounted = false;
    };
  }, [mapReady, currentMerchant, nearbyMerchants, selectedMerchantId]);

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

  const handleCenterOnMe = () => {
    if (!mapInstanceRef.current) return;
    const lat = currentMerchant?.latitude || 12.920737;
    const lng = currentMerchant?.longitude || 77.668710;
    mapInstanceRef.current.setView([lat, lng], 15, { animate: true });
    const marker = markersRef.current['current'];
    if (marker) marker.openPopup();
  };

  return (
    <div className="relative w-full h-full min-h-[460px] rounded-[28px] overflow-hidden border border-stone-200/90 shadow-sm bg-stone-100 flex flex-col">
      {/* Floating Store Count Indicator */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2 bg-white/95 backdrop-blur-md px-3.5 py-1.5 rounded-2xl border border-stone-200/90 shadow-sm text-xs font-bold text-[#16181a]">
        <Store className="w-3.5 h-3.5 text-[#16181a]" />
        <span>Merchant Network ({nearbyMerchants.length + 1} Stores)</span>
      </div>

      {/* Recenter My Store Button */}
      <div className="absolute top-3 right-3 z-10">
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
