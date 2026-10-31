import logging
import os

import httpx

from .base import TelephonyProvider

logger = logging.getLogger(__name__)

PLIVO_API_BASE = "https://api.plivo.com/v1/Account"


class PlivoTelephony(TelephonyProvider):
    def __init__(
        self,
        auth_id: str | None = None,
        auth_token: str | None = None,
        phone_number: str | None = None,
    ):
        self.auth_id = auth_id or os.getenv("PLIVO_AUTH_ID", "")
        self.auth_token = auth_token or os.getenv("PLIVO_AUTH_TOKEN", "")
        self.phone_number = phone_number or os.getenv("PLIVO_PHONE_NUMBER", "")
        if not self.auth_id or not self.auth_token:
            raise ValueError("PLIVO_AUTH_ID and PLIVO_AUTH_TOKEN are required")

    async def make_call(self, to_number: str, message: str) -> dict:
        url = f"{PLIVO_API_BASE}/{self.auth_id}/Call/"
        payload = {
            "from": self.phone_number,
            "to": to_number,
            "answer_url": "https://aerolog.example.com/api/plivo/answer",
            "answer_method": "POST",
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    auth=(self.auth_id, self.auth_token),
                )
                resp.raise_for_status()
                data = resp.json()
            call_uuid = data.get("request_uuid", [""])[0] if isinstance(data.get("request_uuid"), list) else data.get("request_uuid", "")
            logger.info("[Plivo] Call initiated: %s -> %s", call_uuid, to_number)
            return {"call_id": call_uuid, "status": "initiated"}
        except Exception:
            logger.exception("[Plivo] Failed to make call to %s", to_number)
            return {"call_id": "", "status": "failed"}

    async def handle_inbound_webhook(self, request_data: dict) -> dict:
        call_uuid = request_data.get("CallUUID", "")
        from_number = request_data.get("From", "")
        logger.info("[Plivo] Inbound call from %s, UUID: %s", from_number, call_uuid)
        xml_response = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            "<Speak>Welcome to AeroLog maintenance logging. Please begin your report.</Speak>"
            f'<Record action="https://aerolog.example.com/api/plivo/recording" '
            f'maxLength="300" transcriptionUrl="https://aerolog.example.com/api/plivo/transcription" />'
            "</Response>"
        )
        return {"content_type": "application/xml", "body": xml_response}
