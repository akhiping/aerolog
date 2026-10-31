import logging
import os
from typing import AsyncIterator

import httpx

from .base import TTSProvider

logger = logging.getLogger(__name__)

CARTESIA_URL = "https://api.cartesia.ai/tts/bytes"


class CartesiaTTS(TTSProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("CARTESIA_API_KEY", "")
        if not self.api_key:
            raise ValueError("CARTESIA_API_KEY is required for CartesiaTTS")
        self.default_voice_id = "a0e99841-438c-4a64-b679-ae501e7d6091"

    async def synthesize(self, text: str, language: str = "en", voice: str = "default") -> bytes:
        voice_id = self.default_voice_id if voice == "default" else voice
        headers = {
            "X-API-Key": self.api_key,
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json",
        }
        payload = {
            "model_id": "sonic-english",
            "transcript": text,
            "voice": {"mode": "id", "id": voice_id},
            "output_format": {"container": "wav", "encoding": "pcm_s16le", "sample_rate": 24000},
        }
        if language != "en":
            payload["model_id"] = "sonic-multilingual"
            payload["language"] = language

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(CARTESIA_URL, headers=headers, json=payload)
                resp.raise_for_status()
                return resp.content
        except Exception:
            logger.exception("[CartesiaTTS] Synthesis failed")
            return b""

    async def synthesize_stream(
        self, text: str, language: str = "en", voice: str = "default"
    ) -> AsyncIterator[bytes]:
        audio = await self.synthesize(text, language, voice)
        if audio:
            chunk_size = 4096
            for i in range(0, len(audio), chunk_size):
                yield audio[i : i + chunk_size]
