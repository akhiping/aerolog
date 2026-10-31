import logging
import os

import httpx

from .base import TelephonyProvider

logger = logging.getLogger(__name__)


class ExotelTelephony(TelephonyProvider):
    def __init__(
        self,
        sid: str | None = None,
        api_key: str | None = None,
        api_token: str | None = None,
        phone_number: str | None = None,
    ):
        self.sid = sid or os.getenv("EXOTEL_SID", "")
        self.api_key = api_key or os.getenv("EXOTEL_API_KEY", "")
        self.api_token = api_token or os.getenv("EXOTEL_API_TOKEN", "")
        self.phone_number = phone_number or os.getenv("EXOTEL_PHONE_NUMBER", "")
        if not self.sid or not self.api_key:
            raise ValueError("EXOTEL_SID and EXOTEL_API_KEY are required")

    async def make_call(self, to_number: str, message: str) -> dict:
        url = f"https://api.exotel.com/v1/Accounts/{self.sid}/Calls/connect.json"
        payload = {
            "From": to_number,
            "To": self.phone_number,
            "CallerId": self.phone_number,
            "Url": "https://aerolog.example.com/api/exotel/answer",
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    data=payload,
                    auth=(self.api_key, self.api_token),
                )
                resp.raise_for_status()
                data = resp.json()
            call_sid = data.get("Call", {}).get("Sid", "")
            logger.info("[Exotel] Call initiated: %s -> %s", call_sid, to_number)
            return {"call_id": call_sid, "status": "initiated"}
        except Exception:
            logger.exception("[Exotel] Failed to make call to %s", to_number)
            return {"call_id": "", "status": "failed"}

    async def handle_inbound_webhook(self, request_data: dict) -> dict:
        call_sid = request_data.get("CallSid", "")
        from_number = request_data.get("From", "")
        logger.info("[Exotel] Inbound call from %s, SID: %s", from_number, call_sid)
        return {"status": "ok", "session_id": call_sid}
