from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.db.repository import SupervisorRepository, NotificationRepository

logger = logging.getLogger(__name__)


class EscalationManager:
    def __init__(self):
        self._ws_broadcast = None

    def set_ws_broadcast(self, broadcast_fn):
        self._ws_broadcast = broadcast_fn

    async def escalate(
        self,
        record_id: str,
        aircraft_registration: str,
        reason: str,
        finding_summary: str,
        severity: str,
        db_session,
        telephony_provider=None,
        config=None,
    ) -> dict:
        sup_repo = SupervisorRepository(db_session)
        notif_repo = NotificationRepository(db_session)

        supervisors = await sup_repo.get_active()
        if not supervisors:
            logger.warning("No active supervisors found for escalation")

        channel = "dashboard"
        if config:
            channel = getattr(config, "escalation_channel", "dashboard")

        message = (
            f"SAFETY ESCALATION — {severity}\n"
            f"Aircraft: {aircraft_registration}\n"
            f"Finding: {finding_summary}\n"
            f"Reason: {reason}"
        )

        notifications = []
        for sup in supervisors:
            notif = await notif_repo.create({
                "record_id": record_id,
                "supervisor_id": sup.id,
                "channel": channel,
                "message": message,
                "sent_at": datetime.now(timezone.utc),
            })
            notifications.append({
                "notification_id": notif.id,
                "supervisor": sup.name,
                "channel": channel,
            })
            logger.info(
                "Escalation notification sent to %s via %s: %s",
                sup.name, channel, finding_summary,
            )

        if channel == "call" and telephony_provider:
            for sup in supervisors:
                if sup.phone:
                    try:
                        await telephony_provider.make_call(sup.phone, message)
                        logger.info("Escalation call placed to %s at %s", sup.name, sup.phone)
                    except Exception:
                        logger.exception("Failed to place escalation call to %s", sup.name)

        if channel == "webhook" and config and config.escalation_webhook_url:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(
                        config.escalation_webhook_url,
                        json={
                            "type": "safety_escalation",
                            "record_id": record_id,
                            "aircraft": aircraft_registration,
                            "severity": severity,
                            "finding": finding_summary,
                            "reason": reason,
                        },
                        timeout=10,
                    )
            except Exception:
                logger.exception("Failed to send escalation webhook")

        if self._ws_broadcast:
            try:
                await self._ws_broadcast({
                    "type": "escalation",
                    "content": message,
                    "data": {
                        "record_id": record_id,
                        "aircraft_registration": aircraft_registration,
                        "severity": severity,
                        "finding_summary": finding_summary,
                        "notifications": notifications,
                    },
                })
            except Exception:
                logger.exception("Failed to broadcast escalation via WebSocket")

        supervisor_names = [s.name for s in supervisors] if supervisors else ["(no supervisors configured)"]
        return {
            "escalated": True,
            "supervisors_notified": supervisor_names,
            "channel": channel,
            "notifications": notifications,
        }
