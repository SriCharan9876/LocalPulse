"""
Service integration for Sarvam AI Speech-to-Text (STT).
Supports 22 Indian languages + English using the Saaras (saaras:v4) model.
Provides automatic language detection, translation, or transcription modes.
"""

import logging
from typing import Dict, Any, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"

class SarvamVoiceService:
    """Manages voice audio file uploads and speech-to-text transcription via Sarvam AI API."""

    @property
    def is_configured(self) -> bool:
        """Returns True if Sarvam AI subscription key is set in configuration."""
        return bool(settings.SARVAM_API_KEY and settings.SARVAM_API_KEY.strip())

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        content_type: str = "audio/wav",
        language_code: Optional[str] = None,
        model: Optional[str] = None,
        mode: str = "transcribe"
    ) -> Dict[str, Any]:
        """
        Transcribes speech audio using Sarvam AI Saaras model.
        
        Args:
            audio_bytes: Raw bytes of the audio recording
            filename: Name of the file with extension (e.g. 'speech.webm' or 'speech.wav')
            content_type: MIME type of the audio (e.g. 'audio/webm', 'audio/wav', 'audio/mp4')
            language_code: BCP-47 language tag (e.g. 'hi-IN', 'ta-IN', 'te-IN', 'kn-IN', 'en-IN') or None for auto-detection
            model: Sarvam model name ('saaras:v4' or 'saaras:v3')
            mode: 'transcribe' (native script), 'translate' (translates speech directly to English), 'verbatim', 'codemix'
        
        Returns:
            dict containing:
                - transcript: Transcribed/translated text
                - language_code: Detected or processed BCP-47 language code
                - provider: "sarvam"
                - model: Model used
        """
        if not self.is_configured:
            raise ValueError(
                "Sarvam AI API key is not configured. Please set SARVAM_API_KEY in backend/.env"
            )

        api_key = settings.SARVAM_API_KEY.strip()
        selected_model = model or settings.SARVAM_STT_MODEL or "saaras:v4"

        headers = {
            "api-subscription-key": api_key,
        }

        # Sarvam expects multipart/form-data with 'file', 'model', and optional 'language_code' / 'mode'
        files = {
            "file": (filename, audio_bytes, content_type)
        }
        data = {
            "model": selected_model,
            "mode": mode,
        }
        if language_code and language_code.strip() and language_code.lower() != "auto":
            data["language_code"] = language_code.strip()

        logger.info(f"Sending audio ({len(audio_bytes)} bytes) to Sarvam AI STT (model={selected_model}, mode={mode})")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    SARVAM_STT_URL,
                    headers=headers,
                    files=files,
                    data=data
                )
                response.raise_for_status()
                result = response.json()

                transcript = result.get("transcript", "").strip()
                detected_lang = result.get("language_code")

                return {
                    "success": True,
                    "transcript": transcript,
                    "language_code": detected_lang,
                    "provider": "Sarvam AI (Saaras)",
                    "model": selected_model,
                    "request_id": result.get("request_id"),
                }

            except httpx.HTTPStatusError as e:
                err_text = e.response.text
                logger.error(f"Sarvam AI STT API error ({e.response.status_code}): {err_text}")
                return {
                    "success": False,
                    "error": f"Sarvam AI API returned status {e.response.status_code}: {err_text}",
                    "transcript": "",
                    "language_code": None,
                    "provider": "Sarvam AI"
                }
            except Exception as e:
                logger.error(f"Unexpected error communicating with Sarvam AI STT: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "transcript": "",
                    "language_code": None,
                    "provider": "Sarvam AI"
                }


sarvam_voice_service = SarvamVoiceService()
