from dataclasses import asdict, dataclass

from app.services.workflows import WORKFLOWS, match_workflows


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


def accepted(workflow_id: str, method: str = "keyword_rules_v1", **extra) -> RequirementReview:
    """The "this fits a workflow: upload the file" outcome."""
    workflow = WORKFLOWS[workflow_id]
    return RequirementReview(
        method=method,
        candidate_workflow=workflow_id,
        requires_confirmation=True,
        next_action="upload_csv",
        required_inputs=(workflow.file_input,),
        summary=f"The request fits the {workflow.title.lower()} workflow. "
                "Upload a CSV or Excel file to confirm its columns.",
        input_message=f"Upload the file for {workflow.title.lower()} (CSV or Excel). "
                      "SkillForge will suggest the columns for you to confirm.",
        **extra,
    )


def review_requirement(requirement: str) -> RequirementReview:
    matches = match_workflows(requirement)
    if len(matches) == 1:
        return accepted(matches[0])
    options = "; ".join(f"{w.title.lower()} (e.g. \"{w.example}\")" for w in WORKFLOWS.values())
    return RequirementReview(
        method="keyword_rules_v1",
        candidate_workflow=None,
        requires_confirmation=True,
        next_action="clarify_requirement",
        required_inputs=("confirmed_requirement",),
        summary=("The request matches more than one workflow." if matches else
                 "The current rules could not select a candidate workflow confidently."),
        input_message=("Clarification is required. Pick one result to produce. The Workbench can do: "
                       f"{options}. Anything else works in Chat."),
    )

# ---------- model review (runs outside any database transaction) ----------

WORKBENCH_WORKFLOWS = {w.id: w.about for w in WORKFLOWS.values()}
CONFIDENT = 0.7

REVIEW_SYSTEM = """You review requests for SkillForge's Workbench, which runs workflows on an uploaded CSV or Excel file.
Available workflows:
{workflows}

Decide whether the request (and any clarification answers) asks for one of these workflows.
Different wording counts ("total sales per item" is revenue_by_product, "spend per department" is totals_by_group,
"how did sales change each month" is totals_by_month, "get rid of repeated rows" is dedupe_rows).
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
        about = str(verdict.get("summary") or f"Matched the {WORKFLOWS[workflow].title.lower()} workflow.")[:300]
        review = accepted(workflow, method="llm_review_v1", confidence=confidence)
        return RequirementReview(**{**review.payload(), "required_inputs": review.required_inputs,
                                    "summary": f"{about} Upload a CSV or Excel file to confirm its columns."})
    question = question or ("Which result do you need: " + ", ".join(w.title.lower() for w in WORKFLOWS.values())
                            + "? Anything else works in Chat.")
    return RequirementReview(
        method="llm_review_v1", candidate_workflow=None, requires_confirmation=True,
        next_action="clarify_requirement", required_inputs=("clarification",),
        summary=str(verdict.get("summary") or "The request needs one clarification.")[:300],
        input_message=question, confidence=confidence, question=question,
    )
