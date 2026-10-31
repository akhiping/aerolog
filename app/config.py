from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite+aiosqlite:///./aerolog.db")

    voice_provider: str = Field(default="local_sim")
    asr_provider: str = Field(default="local_sim")
    tts_provider: str = Field(default="local_sim")
    llm_provider: str = Field(default="rule_based")

    anthropic_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")
    deepgram_api_key: str = Field(default="")
    sarvam_api_key: str = Field(default="")
    cartesia_api_key: str = Field(default="")

    bolna_api_key: str = Field(default="")
    bolna_agent_id: str = Field(default="")

    plivo_auth_id: str = Field(default="")
    plivo_auth_token: str = Field(default="")
    plivo_phone_number: str = Field(default="")

    exotel_sid: str = Field(default="")
    exotel_api_key: str = Field(default="")
    exotel_api_token: str = Field(default="")
    exotel_phone_number: str = Field(default="")

    escalation_channel: str = Field(default="dashboard")
    escalation_webhook_url: str = Field(default="")

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    frontend_url: str = Field(default="http://localhost:5173")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
