"""Model scoreboard: what each model actually achieved, and routing that learns from it.

Every proof leaves an outcome row. The scoreboard aggregates them per model and
per capability; auto-routing picks the cheapest model that has earned trust for
a capability, and the strongest one when nothing has.
"""

import logging
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.database.outcome_models import ModelOutcome
from app.database.session import SessionLocal
from app.llm import PROVIDERS

logger = logging.getLogger("skillforge.scoreboard")

# Cheapest first: auto-routing prefers the cheapest model that is good enough.
COST_ORDER = ["ollama", "groq", "codex", "claude"]
MIN_SAMPLES = 2
TRUST_RATE = 0.6


def record(provider, role, event, *, model=None, capability=None, attempts=None):
    """Best effort: a scoreboard write must never break a chat turn."""
    try:
        with SessionLocal.begin() as db:
            db.add(ModelOutcome(provider=provider, model=model, role=role, event=event,
                                capability=capability, attempts=attempts))
    except SQLAlchemyError as error:
        logger.warning("Could not record model outcome: %s", getattr(error, "orig", error))


def _counts(db, *where):
    rows = db.execute(
        select(ModelOutcome.provider, ModelOutcome.event, func.count(), func.avg(ModelOutcome.attempts))
        .where(*where).group_by(ModelOutcome.provider, ModelOutcome.event)
    ).all()
    counts = defaultdict(lambda: defaultdict(int))
    attempts = {}
    for provider, event, count, avg in rows:
        counts[provider][event] = count
        if event == "proven" and avg is not None:
            attempts[provider] = float(avg)
    return counts, attempts


def provider_stats(counts, attempts, provider):
    c = counts.get(provider, {})
    proven, exhausted = c.get("proven", 0), c.get("exhausted", 0)
    tasks = proven + exhausted
    first_try = c.get("first_try", 0)
    judged = c.get("agreed", 0) + c.get("disagreed", 0)
    return {
        "provider": provider,
        "skills_proven": proven,
        "tasks_attempted": tasks,
        "success_rate": round(proven / tasks, 3) if tasks else None,
        "first_try_rate": round(first_try / proven, 3) if proven else None,
        "avg_attempts": round(attempts[provider], 2) if provider in attempts else None,
        "rejected_attempts": c.get("rejected", 0),
        "overruled": c.get("overruled", 0),
        "examples_corrected": c.get("example_corrected", 0),
        "escalated_away": c.get("escalated", 0),
        "reuses": c.get("reused", 0),
        "verifier_checks": judged,
        "verifier_agree_rate": round(c.get("agreed", 0) / judged, 3) if judged else None,
    }


def summary(db):
    counts, attempts = _counts(db)
    first_try = db.execute(
        select(ModelOutcome.provider, func.count()).where(ModelOutcome.event == "proven", ModelOutcome.attempts == 1)
        .group_by(ModelOutcome.provider)
    ).all()
    for provider, count in first_try:
        counts[provider]["first_try"] = count
    providers = [provider_stats(counts, attempts, p) for p in COST_ORDER if p in PROVIDERS]
    capability_rows = db.execute(
        select(ModelOutcome.capability, ModelOutcome.provider, ModelOutcome.event, func.count())
        .where(ModelOutcome.capability.is_not(None), ModelOutcome.role == "author")
        .group_by(ModelOutcome.capability, ModelOutcome.provider, ModelOutcome.event)
    ).all()
    capabilities = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for capability, provider, event, count in capability_rows:
        capabilities[capability][provider][event] = count
    by_capability = []
    for capability, per in sorted(capabilities.items()):
        by_capability.append({
            "capability": capability,
            "providers": {p: {"proven": e.get("proven", 0), "exhausted": e.get("exhausted", 0), "reused": e.get("reused", 0)}
                          for p, e in per.items()},
            "routed_to": route_from(per, available=[p for p in COST_ORDER if p in PROVIDERS]),
        })
    return {"providers": providers, "capabilities": by_capability, "policy": {
        "order": "cheapest model that has earned trust for the capability; with no history, the cheapest model, escalating on failure",
        "min_samples": MIN_SAMPLES, "trust_rate": TRUST_RATE,
    }}


def route_from(per_provider, available):
    """Cheapest provider with enough proven results for this capability, or None."""
    for provider in available:
        events = per_provider.get(provider, {})
        tasks = events.get("proven", 0) + events.get("exhausted", 0)
        if tasks >= MIN_SAMPLES and events.get("proven", 0) / tasks >= TRUST_RATE:
            return provider
        if events.get("proven", 0) >= 1 and not events.get("exhausted", 0):
            return provider
    return None


def route_author(capability):
    """Pick the author for a capability: learned choice first, then cheapest-with-good-record, then strongest."""
    available = [p for p in COST_ORDER if p in PROVIDERS and PROVIDERS[p].status().available]
    if not available:
        return None, "No model is available."
    with SessionLocal() as db:
        rows = db.execute(
            select(ModelOutcome.provider, ModelOutcome.event, func.count())
            .where(ModelOutcome.capability == capability, ModelOutcome.role == "author")
            .group_by(ModelOutcome.provider, ModelOutcome.event)
        ).all()
        per = defaultdict(lambda: defaultdict(int))
        for provider, event, count in rows:
            per[provider][event] = count
        learned = route_from(per, available)
        if learned:
            proven = per[learned].get("proven", 0)
            return learned, f"{PROVIDERS[learned].label} has proven {capability} {proven} time(s)."
        counts, _ = _counts(db, ModelOutcome.role == "author")
    for provider in available:
        c = counts.get(provider, {})
        tasks = c.get("proven", 0) + c.get("exhausted", 0)
        if tasks >= MIN_SAMPLES and c.get("proven", 0) / tasks >= TRUST_RATE:
            return provider, f"No history for {capability}; {PROVIDERS[provider].label} is the cheapest model with a good record."
    # No evidence yet: try the cheapest model. Escalation catches a failure, and the outcome teaches the router.
    cheapest = available[0]
    return cheapest, f"No history yet; trying the cheapest model, {PROVIDERS[cheapest].label} (escalates if it fails)."


def pick_planner():
    """Planning is a light task: the cheapest available model."""
    for provider in COST_ORDER:
        if provider in PROVIDERS and PROVIDERS[provider].status().available:
            return provider
    return None
