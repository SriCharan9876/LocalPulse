// Global event for Gemini rate limit / quota exceeded notifications
export const GEMINI_RATE_LIMIT_EVENT = 'localpulse:gemini-rate-limit';

let lastTriggeredTimestamp = 0;
const COOLDOWN_MS = 6000; // Prevent spamming duplicate popups within 6 seconds

export function triggerGeminiRateLimitModal(detail = {}) {
  if (typeof window === 'undefined') return;
  const now = Date.now();
  if (now - lastTriggeredTimestamp < COOLDOWN_MS) {
    return;
  }
  lastTriggeredTimestamp = now;

  window.dispatchEvent(
    new CustomEvent(GEMINI_RATE_LIMIT_EVENT, {
      detail: {
        timestamp: now,
        title: detail.title || 'Gemini AI Limits Reached',
        message:
          detail.message ||
          'The Gemini AI rate limit or quota has been reached. Please wait a few moments and try again after some time to explore all AI capabilities.',
        ...detail,
      },
    })
  );
}
