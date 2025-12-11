"""Notification orchestration."""

from __future__ import annotations

from typing import Iterable, List

from parlaylab.notifications.email_backend import EmailBackend
from parlaylab.notifications.sms_backend import SmsBackend
from parlaylab.parlays.types import ParlayRecommendation


class NotificationService:
    """Send parlay summaries via multiple channels."""

    def __init__(
        self,
        email_backend: EmailBackend | None = None,
        sms_backend: SmsBackend | None = None,
    ) -> None:
        self.email_backend = email_backend or EmailBackend()
        self.sms_backend = sms_backend or SmsBackend()

    @staticmethod
    def _format_parlay(parlay: ParlayRecommendation) -> str:
        lines = [f"Flagship Parlay ({len(parlay.legs)} legs)"]
        for idx, leg in enumerate(parlay.legs, start=1):
            lines.append(f"{idx}. {leg.selection} ({leg.market_type}) @ {leg.american_odds}")
        lines.append(f"Hit probability: {parlay.hit_probability:.2%}")
        lines.append(f"Suggested stake: ${parlay.suggested_stake:.2f}")
        lines.append(f"Expected value: ${parlay.expected_value:.2f}")
        return "\n".join(lines)

    def send_email_digest(self, parlay: ParlayRecommendation, emails: Iterable[str]) -> None:
        body = self._format_parlay(parlay)
        self.email_backend.send(
            subject=f"ParlayLab NBA | {parlay.slate_date} Flagship Parlay",
            body=body,
            recipients=emails,
        )

    def send_sms_digest(self, parlay: ParlayRecommendation, phones: Iterable[str]) -> None:
        body = f"Flagship parlay hit chance {parlay.hit_probability:.1%} | stake ${parlay.suggested_stake:.0f}"
        self.sms_backend.send(body=body, recipients=phones)

    def notify_subscribers(self, parlay: ParlayRecommendation, subscribers: List[dict]) -> None:
        emails = [s["email"] for s in subscribers if s.get("email")]
        phones = [s["phone"] for s in subscribers if s.get("phone")]
        if emails:
            self.send_email_digest(parlay, emails)
        if phones:
            self.send_sms_digest(parlay, phones)
