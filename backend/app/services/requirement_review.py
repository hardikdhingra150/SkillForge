import re
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
    # The request isn't about a spreadsheet at all: the app offers to open it in Chat instead.
    suggest_chat: bool = False

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


# Words that suggest a request is about a table of data. Without any of them, it belongs in Chat.
FILE_WORDS = re.compile(
    r"\b(csv|excel|xlsx?|spreadsheets?|sheets?|files?|tables?|rows?|columns?|data|dataset|exports?|uploads?|sales|"
    r"orders?|revenue|totals?|sum|spend|spending|monthly|months?|duplicates?|dedupe|deduplicate|clean|cleanup|"
    r"regions?|products?|customers?|invoices?|transactions?|records?|list)\b", re.IGNORECASE)

CHAT_MESSAGE = ("This sounds like a Chat task. The Workbench only works on a spreadsheet you upload (CSV or Excel) "
                "and can do: {options}. Open it in Chat, where SkillForge builds a new skill for anything else, "
                "or rephrase it as one of those tasks.")


def short_options() -> str:
    return ", ".join(w.title.lower() for w in WORKFLOWS.values())


def for_chat(method: str = "keyword_rules_v1", **extra) -> RequirementReview:
    """The "this isn't a spreadsheet task" outcome: offer Chat, or let the person rephrase."""
    message = CHAT_MESSAGE.format(options=short_options())
    return RequirementReview(
        method=method, candidate_workflow=None, requires_confirmation=True, next_action="clarify_requirement",
        required_inputs=("confirmed_requirement",), summary="The request is not a spreadsheet task.",
        input_message=message, question=message, suggest_chat=True, **extra)


def review_requirement(requirement: str) -> RequirementReview:
    matches = match_workflows(requirement)
    if len(matches) == 1:
        return accepted(matches[0])
    if not matches and not FILE_WORDS.search(requirement):
        return for_chat()
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
If it is clear, name the workflow with high confidence. If it might be one of them but something is unclear, give
low confidence and ONE short, specific question to the user. If it is not about a table of data at all (writing,
text, code, maths, a new tool), set "chat" to true: SkillForge's Chat handles those.
Reply with ONLY a JSON object:
{{"workflow": "<name>" | null, "confidence": 0.0-1.0, "chat": true | false, "question": "<question or null>",
"summary": "<one line>"}}"""


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
    if verdict.get("chat") is True:
        return for_chat(method="llm_review_v1", confidence=confidence)
    question = question or ("Which result do you need: " + ", ".join(w.title.lower() for w in WORKFLOWS.values())
                            + "? Anything else works in Chat.")
    return RequirementReview(
        method="llm_review_v1", candidate_workflow=None, requires_confirmation=True,
        next_action="clarify_requirement", required_inputs=("clarification",),
        summary=str(verdict.get("summary") or "The request needs one clarification.")[:300],
        input_message=question, confidence=confidence, question=question,
    )
