import logging
import os
from typing import AsyncIterator

import httpx

from .base import TTSProvider

logger = logging.getLogger(__name__)

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


class SarvamTTS(TTSProvider):
    """Sarvam AI TTS with Hindi, Telugu, English support."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY is required for SarvamTTS")

    async def synthesize(self, text: str, language: str = "en", voice: str = "default") -> bytes:
        lang_map = {"en": "en-IN", "hi": "hi-IN", "te": "te-IN"}
        sarvam_lang = lang_map.get(language, "en-IN")

        speaker_map = {"en": "meera", "hi": "meera", "te": "meera"}
        speaker = speaker_map.get(language, "meera") if voice == "default" else voice

        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": [text],
            "target_language_code": sarvam_lang,
            "speaker": speaker,
            "model": "bulbul:v1",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(SARVAM_TTS_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            import base64
            audio_b64 = data.get("audios", [None])[0]
            if audio_b64:
                return base64.b64decode(audio_b64)
            return b""
        except Exception:
            logger.exception("[SarvamTTS] Synthesis failed")
            return b""

    async def synthesize_stream(
        self, text: str, language: str = "en", voice: str = "default"
    ) -> AsyncIterator[bytes]:
        audio = await self.synthesize(text, language, voice)
        if audio:
            chunk_size = 4096
            for i in range(0, len(audio), chunk_size):
                yield audio[i : i + chunk_size]
