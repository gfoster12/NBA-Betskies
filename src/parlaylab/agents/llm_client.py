"""OpenAI Chat Completions helper."""

from __future__ import annotations

from typing import Dict, List

from openai import OpenAI

from parlaylab.config import get_settings
from parlaylab.parlays.types import ParlayRecommendation

settings = get_settings()
_client: OpenAI | None = None


def _client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def chat_completion(messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
    response = _client().chat.completions.create(
        model=settings.openai_model,
        temperature=temperature,
        messages=messages,
    )
    return response.choices[0].message.content or ""


def explain_parlay(parlay: ParlayRecommendation, stats: Dict[str, str]) -> str:
    legs_description = "\n".join(
        f"- {leg.selection} ({leg.market_type}) edge {leg.edge:.1%}" for leg in parlay.legs
    )
    prompt = (
        "Provide a concise explanation of why each leg in the parlay is attractive. "
        "Reference advanced stats when possible and remind the user that outcomes are not guaranteed."
    )
    messages = [
        {
            "role": "system",
            "content": "You are a careful sports analytics assistant who cites data and avoids guarantees.",
        },
        {
            "role": "user",
            "content": f"Parlay details:\n{legs_description}\n\nContext stats: {stats}\n{prompt}",
        },
    ]
    return chat_completion(messages)


def generate_ig_caption(parlay: ParlayRecommendation, stats: Dict[str, str], tone: str) -> str:
    legs_description = " | ".join(f"{leg.selection} ({leg.american_odds:+d})" for leg in parlay.legs)
    messages = [
        {
            "role": "system",
            "content": "You craft Instagram captions about NBA parlays. Include a responsible gambling note.",
        },
        {
            "role": "user",
            "content": (
                f"Create a {tone} caption for this parlay: {legs_description}. "
                f"Hit probability {parlay.hit_probability:.1%}, EV ${parlay.expected_value:.2f}. "
                f"Recent stats: {stats}"
            ),
        },
    ]
    return chat_completion(messages, temperature=0.8 if tone == "fun" else 0.4)
