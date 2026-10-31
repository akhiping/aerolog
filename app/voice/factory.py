import logging
import os

from .providers.base import ASRProvider, TTSProvider, VoiceProvider, TelephonyProvider
from .providers.local_sim import LocalSimASR, LocalSimTTS, LocalSimVoice, LocalSimTelephony

logger = logging.getLogger(__name__)


def create_asr_provider(provider: str | None = None) -> ASRProvider:
    provider = provider or os.getenv("ASR_PROVIDER", "local_sim")
    if provider == "deepgram":
        from .providers.deepgram_asr import DeepgramASR
        return DeepgramASR()
    elif provider == "sarvam":
        from .providers.sarvam_asr import SarvamASR
        return SarvamASR()
    else:
        return LocalSimASR()


def create_tts_provider(provider: str | None = None) -> TTSProvider:
    provider = provider or os.getenv("TTS_PROVIDER", "local_sim")
    if provider == "cartesia":
        from .providers.cartesia_tts import CartesiaTTS
        return CartesiaTTS()
    elif provider == "sarvam":
        from .providers.sarvam_tts import SarvamTTS
        return SarvamTTS()
    else:
        return LocalSimTTS()


def create_voice_provider(provider: str | None = None) -> VoiceProvider:
    provider = provider or os.getenv("VOICE_PROVIDER", "local_sim")
    if provider == "bolna":
        from .providers.bolna_provider import BolnaProvider
        return BolnaProvider()
    else:
        return LocalSimVoice()


def create_telephony_provider(provider: str | None = None) -> TelephonyProvider:
    provider = provider or os.getenv("VOICE_PROVIDER", "local_sim")
    if provider == "bolna":
        from .providers.bolna_provider import BolnaProvider
        return BolnaProvider()
    elif provider == "plivo":
        from .providers.plivo_provider import PlivoTelephony
        return PlivoTelephony()
    elif provider == "exotel":
        from .providers.exotel_provider import ExotelTelephony
        return ExotelTelephony()
    else:
        return LocalSimTelephony()
