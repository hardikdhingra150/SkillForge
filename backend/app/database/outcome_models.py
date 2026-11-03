from sqlalchemy import CheckConstraint, DateTime, Integer, String, Uuid, func, text
from sqlalchemy.orm import mapped_column

from app.database.models import Base

ROLES = ("planner", "author", "verifier")
EVENTS = (
    "proven",              # author: a skill passed every proof (attempts says how many tries)
    "rejected",            # author: one attempt failed its proof
    "exhausted",           # author: no attempt passed within the budget
    "overruled",           # author: the verifier said the output was wrong
    "example_corrected",   # author: a worked example was wrong and the code right
    "reused",              # author: a skill it wrote was reused successfully
    "agreed",              # verifier: agreed with the output
    "disagreed",           # verifier: disagreed with the output
    "escalated",           # author: the task moved to a stronger model
)


class ModelOutcome(Base):
    """One observed outcome for one model, used for the scoreboard and auto-routing."""

    __tablename__ = "model_outcomes"

    id = mapped_column(Uuid, primary_key=True, server_default=text("uuidv7()"))
    provider = mapped_column(String(20), nullable=False, index=True)
    model = mapped_column(String(80), nullable=True)
    role = mapped_column(String(20), nullable=False)
    event = mapped_column(String(30), nullable=False)
    capability = mapped_column(String(80), nullable=True, index=True)
    attempts = mapped_column(Integer, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(f"role IN {ROLES}", name="ck_model_outcomes_role"),
        CheckConstraint(f"event IN {EVENTS}", name="ck_model_outcomes_event"),
    )
