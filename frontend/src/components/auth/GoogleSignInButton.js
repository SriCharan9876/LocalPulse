'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Loader2 } from 'lucide-react';

export function GoogleLogo({ size = 18, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
        fill="#EA4335"
      />
    </svg>
  );
}

// Module-level singletons to avoid repeated script loading and duplicate initialize() warnings
let gsiScriptLoaded = false;
let gsiInitialized = false;
const globalSubscribers = new Set();

function initGsiOnce(clientId) {
  if (gsiInitialized || typeof window === 'undefined' || !window.google?.accounts?.id) return;

  try {
    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: (response) => {
        globalSubscribers.forEach((cb) => {
          try {
            cb(response);
          } catch (e) {
            console.error('GSI subscriber error:', e);
          }
        });
      },
      // Disable FedCM on localhost to prevent "FedCM get() rejects with NetworkError"
      use_fedcm_for_prompt: false,
      auto_select: false,
    });
    gsiInitialized = true;
  } catch (err) {
    console.warn('GSI initialize error:', err);
  }
}

export default function GoogleSignInButton({
  text = 'Continue with Google',
  redirectPath = '/dashboard',
  onGoogleAuth,
  onError,
}) {
  const { loginWithGoogle } = useAuth();
  const router = useRouter();

  const [loading, setLoading] = useState(false);
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  // Manage Google Identity Services script & single initialization
  useEffect(() => {
    if (!clientId || typeof window === 'undefined') return;

    const handleCredential = async (response) => {
      if (!isMounted.current) return;
      setLoading(true);
      try {
        if (onGoogleAuth) {
          await onGoogleAuth({ credential: response.credential });
        } else {
          await loginWithGoogle({ credential: response.credential });
          window.location.href = redirectPath;
        }
      } catch (err) {
        console.error('Google Sign-In failed:', err);
        const msg = err.response?.data?.detail || 'Google authentication failed';
        if (onError) onError(msg);
      } finally {
        if (isMounted.current) setLoading(false);
      }
    };

    globalSubscribers.add(handleCredential);

    if (window.google?.accounts?.id) {
      initGsiOnce(clientId);
    } else if (!gsiScriptLoaded) {
      gsiScriptLoaded = true;
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = () => {
        initGsiOnce(clientId);
      };
      document.body.appendChild(script);
    }

    return () => {
      globalSubscribers.delete(handleCredential);
    };
  }, [clientId, redirectPath, onError, onGoogleAuth, loginWithGoogle]);

  const handleButtonClick = () => {
    if (!clientId) {
      if (onError) {
        onError('Google Client ID is not configured. Please add NEXT_PUBLIC_GOOGLE_CLIENT_ID to .env or sign in with email.');
      }
      return;
    }

    if (typeof window === 'undefined' || !window.google?.accounts?.oauth2) {
      // Script still loading
      setLoading(true);
      const checkInterval = setInterval(() => {
        if (window.google?.accounts?.oauth2) {
          clearInterval(checkInterval);
          setLoading(false);
          launchOAuthPopup();
        }
      }, 200);
      setTimeout(() => {
        clearInterval(checkInterval);
        if (isMounted.current) setLoading(false);
      }, 3000);
      return;
    }

    launchOAuthPopup();
  };

  const launchOAuthPopup = () => {
    try {
      const tokenClient = window.google.accounts.oauth2.initTokenClient({
        client_id: clientId,
        scope: 'email profile openid',
        callback: async (tokenResponse) => {
          if (tokenResponse?.error) {
            // User cancelled or closed
            if (tokenResponse.error === 'access_denied') {
              console.info('Google sign-in permission was denied or cancelled.');
              return;
            }
            console.warn('OAuth token callback error:', tokenResponse.error);
            if (onError) onError(`Google Sign-In: ${tokenResponse.error_description || tokenResponse.error}`);
            return;
          }

          if (tokenResponse?.access_token) {
            setLoading(true);
            try {
              if (onGoogleAuth) {
                // Fetch verified profile from Google's userinfo API
                let userInfo = null;
                try {
                  const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
                    headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
                  });
                  if (res.ok) {
                    userInfo = await res.json();
                  }
                } catch (fetchErr) {
                  console.warn('Could not fetch userinfo directly:', fetchErr);
                }
                await onGoogleAuth({
                  access_token: tokenResponse.access_token,
                  userInfo,
                });
              } else {
                await loginWithGoogle({ access_token: tokenResponse.access_token });
                window.location.href = redirectPath;
              }
            } catch (err) {
              console.error('OAuth token exchange error:', err);
              const msg = err.response?.data?.detail || 'Google authentication failed';
              if (onError) onError(msg);
            } finally {
              if (isMounted.current) setLoading(false);
            }
          }
        },
        error_callback: (err) => {
          // If the user closed the popup window, do NOT show any secondary modal or error
          if (err?.type === 'popup_closed') {
            console.info('Google Sign-In popup closed by user.');
            return;
          }
          if (err?.type === 'popup_failed_to_open') {
            const msg = 'Google Sign-In popup was blocked by your browser. Please allow popups for this site.';
            if (onError) onError(msg);
            return;
          }
          console.warn('Google OAuth client error:', err);
          if (onError) onError('Google Sign-In encountered an error. Please try again.');
        },
      });

      tokenClient.requestAccessToken({ prompt: 'select_account' });
    } catch (err) {
      console.error('Could not launch Google OAuth token client:', err);
      if (onError) onError('Could not launch Google Sign-In. Please check your browser popup settings.');
    }
  };

  return (
    <button
      type="button"
      onClick={handleButtonClick}
      disabled={loading}
      className="w-full py-2.5 px-4 rounded-full bg-white hover:bg-stone-50 border border-stone-300/90 text-stone-800 font-bold text-xs flex items-center justify-center gap-2.5 transition-all shadow-2xs hover:shadow-xs cursor-pointer disabled:opacity-50"
    >
      {loading ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin text-stone-600" />
          <span>Connecting to Google...</span>
        </>
      ) : (
        <>
          <GoogleLogo size={16} />
          <span>{text}</span>
        </>
      )}
    </button>
  );
}
