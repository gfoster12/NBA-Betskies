"""Thin client for the BALLDONTLIE GOAT API."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Iterable, Optional

import httpx
from tenacity import RetryCallState, retry, stop_after_attempt, wait_fixed

from parlaylab.config import get_settings

BASE_URL = "https://api.balldontlie.io"


def _retry_log(retry_state: RetryCallState) -> None:  # pragma: no cover - logging helper
    attempt = retry_state.attempt_number
    exception = retry_state.outcome.exception() if retry_state.outcome else None
    print(f"BallDontLie retry attempt {attempt} due to {exception}")


class BallDontLieClient:
    """Convenient wrapper for the BALDONTLIE API."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = BASE_URL) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.balldontlie_api_key
        if not self.api_key:
            raise RuntimeError("BALLDONTLIE_API_KEY is not configured.")
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=30.0, headers={"Authorization": self.api_key})

    def __enter__(self) -> "BallDontLieClient":  # pragma: no cover - context sugar
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), after=_retry_log)
    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        response = self._client.request(method, url, params=params)
        response.raise_for_status()
        return response.json()

    def get_games(self, target_date: date) -> Iterable[Dict[str, Any]]:
        """Return games for a specific date."""

        payload = self._request("GET", "/v1/games", {"dates[]": target_date.isoformat(), "per_page": 100})
        return payload.get("data", [])

    def get_betting_odds(self, game_id: Optional[int] = None, target_date: Optional[date] = None) -> Iterable[Dict[str, Any]]:
        """Fetch betting odds either by game or date."""

        params: Dict[str, Any] = {"per_page": 100}
        if game_id:
            params["game_ids[]"] = game_id
        if target_date:
            params["dates[]"] = target_date.isoformat()
        payload = self._request("GET", "/v1/betting/odds", params)
        return payload.get("data", [])

    def get_team_stats(self, team_id: int, season: int, last_n_games: int = 10) -> Dict[str, Any]:
        params = {"team_ids[]": team_id, "seasons[]": season, "last_n_games": last_n_games}
        payload = self._request("GET", "/v1/stats/team/advanced", params)
        return payload.get("data", {})

    def get_player_stats(self, player_id: int, season: int, last_n_games: int = 10) -> Dict[str, Any]:
        params = {"player_ids[]": player_id, "seasons[]": season, "last_n_games": last_n_games}
        payload = self._request("GET", "/v1/stats/player/advanced", params)
        return payload.get("data", {})
