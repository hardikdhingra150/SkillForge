import re
from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class RequirementReview:
    method: str
    candidate_workflow: str | None
    requires_confirmation: bool
    next_action: str
    required_inputs: tuple[str, ...]
    summary: str
    input_message: str
    confidence: float | None = None
    question: str | None = None

    def payload(self) -> dict:
        value = asdict(self)

        # Convert the tuple into a JSON-friendly list.
        value["required_inputs"] = list(
            self.required_inputs
        )

        return value


def review_requirement(
    requirement: str,
) -> RequirementReview:
    normalized = " ".join(
        requirement.casefold()
        .replace("\u2019", "'")
        .split()
    )

    # Recognize a narrow candidate workflow.
    phrase = re.search(
        r"\brevenue\s+"
        r"(?:(?:grouped|aggregated)\s+)?"
        r"by\s+products?\b",
        normalized,
    )

    # Requests containing these terms need clarification.
    needs_clarification = re.search(
        r"\b(?:"
        r"not|never|don't|dont|without|instead|"
        r"forecast|predict|average|median|"
        r"margin|profit|region|country|month|date"
        r")\b",
        normalized,
    )

    if phrase and not needs_clarification:
        return RequirementReview(
            method="keyword_rules_v1",
            candidate_workflow="revenue_by_product",
            requires_confirmation=True,
            next_action="upload_csv",
            required_inputs=("sales_csv",),
            summary=(
                "The request may fit the "
                "revenue-by-product workflow. "
                "A sales CSV is needed to confirm "
                "its inputs."
            ),
            input_message=(
                "A sales CSV is required before "
                "column mapping, skill selection, "
                "and analysis can continue."
            ),
        )

    return RequirementReview(
        method="keyword_rules_v1",
        candidate_workflow=None,
        requires_confirmation=True,
        next_action="clarify_requirement",
        required_inputs=("confirmed_requirement",),
        summary=(
            "The current rules could not select "
            "a candidate workflow confidently."
        ),
        input_message=(
            "Clarification is required. "
            "The first supported workflow is "
            "revenue by product from a sales CSV; "
            "confirm whether that matches "
            "your request."
        ),
    )

# ---------- model review (runs outside any database transaction) ----------

WORKBENCH_WORKFLOWS = {
    "revenue_by_product": "Total revenue per product from a sales CSV (needs a product column and a revenue column).",
}
CONFIDENT = 0.7

REVIEW_SYSTEM = """You review requests for SkillForge's Workbench, which runs CSV workflows.
Available workflows:
{workflows}

Decide whether the request (and any clarification answers) asks for one of these workflows.
Different wording counts ("total sales per item", "revenue grouped by product", "how much did each product make").
If it is clear, name the workflow with high confidence. If it might be one of them but something is unclear, or it
asks for something else, give low confidence and ONE short, specific question to the user.
Reply with ONLY a JSON object:
{{"workflow": "<name>" | null, "confidence": 0.0-1.0, "question": "<question or null>", "summary": "<one line>"}}"""


def full_text(requirement: str, clarifications: list[str]) -> str:
    return requirement + "".join(f"\nClarification: {answer}" for answer in clarifications)


def review_with_model(requirement: str, clarifications: list[str], provider, model=None) -> RequirementReview:
    """Ask a model to map the request to a Workbench workflow. Raises on model errors (callers fall back)."""
    from app.llm import complete_json

    workflows = "\n".join(f"- {name}: {about}" for name, about in WORKBENCH_WORKFLOWS.items())
    verdict = complete_json(provider, f"Request: {full_text(requirement, clarifications)}",
                            system=REVIEW_SYSTEM.format(workflows=workflows), model=model, timeout=120)
    workflow = verdict.get("workflow") if verdict.get("workflow") in WORKBENCH_WORKFLOWS else None
    try:
        confidence = max(0.0, min(1.0, float(verdict.get("confidence") or 0)))
    except (TypeError, ValueError):
        confidence = 0.0
    question = str(verdict.get("question") or "").strip()[:400] or None
    if workflow and confidence >= CONFIDENT:
        accepted = review_requirement("revenue by product")  # the canonical "upload a CSV" outcome
        return replace(accepted, method="llm_review_v1", confidence=confidence,
                       summary=f"{str(verdict.get('summary') or 'Matched the revenue-by-product workflow.')[:300]}"
                               " A sales CSV is needed to confirm its inputs.")
    question = question or ("Do you want total revenue per product from a sales CSV? "
                            "If not, describe the result you need.")
    return RequirementReview(
        method="llm_review_v1", candidate_workflow=None, requires_confirmation=True,
        next_action="clarify_requirement", required_inputs=("clarification",),
        summary=str(verdict.get("summary") or "The request needs one clarification.")[:300],
        input_message=question, confidence=confidence, question=question,
    )
