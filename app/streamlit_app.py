"""Streamlit interface for ParlayLab NBA."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import pandas as pd
import streamlit as st

from parlaylab.agents.llm_client import explain_parlay
from parlaylab.agents.marketing_agent import MarketingAgent
from parlaylab.config import get_settings
from parlaylab.data.ingestion import fetch_edges
from sqlalchemy.exc import OperationalError

from parlaylab.db.database import get_session, init_db
from parlaylab.db.models import Bet, Subscriber
from parlaylab.db.models import Parlay as ParlayModel
from parlaylab.db.models import ParlayLeg as ParlayLegModel
from parlaylab.parlays.engine import build_parlays, flagship_and_alternatives
from parlaylab.parlays.types import BetLeg, ParlayRecommendation
from parlaylab.scheduling.jobs import run_daily_job

settings = get_settings()
init_db()

st.set_page_config(page_title="ParlayLab NBA", layout="wide", page_icon="🏀")
st.title("🏀 ParlayLab NBA")
st.caption("Model-backed NBA parlay intelligence. Entertainment purposes only.")


@st.cache_data(show_spinner=False)
def load_flagship_model(target_date: date) -> ParlayModel | None:
    try:
        with get_session() as session:
            return (
                session.query(ParlayModel)
                .filter(ParlayModel.slate_date == target_date)
                .order_by(ParlayModel.created_at.desc())
                .first()
            )
    except OperationalError:
        return None


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


@st.cache_data(show_spinner=False)
def load_bet_legs(edge_threshold: float) -> list[BetLeg]:
    return [_bet_to_leg(bet) for bet in fetch_edges(edge_threshold)]


def parlay_model_to_rec(model: ParlayModel) -> ParlayRecommendation | None:
    with get_session() as session:
        legs_rows = (
            session.query(ParlayLegModel)
            .filter(ParlayLegModel.parlay_id == model.id)
            .order_by(ParlayLegModel.leg_order.asc())
            .all()
        )
        bet_ids = [row.bet_id for row in legs_rows]
        if not bet_ids:
            return None
        bets = {bet.id: bet for bet in session.query(Bet).filter(Bet.id.in_(bet_ids))}
    legs = [_bet_to_leg(bets[row.bet_id]) for row in legs_rows if row.bet_id in bets]
    if not legs:
        return None
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


def render_flagship_card(model: ParlayModel | None) -> ParlayRecommendation | None:
    st.subheader("Flagship Parlay")
    if not model:
        st.info(
            "No flagship parlay is available for this date yet. "
            "Run the daily job or generate a parlay manually."
        )
        return None
    cols = st.columns(4)
    cols[0].metric("Hit %", f"{model.hit_probability:.1%}")
    cols[1].metric("EV", f"${model.expected_value:.2f}")
    cols[2].metric("Stake", f"${model.suggested_stake:.2f}")
    cols[3].metric("Total odds", f"{model.total_odds:.2f}x")
    st.markdown(model.rationale or "_Rationale not available yet._")
    rec = parlay_model_to_rec(model)
    if rec:
        st.write("**Legs**")
        for idx, leg in enumerate(rec.legs, start=1):
            st.write(f"{idx}. {leg.selection} ({leg.market_type}) @ {leg.american_odds:+d}")
    return rec


def render_model_insights() -> None:
    st.subheader("Model Insights & Performance")
    with get_session() as session:
        history = session.query(ParlayModel).order_by(ParlayModel.slate_date.asc()).all()
    if not history:
        st.info("Performance dashboards will populate once you run the pipeline.")
        return
    df = pd.DataFrame(
        {
            "date": [h.slate_date for h in history],
            "expected_value": [h.expected_value for h in history],
            "hit_probability": [h.hit_probability for h in history],
        }
    ).set_index("date")
    col1, col2 = st.columns(2)
    col1.line_chart(df["expected_value"], height=250, use_container_width=True)
    col2.area_chart(df["hit_probability"], height=250, use_container_width=True)


def render_parlay_builder(
    bet_pool: Sequence[BetLeg],
    slate_date: date,
    bankroll: float,
    risk: float,
    max_legs: int,
) -> tuple[ParlayRecommendation | None, list[ParlayRecommendation]]:
    st.subheader("Interactive Parlay Builder")
    if not bet_pool:
        st.warning("No +EV legs available. Train models and sync data first.")
        return None, []
    if st.button("Generate custom parlays", use_container_width=True):
        parlays = build_parlays(
            bet_pool,
            slate_date=slate_date,
            bankroll=bankroll,
            max_legs=max_legs,
            kelly_fraction=settings.kelly_fraction * risk,
            edge_threshold=settings.edge_threshold,
        )
        flagship, alternatives = flagship_and_alternatives(parlays)
        if flagship:
            st.success(
                f"{flagship.name}: {flagship.hit_probability:.1%} hit chance | "
                f"EV ${flagship.expected_value:.2f} | Stake ${flagship.suggested_stake:.2f}"
            )
            try:
                explanation = explain_parlay(flagship, {"risk": risk})
                with st.expander("Model explanation", expanded=False):
                    st.write(explanation)
            except Exception as exc:  # pragma: no cover
                st.warning(f"LLM explanation unavailable: {exc}")
        else:
            st.info("No valid combinable parlays met the filters.")
        if alternatives:
            alt_df = pd.DataFrame(
                [
                    {
                        "name": alt.name,
                        "legs": len(alt.legs),
                        "hit_probability": alt.hit_probability,
                        "EV": alt.expected_value,
                        "stake": alt.suggested_stake,
                    }
                    for alt in alternatives
                ]
            )
            st.dataframe(alt_df, use_container_width=True)
        return flagship, alternatives
    st.caption("Tune bankroll, risk, and max legs from the sidebar, then click generate.")
    return None, []


def render_marketing_agent(rec: ParlayRecommendation | None, bankroll: float) -> None:
    st.subheader("Instagram Marketing Copy")
    if not rec:
        st.info("Run a parlay and save it before generating content.")
        return
    if st.button("Generate today's IG post", use_container_width=True):
        agent = MarketingAgent()
        stats = {"bankroll": bankroll, "run_id": rec.name}
        with st.spinner("Calling OpenAI..."):
            content = agent.run(rec, stats)
        st.code(content.professional, language="markdown")
        st.code(content.hype, language="markdown")
        st.caption(content.hashtags)


def render_subscriber_form(admin_mode: bool) -> None:
    st.subheader("Subscriber Management")
    with st.form("subscriber_form"):
        name = st.text_input("Name")
        email = st.text_input("Email *")
        phone = st.text_input("Phone")
        bankroll_pref = st.number_input(
            "Daily bankroll preference",
            value=50.0,
            min_value=0.0,
            step=10.0,
        )
        submitted = st.form_submit_button("Add subscriber")

    if submitted:
        if not email:
            st.error("Email is required.")
        else:
            with get_session() as session:
                subscriber = Subscriber(
                    name=name,
                    email=email,
                    phone=phone,
                    bankroll_pref=bankroll_pref,
                )
                session.add(subscriber)
            st.success("Subscriber added.")

    if admin_mode:
        with get_session() as session:
            subs = session.query(Subscriber).order_by(Subscriber.created_at.desc()).all()
        if subs:
            st.dataframe(
                pd.DataFrame(
                    [
                        {"name": s.name, "email": s.email, "phone": s.phone, "active": s.active}
                        for s in subs
                    ]
                ),
                use_container_width=True,
            )
        else:
            st.caption("No subscribers yet.")
    else:
        st.caption("Enter the admin password in the sidebar to view subscriber roster.")


# ----- Sidebar Controls -------------------------------------------------------
with st.sidebar:
    slate_date = st.date_input("Slate date", value=date.today())
    bankroll = st.number_input(
        "Bankroll ($)",
        value=settings.default_bankroll,
        min_value=100.0,
        step=50.0,
    )
    risk = st.slider("Risk appetite", 0.1, 1.0, 0.5, help="Higher risk → larger Kelly fraction")
    max_legs = st.slider("Max parlay legs", 2, 5, 3)
    admin_password = st.text_input("Admin password", type="password")
    admin_mode = admin_password == settings.admin_password
    if st.button("Run daily pipeline now"):
        with st.spinner("Ingesting slate, building parlays, and sending notifications..."):
            result = run_daily_job(slate_date)
        st.success(f"Daily job complete: {result}")

# ----- Page Layout ------------------------------------------------------------
col_main, col_right = st.columns([0.62, 0.38], gap="large")

with col_main:
    flagship_model = load_flagship_model(slate_date)
    flagship_rec = render_flagship_card(flagship_model)
    render_model_insights()

with col_right:
    bet_pool = load_bet_legs(settings.edge_threshold)
    generated_flagship, alternatives = render_parlay_builder(
        bet_pool,
        slate_date,
        bankroll,
        risk,
        max_legs,
    )
    render_marketing_agent(flagship_rec or generated_flagship, bankroll)

render_subscriber_form(admin_mode)
