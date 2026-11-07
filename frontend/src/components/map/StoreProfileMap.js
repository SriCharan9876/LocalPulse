'use client';

import React, { useEffect, useRef, useState } from 'react';
import 'leaflet/dist/leaflet.css';

export default function StoreProfileMap({
  latitude,
  longitude,
  businessName = 'My Store',
  category = 'Retail',
  address = '',
  onLocationChange = null,
  interactive = true,
  isEditingLocation = false,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);
  const [mapReady, setMapReady] = useState(false);
  const isEditingLocationRef = useRef(isEditingLocation);

  useEffect(() => {
    isEditingLocationRef.current = isEditingLocation;
  }, [isEditingLocation]);

  const lat = Number(latitude) || 12.920737;
  const lng = Number(longitude) || 77.668710;

  // Initialize Map
  useEffect(() => {
    let isMounted = true;

    async function initMap() {
      if (!mapContainerRef.current) return;
      if (mapInstanceRef.current) return;

      const L = (await import('leaflet')).default;
      if (!isMounted || !mapContainerRef.current) return;

      const map = L.map(mapContainerRef.current, {
        center: [lat, lng],
        zoom: 16,
        zoomControl: false,
      });

      // Free OpenStreetMap Tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      L.control.zoom({ position: 'bottomright' }).addTo(map);

      // Create Custom Branded Pin Marker
      const customIcon = L.divIcon({
        className: 'store-profile-map-marker',
        html: `
          <div class="relative flex items-center justify-center">
            <div class="absolute w-12 h-12 rounded-full bg-[#16181a]/20 animate-ping"></div>
            <div class="relative w-10 h-10 rounded-full bg-[#16181a] border-2 border-[#e0fd53] shadow-xl flex items-center justify-center text-white">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#e0fd53" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            </div>
            <div class="absolute -bottom-6 bg-[#16181a] text-[#e0fd53] font-black text-[9px] px-2.5 py-0.5 rounded-full border border-stone-800 shadow-md whitespace-nowrap">
              STORE LOCATION
            </div>
          </div>
        `,
        iconSize: [42, 42],
        iconAnchor: [21, 21],
        popupAnchor: [0, -24],
      });

      const marker = L.marker([lat, lng], {
        icon: customIcon,
        draggable: Boolean(interactive && onLocationChange && isEditingLocationRef.current),
      }).addTo(map);

      marker.bindPopup(`
        <div style="font-family: inherit; min-width: 190px; padding: 4px;">
          <div style="margin-bottom: 4px;">
            <span style="background: #16181a; color: #e0fd53; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 9999px;">STOREFRONT PIN</span>
          </div>
          <h4 style="font-size: 13px; font-weight: 800; color: #16181a; margin: 0 0 2px 0;">${businessName}</h4>
          <p style="font-size: 11px; color: #666; margin: 0 0 4px 0;">${category}</p>
          ${address ? `<p style="font-size: 10px; color: #555; margin: 0 0 6px 0;">${address}</p>` : ''}
          <div style="font-size: 10px; color: #888; border-top: 1px solid #eee; padding-top: 4px;">
            GPS: ${lat.toFixed(6)}° N, ${lng.toFixed(6)}° E
          </div>
        </div>
      `);

      if (onLocationChange && interactive) {
        marker.on('dragend', function (e) {
          if (!isEditingLocationRef.current) return;
          const newPos = e.target.getLatLng();
          onLocationChange(Number(newPos.lat.toFixed(6)), Number(newPos.lng.toFixed(6)));
        });

        map.on('click', function (e) {
          if (!isEditingLocationRef.current) return;
          const clickedLat = Number(e.latlng.lat.toFixed(6));
          const clickedLng = Number(e.latlng.lng.toFixed(6));
          marker.setLatLng([clickedLat, clickedLng]);
          onLocationChange(clickedLat, clickedLng);
        });
      }

      markerRef.current = marker;
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

  // Sync marker draggable capability when isEditingLocation changes
  useEffect(() => {
    if (!markerRef.current) return;
    if (interactive && onLocationChange && isEditingLocation) {
      markerRef.current.dragging?.enable();
    } else if (markerRef.current.dragging) {
      markerRef.current.dragging?.disable();
    }
  }, [isEditingLocation, interactive, onLocationChange, mapReady]);

  // Update marker position if coordinates change externally
  useEffect(() => {
    if (!mapReady || !mapInstanceRef.current || !markerRef.current) return;
    markerRef.current.setLatLng([lat, lng]);
    mapInstanceRef.current.setView([lat, lng], mapInstanceRef.current.getZoom());
  }, [lat, lng, mapReady]);

  return (
    <div className="relative w-full h-full min-h-[320px] rounded-2xl overflow-hidden border border-stone-200">
      <div ref={mapContainerRef} className="w-full h-full min-h-[320px]" />
      {interactive && onLocationChange && (
        <div
          className={`absolute top-3 left-3 z-[1000] px-3 py-1.5 rounded-xl border text-[11px] font-semibold shadow-sm flex items-center gap-2 transition-all ${isEditingLocation
              ? 'bg-[#16181a] text-[#e0fd53] border-stone-800'
              : 'bg-white/95 backdrop-blur-xs text-stone-700 border-stone-200'
            }`}
        >
          <span
            className={`w-2 h-2 rounded-full ${isEditingLocation ? 'bg-[#e0fd53] animate-ping' : 'bg-stone-400'
              }`}
          />
          <span>
            {isEditingLocation
              ? 'Dragging Enabled: Drag pin or click map to reposition'
              : 'Location Locked: Click "Edit Location" to adjust'}
          </span>
        </div>
      )}
    </div>
  );
}
