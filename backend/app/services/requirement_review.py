import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RequirementReview:
    method: str
    candidate_workflow: str | None
    requires_confirmation: bool
    next_action: str
    required_inputs: tuple[str, ...]
    summary: str
    input_message: str

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