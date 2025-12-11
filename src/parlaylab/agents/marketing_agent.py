"""Instagram marketing content agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from parlaylab.agents.llm_client import generate_ig_caption
from parlaylab.parlays.types import ParlayRecommendation


@dataclass
class MarketingContent:
    professional: str
    hype: str
    hashtags: str


class MarketingAgent:
    """Generates Instagram-ready content using the LLM."""

    def __init__(self, hashtag_block: str | None = None) -> None:
        self.hashtag_block = hashtag_block or "#NBA #ParlayLab #SportsAnalytics #ResponsibleGambling"

    def run(self, parlay: ParlayRecommendation, performance_stats: Dict[str, str]) -> MarketingContent:
        professional = generate_ig_caption(parlay, performance_stats, tone="professional")
        hype = generate_ig_caption(parlay, performance_stats, tone="fun")
        return MarketingContent(professional=professional, hype=hype, hashtags=self.hashtag_block)
