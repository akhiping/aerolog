import logging
import re
from datetime import datetime, timezone
from typing import AsyncIterator, Callable, Awaitable

from .base import ASRProvider, TTSProvider, VoiceProvider, TelephonyProvider

logger = logging.getLogger(__name__)

INDIC_PATTERNS = re.compile(
    r"[ऀ-ॿ]|[ఀ-౿]"  # Devanagari (Hindi) or Telugu ranges
)


def _detect_language(text: str) -> str:
    if INDIC_PATTERNS.search(text):
        hindi_count = len(re.findall(r"[ऀ-ॿ]", text))
        telugu_count = len(re.findall(r"[ఀ-౿]", text))
        if telugu_count > hindi_count:
            return "te"
        return "hi"
    return "en"


class LocalSimASR(ASRProvider):
    async def transcribe(self, audio_data: bytes, language: str = "en") -> dict:
        text = audio_data.decode("utf-8", errors="replace")
        detected = _detect_language(text)
        logger.info("[LocalSimASR] Transcribed: %s", text[:120])
        return {"text": text, "confidence": 0.95, "language": detected}

    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes], language: str = "en"
    ) -> AsyncIterator[dict]:
        async for chunk in audio_stream:
            text = chunk.decode("utf-8", errors="replace")
            detected = _detect_language(text)
            yield {"text": text, "is_final": True, "confidence": 0.95, "language": detected}


class LocalSimTTS(TTSProvider):
    async def synthesize(self, text: str, language: str = "en", voice: str = "default") -> bytes:
        logger.info("[LocalSimTTS] Would speak (%s): %s", language, text[:200])
        return b""

    async def synthesize_stream(
        self, text: str, language: str = "en", voice: str = "default"
    ) -> AsyncIterator[bytes]:
        logger.info("[LocalSimTTS] Stream speak (%s): %s", language, text[:200])
        yield b""


class LocalSimVoice(VoiceProvider):
    def __init__(self):
        self._sessions: dict[str, dict] = {}

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
        logger.info("[LocalSimVoice] Session started: %s", session_id)

    async def end_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        logger.info("[LocalSimVoice] Session ended: %s", session_id)

    async def handle_audio_input(self, session_id: str, audio_data: bytes) -> None:
        session = self._sessions.get(session_id)
        if not session:
            logger.warning("[LocalSimVoice] No session: %s", session_id)
            return
        text = audio_data.decode("utf-8", errors="replace")
        await session["on_transcript"](text, 0.95)

    async def handle_text_input(self, session_id: str, text: str) -> None:
        session = self._sessions.get(session_id)
        if not session:
            logger.warning("[LocalSimVoice] No session: %s", session_id)
            return
        await session["on_transcript"](text, 0.95)

    async def send_response(self, session_id: str, text: str, language: str = "en") -> None:
        session = self._sessions.get(session_id)
        if not session:
            return
        logger.info("[LocalSimVoice] Agent says (%s): %s", language, text[:200])
        await session["on_audio"](b"")


class LocalSimTelephony(TelephonyProvider):
    def __init__(self):
        self.call_log: list[dict] = []

    async def make_call(self, to_number: str, message: str) -> dict:
        entry = {
            "call_id": f"local-{len(self.call_log)+1}",
            "to": to_number,
            "message": message,
            "status": "simulated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.call_log.append(entry)
        logger.info("[LocalSimTelephony] Simulated call to %s: %s", to_number, message[:120])
        return {"call_id": entry["call_id"], "status": "simulated"}

    async def handle_inbound_webhook(self, request_data: dict) -> dict:
        logger.info("[LocalSimTelephony] Inbound webhook (sim): %s", request_data)
        return {"status": "ok", "message": "Local simulation — no real call processed"}
