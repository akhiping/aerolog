from abc import ABC, abstractmethod
from typing import AsyncIterator, Callable, Awaitable


class ASRProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_data: bytes, language: str = "en") -> dict:
        """Returns {"text": str, "confidence": float, "language": str}"""
        ...

    @abstractmethod
    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes], language: str = "en"
    ) -> AsyncIterator[dict]:
        """Yields partial transcription results {"text": str, "is_final": bool, "confidence": float}"""
        ...


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, language: str = "en", voice: str = "default") -> bytes:
        """Returns audio bytes (WAV format)"""
        ...

    @abstractmethod
    async def synthesize_stream(
        self, text: str, language: str = "en", voice: str = "default"
    ) -> AsyncIterator[bytes]:
        """Yields audio chunks for streaming playback"""
        ...


class VoiceProvider(ABC):
    @abstractmethod
    async def start_session(
        self,
        session_id: str,
        on_transcript: Callable[[str, float], Awaitable[None]],
        on_audio: Callable[[bytes], Awaitable[None]],
    ) -> None:
        ...

    @abstractmethod
    async def end_session(self, session_id: str) -> None:
        ...

    @abstractmethod
    async def handle_audio_input(self, session_id: str, audio_data: bytes) -> None:
        ...

    @abstractmethod
    async def handle_text_input(self, session_id: str, text: str) -> None:
        """For LocalSim / browser Web Speech API mode — accept text directly."""
        ...

    @abstractmethod
    async def send_response(self, session_id: str, text: str, language: str = "en") -> None:
        ...


class TelephonyProvider(ABC):
    @abstractmethod
    async def make_call(self, to_number: str, message: str) -> dict:
        """Initiate outbound call. Returns {"call_id": str, "status": str}"""
        ...

    @abstractmethod
    async def handle_inbound_webhook(self, request_data: dict) -> dict:
        """Process inbound call webhook. Returns response dict for the telephony platform."""
        ...
