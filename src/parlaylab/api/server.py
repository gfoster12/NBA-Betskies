"""FastAPI server powering ParlayLab GPT integrations."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from parlaylab.config import get_settings
from parlaylab.data.ingestion import fetch_edges, sync_daily
from parlaylab.db.database import SessionLocal, get_session
from parlaylab.db.models import Bet, Parlay as ParlayModel, ParlayLeg as ParlayLegModel
from parlaylab.parlays.engine import build_parlays, flagship_and_alternatives
from parlaylab.parlays.types import BetLeg, ParlayRecommendation

settings = get_settings()

app = FastAPI(title="ParlayLab API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateParlayRequest(BaseModel):
    slate_date: date = Field(..., description="Date of NBA slate to analyze")


class ParlayLegSchema(BaseModel):
    selection: str
    market_type: str
    sportsbook: str
    american_odds: int
    implied_prob: float
    model_prob: float
    edge: float


class ParlaySchema(BaseModel):
    name: str
    slate_date: date
    total_odds: float
    hit_probability: float
    expected_value: float
    suggested_stake: float
    correlation_score: float | None = None
    legs: list[ParlayLegSchema]


class ParlayStatsSchema(BaseModel):
    id: int
    name: str
    slate_date: date
    hit_probability: float
    expected_value: float
    total_odds: float
    suggested_stake: float
    created_at: str


def _bet_to_leg(bet: Bet) -> BetLeg:
    return BetLeg(
        bet_id=bet.id,
        market_type=bet.market_type,
        selection=bet.selection,
        sportsbook=bet.sportsbook,
        american_odds=bet.american_odds,
        implied_prob=bet.implied_prob,
        model_prob=bet.model_prob,
        edge=bet.edge,
        game_id=bet.game_id,
        team_id=bet.team_id,
        player_id=bet.player_id,
        tags={"book": bet.sportsbook},
    )


def _persist_parlay(rec: ParlayRecommendation) -> ParlayModel:
    with get_session() as session:
        parlay = ParlayModel(
            name=rec.name,
            slate_date=rec.slate_date,
            total_odds=rec.total_odds,
            hit_probability=rec.hit_probability,
            expected_value=rec.expected_value,
            suggested_stake=rec.suggested_stake,
            flagship=True,
            rationale=rec.rationale,
        )
        session.add(parlay)
        session.flush()
        for order, leg in enumerate(rec.legs):
            session.add(ParlayLegModel(parlay_id=parlay.id, bet_id=leg.bet_id, leg_order=order))
        session.commit()
        session.refresh(parlay)
        return parlay


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/generate_parlay", response_model=dict)
def generate_parlay(payload: GenerateParlayRequest) -> dict[str, Any]:
    """Trigger ingestion + parlay generation for a date."""

    try:
        sync_daily(payload.slate_date)
    except Exception as exc:  # pragma: no cover - upstream API issues
        raise HTTPException(status_code=502, detail=f"Failed to sync daily data: {exc}") from exc

    bet_legs = [_bet_to_leg(bet) for bet in fetch_edges(settings.edge_threshold)]
    if not bet_legs:
        raise HTTPException(status_code=404, detail="No +EV bets available for that date.")

    parlays = build_parlays(
        bet_legs,
        slate_date=payload.slate_date,
        bankroll=settings.default_bankroll,
        max_legs=4,
        kelly_fraction=settings.kelly_fraction,
        edge_threshold=settings.edge_threshold,
    )
    flagship, alternatives = flagship_and_alternatives(parlays)
    if not flagship:
        raise HTTPException(status_code=404, detail="Unable to construct a flagship parlay.")

    _persist_parlay(flagship)

    def to_schema(rec: ParlayRecommendation) -> ParlaySchema:
        legs = [
            ParlayLegSchema(
                selection=leg.selection,
                market_type=leg.market_type,
                sportsbook=leg.sportsbook,
                american_odds=leg.american_odds,
                implied_prob=leg.implied_prob,
                model_prob=leg.model_prob,
                edge=leg.edge,
            )
            for leg in rec.legs
        ]
        return ParlaySchema(
            name=rec.name,
            slate_date=rec.slate_date,
            total_odds=rec.total_odds,
            hit_probability=rec.hit_probability,
            expected_value=rec.expected_value,
            suggested_stake=rec.suggested_stake,
            correlation_score=rec.correlation_score,
            legs=legs,
        )

    response = {"flagship": to_schema(flagship), "alternatives": []}
    response["alternatives"] = [to_schema(alt) for alt in alternatives[:3]]
    return response


@app.get("/parlay_stats", response_model=list[ParlayStatsSchema])
def parlay_stats(
    slate_date: date | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_db_session),
) -> list[ParlayStatsSchema]:
    stmt = select(ParlayModel).order_by(ParlayModel.slate_date.desc(), ParlayModel.created_at.desc())
    if slate_date:
        stmt = stmt.where(ParlayModel.slate_date == slate_date)
    stmt = stmt.limit(limit)
    rows = session.scalars(stmt).all()
    return [
        ParlayStatsSchema(
            id=row.id,
            name=row.name,
            slate_date=row.slate_date,
            hit_probability=row.hit_probability,
            expected_value=row.expected_value,
            total_odds=row.total_odds,
            suggested_stake=row.suggested_stake,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
