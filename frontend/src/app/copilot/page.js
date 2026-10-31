'use client';

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import AppLayout from '@/components/layout/AppLayout';
import Badge from '@/components/ui/Badge';
import api from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { convertBlobTo16kWav } from '@/lib/audioUtils';
import ChartOffer from '@/components/copilot/ChartOffer';
import {
  Sparkles,
  Send,
  Bot,
  User,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Info,
  Loader2,
  ArrowRight,
  Package,
  Megaphone,
  Handshake,
  PlusCircle,
  XCircle,
  BarChart3,
  Percent,
  RotateCcw,
  Copy,
  Check,
  ExternalLink,
  Store,
  TrendingUp,
  Tag,
  Zap,
  Mic,
  MicOff,
  Volume2,
  Globe,
  SlidersHorizontal,
} from 'lucide-react';

// Categorized operational queries grounded in actual backend capabilities
const SUGGESTED_CATEGORIES = [
  {
    category: 'Restock & Inventory',
    icon: Package,
    queries: [
      'Which products are running low and need restocking?',
      'Restock top low-stock item by 30 units',
    ],
  },
  {
    category: 'Discount & Clearance',
    icon: Percent,
    queries: [
      'Recommend clearance discounts for excess stock',
      'Draft a weekend discount campaign with 12% off',
    ],
  },
  {
    category: 'Analytics & Sales',
    icon: BarChart3,
    queries: [
      'Analyze performance of our top product over the last 14 days',
      'Give me a full business health overview',
    ],
  },
  {
    category: 'Catalog & Campaigns',
    icon: PlusCircle,
    queries: [
      'Add product Greek Yogurt category Dairy cost 45 selling 75 stock 30',
      'End active promotional campaign',
    ],
  },
];

// Inline markdown parser: handles **bold**, `code`, *italics*
function InlineText({ text }) {
  if (!text) return null;
  const tokens = [];
  const regex = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      tokens.push({ type: 'text', val: text.substring(lastIndex, match.index) });
    }
    const raw = match[0];
    if (raw.startsWith('**') && raw.endsWith('**')) {
      tokens.push({ type: 'bold', val: raw.slice(2, -2) });
    } else if (raw.startsWith('`') && raw.endsWith('`')) {
      tokens.push({ type: 'code', val: raw.slice(1, -1) });
    } else if (raw.startsWith('*') && raw.endsWith('*')) {
      tokens.push({ type: 'italic', val: raw.slice(1, -1) });
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    tokens.push({ type: 'text', val: text.substring(lastIndex) });
  }

  return (
    <>
      {tokens.map((token, i) => {
        if (token.type === 'bold') {
          return (
            <strong key={i} className="font-bold text-[#16181a]">
              {token.val}
            </strong>
          );
        }
        if (token.type === 'code') {
          return (
            <code
              key={i}
              className="px-1.5 py-0.5 rounded-md bg-stone-100 border border-stone-200/90 font-mono text-[11px] text-[#16181a] font-semibold"
            >
              {token.val}
            </code>
          );
        }
        if (token.type === 'italic') {
          return (
            <em key={i} className="italic text-stone-500">
              {token.val}
            </em>
          );
        }
        return <span key={i}>{token.val}</span>;
      })}
    </>
  );
}

// Structured message block formatter (ZERO EMOJIS, clean Lucide iconography)
function FormattedMessage({ content }) {
  if (!content) return null;
  // Clean out any accidental unicode emojis in incoming text
  const cleanContent = content.replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '');
  const lines = cleanContent.split('\n');

  return (
    <div className="space-y-1.5 text-xs leading-relaxed text-stone-800">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={idx} className="h-1" />;
        }

        // Section header / Alert callout
        const isWarning = trimmed.includes('Stockout Warning') || trimmed.includes('Restock Recommendations');
        const isSuccess = trimmed.includes('Inventory is Healthy') || trimmed.includes('Confirmed');
        const isError = trimmed.includes('Error:') || trimmed.includes('Could not locate');
        const isAction = trimmed.includes('Drafted');

        if (
          trimmed.startsWith('**') &&
          trimmed.endsWith('**') &&
          (isWarning || isSuccess || isError || isAction || trimmed.includes('Analysis') || trimmed.includes('Overview'))
        ) {
          return (
            <div
              key={idx}
              className={`py-2 px-3.5 rounded-2xl font-semibold flex items-center gap-2.5 my-1.5 text-[11.5px] ${
                isWarning
                  ? 'bg-[#faeed6] text-[#8c5208] border border-[#f2d8a5]'
                  : isSuccess
                  ? 'bg-emerald-50 text-emerald-900 border border-emerald-200'
                  : isError
                  ? 'bg-[#fbe8e4] text-[#a43b27] border border-[#f3c5bd]'
                  : isAction
                  ? 'bg-[#f7f8f4] text-[#16181a] border border-stone-200/90'
                  : 'bg-stone-50 text-[#16181a] border border-stone-200/80 font-bold'
              }`}
            >
              {isWarning ? (
                <AlertTriangle className="w-4 h-4 text-[#8c5208] shrink-0" />
              ) : isSuccess ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
              ) : isError ? (
                <AlertTriangle className="w-4 h-4 text-[#a43b27] shrink-0" />
              ) : isAction ? (
                <Sparkles className="w-4 h-4 text-[#16181a] shrink-0" />
              ) : (
                <BarChart3 className="w-4 h-4 text-[#16181a] shrink-0" />
              )}
              <div className="min-w-0">
                <InlineText text={trimmed} />
              </div>
            </div>
          );
        }

        // Bullet point: - **Item**: ... or • Item: ...
        if (trimmed.startsWith('- ') || trimmed.startsWith('• ') || trimmed.startsWith('* ')) {
          const bulletContent = trimmed.replace(/^[-•*]\s+/, '');
          return (
            <div key={idx} className="flex items-start gap-2.5 pl-2 py-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#16181a] mt-1.5 shrink-0" />
              <div className="min-w-0">
                <InlineText text={bulletContent} />
              </div>
            </div>
          );
        }

        // Numbered list item: 1. ...
        if (/^\d+\.\s+/.test(trimmed)) {
          const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
          return (
            <div key={idx} className="flex items-start gap-2.5 pl-2 py-0.5">
              <span className="text-[11px] font-bold text-[#16181a] shrink-0 w-4">
                {numMatch ? numMatch[1] : '•'}.
              </span>
              <div className="min-w-0">
                <InlineText text={numMatch ? numMatch[2] : trimmed} />
              </div>
            </div>
          );
        }

        // Sub-bullet with arrow: -> ...
        if (trimmed.startsWith('->') || trimmed.startsWith('↳') || trimmed.startsWith('➔')) {
          return (
            <div key={idx} className="pl-6 text-stone-700 flex items-start gap-1.5 text-[11px] py-0.5">
              <span className="text-[#16181a] font-bold shrink-0">→</span>
              <div className="min-w-0">
                <InlineText text={trimmed.replace(/^(->|➔|↳)\s*/, '')} />
              </div>
            </div>
          );
        }

        // Standard text paragraph
        return (
          <p key={idx} className="py-0.5">
            <InlineText text={trimmed} />
          </p>
        );
      })}
    </div>
  );
}

// Action Confirmation Card Component (Clean Dribbble Card Style)
function DraftActionCard({
  draftAction,
  index,
  isConfirming,
  onConfirm,
  confirmedMessage,
}) {
  const isConfirmed = draftAction.status === 'CONFIRMED';

  const getActionIcon = () => {
    switch (draftAction.action_type) {
      case 'RESTOCK_INVENTORY':
        return <Package className="w-4 h-4 text-[#8c5208]" />;
      case 'CREATE_CAMPAIGN':
        return <Megaphone className="w-4 h-4 text-[#16181a]" />;
      case 'ADD_PRODUCT':
        return <PlusCircle className="w-4 h-4 text-emerald-700" />;
      case 'END_CAMPAIGN':
        return <XCircle className="w-4 h-4 text-[#a43b27]" />;
      default:
        return <Zap className="w-4 h-4 text-[#16181a]" />;
    }
  };

  const getActionTypeLabel = () => {
    switch (draftAction.action_type) {
      case 'RESTOCK_INVENTORY':
        return 'INVENTORY REPLENISHMENT';
      case 'CREATE_CAMPAIGN':
        return 'PROMOTIONAL CAMPAIGN DRAFT';
      case 'ADD_PRODUCT':
        return 'CATALOG PRODUCT INTAKE';
      case 'END_CAMPAIGN':
        return 'CONCLUDE CAMPAIGN';
      default:
        return 'PROPOSED STORE ACTION';
    }
  };

  return (
    <div
      className={`mt-3 p-5 rounded-[24px] border transition-all shadow-xs ${
        isConfirmed
          ? 'bg-emerald-50/40 border-emerald-200'
          : 'bg-[#fafaf7] border-stone-200/90 hover:border-stone-400'
      }`}
    >
      {/* Top Header */}
      <div className="flex items-center justify-between gap-3 mb-2.5">
        <div className="flex items-center gap-2.5">
          <div
            className={`w-8 h-8 rounded-full border border-stone-200 flex items-center justify-center shrink-0 ${
              isConfirmed ? 'bg-emerald-100' : 'bg-white'
            }`}
          >
            {getActionIcon()}
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block">
              {getActionTypeLabel()}
            </span>
            <h4 className="font-bold text-[#16181a] text-xs tracking-tight">
              {draftAction.title}
            </h4>
          </div>
        </div>

        <Badge
          variant={isConfirmed ? 'success' : 'warning'}
          dot
          size="sm"
        >
          {isConfirmed ? 'Confirmed & Applied' : 'Pending Confirmation'}
        </Badge>
      </div>

      {/* Description */}
      <p className="text-stone-600 text-[11.5px] mb-3 leading-relaxed">
        {draftAction.description}
      </p>

      {/* Payload Details Summary Grid */}
      {draftAction.payload && (
        <div className="p-3 rounded-2xl bg-white border border-stone-200/80 mb-3 grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-[10.5px]">
          {draftAction.action_type === 'RESTOCK_INVENTORY' && (
            <>
              <div>
                <span className="text-stone-400 block text-[9.5px]">Product</span>
                <span className="font-semibold text-stone-900 truncate block">
                  {draftAction.payload.product_name || draftAction.payload.product_id}
                </span>
              </div>
              <div>
                <span className="text-stone-400 block text-[9.5px]">Adjustment</span>
                <span className="font-bold text-[#8c5208]">
                  +{draftAction.payload.quantity} units
                </span>
              </div>
              <div>
                <span className="text-stone-400 block text-[9.5px]">Type</span>
                <span className="font-semibold text-stone-800">
                  {draftAction.payload.adjustment_type || 'RESTOCK'}
                </span>
              </div>
            </>
          )}

          {draftAction.action_type === 'CREATE_CAMPAIGN' && (
            <>
              <div>
                <span className="text-stone-400 block text-[9.5px]">Discount</span>
                <span className="font-bold text-emerald-700">
                  {draftAction.payload.discount_pct}% OFF
                </span>
              </div>
              <div>
                <span className="text-stone-400 block text-[9.5px]">Duration</span>
                <span className="font-semibold text-stone-800">
                  {draftAction.payload.start_date} to {draftAction.payload.end_date}
                </span>
              </div>
              <div>
                <span className="text-stone-400 block text-[9.5px]">Budget</span>
                <span className="font-semibold text-stone-800">
                  ₹{Number(draftAction.payload.budget_allocated || 0).toLocaleString()}
                </span>
              </div>
            </>
          )}

          {draftAction.action_type === 'ADD_PRODUCT' && (
            <>
              <div>
                <span className="text-stone-400 block text-[9.5px]">Category</span>
                <span className="font-semibold text-stone-800">
                  {draftAction.payload.category}
                </span>
              </div>
              <div>
                <span className="text-stone-400 block text-[9.5px]">Pricing</span>
                <span className="font-semibold text-stone-800">
                  Cost: ₹{draftAction.payload.cost_price} | Sell: ₹{draftAction.payload.selling_price}
                </span>
              </div>
              <div>
                <span className="text-stone-400 block text-[9.5px]">Initial Stock</span>
                <span className="font-bold text-emerald-700">
                  {draftAction.payload.current_stock} {draftAction.payload.unit || 'units'}
                </span>
              </div>
            </>
          )}

          {draftAction.action_type === 'END_CAMPAIGN' && (
            <div className="col-span-2 sm:col-span-3">
              <span className="text-stone-400 block text-[9.5px]">Impact</span>
              <span className="font-semibold text-stone-800">
                Mark status as COMPLETED and automatically restore standard non-discounted catalog prices.
              </span>
            </div>
          )}
        </div>
      )}

      {/* Confirmation State Action Bar */}
      {!isConfirmed ? (
        <div className="pt-1 flex flex-wrap items-center justify-between gap-3">
          <span className="text-[10px] text-stone-500 font-medium flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-stone-500 shrink-0" />
            <span>Requires merchant authorization before modifying live store accounts</span>
          </span>

          <button
            onClick={() => onConfirm(index, draftAction)}
            disabled={isConfirming}
            className="px-5 py-2.5 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs flex items-center gap-2 shadow-xs transition-all disabled:opacity-50 cursor-pointer"
          >
            {isConfirming ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin text-[#e0fd53]" />
                <span>Applying to Store DB...</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-[#e0fd53]" />
                <span>Confirm & Apply</span>
              </>
            )}
          </button>
        </div>
      ) : (
        <div className="pt-2 flex flex-wrap items-center justify-between gap-3 border-t border-emerald-200/60 mt-1">
          <div className="flex items-center gap-1.5 text-emerald-900 font-semibold text-[11px]">
            <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
            <span>
              {confirmedMessage || 'Action executed successfully and recorded in audited database logs.'}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {(draftAction.action_type === 'RESTOCK_INVENTORY' || draftAction.action_type === 'ADD_PRODUCT') && (
              <Link
                href="/demand"
                className="inline-flex items-center gap-1 text-[11px] font-bold text-[#16181a] hover:underline"
              >
                <span>View in Inventory</span>
                <ExternalLink className="w-3 h-3" />
              </Link>
            )}
            {(draftAction.action_type === 'CREATE_CAMPAIGN' || draftAction.action_type === 'END_CAMPAIGN') && (
              <Link
                href="/campaigns"
                className="inline-flex items-center gap-1 text-[11px] font-bold text-[#16181a] hover:underline"
              >
                <span>View in Campaigns</span>
                <ExternalLink className="w-3 h-3" />
              </Link>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const STATIC_WELCOME_MESSAGE = {
  role: 'assistant',
  content: `**Welcome to your LocalPulse AI Business Copilot!**\n\nI am connected directly to your store's live catalog, sales history, and demand forecasting pipeline.\n\n**Here are store operations you can execute right now:**\n- **Stockout & Restock:** Ask which items are running low or trigger audited inventory replenishment.\n- **Clearance & Pricing:** Calculate margin-safe discount strategies for surplus stock.\n- **Promotional Campaigns:** Draft instant discount offers with custom budgets and target SKUs.\n- **Demand Analytics:** Inspect 7-day projected unit velocities, runway days, and revenue estimates.\n- **Catalog Management:** Add new products or end active promotional campaigns with automatic retail price restoration.`,
  timestamp: '2026-10-31T04:00:00.000Z',
  evidence: [],
  draft_action: null,
  provider_info: 'LocalPulse Grounded Intelligence Engine',
};

export default function CopilotPage() {
  const { merchant } = useAuth();
  const [mounted, setMounted] = useState(false);
  const [messages, setMessages] = useState([STATIC_WELCOME_MESSAGE]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [confirmingIndex, setConfirmingIndex] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [activeCategoryTab, setActiveCategoryTab] = useState(0);

  // Multilingual Voice Recording via Sarvam AI
  const [isRecording, setIsRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState('auto');
  const [speechMode, setSpeechMode] = useState('transcribe');
  const [voiceNotice, setVoiceNotice] = useState('');
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Hydrate persisted conversation memory from MongoDB for the active merchant
  useEffect(() => {
    let isSubscribed = true;

    const fetchHistory = async () => {
      if (!mounted) return;
      try {
        setHistoryLoading(true);
        const res = await api.get('/copilot/history');
        if (isSubscribed) {
          if (res.data?.messages && res.data.messages.length > 0) {
            setMessages(res.data.messages);
          } else {
            setMessages([
              {
                ...STATIC_WELCOME_MESSAGE,
                content: `**Welcome to your LocalPulse AI Business Copilot for ${
                  merchant?.business_name || 'your store'
                }!**\n\nI am connected directly to your store's live catalog, sales history, and demand forecasting pipeline.\n\n**Here are store operations you can execute right now:**\n- **Stockout & Restock:** Ask which items are running low or trigger audited inventory replenishment.\n- **Clearance & Pricing:** Calculate margin-safe discount strategies for surplus stock.\n- **Promotional Campaigns:** Draft instant discount offers with custom budgets and target SKUs.\n- **Demand Analytics:** Inspect 7-day projected unit velocities, runway days, and revenue estimates.\n- **Catalog Management:** Add new products or end active promotional campaigns with automatic retail price restoration.`,
              },
            ]);
          }
        }
      } catch (err) {
        console.warn('Could not load merchant copilot history:', err);
        if (isSubscribed) {
          setMessages([STATIC_WELCOME_MESSAGE]);
        }
      } finally {
        if (isSubscribed) {
          setHistoryLoading(false);
        }
      }
    };

    fetchHistory();

    return () => {
      isSubscribed = false;
    };
  }, [mounted, merchant?.merchant_id]);

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleResetChat = async () => {
    if (window.confirm(`Clear chat history memory for ${merchant?.business_name || 'this merchant'} and start a fresh session?`)) {
      try {
        await api.delete('/copilot/history');
      } catch (err) {
        console.warn('Failed to clear remote copilot history:', err);
      }
      setMessages([
        {
          ...STATIC_WELCOME_MESSAGE,
          content: `**Welcome to your LocalPulse AI Business Copilot for ${
            merchant?.business_name || 'your store'
          }!**\n\nI am connected directly to your store's live catalog, sales history, and demand forecasting pipeline.\n\n**Here are store operations you can execute right now:**\n- **Stockout & Restock:** Ask which items are running low or trigger audited inventory replenishment.\n- **Clearance & Pricing:** Calculate margin-safe discount strategies for surplus stock.\n- **Promotional Campaigns:** Draft instant discount offers with custom budgets and target SKUs.\n- **Demand Analytics:** Inspect 7-day projected unit velocities, runway days, and revenue estimates.\n- **Catalog Management:** Add new products or end active promotional campaigns with automatic retail price restoration.`,
        },
      ]);
      setInputQuery('');
    }
  };

  const handleSendMessage = async (customQuery = null) => {
    const queryToSend = customQuery || inputQuery;
    if (!queryToSend.trim() || loading) return;

    const userMsg = {
      role: 'user',
      content: queryToSend.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!customQuery) setInputQuery('');
    setLoading(true);

    try {
      const res = await api.post('/copilot/chat', {
        message: userMsg.content,
        query: userMsg.content,
      });

      const assistantMsg = {
        message_id: res.data.message_id,
        role: 'assistant',
        content: res.data.reply,
        timestamp: res.data.timestamp || new Date().toISOString(),
        evidence: res.data.evidence || [],
        draft_action: res.data.draft_action || null,
        provider_info: res.data.provider_info || 'LocalPulse Rule-Based Intelligence',
        llm_configured: res.data.llm_configured,
        chart: res.data.chart || null,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error('Copilot request failed:', err);
      const serverDetail =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        (err.code === 'ERR_NETWORK'
          ? 'Network Error: Cannot connect to backend server. Please verify backend is running on port 8000.'
          : 'Sorry, I encountered an issue communicating with the LocalPulse advisory service.');
      const detailStr = typeof serverDetail === 'object' ? JSON.stringify(serverDetail) : serverDetail;
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `**Communication Error:** ${detailStr}`,
          timestamp: new Date().toISOString(),
          evidence: [],
          draft_action: null,
          provider_info: 'Error Service',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // ── Multilingual Voice-to-Text via Sarvam AI ─────────────────────────────
  const startVoiceRecording = async () => {
    try {
      setVoiceNotice('');
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Audio recording is not supported in this browser.');
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/mp4')
        ? 'audio/mp4'
        : 'audio/webm';

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());

        const rawBlob = new Blob(audioChunksRef.current, { type: mimeType });
        if (rawBlob.size === 0) {
          setVoiceNotice('Audio recording was empty. Please try again.');
          return;
        }

        setTranscribing(true);
        setVoiceNotice('Processing audio & transcribing via Sarvam AI (Saaras)...');

        try {
          let finalBlob = rawBlob;
          let filename = `speech_${Date.now()}.wav`;
          try {
            finalBlob = await convertBlobTo16kWav(rawBlob);
          } catch (convErr) {
            console.warn('WAV resampling fallback to raw recording:', convErr);
            const ext = mimeType.includes('mp4') ? 'mp4' : 'webm';
            filename = `speech_${Date.now()}.${ext}`;
          }

          const formData = new FormData();
          formData.append('audio', finalBlob, filename);
          if (selectedLanguage && selectedLanguage !== 'auto') {
            formData.append('language_code', selectedLanguage);
          }
          formData.append('mode', speechMode);

          const res = await api.post('/copilot/voice-to-text', formData);

          if (res.data?.success && res.data.transcript) {
            const transcribedText = res.data.transcript;
            setInputQuery(transcribedText);
            setVoiceNotice(
              `Converted from ${res.data.language_code || 'audio'} via ${res.data.provider || 'Sarvam AI'}`
            );
            setTimeout(() => setVoiceNotice(''), 4000);
          } else {
            setVoiceNotice('No clear speech recognized. Please speak closer to the microphone.');
            setTimeout(() => setVoiceNotice(''), 4000);
          }
        } catch (err) {
          console.error('Sarvam STT failed:', err);
          const detailMsg =
            err.response?.data?.detail ||
            'Sarvam AI STT error. Check that SARVAM_API_KEY is configured in backend/.env';
          setVoiceNotice(`Voice Error: ${detailMsg}`);
          setTimeout(() => setVoiceNotice(''), 6000);
        } finally {
          setTranscribing(false);
        }
      };

      mediaRecorder.start(250);
      setIsRecording(true);
    } catch (err) {
      console.error('Microphone access denied or error:', err);
      alert('Could not access microphone. Please ensure microphone permissions are granted.');
    }
  };

  const stopVoiceRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // Confirm proposed action
  const handleConfirmAction = async (msgIndex, draftAction) => {
    setConfirmingIndex(msgIndex);
    try {
      const res = await api.post('/copilot/confirm-action', {
        action_type: draftAction.action_type,
        payload: draftAction.payload,
      });

      if (res.data.success) {
        setMessages((prev) =>
          prev.map((m, idx) =>
            idx === msgIndex
              ? {
                  ...m,
                  draft_action: {
                    ...m.draft_action,
                    status: 'CONFIRMED',
                  },
                  confirmation_message: res.data.message,
                  result_data: res.data.result_data,
                }
              : m
          )
        );
      } else {
        alert(`Action failed: ${res.data.message || 'Unknown reason'}`);
      }
    } catch (err) {
      console.error('Confirmation error:', err);
      const serverDetail =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        (err.code === 'ERR_NETWORK'
          ? 'Network Error: Cannot connect to backend server at ' + (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') + '. Please verify backend is running.'
          : err.message);
      alert(`Execution failed: ${serverDetail}`);
    } finally {
      setConfirmingIndex(null);
    }
  };

  return (
    <AppLayout
      title="AI Business Copilot"
      subtitle="Audited operational decision engine grounded strictly in live catalog, sales, and demand projections"
      fullHeight={true}
    >
      <div className="flex-1 flex flex-col min-h-0 bg-white rounded-[28px] border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)] overflow-hidden">
        {/* Transparency Status Bar */}
        <div className="px-6 py-3 bg-[#f7f8f4] border-b border-stone-200/90 flex flex-wrap items-center justify-between gap-3 text-xs shrink-0">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#e0fd53] border border-[#16181a] shrink-0" />
            <span className="font-bold text-[#16181a]">
              LocalPulse Grounded Advisory
            </span>
            <span className="text-stone-300">•</span>
            <span className="text-stone-500 text-[11px] truncate max-w-xs sm:max-w-md">
              Grounded in {merchant?.business_name || 'live'} MongoDB records
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden md:flex items-center gap-1.5 text-[11px] text-[#16181a] bg-white border border-stone-200/90 px-3 py-1 rounded-full font-semibold shadow-2xs">
              <Sparkles className="w-3.5 h-3.5 text-[#16181a]" />
              <span>Multi-Turn Memory</span>
            </div>

            <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-[#16181a] bg-[#e0fd53] border border-[#d6f447] px-3 py-1 rounded-full font-bold shadow-2xs">
              <ShieldAlert className="w-3.5 h-3.5 text-[#16181a]" />
              <span>Strict Confirmation</span>
            </div>

            <button
              onClick={handleResetChat}
              className="flex items-center gap-1 text-[11px] font-semibold text-stone-600 hover:text-[#16181a] bg-white hover:bg-stone-50 border border-stone-200/90 px-3 py-1 rounded-full transition-colors cursor-pointer shadow-2xs"
              title="Clear persisted memory for this merchant"
            >
              <RotateCcw className="w-3 h-3 text-stone-400" />
              <span>Reset Chat</span>
            </button>
          </div>
        </div>

        {/* Chat Message Stream */}
        <div
          ref={chatContainerRef}
          className="flex-1 min-h-0 overflow-y-auto p-5 sm:p-6 space-y-4 bg-[#fbfbf9]"
        >
          {historyLoading ? (
            <div className="flex flex-col items-center justify-center py-24 text-stone-400 gap-2.5">
              <Loader2 className="w-6 h-6 text-[#16181a] animate-spin" />
              <span className="text-xs font-semibold">Restoring {merchant?.business_name || 'store'} conversation memory...</span>
            </div>
          ) : (
            messages.map((msg, index) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={index}
                  className={`flex gap-3 max-w-3xl ${
                    isUser ? 'ml-auto flex-row-reverse' : ''
                  }`}
                >
                  {/* Avatar */}
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 font-bold shadow-xs ${
                      isUser
                        ? 'bg-[#16181a] text-[#e0fd53]'
                        : 'bg-white border border-stone-200/90 text-[#16181a]'
                    }`}
                  >
                    {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  {/* Message Bubble */}
                  <div
                    className={`relative group p-4 sm:p-5 rounded-[22px] text-xs space-y-2.5 transition-all ${
                      isUser
                        ? 'bg-[#16181a] text-white rounded-tr-xs shadow-xs max-w-xl'
                        : 'bg-white border border-stone-200/90 text-[#16181a] rounded-tl-xs shadow-[0_2px_12px_rgba(20,24,20,0.02)] w-full'
                    }`}
                  >
                    {/* Top Bar for Assistant Message: timestamp & copy */}
                    {!isUser && (
                      <div className="flex items-center justify-between pb-1 border-b border-stone-100 text-[10px] text-stone-400">
                        <span className="font-semibold text-stone-600">
                          LocalPulse Copilot
                        </span>
                        <div className="flex items-center gap-2">
                          <span>
                            {mounted && msg.timestamp
                              ? new Date(msg.timestamp).toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })
                              : ''}
                          </span>
                          <button
                            onClick={() => handleCopy(msg.content, index)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:text-stone-700 rounded-md hover:bg-stone-100 cursor-pointer"
                            title="Copy response"
                          >
                            {copiedIndex === index ? (
                              <Check className="w-3 h-3 text-emerald-600" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Formatted Content Body */}
                    {isUser ? (
                      <p className="whitespace-pre-line text-xs font-normal leading-relaxed text-stone-100">
                        {msg.content}
                      </p>
                    ) : (
                      <FormattedMessage content={msg.content} />
                    )}

                    {/* Optional chart (shown only when the merchant asks for it) */}
                    {!isUser && msg.chart && <ChartOffer chart={msg.chart} />}

                    {/* Grounded Evidence Citations */}
                    {msg.evidence && msg.evidence.length > 0 && (
                      <div className="pt-2.5 border-t border-stone-100 mt-2 space-y-1.5">
                        <p className="text-[10px] font-bold text-stone-400 uppercase tracking-widest flex items-center gap-1">
                          <TrendingUp className="w-3 h-3 text-[#16181a]" />
                          <span>Grounded Citations</span>
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.evidence.map((ev, evIdx) => (
                            <div
                              key={evIdx}
                              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#f7f8f4] border border-stone-200/90 text-[10.5px] text-stone-700 shadow-2xs"
                              title={ev.context}
                            >
                              <span className="font-bold text-[#16181a]">
                                {ev.source_metric}:
                              </span>
                              <span className="font-semibold text-stone-800">
                                {ev.value}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Proposed Action Card */}
                    {msg.draft_action && (
                      <DraftActionCard
                        draftAction={msg.draft_action}
                        index={index}
                        isConfirming={confirmingIndex === index}
                        onConfirm={handleConfirmAction}
                        confirmedMessage={msg.confirmation_message}
                      />
                    )}

                    {/* Provider Info Tag */}
                    {!isUser && msg.provider_info && (
                      <p className="text-[9.5px] text-stone-400 text-right pt-1 font-mono">
                        Source: {msg.provider_info}
                      </p>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {/* Loading Animation Bubble */}
          {loading && (
            <div className="flex gap-3 max-w-md animate-in fade-in">
              <div className="w-8 h-8 rounded-full bg-white border border-stone-200/90 flex items-center justify-center text-[#16181a] shrink-0 shadow-xs">
                <Bot className="w-4 h-4" />
              </div>
              <div className="p-4 rounded-2xl bg-white border border-stone-200/90 text-xs text-stone-600 flex items-center gap-2.5 shadow-xs">
                <Loader2 className="w-4 h-4 text-[#16181a] animate-spin" />
                <span className="font-semibold">
                  Querying live catalog & calculating velocities...
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Categorized Quick Query Pill Drawer (Dribbble horizontal pill layout) */}
        <div className="px-5 py-3 bg-white border-t border-stone-100 shrink-0">
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className="flex items-center gap-1.5 text-[10px] font-bold text-stone-400 uppercase tracking-widest">
              <Sparkles className="w-3.5 h-3.5 text-[#16181a]" />
              <span>Operational Quick Actions</span>
            </div>

            {/* Category Filter Tabs */}
            <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
              {SUGGESTED_CATEGORIES.map((cat, idx) => {
                const Icon = cat.icon;
                const isActive = activeCategoryTab === idx;
                return (
                  <button
                    key={idx}
                    onClick={() => setActiveCategoryTab(idx)}
                    className={`px-3 py-1 rounded-full text-[10.5px] font-semibold transition-all flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
                      isActive
                        ? 'bg-[#16181a] text-white shadow-2xs font-bold'
                        : 'bg-stone-50 text-stone-600 hover:bg-stone-100 hover:text-stone-900 border border-stone-200/80'
                    }`}
                  >
                    <Icon className="w-3 h-3" />
                    <span>{cat.category}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Quick Query Pills for Active Category */}
          <div className="flex flex-wrap items-center gap-2">
            {SUGGESTED_CATEGORIES[activeCategoryTab]?.queries.map((sq, i) => (
              <button
                key={i}
                onClick={() => handleSendMessage(sq)}
                disabled={loading}
                className="text-[11px] px-3.5 py-1.5 rounded-full bg-stone-50 hover:bg-stone-100 border border-stone-200/90 text-stone-800 font-semibold transition-all shadow-2xs cursor-pointer flex items-center gap-1.5 disabled:opacity-50"
              >
                <span>{sq}</span>
                <ArrowRight className="w-3 h-3 text-stone-400" />
              </button>
            ))}
          </div>
        </div>

        {/* Voice Feedback Banner */}
        {(voiceNotice || isRecording || transcribing) && (
          <div className="px-5 py-2.5 bg-[#16181a] text-white flex items-center justify-between text-xs animate-in fade-in shrink-0">
            <div className="flex items-center gap-2">
              {isRecording ? (
                <>
                  <span className="w-2.5 h-2.5 rounded-full bg-[#c25e4e] animate-ping" />
                  <span className="font-semibold text-stone-200">Listening to voice... Speak in any Indian language or English.</span>
                </>
              ) : transcribing ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-[#e0fd53]" />
                  <span className="text-stone-200">Converting speech to text via Sarvam AI Saaras...</span>
                </>
              ) : (
                <>
                  <Volume2 className="w-3.5 h-3.5 text-[#e0fd53]" />
                  <span className="text-stone-300">{voiceNotice}</span>
                </>
              )}
            </div>

            {isRecording && (
              <button
                type="button"
                onClick={stopVoiceRecording}
                className="px-3.5 py-1 rounded-full bg-[#c25e4e] hover:bg-[#a43b27] text-white font-bold text-[11px] flex items-center gap-1 cursor-pointer transition-colors shadow-2xs"
              >
                <MicOff className="w-3 h-3" />
                <span>Done Speaking</span>
              </button>
            )}
          </div>
        )}

        {/* Input Bar */}
        <div className="p-3 sm:p-4 bg-white border-t border-stone-100 shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2 sm:gap-3"
          >
            {/* Multilingual Voice Recording Trigger Button */}
            <div className="relative shrink-0 flex items-center gap-1.5">
              <button
                type="button"
                onClick={isRecording ? stopVoiceRecording : startVoiceRecording}
                disabled={loading || transcribing}
                className={`w-11 h-11 rounded-full flex items-center justify-center transition-all cursor-pointer shadow-xs ${
                  isRecording
                    ? 'bg-[#c25e4e] text-white ring-4 ring-[#c25e4e]/20 animate-pulse'
                    : transcribing
                    ? 'bg-stone-100 text-[#16181a]'
                    : 'bg-stone-50 hover:bg-stone-100 text-stone-700 border border-stone-200/90'
                }`}
                title={isRecording ? 'Click to stop recording' : 'Speak query in Hindi, Tamil, Telugu, Kannada, English, etc. (Sarvam AI)'}
              >
                {transcribing ? (
                  <Loader2 className="w-4 h-4 animate-spin text-[#16181a]" />
                ) : isRecording ? (
                  <MicOff className="w-4 h-4 text-white" />
                ) : (
                  <Mic className="w-4 h-4" />
                )}
              </button>

              {/* Language Dropdown Filter for Indic Voice */}
              <div className="hidden md:flex items-center gap-1 bg-[#f7f8f4] border border-stone-200/90 rounded-full px-3 py-1.5 text-[11px] text-stone-700">
                <Globe className="w-3 h-3 text-[#16181a] shrink-0" />
                <select
                  value={selectedLanguage}
                  onChange={(e) => setSelectedLanguage(e.target.value)}
                  className="bg-transparent border-0 text-stone-800 font-semibold text-[10.5px] focus:outline-hidden cursor-pointer"
                  title="Target Spoken Language for Sarvam AI"
                >
                  <option value="auto">Auto Detect (23 Languages)</option>
                  <option value="hi-IN">Hindi (हिन्दी)</option>
                  <option value="en-IN">Indian English</option>
                  <option value="ta-IN">Tamil (தமிழ்)</option>
                  <option value="te-IN">Telugu (తెలుగు)</option>
                  <option value="kn-IN">Kannada (ಕನ್ನಡ)</option>
                  <option value="ml-IN">Malayalam (മലയാളം)</option>
                  <option value="mr-IN">Marathi (मराठी)</option>
                  <option value="bn-IN">Bengali (বাংলা)</option>
                  <option value="gu-IN">Gujarati (ગુજરાતી)</option>
                  <option value="pa-IN">Punjabi (ਪੰਜਾਬੀ)</option>
                  <option value="od-IN">Odia (ଓଡ଼ିଆ)</option>
                  <option value="ur-IN">Urdu (اردو)</option>
                </select>
              </div>
            </div>

            <div className="relative flex-1">
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                placeholder={isRecording ? "Listening to your voice... Speak now" : "Type query or click Mic to speak in Hindi, English, Tamil, Telugu..."}
                className={`w-full px-5 py-3 rounded-full border text-xs placeholder-stone-400 focus:outline-hidden shadow-2xs transition-all ${
                  isRecording
                    ? 'border-[#c25e4e] bg-[#fbe8e4]/30 text-[#16181a] ring-2 ring-[#c25e4e]/10'
                    : 'border-stone-200/90 bg-[#f7f8f4] focus:bg-white text-[#16181a] focus:border-[#16181a] focus:ring-2 focus:ring-[#16181a]/10'
                }`}
              />
            </div>
            <button
              type="submit"
              disabled={loading || !inputQuery.trim()}
              className="px-6 py-3 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs flex items-center gap-2 shadow-xs transition-all disabled:opacity-40 cursor-pointer shrink-0"
            >
              {loading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-[#e0fd53]" />
              ) : (
                <Send className="w-3.5 h-3.5 text-[#e0fd53]" />
              )}
              <span>Send</span>
            </button>
          </form>
        </div>
      </div>
    </AppLayout>
  );
}
