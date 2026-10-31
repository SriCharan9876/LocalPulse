'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import api, { setAuthSession, clearAuthSession, getStoredMerchant, getStoredToken } from '@/lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [merchant, setMerchant] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [demoMerchants, setDemoMerchants] = useState([]);

  useEffect(() => {
    // Hydrate session from localStorage
    const storedToken = getStoredToken();
    const storedMerchant = getStoredMerchant();
    if (storedToken && storedMerchant) {
      setToken(storedToken);
      setMerchant(storedMerchant);
    }
    setLoading(false);

    // Fetch demo merchants list for the switcher
    api.get('/auth/demo-merchants')
      .then((res) => {
        if (res.data?.merchants) {
          setDemoMerchants(res.data.merchants);
        }
      })
      .catch((err) => {
        console.warn('Could not load demo merchants list:', err);
      });
  }, []);

  const login = async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    const { access_token, merchant: profile } = res.data;
    setAuthSession(access_token, profile);
    setToken(access_token);
    setMerchant(profile);
    return profile;
  };

  const signup = async (formData) => {
    const res = await api.post('/auth/signup', formData);
    const { access_token, merchant: profile } = res.data;
    setAuthSession(access_token, profile);
    setToken(access_token);
    setMerchant(profile);
    return profile;
  };

  const switchDemoMerchant = async (merchantId) => {
    setLoading(true);
    try {
      const res = await api.post('/auth/switch-demo', { merchant_id: merchantId });
      const { access_token, merchant: profile } = res.data;
      setAuthSession(access_token, profile);
      setToken(access_token);
      setMerchant(profile);
      // Reload current page to refresh all queries with new merchant token
      window.location.reload();
      return profile;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    clearAuthSession();
    setToken(null);
    setMerchant(null);
    window.location.href = '/login';
  };

  return (
    <AuthContext.Provider
      value={{
        merchant,
        token,
        loading,
        demoMerchants,
        login,
        signup,
        switchDemoMerchant,
        logout,
        isAuthenticated: !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
