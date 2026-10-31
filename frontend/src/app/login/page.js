'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import {
  Store,
  Lock,
  Mail,
  ArrowRight,
  Loader2,
  AlertCircle,
  Users,
} from 'lucide-react';
import { LogoMark } from '@/components/ui/Logo';

export default function LoginPage() {
  const { login, switchDemoMerchant, demoMerchants } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState('sharma.kirana@localpulse.demo');
  const [password, setPassword] = useState('password123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(email, password);
      router.push('/dashboard');
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail || 'Failed to sign in. Please verify credentials.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleDemoSelect = async (demoEmail, merchantId) => {
    setLoading(true);
    setError('');
    try {
      if (merchantId) {
        await switchDemoMerchant(merchantId);
      } else {
        await login(demoEmail, 'password123');
      }
      router.push('/dashboard');
    } catch (err) {
      console.error(err);
      setError('Could not switch to demo merchant. Ensure backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#edece4] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <LogoMark size={56} className="mx-auto shadow-md" />
        <h2 className="mt-4 text-2xl font-black text-[#16181a] tracking-tight">
          Sign In to LocalPulse AI
        </h2>
        <p className="mt-1 text-xs text-stone-500 font-medium">
          Merchant Growth AI Platform • Paytm Build for India Hackathon
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-[0_4px_24px_rgba(20,24,20,0.06)] rounded-[28px] border border-stone-200/90 sm:px-10">
          {/* Quick Demo Switcher Section */}
          <div className="mb-6 p-4 rounded-2xl bg-[#f7f8f4] border border-stone-200/80">
            <div className="flex items-center gap-2 mb-1.5 text-xs font-bold text-[#16181a]">
              <Users className="w-4 h-4 text-[#16181a]" />
              <span>Quick 1-Click Demo Workspaces</span>
            </div>
            <p className="text-[11px] text-stone-500 mb-3">
              Click any merchant below to instantly log in with pre-seeded sales and inventory:
            </p>
            <div className="space-y-1.5">
              <button
                type="button"
                onClick={() => handleDemoSelect('sharma.kirana@localpulse.demo', 'merchant-001')}
                className="w-full text-left px-3.5 py-2.5 rounded-xl bg-white border border-stone-200/80 hover:border-[#16181a] text-xs font-semibold text-stone-800 flex items-center justify-between transition-colors shadow-2xs"
              >
                <span>Sharma Kirana & General Store</span>
                <span className="text-[10px] text-[#16181a] font-bold bg-[#e0fd53] px-2.5 py-0.5 rounded-full">Grocery</span>
              </button>
              <button
                type="button"
                onClick={() => handleDemoSelect('priya.bakery@localpulse.demo', 'merchant-002')}
                className="w-full text-left px-3.5 py-2.5 rounded-xl bg-white border border-stone-200/80 hover:border-[#16181a] text-xs font-semibold text-stone-800 flex items-center justify-between transition-colors shadow-2xs"
              >
                <span>Chai Point & Baker&apos;s Corner</span>
                <span className="text-[10px] text-[#16181a] font-bold bg-[#e0fd53] px-2.5 py-0.5 rounded-full">Cafe</span>
              </button>
              <button
                type="button"
                onClick={() => handleDemoSelect('greenvalley@localpulse.demo', 'merchant-003')}
                className="w-full text-left px-3.5 py-2.5 rounded-xl bg-white border border-stone-200/80 hover:border-[#16181a] text-xs font-semibold text-stone-800 flex items-center justify-between transition-colors shadow-2xs"
              >
                <span>Green Valley Organic Produce</span>
                <span className="text-[10px] text-[#16181a] font-bold bg-[#e0fd53] px-2.5 py-0.5 rounded-full">Produce</span>
              </button>
            </div>
          </div>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-stone-100" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-stone-400 font-bold text-[10px] tracking-widest">
                Or sign in with email
              </span>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-xl bg-[#fbe8e4] border border-[#f3c5bd] flex items-start gap-2 text-[#a43b27] text-xs">
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
                  className="w-full pl-9 pr-3 py-2 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a] shadow-2xs transition-all"
                  placeholder="merchant@example.com"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-stone-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 rounded-xl border border-stone-200 text-xs focus:outline-hidden focus:border-[#16181a] shadow-2xs transition-all"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3 px-4 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-xs disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-[#e0fd53]" />
                  <span>Signing In...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4 text-[#e0fd53]" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-xs text-stone-500">
              Don&apos;t have an account?{' '}
              <Link href="/signup" className="font-bold text-[#16181a] hover:underline">
                Register new merchant
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
