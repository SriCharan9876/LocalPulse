'use client';

import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import AppLayout from '@/components/layout/AppLayout';
import Badge from '@/components/ui/Badge';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import {
  Store,
  User,
  Mail,
  Phone,
  MapPin,
  Compass,
  Calendar,
  Save,
  Loader2,
  CheckCircle2,
  Edit3,
  ExternalLink,
  ShieldCheck,
  RefreshCw,
  Navigation,
  Lock,
  Unlock,
} from 'lucide-react';

// Dynamic import for Leaflet map to prevent SSR window reference errors
const StoreProfileMap = dynamic(
  () => import('@/components/map/StoreProfileMap'),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-[360px] rounded-2xl bg-stone-100 border border-stone-200 flex flex-col items-center justify-center gap-2">
        <Loader2 className="w-6 h-6 text-[#16181a] animate-spin" />
        <p className="text-xs font-semibold text-stone-500">Loading spatial map...</p>
      </div>
    ),
  }
);

export default function ProfilePage() {
  const { merchant, updateProfile } = useAuth();

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [geoDetecting, setGeoDetecting] = useState(false);
  const [successNotice, setSuccessNotice] = useState('');
  const [errorNotice, setErrorNotice] = useState('');

  // Editable Form State
  const [formData, setFormData] = useState({
    business_name: '',
    owner_name: '',
    category: '',
    phone: '',
    address: '',
    latitude: 12.920737,
    longitude: 77.668710,
  });

  const [isEditing, setIsEditing] = useState(false);
  const [isEditingLocation, setIsEditingLocation] = useState(false);

  // Fetch full profile from backend
  useEffect(() => {
    async function fetchProfile() {
      try {
        setLoading(true);
        const res = await api.get('/auth/me');
        const data = res.data;
        setProfile(data);
        setFormData({
          business_name: data.business_name || '',
          owner_name: data.owner_name || '',
          category: data.category || 'Retail',
          phone: data.phone || '',
          address: data.address || '',
          latitude: data.latitude ?? 12.920737,
          longitude: data.longitude ?? 77.668710,
        });
      } catch (err) {
        console.error('Failed to load profile:', err);
        setErrorNotice('Failed to fetch merchant profile.');
      } finally {
        setLoading(false);
      }
    }

    fetchProfile();
  }, [merchant?.merchant_id]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleLocationRecalibrated = (newLat, newLng) => {
    setFormData((prev) => ({
      ...prev,
      latitude: newLat,
      longitude: newLng,
    }));
  };

  const handleDetectDeviceLocation = () => {
    if (typeof window === 'undefined' || !navigator.geolocation) {
      alert('Geolocation is not supported by your browser.');
      return;
    }
    setGeoDetecting(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = Number(pos.coords.latitude.toFixed(6));
        const lng = Number(pos.coords.longitude.toFixed(6));
        setFormData((prev) => ({
          ...prev,
          latitude: lat,
          longitude: lng,
        }));
        setGeoDetecting(false);
        setIsEditingLocation(true);
        setSuccessNotice(`GPS position calibrated: [${lat}, ${lng}]. Pin dragging is unlocked if you wish to adjust.`);
      },
      (err) => {
        console.warn('Geolocation error:', err);
        setGeoDetecting(false);
        alert('Could not access device GPS. Click "Edit Location" to enable dragging the map pin manually.');
      },
      { timeout: 8000 }
    );
  };

  const handleSaveProfile = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    setSaving(true);
    setSuccessNotice('');
    setErrorNotice('');

    try {
      const payload = {
        business_name: formData.business_name,
        owner_name: formData.owner_name,
        category: formData.category,
        phone: formData.phone,
        address: formData.address,
        latitude: Number(formData.latitude),
        longitude: Number(formData.longitude),
      };

      const res = await api.put('/auth/me', payload);
      const updated = res.data;
      setProfile(updated);
      updateProfile(updated);
      setSuccessNotice('Store profile and map location updated successfully!');
      setIsEditing(false);
      setIsEditingLocation(false);
    } catch (err) {
      console.error('Failed to update profile:', err);
      setErrorNotice(err.response?.data?.detail || 'Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppLayout
      title="Store Profile & Location"
      subtitle="Manage your store details, contact information, and exact neighborhood storefront coordinates."
    >
      <div className="space-y-6 pb-12">
        {/* Alerts / Toasts */}
        {successNotice && (
          <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center justify-between shadow-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{successNotice}</span>
            </div>
            <button
              onClick={() => setSuccessNotice('')}
              className="text-emerald-700 hover:text-emerald-900 font-bold ml-4 cursor-pointer"
            >
              ✕
            </button>
          </div>
        )}

        {errorNotice && (
          <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold flex items-center justify-between shadow-xs">
            <span>{errorNotice}</span>
            <button onClick={() => setErrorNotice('')} className="text-rose-700 hover:text-rose-900 font-bold ml-4 cursor-pointer">
              ✕
            </button>
          </div>
        )}

        {loading ? (
          <div className="p-16 flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-8 h-8 text-[#16181a] animate-spin" />
            <p className="text-sm font-semibold text-stone-500">Loading merchant profile...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Column: Profile Card & Editable Info */}
            <div className="lg:col-span-5 space-y-6">
              {/* Store Identity Card */}
              <div className="p-6 rounded-[28px] bg-white border border-stone-200/90 shadow-sm space-y-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3.5">
                    <div className="w-12 h-12 rounded-2xl bg-[#16181a] text-[#e0fd53] flex items-center justify-center font-black text-lg shadow-md">
                      <Store className="w-6 h-6" />
                    </div>
                    <div>
                      <h2 className="text-lg font-black text-[#16181a] leading-tight">
                        {profile?.business_name || 'My Local Store'}
                      </h2>
                      <p className="text-xs text-stone-500 font-medium">
                        ID: <code className="bg-stone-100 px-1.5 py-0.5 rounded text-[11px] text-stone-700">{profile?.merchant_id}</code>
                      </p>
                    </div>
                  </div>
                  <Badge variant="primary" size="sm">
                    {profile?.category || 'Retail'}
                  </Badge>
                </div>

                <div className="border-t border-stone-100 pt-4 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-stone-500 font-medium flex items-center gap-2">
                      <User className="w-3.5 h-3.5 text-stone-400" />
                      Proprietor
                    </span>
                    <span className="font-bold text-stone-900">{profile?.owner_name || 'Store Owner'}</span>
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <span className="text-stone-500 font-medium flex items-center gap-2">
                      <Mail className="w-3.5 h-3.5 text-stone-400" />
                      Account Email
                    </span>
                    <span className="font-semibold text-stone-900">{profile?.email || '—'}</span>
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <span className="text-stone-500 font-medium flex items-center gap-2">
                      <Phone className="w-3.5 h-3.5 text-stone-400" />
                      Contact Phone
                    </span>
                    <span className="font-semibold text-stone-900">{profile?.phone || '—'}</span>
                  </div>

                  <div className="flex items-start justify-between text-xs pt-1">
                    <span className="text-stone-500 font-medium flex items-center gap-2 shrink-0">
                      <MapPin className="w-3.5 h-3.5 text-stone-400" />
                      Store Address
                    </span>
                    <span className="font-medium text-stone-800 text-right max-w-[220px]">
                      {profile?.address || 'Indiranagar, Bengaluru'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-xs pt-2 border-t border-stone-100">
                    <span className="text-stone-500 font-medium flex items-center gap-2">
                      <Calendar className="w-3.5 h-3.5 text-stone-400" />
                      Joined Platform
                    </span>
                    <span className="text-stone-600 font-medium">
                      {profile?.created_at ? new Date(profile.created_at).toLocaleDateString() : 'Active Member'}
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => setIsEditing(!isEditing)}
                  className="w-full py-2.5 px-4 rounded-xl border border-stone-200 text-xs font-bold text-stone-800 hover:bg-stone-50 flex items-center justify-center gap-2 transition-colors cursor-pointer"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>{isEditing ? 'Close Editing Form' : 'Edit Store Details'}</span>
                </button>
              </div>

              {/* Edit Details Form */}
              {isEditing && (
                <div className="p-6 rounded-[28px] bg-white border border-stone-200/90 shadow-sm space-y-4">
                  <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                    <h3 className="text-sm font-black text-[#16181a]">Update Information</h3>
                    <span className="text-[10px] text-stone-400 font-medium">Saves to MongoDB</span>
                  </div>

                  <form onSubmit={handleSaveProfile} className="space-y-3.5">
                    <div>
                      <label className="block text-[11px] font-bold text-stone-700 mb-1">Business Name</label>
                      <input
                        type="text"
                        name="business_name"
                        value={formData.business_name}
                        onChange={handleChange}
                        required
                        className="w-full px-3.5 py-2 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a]"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-bold text-stone-700 mb-1">Owner Name</label>
                      <input
                        type="text"
                        name="owner_name"
                        value={formData.owner_name}
                        onChange={handleChange}
                        required
                        className="w-full px-3.5 py-2 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a]"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-bold text-stone-700 mb-1">Trade Category</label>
                      <select
                        name="category"
                        value={formData.category}
                        onChange={handleChange}
                        className="w-full px-3.5 py-2 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a] bg-white"
                      >
                        <option value="Grocery & Daily Essentials">Grocery & Daily Essentials</option>
                        <option value="Cafe & Bakery">Cafe & Bakery</option>
                        <option value="Fresh Fruits & Vegetables">Fresh Fruits & Vegetables</option>
                        <option value="Fashion & Textiles">Fashion & Textiles</option>
                        <option value="Health & Wellness">Health & Wellness</option>
                        <option value="Traditional Sweets & Snacks">Traditional Sweets & Snacks</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-bold text-stone-700 mb-1">Phone</label>
                      <input
                        type="text"
                        name="phone"
                        value={formData.phone}
                        onChange={handleChange}
                        className="w-full px-3.5 py-2 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a]"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-bold text-stone-700 mb-1">Store Address</label>
                      <textarea
                        name="address"
                        rows={2}
                        value={formData.address}
                        onChange={handleChange}
                        className="w-full px-3.5 py-2 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a]"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3 pt-1">
                      <div>
                        <label className="block text-[10px] font-bold text-stone-500 mb-1">Latitude</label>
                        <input
                          type="number"
                          step="0.000001"
                          name="latitude"
                          value={formData.latitude}
                          onChange={handleChange}
                          className="w-full px-2.5 py-1.5 rounded-lg border border-stone-200 text-xs font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-stone-500 mb-1">Longitude</label>
                        <input
                          type="number"
                          step="0.000001"
                          name="longitude"
                          value={formData.longitude}
                          onChange={handleChange}
                          className="w-full px-2.5 py-1.5 rounded-lg border border-stone-200 text-xs font-mono"
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={saving}
                      className="w-full mt-2 py-2.5 px-4 rounded-xl bg-[#16181a] text-[#e0fd53] font-bold text-xs hover:bg-stone-800 flex items-center justify-center gap-2 transition-colors disabled:opacity-50 cursor-pointer"
                    >
                      {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                      <span>Save Changes</span>
                    </button>
                  </form>
                </div>
              )}
            </div>

            {/* Right Column: Spatial Map & Geolocation Recalibration */}
            <div className="lg:col-span-7 space-y-6">
              <div className="p-6 rounded-[28px] bg-white border border-stone-200/90 shadow-sm space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-black text-[#16181a]">Storefront Spatial Location</h3>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-md border flex items-center gap-1 transition-all ${
                          isEditingLocation
                            ? 'bg-amber-50 text-amber-900 border-amber-300'
                            : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                        }`}
                      >
                        {isEditingLocation ? (
                          <>
                            <Unlock className="w-3 h-3 text-amber-600 animate-pulse" />
                            <span>Dragging Unlocked</span>
                          </>
                        ) : (
                          <>
                            <Lock className="w-3 h-3 text-emerald-700" />
                            <span>Pin Locked</span>
                          </>
                        )}
                      </span>
                    </div>
                    <p className="text-xs text-stone-500 font-medium mt-0.5">
                      Your store's physical position is used to compute walking distances and discover nearby collaboration partners.
                    </p>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    {/* Edit Location toggle button */}
                    <button
                      type="button"
                      onClick={() => setIsEditingLocation((prev) => !prev)}
                      className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 cursor-pointer ${
                        isEditingLocation
                          ? 'bg-[#16181a] text-[#e0fd53] hover:bg-stone-800 shadow-xs'
                          : 'bg-white hover:bg-stone-50 text-stone-800 border border-stone-200/90 shadow-2xs'
                      }`}
                      title={isEditingLocation ? 'Lock the pin to prevent accidental movement' : 'Unlock pin to drag or click map to reposition'}
                    >
                      {isEditingLocation ? (
                        <>
                          <Lock className="w-3.5 h-3.5 text-[#e0fd53]" />
                          <span>Lock Location</span>
                        </>
                      ) : (
                        <>
                          <Edit3 className="w-3.5 h-3.5" />
                          <span>Edit Location</span>
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={handleDetectDeviceLocation}
                      disabled={geoDetecting}
                      className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-stone-100 hover:bg-stone-200 text-[#16181a] text-xs font-bold transition-colors shrink-0 cursor-pointer"
                    >
                      {geoDetecting ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Compass className="w-3.5 h-3.5 text-[#16181a]" />
                      )}
                      <span>{geoDetecting ? 'Detecting GPS...' : 'Use My GPS Location'}</span>
                    </button>
                  </div>
                </div>

                {/* Map Display */}
                <div className="h-[400px] w-full">
                  <StoreProfileMap
                    latitude={formData.latitude}
                    longitude={formData.longitude}
                    businessName={formData.business_name}
                    category={formData.category}
                    address={formData.address}
                    onLocationChange={handleLocationRecalibrated}
                    interactive={true}
                    isEditingLocation={isEditingLocation}
                  />
                </div>

                {/* Coordinates & Location Bar */}
                <div className="p-4 rounded-2xl bg-stone-50 border border-stone-200/70 flex flex-col sm:flex-row items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <Navigation className="w-4 h-4 text-[#16181a] shrink-0" />
                    <div>
                      <p className="text-xs font-bold text-[#16181a]">
                        Coordinates: <span className="font-mono text-stone-600">{Number(formData.latitude).toFixed(6)}° N, {Number(formData.longitude).toFixed(6)}° E</span>
                      </p>
                      <p className="text-[11px] text-stone-500 font-medium">
                        {isEditingLocation
                          ? 'Dragging is enabled. Drag the pin or click on the map to set your entrance, then click Save Coordinates.'
                          : 'Pin is locked to prevent accidental dragging. Click "Edit Location" above or below to reposition.'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() => setIsEditingLocation((prev) => !prev)}
                      className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                        isEditingLocation
                          ? 'bg-amber-100 hover:bg-amber-200 text-amber-900 border border-amber-300'
                          : 'bg-white hover:bg-stone-100 text-stone-800 border border-stone-200'
                      }`}
                    >
                      {isEditingLocation ? (
                        <>
                          <Lock className="w-3.5 h-3.5 text-amber-800" />
                          <span>Lock Pin</span>
                        </>
                      ) : (
                        <>
                          <Edit3 className="w-3.5 h-3.5 text-stone-700" />
                          <span>Edit Location</span>
                        </>
                      )}
                    </button>

                    <button
                      onClick={handleSaveProfile}
                      disabled={saving}
                      className="px-4 py-2 rounded-xl bg-[#16181a] text-[#e0fd53] text-xs font-bold hover:bg-stone-800 transition-colors flex items-center gap-2 shrink-0 cursor-pointer"
                    >
                      {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                      <span>Save Coordinates</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
