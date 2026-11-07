import contextvars
import logging

logger = logging.getLogger(__name__)

# Context variable to track if Gemini rate limit was encountered in the current request
_gemini_rate_limited: contextvars.ContextVar[bool] = contextvars.ContextVar("gemini_rate_limited", default=False)


def is_gemini_rate_limit_error(e: Exception) -> bool:
    """
    Checks if an exception indicates Gemini API rate limit or quota exhaustion.
    Catches 429 status codes, RESOURCE_EXHAUSTED errors, and quota-related messages.
    """
    if e is None:
        return False

    err_str = str(e).lower()

    # Check status code attribute if present (e.g. google.genai.errors.APIError or httpx.HTTPStatusError)
    status_code = getattr(e, "code", None) or getattr(e, "status_code", None)
    if status_code in (429, "429"):
        return True

    keywords = [
        "429",
        "resource_exhausted",
        "resourceexhausted",
        "quota exceeded",
        "quota_exceeded",
        "exceeded your current quota",
        "check quota",
        "rate limit",
        "rate_limit",
        "too many requests",
        "resource has been exhausted",
    ]
    return any(k in err_str for k in keywords)


def record_gemini_rate_limit() -> None:
    """Mark that a Gemini rate limit or quota exceeded was encountered in the current request context."""
    _gemini_rate_limited.set(True)
    logger.warning("Gemini rate limit / quota exhaustion recorded in request context.")


def has_gemini_rate_limit_occurred() -> bool:
    """Returns True if a Gemini rate limit or quota exceeded occurred in the current request."""
    return _gemini_rate_limited.get()


def reset_gemini_rate_limit() -> None:
    """Resets the context variable for a new request."""
    _gemini_rate_limited.set(False)
