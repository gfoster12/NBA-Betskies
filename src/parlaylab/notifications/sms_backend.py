"""Twilio SMS backend with rate limiting."""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Callable, Iterable

from twilio.rest import Client

from parlaylab.config import get_settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token-bucket style limiter to cap SMS throughput."""

    def __init__(
        self,
        max_events: int,
        window_seconds: float = 60.0,
        *,
        time_fn: Callable[[], float] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._time = time_fn or time.time
        self._sleep = sleep_fn or time.sleep

    def wait_for_slot(self) -> None:
        if self.max_events <= 0:
            return
        now = self._time()
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
        if len(self._timestamps) >= self.max_events:
            sleep_time = self.window_seconds - (now - self._timestamps[0])
            if sleep_time > 0:
                self._sleep(sleep_time)
        self._timestamps.append(self._time())


class SmsBackend:
    """Twilio SMS sender with simple rate limiting."""

    def __init__(
        self,
        client: Client | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.settings = get_settings()
        self.enabled = bool(
            self.settings.twilio_account_sid
            and self.settings.twilio_auth_token
            and self.settings.twilio_from_number
        )
        self.client = client if client else self._build_client()
        self.rate_limiter = rate_limiter or RateLimiter(self.settings.sms_rate_limit_per_minute)

    def _build_client(self) -> Client | None:
        if not self.enabled:
            return None
        return Client(self.settings.twilio_account_sid, self.settings.twilio_auth_token)

    def send(self, body: str, recipients: Iterable[str]) -> None:
        if not recipients:
            return
        if not self.client:
            for phone in recipients:
                logger.info("[SMS disabled] %s -> %s", phone, body)
            return
        for phone in recipients:
            self.rate_limiter.wait_for_slot()
            try:
                self.client.messages.create(
                    body=body,
                    from_=self.settings.twilio_from_number,
                    to=phone,
                )
            except Exception as exc:  # pragma: no cover - network errors
                logger.error("Failed to send SMS to %s: %s", phone, exc)
