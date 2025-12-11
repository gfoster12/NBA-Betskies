"""Streamlit interface for ParlayLab NBA."""

from __future__ import annotations

from datetime import date
from typing import List

import pandas as pd
import streamlit as st

from parlaylab.agents.llm_client import explain_parlay
from parlaylab.agents.marketing_agent import MarketingAgent
from parlaylab.config import get_settings
from parlaylab.data.ingestion import fetch_edges
from parlaylab.db.database import get_session
from parlaylab.db.models import Bet, Parlay as ParlayModel, ParlayLeg as ParlayLegModel, Subscriber
from parlaylab.parlays.engine import build_parlays, flagship_and_alternatives
from parlaylab.parlays.types import BetLeg, ParlayRecommendation
from parlaylab.scheduling.jobs import run_daily_job

settings = get_settings()

st.set_page_config(page_title="ParlayLab NBA", layout="wide")
st.title("🏀 ParlayLab NBA")
st.caption("Analytics-driven NBA parlay lab. Entertainment use only.")


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
        team_tag=f"game_{bet.game_id}",
        player_tag=None,
    )


def load_flagship_parlay(target_date: date) -> ParlayModel | None:
    with get_session() as session:
        return (
            session.query(ParlayModel)
            .filter(ParlayModel.slate_date == target_date)
            .order_by(ParlayModel.created_at.desc())
            .first()
        )


@st.cache_data(show_spinner=False)
def load_bet_legs() -> List[BetLeg]:
    return [_bet_to_leg(bet) for bet in fetch_edges(settings.edge_threshold)]


def parlay_model_to_rec(model_id: int) -> ParlayRecommendation | None:
    with get_session() as session:
        model = session.get(ParlayModel, model_id)
        if not model:
            return None
        leg_rows = (
            session.query(ParlayLegModel)
            .filter(ParlayLegModel.parlay_id == model.id)
            .order_by(ParlayLegModel.leg_order.asc())
            .all()
        )
        bet_ids = [leg.bet_id for leg in leg_rows]
        if not bet_ids:
            return None
        bets = {bet.id: bet for bet in session.query(Bet).filter(Bet.id.in_(bet_ids)).all()}
        legs = [_bet_to_leg(bets[leg.bet_id]) for leg in leg_rows if leg.bet_id in bets]
    return ParlayRecommendation(
        name=model.name,
        slate_date=model.slate_date,
        legs=legs,
        total_odds=model.total_odds,
        hit_probability=model.hit_probability,
        expected_value=model.expected_value,
        suggested_stake=model.suggested_stake,
        rationale=model.rationale or "",
    )


with st.sidebar:
    slate_date = st.date_input("Slate date", value=date.today())
    bankroll = st.number_input("Bankroll ($)", value=settings.default_bankroll, min_value=100.0, step=50.0)
    risk = st.slider("Risk appetite", 0.1, 1.0, 0.5)
    max_legs = st.slider("Max parlay legs", 2, 5, 3)
    admin_password = st.text_input("Admin password", type="password")
    admin_mode = admin_password == settings.admin_password
    if st.button("Run today's parlay & notify now"):
        with st.spinner("Running end-to-end job..."):
            result = run_daily_job(slate_date)
        st.success(f"Daily job complete: {result}")

flagship_container = st.container()
insights_container = st.container()
parlay_builder_container = st.container()
marketing_container = st.container()
subscriber_container = st.container()


with flagship_container:
    st.subheader("Flagship Parlay")
    flagship_model = load_flagship_parlay(slate_date)
    if flagship_model:
        cols = st.columns(3)
        cols[0].metric("Hit probability", f"{flagship_model.hit_probability:.1%}")
        cols[1].metric("Expected value", f"${flagship_model.expected_value:.2f}")
        cols[2].metric("Stake", f"${flagship_model.suggested_stake:.2f}")
        st.write(flagship_model.rationale or "Rationale pending generation.")
    else:
        st.info("No flagship parlay saved yet. Use the builder to create one.")


with insights_container:
    st.subheader("Model Insights")
    with get_session() as session:
        history = session.query(ParlayModel).order_by(ParlayModel.slate_date.asc()).all()
    if history:
        df = pd.DataFrame(
            {
                "date": [h.slate_date for h in history],
                "expected_value": [h.expected_value for h in history],
                "hit_probability": [h.hit_probability for h in history],
            }
        )
        st.line_chart(df.set_index("date")["expected_value"], height=200)
        st.bar_chart(df.set_index("date")["hit_probability"], height=200)
    else:
        st.caption("Charts will appear after the first model run.")


with parlay_builder_container:
    st.subheader("Interactive Parlay Builder")
    bet_legs = load_bet_legs()
    if not bet_legs:
        st.info("No +EV legs available yet. Train models and ingest odds first.")
    elif st.button("Generate custom parlays"):
        parlays = build_parlays(
            bet_legs,
            slate_date=slate_date,
            bankroll=bankroll,
            max_legs=max_legs,
            kelly_fraction=settings.kelly_fraction * risk,
            edge_threshold=settings.edge_threshold,
        )
        flagship, alternatives = flagship_and_alternatives(parlays)
        if flagship:
            st.success(
                f"{flagship.name}: {flagship.hit_probability:.1%} hit | EV ${flagship.expected_value:.2f}"
            )
            try:
                rationale = explain_parlay(flagship, {"risk": risk})
                st.write(rationale)
            except Exception as exc:  # pragma: no cover - optional LLM call
                st.warning(f"LLM explanation unavailable: {exc}")
            if alternatives:
                alt_df = pd.DataFrame(
                    [
                        {
                            "name": alt.name,
                            "legs": len(alt.legs),
                            "probability": alt.hit_probability,
                            "EV": alt.expected_value,
                        }
                        for alt in alternatives
                    ]
                )
                st.dataframe(alt_df)
        else:
            st.write("No valid parlays passed the filters.")


with marketing_container:
    st.subheader("Instagram Marketing Agent")
    if flagship_model and st.button("Generate today's IG post"):
        rec = parlay_model_to_rec(flagship_model.id)
        if rec:
            agent = MarketingAgent()
            stats = {"last_7_day_roi": "+8.4%", "bankroll": bankroll}
            with st.spinner("Calling OpenAI..."):
                content = agent.run(rec, stats)
            st.code(content.professional, language="markdown")
            st.code(content.hype, language="markdown")
            st.text(content.hashtags)
        else:
            st.warning("Unable to load legs for this parlay.")
    elif not flagship_model:
        st.caption("Save a flagship parlay before generating marketing copy.")


with subscriber_container:
    st.subheader("Subscriber Management")
    name = st.text_input("Name", key="sub_name")
    email = st.text_input("Email *", key="sub_email")
    phone = st.text_input("Phone", key="sub_phone")
    bankroll_pref = st.number_input(
        "Daily bankroll preference", value=50.0, min_value=0.0, step=10.0
    )
    if st.button("Add subscriber"):
        if not email:
            st.error("Email is required.")
        else:
            with get_session() as session:
                subscriber = Subscriber(name=name, email=email, phone=phone, bankroll_pref=bankroll_pref)
                session.add(subscriber)
            st.success("Subscriber added!")
    if admin_mode:
        with get_session() as session:
            subs = session.query(Subscriber).order_by(Subscriber.created_at.desc()).all()
        if subs:
            st.write(
                pd.DataFrame(
                    [
                        {
                            "name": s.name,
                            "email": s.email,
                            "phone": s.phone,
                            "active": s.active,
                        }
                        for s in subs
                    ]
                )
            )
        else:
            st.info("No subscribers recorded yet.")
    else:
        st.caption("Enter the admin password to view subscriber data.")
