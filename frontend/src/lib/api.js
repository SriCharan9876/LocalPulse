import axios from 'axios';

// Clean and normalize API base URL (handles trailing slashes and prevents duplicate /api suffix)
const rawBase = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').trim().replace(/\/+$/, '');
export const API_BASE_URL = rawBase.endsWith('/api') ? rawBase : `${rawBase}/api`;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// Request interceptor: attach JWT bearer token if present
api.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('localpulse_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    // If sending FormData (e.g. audio upload), remove Content-Type so Axios/browser sets boundary
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 unauth
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (typeof window !== 'undefined' && error.response?.status === 401) {
      // Token expired or invalid
      const currentPath = window.location.pathname;
      if (currentPath !== '/login' && currentPath !== '/signup') {
        localStorage.removeItem('localpulse_token');
        localStorage.removeItem('localpulse_merchant');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth Helpers
export const setAuthSession = (token, merchant) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem('localpulse_token', token);
    localStorage.setItem('localpulse_merchant', JSON.stringify(merchant));
  }
};

export const clearAuthSession = () => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('localpulse_token');
    localStorage.removeItem('localpulse_merchant');
  }
};

export const getStoredMerchant = () => {
  if (typeof window !== 'undefined') {
    const raw = localStorage.getItem('localpulse_merchant');
    if (raw) {
      try {
        return JSON.parse(raw);
      } catch {
        return null;
      }
    }
  }
  return null;
};

export const getStoredToken = () => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('localpulse_token');
  }
  return null;
};

export default api;
