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
  Sparkles,
  CheckCircle2,
  Package,
  Layers,
  Check,
} from 'lucide-react';
import { LogoMark } from '@/components/ui/Logo';
import GoogleSignInButton from '@/components/auth/GoogleSignInButton';

// Category-tailored starter inventory previews
const CATEGORY_STARTER_PREVIEWS = {
  'Grocery & Daily Essentials': {
    badge: 'Grocery',
    badgeColor: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    items: [
      { name: 'Aashirvaad Chakki Atta 5kg', price: '₹275', category: 'Flour & Grains', note: '8 packs/day demand' },
      { name: 'Amul Taaza Milk 1L', price: '₹74', category: 'Dairy', note: 'Low-stock trigger (10 left, reorder 20)', isLowStock: true },
      { name: 'Brooke Bond Red Label Tea 500g', price: '₹280', category: 'Tea & Coffee', note: 'Staple inventory' },
      { name: 'Fortune Refined Sunflower Oil 1L', price: '₹165', category: 'Edible Oils', note: 'Cooking oil staple' },
    ],
  },
  'Cafe & Bakery': {
    badge: 'Bakery & Cafe',
    badgeColor: 'bg-amber-50 text-amber-800 border-amber-200',
    items: [
      { name: 'Artisan Country Sourdough Loaf', price: '₹160', category: 'Bakery', note: '10 loaves/day demand' },
      { name: 'Banana Walnut Teacake Slice', price: '₹95', category: 'Bakery', note: 'Low-stock trigger (5 left, reorder 12)', isLowStock: true },
      { name: 'Signature Spiced Chai Blend 250g', price: '₹190', category: 'Beverages', note: 'High-margin beverage' },
      { name: 'Dark Chocolate Cookies Box (6pc)', price: '₹220', category: 'Confectionery', note: 'Combo pairing item' },
    ],
  },
  'Fresh Fruits & Vegetables': {
    badge: 'Fresh Produce',
    badgeColor: 'bg-lime-50 text-lime-900 border-lime-200',
    items: [
      { name: 'Hydroponic Salad Greens 250g', price: '₹120', category: 'Organic Vegetables', note: '11 boxes/day morning demand' },
      { name: 'Fresh Hass Avocados (Twin Pack)', price: '₹240', category: 'Fresh Fruits', note: 'Low-stock trigger (6 left, reorder 12)', isLowStock: true },
      { name: 'Himachal Royal Delicious Apples 1kg', price: '₹190', category: 'Fresh Fruits', note: 'Daily fruit staple' },
      { name: 'Organic Farm Ooty Carrots 1kg', price: '₹75', category: 'Vegetables', note: 'Kitchen vegetable staple' },
    ],
  },
  'Fashion & Textiles': {
    badge: 'Fashion & Apparel',
    badgeColor: 'bg-indigo-50 text-indigo-800 border-indigo-200',
    items: [
      { name: 'Handloom Pure Khadi Cotton Kurta', price: '₹950', category: 'Apparel', note: 'Ethnic festive line' },
      { name: 'Pure Linen Mandarin Collar Shirt', price: '₹1199', category: 'Apparel', note: 'Low-stock trigger (4 left, reorder 10)', isLowStock: true },
      { name: 'Handcrafted Pochampally Ikat Dupatta', price: '₹499', category: 'Apparel', note: 'Artisan handloom' },
      { name: 'Handblock Printed Chanderi Stole', price: '₹450', category: 'Accessories', note: 'High gross margin item' },
    ],
  },
  'Health & Wellness': {
    badge: 'Ayurveda & Health',
    badgeColor: 'bg-teal-50 text-teal-800 border-teal-200',
    items: [
      { name: 'Sanjeevani Pure Amla Chyawanprash 1kg', price: '₹420', category: 'Ayurveda', note: 'Seasonal immunity staple' },
      { name: 'Organic Ashwagandha Root Powder 200g', price: '₹249', category: 'Ayurveda', note: 'Low-stock trigger (5 left, reorder 12)', isLowStock: true },
      { name: 'Cold-Pressed Virgin Coconut Oil 500ml', price: '₹260', category: 'Organic Wellness', note: 'Herbal cold-pressed' },
      { name: 'Tulsi Ginger Herbal Immunity Tea 100g', price: '₹185', category: 'Health Beverages', note: 'Daily wellness drink' },
    ],
  },
  'Traditional Sweets & Snacks': {
    badge: 'Sweets & Snacks',
    badgeColor: 'bg-rose-50 text-rose-800 border-rose-200',
    items: [
      { name: 'Royal Silver Foil Kaju Katli Box 500g', price: '₹550', category: 'Traditional Sweets', note: 'Festival rush favorite' },
      { name: 'Pure Ghee Special Mysore Pak 400g', price: '₹340', category: 'Traditional Sweets', note: 'Low-stock trigger (7 left, reorder 15)', isLowStock: true },
      { name: 'Special Bengaluru Spicy Mixture 250g', price: '₹110', category: 'Savories', note: 'Daily evening snack' },
      { name: 'Roasted Salted Pepper Cashews 200g', price: '₹260', category: 'Savories', note: 'Gift box dry fruit' },
    ],
  },
};

export default function SignupPage() {
  const { signup, loginWithGoogle } = useAuth();
  const router = useRouter();

  const [formData, setFormData] = useState({
    business_name: '',
    owner_name: '',
    category: 'Grocery & Daily Essentials',
    address: 'Bellandur Retail Cluster, Bengaluru',
    phone: '',
    email: '',
    password: '',
    latitude: 12.920737,
    longitude: 77.668710,
  });

  const [googleAuthData, setGoogleAuthData] = useState(null); // { access_token, userInfo }
  const [loading, setLoading] = useState(false);
  const [geoLoading, setGeoLoading] = useState(false);
  const [geoDetected, setGeoDetected] = useState(false);
  const [error, setError] = useState('');

  const currentStarter = CATEGORY_STARTER_PREVIEWS[formData.category] || CATEGORY_STARTER_PREVIEWS['Grocery & Daily Essentials'];

  const handleDetectLocation = () => {
    if (typeof window === 'undefined' || !navigator.geolocation) {
      alert('Geolocation is not supported by your browser.');
      return;
    }
    setGeoLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = Number(pos.coords.latitude.toFixed(6));
        const lng = Number(pos.coords.longitude.toFixed(6));
        setFormData((prev) => ({
          ...prev,
          latitude: lat,
          longitude: lng,
        }));
        setGeoDetected(true);
        setGeoLoading(false);
      },
      (err) => {
        console.warn('Geolocation error:', err);
        setGeoLoading(false);
        alert('Could not access device GPS. Your shop will be assigned a realistic storefront position in the Bengaluru neighborhood cluster automatically.');
      },
      { timeout: 8000 }
    );
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // Called when Google OAuth succeeds
  const handleGoogleAuth = async ({ access_token, userInfo }) => {
    setGoogleAuthData({ access_token, userInfo });
    setError('');

    // Pre-populate verified identity
    setFormData((prev) => ({
      ...prev,
      owner_name: userInfo?.name || prev.owner_name,
      email: userInfo?.email || prev.email,
      business_name: prev.business_name || (userInfo?.name ? `${userInfo.name}'s Store` : ''),
      phone: prev.phone || '+91 98450 00000',
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (googleAuthData?.access_token) {
        // Registering with Google verified token + user-confirmed store details
        await loginWithGoogle({
          access_token: googleAuthData.access_token,
          business_name: formData.business_name,
          category: formData.category,
          address: formData.address,
          phone: formData.phone,
          latitude: formData.latitude,
          longitude: formData.longitude,
        });
        window.location.href = '/dashboard';
      } else {
        // Standard email/password registration
        await signup(formData);
        window.location.href = '/dashboard';
      }
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail || 'Failed to create merchant account. Please check inputs.'
      );
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#edece4] text-[#16181a] flex flex-col justify-center py-10 px-4 sm:px-6 lg:px-8 selection:bg-[#e0fd53] selection:text-[#16181a]">
      {/* Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-2xl text-center">
        <Link href="/" className="inline-flex items-center gap-2 mb-3 group">
          <LogoMark size={56} className="shadow-md shadow-stone-900/10 group-hover:scale-105 transition-transform" />
        </Link>
        <h1 className="text-2xl sm:text-3xl font-black text-[#16181a] tracking-tight">
          Register New Merchant Store
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-stone-600 font-medium">
          Autonomous Merchant Growth AI Platform • Paytm Build for India Hackathon
        </p>
      </div>

      {/* Main Registration Card */}
      <div className="mt-7 sm:mx-auto sm:w-full sm:max-w-2xl">
        <div className="bg-white py-8 px-6 shadow-[0_8px_32px_rgba(20,24,20,0.06)] rounded-[32px] border border-stone-200/90 sm:px-10">
          
          {/* Google Sign Up Button */}
          {!googleAuthData ? (
            <div className="mb-6">
              <GoogleSignInButton
                text="Sign Up with Google"
                onGoogleAuth={handleGoogleAuth}
                onError={(msg) => setError(msg)}
              />
              <div className="relative mt-5">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-stone-200" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-white px-2.5 text-stone-400 font-bold text-[10px] tracking-widest">
                    Or register store details manually
                  </span>
                </div>
              </div>
            </div>
          ) : (
            /* Banner when Google Identity is verified */
            <div className="mb-6 p-4 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold text-emerald-950">
                    Google Account Verified
                  </p>
                  <button
                    type="button"
                    onClick={() => setGoogleAuthData(null)}
                    className="text-[10px] font-bold text-emerald-700 hover:underline"
                  >
                    Change
                  </button>
                </div>
                <p className="text-xs text-emerald-800 font-medium mt-0.5">
                  Signed in as <strong>{googleAuthData.userInfo?.name}</strong> ({googleAuthData.userInfo?.email})
                </p>
                <p className="text-[11px] text-emerald-700 mt-1 leading-relaxed">
                  Please review and confirm your <strong>Store Name, Category, and Location</strong> below to complete your storefront setup.
                </p>
              </div>
            </div>
          )}

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
                  Store / Business Name *
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
                  Owner / Proprietor Name *
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

            {/* Store Category Selection */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-bold text-stone-700">
                  Store Category *
                </label>
                <span className="text-[10px] text-stone-500 font-medium">
                  Pre-populates tailored inventory & 45-day sales telemetry
                </span>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-stone-400">
                  <Tag className="w-4 h-4" />
                </div>
                <select
                  name="category"
                  value={formData.category}
                  onChange={handleChange}
                  className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a] bg-white shadow-2xs font-bold text-[#16181a]"
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

            {/* Dynamic Starter Inventory Preview Box */}
            <div className="p-4 rounded-2xl bg-[#f7f8f4] border border-stone-200/90">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-stone-800" />
                  <span className="text-xs font-black text-[#16181a]">
                    Starter Data Pre-Seeded for {formData.category}
                  </span>
                </div>
                <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full border ${currentStarter.badgeColor}`}>
                  {currentStarter.badge}
                </span>
              </div>
              <p className="text-[11px] text-stone-600 leading-relaxed mb-3">
                Your store will be pre-loaded with <strong>4 category-tailored products</strong> (including a deliberate low-stock trigger) and <strong>45 days of realistic daily sales records</strong>. Your 7-day demand forecasts, margin analysis, and AI copilot will work out-of-the-box immediately!
              </p>

              {/* 4 Preview items */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {currentStarter.items.map((item, idx) => (
                  <div
                    key={idx}
                    className={`p-2.5 rounded-xl border text-[11px] flex flex-col justify-between ${
                      item.isLowStock
                        ? 'bg-amber-50/70 border-amber-200'
                        : 'bg-white border-stone-200/80 shadow-2xs'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between gap-1 mb-0.5">
                        <span className="font-bold text-stone-900 truncate">{item.name}</span>
                        <span className="font-extrabold text-stone-900 text-xs shrink-0">{item.price}</span>
                      </div>
                      <span className="text-[10px] text-stone-400 font-medium block">{item.category}</span>
                    </div>
                    <div className="mt-1 flex items-center justify-between text-[10px]">
                      <span className={item.isLowStock ? 'text-amber-700 font-bold' : 'text-stone-500'}>
                        {item.note}
                      </span>
                      {item.isLowStock && (
                        <span className="px-1.5 py-0.2 rounded bg-amber-200 text-amber-900 font-black text-[9px] uppercase">
                          Low Stock Alert
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Address and Phone */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-stone-700 mb-1">
                  Contact Phone Number *
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
                  Street Address / Area *
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
                    placeholder="12th Main, Indiranagar, Bengaluru"
                  />
                </div>
              </div>
            </div>

            {/* GPS Pinning */}
            <div className="p-3 rounded-2xl bg-stone-50 border border-stone-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Compass className="w-4 h-4 text-stone-700 shrink-0" />
                <div>
                  <span className="text-xs font-bold text-stone-800 block">
                    Storefront Geolocation Coordinates
                  </span>
                  <span className="text-[11px] text-stone-500">
                    Lat: {formData.latitude || '12.920737'}, Lng: {formData.longitude || '77.668710'} (Bengaluru Retail Cluster)
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={handleDetectLocation}
                disabled={geoLoading}
                className="self-start sm:self-center px-3 py-1.5 rounded-full bg-white border border-stone-300 hover:bg-stone-100 text-stone-700 font-bold text-[11px] transition-colors cursor-pointer flex items-center gap-1.5"
              >
                {geoLoading ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin text-stone-800" />
                    <span>Detecting GPS...</span>
                  </>
                ) : (
                  <>
                    <Compass className="w-3 h-3 text-stone-800" />
                    <span>{geoDetected ? 'GPS Detected ✓' : 'Detect My Location'}</span>
                  </>
                )}
              </button>
            </div>

            {/* Email and Password (only required for manual email registration) */}
            {!googleAuthData && (
              <>
                <div>
                  <label className="block text-xs font-bold text-stone-700 mb-1">
                    Merchant Login Email *
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
                    Account Password (min 6 characters) *
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
              </>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-4 py-3.5 px-4 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-sm disabled:opacity-50 cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-[#e0fd53]" />
                  <span>Configuring & Seeding Storefront...</span>
                </>
              ) : (
                <>
                  <span>
                    {googleAuthData
                      ? 'Complete Google Registration & Launch Storefront'
                      : 'Create Merchant Workspace'}
                  </span>
                  <ArrowRight className="w-4 h-4 text-[#e0fd53]" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-stone-100 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-stone-500">
            <span>Already registered your store?</span>
            <Link href="/login" className="font-extrabold text-[#16181a] hover:underline flex items-center gap-1">
              <span>Sign in with Password, OTP, or Google</span>
              <ArrowRight className="w-3.5 h-3.5 text-[#16181a]" />
            </Link>
          </div>
        </div>

        {/* Security and Protocol Assurance */}
        <div className="mt-6 flex items-center justify-center gap-2 text-stone-500 text-[11px] font-medium text-center">
          <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>Stateless JWT Auth • Automated 45-Day Data Seeding • Paytm Build for India Hackathon</span>
        </div>
      </div>
    </div>
  );
}
