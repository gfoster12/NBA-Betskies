"""FastAPI backend for ParlayLab NBA."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from parlaylab.api.schemas import ParlayLeg, ParlayResponse, StatsResponse
from parlaylab.config import get_api_access_key, get_settings
from parlaylab.data.ingestion import fetch_edges, sync_daily
from parlaylab.db.database import SessionLocal, get_session
from parlaylab.db.models import (
    Bet,
    ModelRun,
)
from parlaylab.db.models import (
    Parlay as ParlayModel,
)
from parlaylab.db.models import (
    ParlayLeg as ParlayLegModel,
)
from parlaylab.parlays.engine import build_parlays, flagship_and_alternatives
from parlaylab.parlays.types import BetLeg, ParlayRecommendation
from parlaylab.scheduling.jobs import run_daily_job

settings = get_settings()

app = FastAPI(
    title="ParlayLab NBA API",
    version="0.1.0",
    description="Backend for GPT Actions; returns numeric/stat outputs only.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected = get_api_access_key()
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _latest_model_version(session: Session) -> str | None:
    run = session.execute(select(ModelRun).order_by(ModelRun.trained_at.desc())).scalars().first()
    return run.version if run else None


SessionDep = Annotated[Session, Depends(get_db)]
APIKeyDep = Annotated[None, Depends(require_api_key)]
DateQuery = Annotated[date | None, Query(default=None)]
LimitQuery = Annotated[int, Query(default=10, ge=1, le=50)]
WindowQuery = Annotated[int, Query(default=30, ge=1, le=365)]


@app.get("/version")
def version(session: SessionDep) -> dict[str, Any]:
    return {
        "name": "parlaylab-nba",
        "version": "0.1.0",
        "model_version": _latest_model_version(session),
    }


class GenerateParlayRequest(BaseModel):
    slate_date: date
    max_legs: int = 5
    min_edge: float = 0.03
    risk_level: str = Field(default="balanced", regex="^(conservative|balanced|aggressive)$")
    bankroll: float = 1000.0


@app.post("/generate_parlay", response_model=ParlayResponse)
def generate_parlay(
    payload: GenerateParlayRequest,
    _: APIKeyDep,
    session: SessionDep,
) -> ParlayResponse:
    try:
        sync_daily(payload.slate_date)
    except Exception as exc:  # pragma: no cover - external API failure
        raise HTTPException(status_code=502, detail=f"Failed to sync slate: {exc}") from exc

    bet_legs = [_bet_to_leg(bet) for bet in fetch_edges(payload.min_edge)]
    if not bet_legs:
        raise HTTPException(status_code=404, detail="No +EV legs available for this slate.")

    risk_map = {"conservative": 0.5, "balanced": 1.0, "aggressive": 1.5}
    risk_factor = risk_map.get(payload.risk_level, 1.0)
    parlays = build_parlays(
        bet_legs,
        slate_date=payload.slate_date,
        bankroll=payload.bankroll,
        max_legs=payload.max_legs,
        kelly_fraction=settings.kelly_fraction * risk_factor,
        edge_threshold=payload.min_edge,
    )
    flagship, _ = flagship_and_alternatives(parlays)
    if not flagship:
        raise HTTPException(
            status_code=404,
            detail="Unable to construct a parlay with current filters.",
        )

    orm_parlay = _persist_parlay(flagship)
    return _parlay_to_response(orm_parlay, session, flagship_flag=True)


@app.get("/parlays", response_model=list[ParlayResponse])
def list_parlays(
    slate_date: DateQuery,
    limit: LimitQuery,
    _: APIKeyDep,
    session: SessionDep,
) -> list[ParlayResponse]:
    stmt = select(ParlayModel).order_by(
        ParlayModel.slate_date.desc(),
        ParlayModel.created_at.desc(),
    )
    if slate_date:
        stmt = stmt.where(ParlayModel.slate_date == slate_date)
    stmt = stmt.limit(limit)
    rows = session.execute(stmt).scalars().all()
    return [_parlay_to_response(row, session, flagship_flag=row.flagship) for row in rows]


@app.get("/stats", response_model=StatsResponse)
def stats(
    window_days: WindowQuery,
    _: APIKeyDep,
    session: SessionDep,
) -> StatsResponse:
    window_start = datetime.utcnow() - timedelta(days=window_days)
    stmt = select(ParlayModel).where(ParlayModel.created_at >= window_start)
    rows = session.execute(stmt).scalars().all()
    total = len(rows)
    wins = pushes = 0  # outcome tracking TBD
    total_stake = sum(row.suggested_stake for row in rows)
    total_ev = sum(row.expected_value for row in rows)
    roi = (total_ev / total_stake) if total_stake else 0.0
    avg_ev = (total_ev / total) if total else 0.0
    last_updated = max((row.created_at for row in rows), default=datetime.utcnow())
    losses = total - wins - pushes
    return StatsResponse(
        window_days=window_days,
        total_parlays=total,
        wins=wins,
        losses=losses,
        pushes=pushes,
        win_rate=(wins / total) if total else 0.0,
        roi=roi,
        avg_ev=avg_ev,
        last_updated=last_updated,
    )


class DailyJobRequest(BaseModel):
    target_date: date | None = None


@app.post("/run_daily_job")
def api_run_daily_job(
    payload: DailyJobRequest,
    _: APIKeyDep,
) -> dict[str, Any]:
    target = payload.target_date or date.today()
    try:
        summary = run_daily_job(target)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Daily job failed: {exc}") from exc
    return {"status": "ok", "target_date": target, "details": summary}


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
            rationale="",
        )
        session.add(parlay)
        session.flush()
        for order, leg in enumerate(rec.legs):
            session.add(ParlayLegModel(parlay_id=parlay.id, bet_id=leg.bet_id, leg_order=order))
        session.commit()
        session.refresh(parlay)
        return parlay


def _parlay_to_response(
    parlay: ParlayModel,
    session: Session,
    flagship_flag: bool,
) -> ParlayResponse:
    leg_rows = (
        session.query(ParlayLegModel, Bet)
        .join(Bet, ParlayLegModel.bet_id == Bet.id)
        .filter(ParlayLegModel.parlay_id == parlay.id)
        .order_by(ParlayLegModel.leg_order.asc())
        .all()
    )
    legs = [
        ParlayLeg(
            market_type=bet.market_type,
            description=bet.selection,
            odds=str(bet.american_odds),
            model_prob=bet.model_prob,
            implied_prob=bet.implied_prob,
            edge=bet.edge,
            metadata={
                "game_id": bet.game_id,
                "team_id": bet.team_id,
                "player_id": bet.player_id,
                "sportsbook": bet.sportsbook,
            },
        )
        for _, bet in leg_rows
    ]
    model_version = _latest_model_version(session)
    return ParlayResponse(
        slate_date=parlay.slate_date,
        name=parlay.name,
        legs=legs,
        total_odds=parlay.total_odds,
        hit_probability=parlay.hit_probability,
        expected_value=parlay.expected_value,
        suggested_stake=parlay.suggested_stake,
        flagship=flagship_flag,
        created_at=parlay.created_at,
        model_version=model_version,
    )
