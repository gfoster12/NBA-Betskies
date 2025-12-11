"""SMS backend stub for logging purposes."""

from __future__ import annotations

from typing import Iterable


class SmsBackend:
    """Placeholder backend that logs outbound SMS payloads."""

    def send(self, body: str, recipients: Iterable[str]) -> None:
        for phone in recipients:
            print(f"[SMS] -> {phone}: {body}")
