import logging
import os
from typing import AsyncIterator

import httpx

from .base import ASRProvider

logger = logging.getLogger(__name__)

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


class DeepgramASR(ASRProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY", "")
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY is required for DeepgramASR")

    async def transcribe(self, audio_data: bytes, language: str = "en") -> dict:
        params = {
            "model": "nova-2",
            "smart_format": "true",
            "punctuate": "true",
            "detect_language": "true",
        }
        if language != "auto":
            params["language"] = language

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    DEEPGRAM_URL, params=params, headers=headers, content=audio_data
                )
                resp.raise_for_status()
                data = resp.json()

            channel = data["results"]["channels"][0]
            alt = channel["alternatives"][0]
            detected = channel.get("detected_language", language)
            return {
                "text": alt["transcript"],
                "confidence": alt.get("confidence", 0.0),
                "language": detected,
            }
        except Exception:
            logger.exception("[DeepgramASR] Transcription failed")
            return {"text": "", "confidence": 0.0, "language": language}

    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes], language: str = "en"
    ) -> AsyncIterator[dict]:
        collected = bytearray()
        async for chunk in audio_stream:
            collected.extend(chunk)
            if len(collected) >= 16000:
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
