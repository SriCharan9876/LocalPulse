'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import {
  Store,
  Lock,
  Mail,
  Phone,
  KeyRound,
  ArrowRight,
  Loader2,
  AlertCircle,
  Users,
  Sparkles,
  Zap,
  ShoppingBag,
  Coffee,
  Apple,
  Shirt,
  HeartPulse,
  Cake,
  Check,
  CheckCircle2,
  Send,
  RefreshCw,
} from 'lucide-react';
import { LogoMark } from '@/components/ui/Logo';
import GoogleSignInButton from '@/components/auth/GoogleSignInButton';

// All 6 seeded demo merchant accounts
const SEEDED_DEMO_ACCOUNTS = [
  {
    merchant_id: 'merchant-001',
    business_name: 'Sharma Kirana & General Store',
    owner_name: 'Ramesh Sharma',
    email: 'sharma.kirana@localpulse.demo',
    phone: '+91 98450 12345',
    category: 'Grocery & Daily Essentials',
    icon: ShoppingBag,
    badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    highlight: 'FMCG staples, dairy expiry radar, reorder threshold triggers',
  },
  {
    merchant_id: 'merchant-002',
    business_name: "Chai Point & Baker's Corner",
    owner_name: 'Priya Nair',
    email: 'priya.bakery@localpulse.demo',
    phone: '+91 98451 23456',
    category: 'Cafe & Bakery',
    icon: Coffee,
    badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
    highlight: 'Artisan sourdough & chai combos, Sunday breakfast bundle partner',
  },
  {
    merchant_id: 'merchant-003',
    business_name: 'Green Valley Organic Produce',
    owner_name: 'Vikram Patel',
    email: 'greenvalley@localpulse.demo',
    phone: '+91 98452 34567',
    category: 'Fresh Fruits & Vegetables',
    icon: Apple,
    badgeColor: 'bg-lime-50 text-lime-800 border-lime-200',
    highlight: 'Hydroponic salad greens, perishables tracking & weekend surges',
  },
  {
    merchant_id: 'merchant-004',
    business_name: 'Modern Threads & Apparel',
    owner_name: 'Anita Roy',
    email: 'modernthreads@localpulse.demo',
    phone: '+91 98453 45678',
    category: 'Fashion & Textiles',
    icon: Shirt,
    badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    highlight: 'Pure Khadi kurtas, Ikat dupattas, festive stock planning',
  },
  {
    merchant_id: 'merchant-005',
    business_name: 'Sanjeevani Ayurvedic Wellness',
    owner_name: 'Dr. Alok Gupta',
    email: 'sanjeevani@localpulse.demo',
    phone: '+91 98454 56789',
    category: 'Health & Wellness',
    icon: HeartPulse,
    badgeColor: 'bg-teal-50 text-teal-700 border-teal-200',
    highlight: 'Chyawanprash, cold-pressed virgin oils, seasonal health campaigns',
  },
  {
    merchant_id: 'merchant-006',
    business_name: 'Anand Sweets & Savories',
    owner_name: 'Anand Joshi',
    email: 'anandsweets@localpulse.demo',
    phone: '+91 98455 67890',
    category: 'Traditional Sweets & Snacks',
    icon: Cake,
    badgeColor: 'bg-rose-50 text-rose-700 border-rose-200',
    highlight: 'Kaju Katli gifting surges, spicy savories, festival rush telemetry',
  },
];

export default function LoginPage() {
  const { login, switchDemoMerchant, sendOtp, verifyOtp, isAuthenticated } = useAuth();
  const router = useRouter();

  // Mode: 'password' or 'otp'
  const [authMethod, setAuthMethod] = useState('password');

  // Password Login State
  const [email, setEmail] = useState('sharma.kirana@localpulse.demo');
  const [password, setPassword] = useState('password123');
  const [loading, setLoading] = useState(false);
  const [activeDemoId, setActiveDemoId] = useState(null);
  const [copiedEmail, setCopiedEmail] = useState(null);
  const [error, setError] = useState('');

  // OTP Login State
  const [otpTarget, setOtpTarget] = useState('+91 98450 12345');
  const [otpStep, setOtpStep] = useState('request'); // 'request' | 'verify'
  const [otpCode, setOtpCode] = useState('123456');
  const [otpLoading, setOtpLoading] = useState(false);
  const [otpMessage, setOtpMessage] = useState('');
  const [otpError, setOtpError] = useState('');

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.replace('/dashboard');
    }
  }, [isAuthenticated, router]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(email, password);
      window.location.href = '/dashboard';
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail || 'Failed to sign in. Please verify credentials.'
      );
      setLoading(false);
    }
  };

  const handleSendOtp = async (e) => {
    if (e) e.preventDefault();
    setOtpLoading(true);
    setOtpError('');
    setOtpMessage('');
    try {
      const res = await sendOtp(otpTarget);
      setOtpStep('verify');
      setOtpMessage(res.message || 'OTP sent successfully!');
      if (res.demo_otp) {
        setOtpCode(res.demo_otp);
      }
    } catch (err) {
      console.error(err);
      setOtpError(
        err.response?.data?.detail || 'Failed to send OTP. Please check your phone/email.'
      );
    } finally {
      setOtpLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setOtpLoading(true);
    setOtpError('');
    try {
      await verifyOtp(otpTarget, otpCode);
      window.location.href = '/dashboard';
    } catch (err) {
      console.error(err);
      setOtpError(
        err.response?.data?.detail || 'Invalid or expired OTP. Please enter 123456 or retry.'
      );
      setOtpLoading(false);
    }
  };

  const handleDemoSelect = async (account) => {
    setActiveDemoId(account.merchant_id);
    setLoading(true);
    setError('');
    setEmail(account.email);
    setPassword('password123');
    setOtpTarget(account.phone);

    try {
      if (account.merchant_id) {
        await switchDemoMerchant(account.merchant_id);
      } else {
        await login(account.email, 'password123');
      }
      window.location.href = '/dashboard';
    } catch (err) {
      console.warn('Direct switch failed, falling back to login API:', err);
      try {
        await login(account.email, 'password123');
        window.location.href = '/dashboard';
      } catch (loginErr) {
        console.error(loginErr);
        setError(
          loginErr.response?.data?.detail ||
          'Could not authenticate with demo account. Ensure backend server is running.'
        );
        setLoading(false);
        setActiveDemoId(null);
      }
    }
  };

  const handleAutofill = (account, e) => {
    e.stopPropagation();
    setEmail(account.email);
    setPassword('password123');
    setOtpTarget(account.phone);
    setError('');
    setCopiedEmail(account.merchant_id);
    setTimeout(() => setCopiedEmail(null), 2000);
  };

  return (
    <div className="min-h-screen bg-[#edece4] py-10 px-4 sm:px-6 lg:px-8 flex flex-col justify-center">
      <div className="max-w-6xl mx-auto w-full">
        {/* Header Branding */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex flex-col items-center group">
            <LogoMark size={54} className="shadow-md transition-transform group-hover:scale-105" />
            <h1 className="mt-3 text-2xl sm:text-3xl font-black text-[#16181a] tracking-tight">
              Sign In to LocalPulse AI
            </h1>
          </Link>
          <p className="mt-1 text-xs sm:text-sm text-stone-600 font-medium">
            Autonomous Merchant Growth AI Platform • Paytm Build for India Hackathon
          </p>
        </div>

        {/* Two-Column Responsive Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Sign In Form & OTP (5 cols on lg) */}
          <div className="lg:col-span-5 bg-white p-6 sm:p-8 rounded-[28px] border border-stone-200/90 shadow-[0_8px_30px_rgba(20,24,20,0.06)]">
            
            {/* Method Toggle Tab */}
            <div className="flex p-1 bg-stone-100 rounded-2xl mb-5">
              <button
                type="button"
                onClick={() => { setAuthMethod('password'); setError(''); }}
                className={`flex-1 py-2 text-xs font-bold rounded-xl transition-all ${
                  authMethod === 'password'
                    ? 'bg-white text-[#16181a] shadow-2xs'
                    : 'text-stone-500 hover:text-stone-900'
                }`}
              >
                Password / Google
              </button>
              <button
                type="button"
                onClick={() => { setAuthMethod('otp'); setOtpError(''); }}
                className={`flex-1 py-2 text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-1.5 ${
                  authMethod === 'otp'
                    ? 'bg-white text-[#16181a] shadow-2xs'
                    : 'text-stone-500 hover:text-stone-900'
                }`}
              >
                <span>Mobile OTP</span>
                <span className="px-1.5 py-0.2 rounded-full bg-[#e0fd53] text-[#16181a] text-[9px] font-black uppercase">
                  Fast
                </span>
              </button>
            </div>

            {authMethod === 'password' ? (
              <>
                {/* Google Sign In */}
                <div className="mb-5">
                  <GoogleSignInButton text="Sign In with Google" onError={(msg) => setError(msg)} />
                </div>

                <div className="relative mb-5">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-stone-200" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-white px-2.5 text-stone-400 font-bold text-[10px] tracking-widest">
                      Or sign in with email
                    </span>
                  </div>
                </div>

                {error && (
                  <div className="mb-4 p-3 rounded-xl bg-[#fbe8e4] border border-[#f3c5bd] flex items-start gap-2 text-[#a43b27] text-xs leading-relaxed">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-stone-700 mb-1">
                      Merchant Email
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-stone-400">
                        <Mail className="w-4 h-4" />
                      </div>
                      <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-stone-200 text-xs text-stone-900 focus:outline-hidden focus:border-[#16181a] focus:ring-1 focus:ring-[#16181a] shadow-2xs transition-all"
                        placeholder="merchant@example.com"
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="block text-xs font-semibold text-stone-700">
                        Password
                      </label>
                      <span className="text-[10px] text-stone-400 font-medium">
                        Demo password: <code className="bg-stone-100 px-1 py-0.5 rounded text-stone-600 font-bold">password123</code>
                      </span>
                    </div>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-stone-400">
                        <Lock className="w-4 h-4" />
                      </div>
                      <input
                        type="password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-stone-200 text-xs text-stone-900 focus:outline-hidden focus:border-[#16181a] focus:ring-1 focus:ring-[#16181a] shadow-2xs transition-all"
                        placeholder="••••••••"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full mt-2 py-3 px-4 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-xs disabled:opacity-50 cursor-pointer"
                  >
                    {loading && !activeDemoId ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin text-[#e0fd53]" />
                        <span>Signing In...</span>
                      </>
                    ) : (
                      <>
                        <span>Sign In to Dashboard</span>
                        <ArrowRight className="w-4 h-4 text-[#e0fd53]" />
                      </>
                    )}
                  </button>
                </form>
              </>
            ) : (
              /* OTP Authentication Form */
              <div className="space-y-4">
                <div className="mb-3">
                  <h3 className="text-sm font-bold text-[#16181a]">
                    {otpStep === 'request' ? 'Instant Mobile / Email OTP Sign-In' : 'Enter 6-Digit OTP Code'}
                  </h3>
                  <p className="text-xs text-stone-500 mt-0.5">
                    {otpStep === 'request'
                      ? 'Enter your registered merchant mobile number or email to receive a login code.'
                      : `A verification code was sent to ${otpTarget}.`}
                  </p>
                </div>

                {otpError && (
                  <div className="p-3 rounded-xl bg-[#fbe8e4] border border-[#f3c5bd] flex items-start gap-2 text-[#a43b27] text-xs leading-relaxed">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{otpError}</span>
                  </div>
                )}

                {otpMessage && otpStep === 'verify' && (
                  <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-2 text-emerald-800 text-xs">
                    <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-600" />
                    <div>
                      <span>{otpMessage}</span>
                      <p className="font-bold mt-0.5 text-emerald-900">
                        Demo Hackathon Test OTP: <code className="bg-emerald-100 px-1 rounded text-emerald-950 font-black">123456</code>
                      </p>
                    </div>
                  </div>
                )}

                {otpStep === 'request' ? (
                  <form onSubmit={handleSendOtp} className="space-y-4">
                    <div>
                      <label className="block text-xs font-semibold text-stone-700 mb-1">
                        Merchant Mobile Number or Email
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-stone-400">
                          <Phone className="w-4 h-4" />
                        </div>
                        <input
                          type="text"
                          required
                          value={otpTarget}
                          onChange={(e) => setOtpTarget(e.target.value)}
                          className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-stone-200 text-xs text-stone-900 focus:outline-hidden focus:border-[#16181a] shadow-2xs font-medium"
                          placeholder="+91 98450 12345 or email@store.in"
                        />
                      </div>
                    </div>

                    {/* Quick Demo Phone Chips */}
                    <div className="p-3 rounded-2xl bg-stone-50 border border-stone-200/80">
                      <span className="text-[10px] uppercase font-bold text-stone-400 block mb-1.5 tracking-wider">
                        Quick Demo Merchant Numbers
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {SEEDED_DEMO_ACCOUNTS.slice(0, 3).map((acc) => (
                          <button
                            key={acc.merchant_id}
                            type="button"
                            onClick={() => { setOtpTarget(acc.phone); setOtpError(''); }}
                            className="px-2 py-1 rounded-lg bg-white border border-stone-200 hover:border-stone-400 text-[10px] font-bold text-stone-700 transition-colors"
                          >
                            {acc.owner_name.split(' ')[0]}: {acc.phone}
                          </button>
                        ))}
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={otpLoading}
                      className="w-full py-3 px-4 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-xs disabled:opacity-50 cursor-pointer"
                    >
                      {otpLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin text-[#e0fd53]" />
                          <span>Sending 6-Digit OTP...</span>
                        </>
                      ) : (
                        <>
                          <Send className="w-3.5 h-3.5 text-[#e0fd53]" />
                          <span>Send Login OTP</span>
                        </>
                      )}
                    </button>
                  </form>
                ) : (
                  /* Verify OTP Form */
                  <form onSubmit={handleVerifyOtp} className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="block text-xs font-semibold text-stone-700">
                          Enter 6-Digit OTP
                        </label>
                        <button
                          type="button"
                          onClick={() => setOtpStep('request')}
                          className="text-[10px] font-bold text-stone-500 hover:text-[#16181a] underline"
                        >
                          Change Number
                        </button>
                      </div>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-stone-400">
                          <KeyRound className="w-4 h-4" />
                        </div>
                        <input
                          type="text"
                          required
                          maxLength={6}
                          value={otpCode}
                          onChange={(e) => setOtpCode(e.target.value)}
                          className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-stone-200 text-sm font-mono tracking-widest text-stone-900 focus:outline-hidden focus:border-[#16181a] shadow-2xs font-bold"
                          placeholder="123456"
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={otpLoading}
                      className="w-full py-3 px-4 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-xs disabled:opacity-50 cursor-pointer"
                    >
                      {otpLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin text-[#e0fd53]" />
                          <span>Verifying OTP...</span>
                        </>
                      ) : (
                        <>
                          <span>Verify OTP & Open Dashboard</span>
                          <ArrowRight className="w-4 h-4 text-[#e0fd53]" />
                        </>
                      )}
                    </button>

                    <div className="text-center pt-1">
                      <button
                        type="button"
                        onClick={handleSendOtp}
                        disabled={otpLoading}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-stone-500 hover:text-stone-900"
                      >
                        <RefreshCw className="w-3 h-3" />
                        <span>Resend OTP Code</span>
                      </button>
                    </div>
                  </form>
                )}
              </div>
            )}

            <div className="mt-5 pt-4 border-t border-stone-100 text-center">
              <p className="text-xs text-stone-500">
                New merchant?{' '}
                <Link href="/signup" className="font-bold text-[#16181a] hover:underline">
                  Create a new store profile
                </Link>
              </p>
            </div>
          </div>

          {/* Right Column: All 6 Seeded Demo Accounts (7 cols on lg) */}
          <div className="lg:col-span-7 bg-white p-6 sm:p-8 rounded-[28px] border border-stone-200/90 shadow-[0_8px_30px_rgba(20,24,20,0.06)]">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-stone-100">
              <div>
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-[#e0fd53]/40 flex items-center justify-center text-stone-900">
                    <Zap className="w-4 h-4 fill-stone-900" />
                  </div>
                  <h2 className="text-base font-black text-[#16181a] tracking-tight">
                    1-Click Seeded Demo Workspaces
                  </h2>
                </div>
                <p className="text-xs text-stone-500 mt-1">
                  Click any account below to immediately launch its dashboard with live 90-day telemetry.
                </p>
              </div>
              <span className="self-start sm:self-center px-2 py-1 rounded-full bg-stone-100 border border-stone-200 text-[10px] font-bold text-stone-600">
                6 Verified Stores
              </span>
            </div>

            {/* Grid of 6 Demo Merchants */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {SEEDED_DEMO_ACCOUNTS.map((account) => {
                const IconComponent = account.icon;
                const isSelected = activeDemoId === account.merchant_id;
                const isCopied = copiedEmail === account.merchant_id;
                const isCurrentForm = email === account.email || otpTarget === account.phone;

                return (
                  <div
                    key={account.merchant_id}
                    onClick={() => handleDemoSelect(account)}
                    className={`group relative p-3.5 rounded-2xl border transition-all text-left flex flex-col justify-between cursor-pointer ${
                      isCurrentForm
                        ? 'border-[#16181a] bg-stone-50/80 shadow-xs'
                        : 'border-stone-200 hover:border-stone-400 hover:bg-stone-50/50 hover:shadow-xs'
                    }`}
                  >
                    <div>
                      {/* Top Row: Icon + Badge + Autofill button */}
                      <div className="flex items-center justify-between gap-1 mb-2">
                        <div className="flex items-center gap-1.5">
                          <div className="w-6 h-6 rounded-md bg-stone-100 flex items-center justify-center text-stone-700 group-hover:bg-[#16181a] group-hover:text-white transition-colors">
                            <IconComponent className="w-3.5 h-3.5" />
                          </div>
                          <span
                            className={`text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded-md border ${account.badgeColor}`}
                          >
                            {account.category.split('&')[0].trim()}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => handleAutofill(account, e)}
                          title="Fill credentials into form without submitting"
                          className="text-[10px] font-bold text-stone-400 hover:text-stone-700 px-1.5 py-0.5 rounded hover:bg-stone-200/60 transition-colors flex items-center gap-1"
                        >
                          {isCopied ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-600" />
                              <span className="text-emerald-600">Filled</span>
                            </>
                          ) : (
                            <span>Fill</span>
                          )}
                        </button>
                      </div>

                      {/* Store Name & Owner */}
                      <h3 className="text-xs font-bold text-[#16181a] group-hover:text-stone-900 line-clamp-1">
                        {account.business_name}
                      </h3>
                      <p className="text-[10px] text-stone-500 mt-0.5">
                        Owner: <span className="font-medium text-stone-700">{account.owner_name}</span> • <span className="font-mono text-stone-400">{account.phone}</span>
                      </p>

                      {/* Highlight */}
                      <p className="text-[10px] text-stone-500 mt-1.5 leading-snug line-clamp-2">
                        {account.highlight}
                      </p>
                    </div>

                    {/* Bottom Row: 1-Click Launch Button */}
                    <div className="mt-3 pt-2.5 border-t border-stone-100 flex items-center justify-between text-[11px]">
                      <span className="text-[10px] font-mono text-stone-400 truncate max-w-[140px]">
                        {account.email.split('@')[0]}
                      </span>
                      <button
                        type="button"
                        disabled={loading}
                        className="px-2.5 py-1 rounded-full bg-[#16181a] group-hover:bg-stone-800 text-white font-bold text-[10px] flex items-center gap-1 transition-all"
                      >
                        {isSelected && loading ? (
                          <>
                            <Loader2 className="w-3 h-3 animate-spin text-[#e0fd53]" />
                            <span>Launching...</span>
                          </>
                        ) : (
                          <>
                            <span>1-Click Launch</span>
                            <ArrowRight className="w-3 h-3 text-[#e0fd53] group-hover:translate-x-0.5 transition-transform" />
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Bottom Note */}
            <div className="mt-4 p-3 rounded-xl bg-stone-50 border border-stone-200/70 flex items-center gap-2.5 text-stone-600 text-[11px]">
              <Sparkles className="w-4 h-4 text-stone-800 shrink-0" />
              <span>
                Each demo store includes pre-computed 90-day sales, low-stock triggers, multi-store collaboration synergy radars, and AI Copilot contexts.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
