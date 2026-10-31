'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import {
  Store,
  User,
  Mail,
  Lock,
  MapPin,
  Phone,
  Tag,
  ArrowRight,
  Loader2,
  AlertCircle,
  ShieldCheck,
  Compass,
} from 'lucide-react';
import { LogoMark } from '@/components/ui/Logo';

export default function SignupPage() {
  const { signup } = useAuth();
  const router = useRouter();

  const [formData, setFormData] = useState({
    business_name: '',
    owner_name: '',
    category: 'Grocery & Daily Essentials',
    address: '',
    phone: '',
    email: '',
    password: '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await signup(formData);
      router.push('/dashboard');
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail || 'Failed to create merchant account. Please check inputs.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#edece4] text-[#16181a] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 selection:bg-[#e0fd53] selection:text-[#16181a]">
      {/* Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-lg text-center">
        <Link href="/" className="inline-flex items-center gap-2 mb-3 group">
          <LogoMark size={56} className="shadow-md shadow-stone-900/10 group-hover:scale-105 transition-transform" />
        </Link>
        <h2 className="text-2xl sm:text-3xl font-black text-[#16181a] tracking-tight">
          Register New Merchant
        </h2>
        <p className="mt-1 text-xs sm:text-sm text-stone-500 font-medium">
          Unlock 7-day demand forecasting, Indic voice copilot, and proximity collaboration
        </p>
      </div>

      {/* Main Registration Card */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-xl">
        <div className="bg-white py-8 px-6 shadow-[0_4px_30px_rgba(20,24,20,0.06)] rounded-[32px] border border-stone-200/90 sm:px-10">
          
          {/* Quick Notice about Geolocation Clustering */}
          <div className="mb-6 p-4 rounded-2xl bg-[#f7f8f4] border border-stone-200/80 flex items-start gap-3">
            <div className="w-8 h-8 rounded-xl bg-[#edece4] text-[#16181a] flex items-center justify-center shrink-0 mt-0.5">
              <Compass className="w-4 h-4 text-[#16181a]" />
            </div>
            <div>
              <p className="text-xs font-bold text-[#16181a]">
                Automatic Retail Cluster GPS Pinning
              </p>
              <p className="text-[11px] text-stone-500 mt-0.5 leading-relaxed font-medium">
                Registered stores are assigned real coordinates in the active retail cluster (Bellandur/Sarjapur cluster, Bengaluru) to instantly participate in proximity maps and collaborative co-promotions.
              </p>
            </div>
          </div>

          {error && (
            <div className="mb-5 p-3.5 rounded-2xl bg-[#fbe8e4] border border-[#f3c5bd] flex items-start gap-2.5 text-[#a43b27] text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span className="font-medium">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-stone-700 mb-1">
                  Store / Business Name
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-stone-400">
                    <Store className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    name="business_name"
                    required
                    value={formData.business_name}
                    onChange={handleChange}
                    className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a] shadow-2xs font-medium"
                    placeholder="e.g. Apex Supermarket"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-stone-700 mb-1">
                  Owner / Proprietor Name
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-stone-400">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    name="owner_name"
                    required
                    value={formData.owner_name}
                    onChange={handleChange}
                    className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a] shadow-2xs font-medium"
                    placeholder="e.g. Rahul Verma"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-stone-700 mb-1">
                Store Category
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-stone-400">
                  <Tag className="w-4 h-4" />
                </div>
                <select
                  name="category"
                  value={formData.category}
                  onChange={handleChange}
                  className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a] bg-white shadow-2xs font-medium"
                >
                  <option value="Grocery & Daily Essentials">Grocery & Daily Essentials</option>
                  <option value="Cafe & Bakery">Cafe & Bakery</option>
                  <option value="Fresh Fruits & Vegetables">Fresh Fruits & Vegetables</option>
                  <option value="Fashion & Textiles">Fashion & Textiles</option>
                  <option value="Health & Wellness">Health & Wellness</option>
                  <option value="Traditional Sweets & Snacks">Traditional Sweets & Snacks</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-stone-700 mb-1">
                  Contact Phone Number
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-stone-400">
                    <Phone className="w-4 h-4" />
                  </div>
                  <input
                    type="tel"
                    name="phone"
                    required
                    value={formData.phone}
                    onChange={handleChange}
                    className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a] shadow-2xs font-medium"
                    placeholder="+91 98765 43210"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-stone-700 mb-1">
                  Street Address / Area
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-stone-400">
                    <MapPin className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    name="address"
                    required
                    value={formData.address}
                    onChange={handleChange}
                    className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a] shadow-2xs font-medium"
                    placeholder="12th Main, Sarjapur Rd, Bengaluru"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-stone-700 mb-1">
                Merchant Login Email
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-stone-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  name="email"
                  required
                  value={formData.email}
                  onChange={handleChange}
                  className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a] shadow-2xs font-medium"
                  placeholder="owner@yourstore.in"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-stone-700 mb-1">
                Account Password (min 6 characters)
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-stone-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  name="password"
                  required
                  minLength={6}
                  value={formData.password}
                  onChange={handleChange}
                  className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a] shadow-2xs font-medium"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-4 py-3 px-4 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-sm disabled:opacity-50 cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-[#e0fd53]" />
                  <span>Registering Merchant Store...</span>
                </>
              ) : (
                <>
                  <span>Create Merchant Workspace</span>
                  <ArrowRight className="w-4 h-4 text-[#e0fd53]" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-stone-100 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-stone-500">
            <span>Already have an account?</span>
            <Link href="/login" className="font-extrabold text-[#16181a] hover:underline flex items-center gap-1">
              <span>Sign in to workspace</span>
              <ArrowRight className="w-3.5 h-3.5 text-[#16181a]" />
            </Link>
          </div>
        </div>

        {/* Security and Protocol Assurance */}
        <div className="mt-6 flex items-center justify-center gap-2 text-stone-500 text-[11px] font-medium">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Stateless JWT Auth • Encrypted Passwords • Paytm Build for India Hackathon</span>
        </div>
      </div>
    </div>
  );
}
