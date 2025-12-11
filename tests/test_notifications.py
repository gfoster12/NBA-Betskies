"""Notification backend tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from parlaylab.notifications import sms_backend


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, duration: float) -> None:
        self.sleeps.append(duration)
        self.now += duration


def test_rate_limiter_waits_when_limit_exceeded() -> None:
    clock = FakeClock()
    limiter = sms_backend.RateLimiter(
        max_events=2,
        window_seconds=10,
        time_fn=clock.time,
        sleep_fn=clock.sleep,
    )
    limiter.wait_for_slot()
    clock.now += 1
    limiter.wait_for_slot()
    clock.now += 1
    limiter.wait_for_slot()
    assert pytest.approx(clock.sleeps[-1], rel=0.01) == 8.0


class DummyClient:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.messages = self

    def create(self, **kwargs) -> None:
        self.sent.append(kwargs)


def test_sms_backend_uses_twilio_client(monkeypatch) -> None:
    settings = SimpleNamespace(
        twilio_account_sid="sid",
        twilio_auth_token="token",
        twilio_from_number="+1000000000",
        sms_rate_limit_per_minute=100,
    )
    monkeypatch.setattr(sms_backend, "get_settings", lambda: settings)
    dummy_client = DummyClient()
    backend = sms_backend.SmsBackend(
        client=dummy_client,
        rate_limiter=sms_backend.RateLimiter(0),
    )
    backend.send("hi", ["+1", "+2"])
    assert len(dummy_client.sent) == 2
    assert all(
        msg["from_"] == settings.twilio_from_number
        for msg in dummy_client.sent
    )
