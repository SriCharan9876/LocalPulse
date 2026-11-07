import axios from 'axios';
import { triggerGeminiRateLimitModal } from './geminiRateLimit';

// Clean and normalize API base URL (handles trailing slashes and prevents duplicate /api suffix)
const rawBase = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').trim().replace(/\/+$/, '');
export const API_BASE_URL = rawBase.endsWith('/api') ? rawBase : `${rawBase}/api`;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 35000,
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

// Response interceptor: handle 401 unauth & global Gemini rate limit detection
api.interceptors.response.use(
  (response) => {
    // Check if Gemini rate limit was encountered in the backend response
    const headers = response.headers || {};
    const isHeaderRateLimited =
      headers['x-gemini-rate-limited'] === 'true' ||
      headers['x-gemini-quota-exceeded'] === 'true';
    const isBodyRateLimited = response.data?.llm_rate_limited === true;

    if (isHeaderRateLimited || isBodyRateLimited) {
      triggerGeminiRateLimitModal({
        source: response.config?.url || 'AI Engine',
      });
    }

    return response;
  },
  (error) => {
    if (typeof window !== 'undefined') {
      const status = error.response?.status;
      const headers = error.response?.headers || {};
      const data = error.response?.data;

      // Handle 401 unauth
      if (status === 401) {
        const currentPath = window.location.pathname;
        if (currentPath !== '/login' && currentPath !== '/signup') {
          localStorage.removeItem('localpulse_token');
          localStorage.removeItem('localpulse_merchant');
          window.location.href = '/login';
        }
      }

      // Check if this error was caused by Gemini API limits / quota exhaustion
      const isHeaderRateLimited =
        headers['x-gemini-rate-limited'] === 'true' ||
        headers['x-gemini-quota-exceeded'] === 'true';
      const is429 = status === 429;

      const errString = (
        (typeof data?.detail === 'string' ? data.detail : '') + ' ' +
        (typeof data?.message === 'string' ? data.message : '') + ' ' +
        (typeof error.message === 'string' ? error.message : '')
      ).toLowerCase();

      const isQuotaExceeded =
        is429 ||
        isHeaderRateLimited ||
        errString.includes('resource_exhausted') ||
        errString.includes('resourceexhausted') ||
        errString.includes('quota exceeded') ||
        errString.includes('quota_exceeded') ||
        errString.includes('exceeded your current quota') ||
        errString.includes('check quota') ||
        errString.includes('rate limit') ||
        errString.includes('too many requests') ||
        errString.includes('gemini limit');

      if (isQuotaExceeded) {
        triggerGeminiRateLimitModal({
          source: error.config?.url || 'AI Engine',
          detail: typeof data?.detail === 'string' ? data.detail : null,
        });
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
