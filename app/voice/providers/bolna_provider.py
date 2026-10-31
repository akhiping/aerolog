import logging
import os
from typing import AsyncIterator, Callable, Awaitable

import httpx

from .base import VoiceProvider, TelephonyProvider

logger = logging.getLogger(__name__)

BOLNA_API_BASE = "https://api.bolna.dev/v2"


class BolnaProvider(VoiceProvider, TelephonyProvider):
    """Bolna voice agent integration for phone-based voice interactions."""

    def __init__(
        self,
        api_key: str | None = None,
        agent_id: str | None = None,
    ):
        self.api_key = api_key or os.getenv("BOLNA_API_KEY", "")
        self.agent_id = agent_id or os.getenv("BOLNA_AGENT_ID", "")
        if not self.api_key:
            raise ValueError("BOLNA_API_KEY is required for BolnaProvider")
        self._sessions: dict[str, dict] = {}

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def start_session(
        self,
        session_id: str,
        on_transcript: Callable[[str, float], Awaitable[None]],
        on_audio: Callable[[bytes], Awaitable[None]],
    ) -> None:
        self._sessions[session_id] = {
            "on_transcript": on_transcript,
            "on_audio": on_audio,
        }
        logger.info("[Bolna] Session started: %s", session_id)

    async def end_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        logger.info("[Bolna] Session ended: %s", session_id)

    async def handle_audio_input(self, session_id: str, audio_data: bytes) -> None:
        logger.info("[Bolna] Audio input received for session %s (%d bytes)", session_id, len(audio_data))

    async def handle_text_input(self, session_id: str, text: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            await session["on_transcript"](text, 0.9)

    async def send_response(self, session_id: str, text: str, language: str = "en") -> None:
        logger.info("[Bolna] Sending response for session %s: %s", session_id, text[:120])

    async def make_call(self, to_number: str, message: str) -> dict:
        payload = {
            "agent_id": self.agent_id,
            "recipient_phone_number": to_number,
            "first_message": message,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{BOLNA_API_BASE}/call",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
            call_id = data.get("call_id", data.get("id", "unknown"))
            logger.info("[Bolna] Outbound call initiated: %s -> %s", call_id, to_number)
            return {"call_id": call_id, "status": "initiated"}
        except Exception:
            logger.exception("[Bolna] Failed to initiate call to %s", to_number)
            return {"call_id": "", "status": "failed"}

    async def handle_inbound_webhook(self, request_data: dict) -> dict:
        event = request_data.get("event", "unknown")
        logger.info("[Bolna] Inbound webhook event: %s", event)
        if event == "call.started":
            session_id = request_data.get("call_id", "")
            return {"status": "ok", "session_id": session_id}
        elif event == "transcription":
            session_id = request_data.get("call_id", "")
            text = request_data.get("transcript", "")
            session = self._sessions.get(session_id)
            if session:
                await session["on_transcript"](text, 0.9)
            return {"status": "ok"}
        return {"status": "ok"}
