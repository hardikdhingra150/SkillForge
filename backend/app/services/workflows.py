"""The Workbench's file workflows: what each one needs, how a request is matched to it, and column suggestions.

A workflow maps a confirmed file onto one skill capability. Its roles become the skill's `<role>_column`
inputs (the confirmed mapping is {role: header}), so adding a workflow needs a skill, a reference check and
an entry here, nothing else.
"""

import re
from dataclasses import dataclass, field
from decimal import InvalidOperation

from app.sandbox.tools import ToolError, loose, parse_dates
from app.services.csv_inputs import parse_amount


@dataclass(frozen=True)
class Role:
    name: str
    label: str
    kind: str  # label (text to group by), amount (money/number), date, key (any column)
    help: str = ""
    required: bool = True
    hints: tuple[str, ...] = ()


@dataclass(frozen=True)
class Workflow:
    id: str
    title: str
    about: str
    pattern: str
    roles: tuple[Role, ...] = ()
    example: str = ""
    file_input: str = "data_csv"
    extra_words: tuple[str, ...] = field(default=())

    def public(self):
        return {"id": self.id, "title": self.title, "about": self.about, "example": self.example,
                "roles": [{"name": r.name, "label": r.label, "kind": r.kind, "help": r.help, "required": r.required}
                          for r in self.roles]}


AMOUNT_HINTS = ("revenue", "sales", "amount", "total", "price", "value", "net", "gross", "income", "spend", "cost",
                "paid", "subtotal")
GROUP_HINTS = ("region", "country", "state", "city", "category", "store", "customer", "channel", "department",
               "segment", "team", "location", "area", "territory", "supplier", "vendor", "brand", "type")
TOTAL_WORDS = r"(?:revenue|sales|totals?|sum|amounts?|spend|spending|costs?|income|turnover)"

WORKFLOWS = {w.id: w for w in (
    Workflow(
        id="revenue_by_product", title="Revenue by product",
        about="Total revenue per product from a sales file (needs a product column and a revenue column).",
        pattern=r"\brevenue\s+(?:(?:grouped|aggregated)\s+)?by\s+products?\b",
        example="Show revenue by product from my sales data.", file_input="sales_csv",
        roles=(
            Role("product", "Product", "label", "The column that names what was sold.",
                 hints=("product", "item", "sku", "product name", "name", "title", "description")),
            Role("revenue", "Revenue", "amount", "The sale amount for each row.", hints=AMOUNT_HINTS),
        ),
    ),
    Workflow(
        id="totals_by_group", title="Totals by a column",
        about="Sum an amount per value of any column: region, country, category, store, customer...",
        pattern=TOTAL_WORDS + r"\b.*\b(?:by|per|for each|for every|grouped by)\s+(?:" + "|".join(
            ("regions?", "countr(?:y|ies)", "states?", "cit(?:y|ies)", "categor(?:y|ies)", "stores?", "customers?",
             "channels?", "departments?", "segments?", "teams?", "locations?", "areas?", "territor(?:y|ies)",
             "suppliers?", "vendors?", "brands?")) + r")\b",
        example="Total sales by region.",
        roles=(
            Role("group", "Group by", "label", "The column whose values become the rows of the result.",
                 hints=GROUP_HINTS),
            Role("amount", "Amount", "amount", "The number to add up.", hints=AMOUNT_HINTS),
        ),
    ),
    Workflow(
        id="totals_by_month", title="Totals by month",
        about="Sum an amount per calendar month from a date column (reads ISO, 15/03/2026, Mar 15, 2026...).",
        pattern=r"\b(?:" + TOTAL_WORDS + r"\b.*\b(?:by|per|each|every)\s+months?|monthly\s+" + TOTAL_WORDS
                + r"|" + TOTAL_WORDS + r"\s+(?:by|per)\s+(?:date|month))\b",
        example="Monthly sales totals from my orders file.",
        roles=(
            Role("date", "Date", "date", "When each row happened.",
                 hints=("date", "order date", "day", "created", "created at", "ordered", "timestamp", "time", "period",
                        "month", "invoice date", "transaction date")),
            Role("amount", "Amount", "amount", "The number to add up.", hints=AMOUNT_HINTS),
        ),
    ),
    Workflow(
        id="dedupe_rows", title="Remove duplicate rows",
        about="Drop repeated rows, keeping the first. Optionally compare only one key column (an id or email).",
        pattern=r"\b(?:de-?dupe|de-?duplicate|remove\s+(?:the\s+)?duplicates?|duplicate\s+rows|"
                r"drop\s+(?:the\s+)?duplicates?|unique\s+rows)\b",
        example="Remove duplicate rows from my customer list.",
        roles=(
            Role("key", "Compare by", "key", "Leave empty to compare whole rows. Pick an id or email column to "
                 "treat rows with the same value as duplicates.", required=False,
                 hints=("id", "email", "e-mail", "customer id", "order id", "key", "sku")),
        ),
    ),
    Workflow(
        id="clean_table", title="Clean up a table",
        about="Trim stray spaces, collapse repeated spaces and blank out placeholders like N/A, null and '-'.",
        pattern=r"\b(?:clean(?:\s+up)?|tidy(?:\s+up)?|trim|normali[sz]e)\b.*\b(?:data|csv|file|table|spreadsheet|"
                r"sheet|rows|cells|export|list)\b",
        example="Clean up this spreadsheet export.",
    ),
)}

BLOCKERS = re.compile(r"\b(?:not|never|don't|dont|without|instead|forecast|predict|average|median|margin|profit)\b")

# "by product and region": two group-bys at once is not one of these workflows.
TWO_DIMENSIONS = re.compile(r"\b(?:by|per)\s+\w+\s+(?:and|&)\s+(?:by\s+|per\s+)?\w+\b")


def normalize(text: str) -> str:
    return " ".join(text.casefold().replace("’", "'").split())


def match_workflows(requirement: str) -> list[str]:
    """Workflows whose wording the request uses. Negations and unsupported maths match nothing."""
    text = normalize(requirement)
    if BLOCKERS.search(text) or TWO_DIMENSIONS.search(text):
        return []
    return [w.id for w in WORKFLOWS.values() if re.search(w.pattern, text)]


# ---------- column suggestions ----------

def _fits(kind, values):
    """Share of sampled values that fit a role's kind (0..1)."""
    sample = [v for v in values[:200] if str(v).strip()]
    if not sample:
        return 0.0
    if kind == "amount":
        good = 0
        for value in sample:
            try:
                parse_amount(value)
                good += 1
            except (InvalidOperation, ValueError):
                pass
        return good / len(sample)
    if kind == "date":
        try:
            parse_dates(sample)
            return 1.0
        except ToolError:
            return 0.0
    if kind == "label":
        numeric = _fits("amount", sample)
        return 1.0 - numeric
    return 1.0


def _name_score(header, role, requirement):
    name = loose(header)
    score = 0.0
    for rank, hint in enumerate(role.hints):
        if name == hint:
            score = max(score, 3.0 - rank * 0.05)
        elif hint in name.split() or name.startswith(hint) or name.endswith(hint):
            score = max(score, 2.0 - rank * 0.05)
    if requirement and len(name) > 2 and re.search(rf"\b{re.escape(name)}s?\b", requirement):
        score += 4.0  # the person named this column in their request ("totals by region")
    return score


def suggest_mapping(workflow_id, headers, rows, requirement="") -> dict:
    """Best guess at {role: header} from header names, the request wording and the values themselves."""
    workflow = WORKFLOWS.get(workflow_id)
    if workflow is None:
        return {}
    text = normalize(requirement)
    columns = {header: [row[i] for row in rows] for i, header in enumerate(headers)}
    candidates = []
    for role in workflow.roles:
        if not role.required and role.kind == "key":
            for header in headers:  # optional key: only when the name clearly says so
                if _name_score(header, role, "") >= 2.9 or (text and _name_score(header, role, text) >= 4.0):
                    candidates.append((10.0, role.name, header))
            continue
        for header, values in columns.items():
            fit = _fits(role.kind, values)
            if fit < 0.9:
                continue
            candidates.append((_name_score(header, role, text) + fit, role.name, header))
    mapping, used = {}, set()
    for _score, role_name, header in sorted(candidates, key=lambda c: -c[0]):
        if role_name not in mapping and header not in used:
            mapping[role_name] = header
            used.add(header)
    return mapping


# ---------- mapping validation ----------

def check_amount(role, row_number, text):
    try:
        number = parse_amount(text)
    except InvalidOperation:
        raise ValueError(f"The {role.label.lower()} value is not numeric on data row {row_number}.") from None
    if not number.is_finite() or number.adjusted() > 17 or number.as_tuple().exponent < -6:
        raise ValueError(f"{role.label} on data row {row_number} must be finite, "
                         "with at most 18 integer digits and 6 decimal places.")


def validate_columns(workflow_id, headers, rows, mapping: dict) -> dict:
    """Check a {role: header} mapping against the file. Returns the mapping with optional empties dropped."""
    workflow = WORKFLOWS[workflow_id]
    roles = {role.name: role for role in workflow.roles}
    unknown = set(mapping) - set(roles)
    if unknown:
        raise ValueError(f"{workflow.title} has no column called {', '.join(sorted(unknown))}.")
    chosen = {name: header for name, header in mapping.items() if header}
    for role in workflow.roles:
        if role.required and role.name not in chosen:
            raise ValueError(f"Choose the {role.label.lower()} column.")
    if any(header not in headers for header in chosen.values()):
        raise ValueError("Choose columns from this file's headers.")
    if len(set(chosen.values())) != len(chosen):
        raise ValueError("Each column can only be used once.")
    for name, header in chosen.items():
        role, index = roles[name], headers.index(header)
        values = [row[index] for row in rows]
        if role.kind == "label":
            for row_number, value in enumerate(values, start=1):
                if not value.strip():
                    raise ValueError(f"The {role.label.lower()} value is empty on data row {row_number}.")
        elif role.kind == "amount":
            for row_number, value in enumerate(values, start=1):
                check_amount(role, row_number, value)
        elif role.kind == "date":
            for row_number, value in enumerate(values, start=1):
                if not value.strip():
                    raise ValueError(f"The date is empty on data row {row_number}.")
            try:
                parse_dates(values)
            except ToolError as error:
                raise ValueError(f"The date column can't be read: {error}") from None
    return chosen


def describe_mapping(workflow_id, mapping) -> str:
    roles = {role.name: role for role in WORKFLOWS[workflow_id].roles}
    if not mapping:
        return "No columns needed."
    return "; ".join(f"{roles[name].label.lower()} = {header}" for name, header in mapping.items())
