import logging
import os
from typing import AsyncIterator

import httpx

from .base import ASRProvider

logger = logging.getLogger(__name__)

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text-translate"


class SarvamASR(ASRProvider):
    """Sarvam AI speech-to-text with support for Hindi, Telugu, English, and code-switching."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY is required for SarvamASR")

    async def transcribe(self, audio_data: bytes, language: str = "en") -> dict:
        lang_map = {"en": "en-IN", "hi": "hi-IN", "te": "te-IN"}
        sarvam_lang = lang_map.get(language, "en-IN")

        headers = {
            "api-subscription-key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    SARVAM_STT_URL,
                    headers=headers,
                    files={"file": ("audio.wav", audio_data, "audio/wav")},
                    data={
                        "language_code": sarvam_lang,
                        "model": "saarika:v2",
                        "with_timestamps": "false",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            return {
                "text": data.get("transcript", ""),
                "confidence": data.get("confidence", 0.8),
                "language": language,
            }
        except Exception:
            logger.exception("[SarvamASR] Transcription failed")
            return {"text": "", "confidence": 0.0, "language": language}

    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes], language: str = "en"
    ) -> AsyncIterator[dict]:
        collected = bytearray()
        async for chunk in audio_stream:
            collected.extend(chunk)
            if len(collected) >= 32000:
                result = await self.transcribe(bytes(collected), language)
                collected.clear()
                yield {
                    "text": result["text"],
                    "is_final": True,
                    "confidence": result["confidence"],
                    "language": result["language"],
                }
        if collected:
            result = await self.transcribe(bytes(collected), language)
            yield {
                "text": result["text"],
                "is_final": True,
                "confidence": result["confidence"],
                "language": result["language"],
            }
