"""The approved toolkit a skill receives as `tools`.

Stdlib only: the sandbox child process imports this module directly. A skill
sees only the tools its contract lists, as plain functions on a namespace.
"""

import csv
import io
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from types import SimpleNamespace

PRECISION = 50


CURRENCY_SYMBOLS = "$€£₹¥"
GROUPED = re.compile(r"^\d{1,3}(,\d{3})+(\.\d+)?$")
PLAIN = re.compile(r"^\d+(\.\d+)?$")


class ToolError(ValueError):
    """A tool failure with a machine-readable code the repair loop can act on."""

    def __init__(self, code, message, **details):
        super().__init__(message)
        self.code = code
        self.details = details


ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
YMD = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[ T].*)?$")
NUMERIC = re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})(?:[ T].*)?$")
MONTHS = {name: number for number, names in enumerate((
    ("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"), ("may",), ("jun", "june"),
    ("jul", "july"), ("aug", "august"), ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"),
    ("dec", "december")), start=1) for name in names}
DAY_MONTH = re.compile(r"^(\d{1,2})[ -]([a-z]+)\.?[ -,]+(\d{4})$")
MONTH_DAY = re.compile(r"^([a-z]+)\.?[ -](\d{1,2})(?:st|nd|rd|th)?,?[ -]+(\d{4})$")


def _iso(year, month, day, raw):
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        raise ToolError("DATE_FORMAT", f"{raw!r} is not a real calendar date.", value=raw[:80]) from None


def iso_dates(values):
    """Strict: every value must be an ISO date (2026-03-15). Returns the dates as ISO strings."""
    result = []
    for value in values:
        raw = str(value).strip()
        match = ISO_DATE.match(raw)
        if not match:
            raise ToolError("DATE_FORMAT", f"{raw!r} is not an ISO date (YYYY-MM-DD).", value=raw[:80])
        result.append(_iso(*match.groups(), raw))
    return result


def date_order(values):
    """For numeric dates like 03/04/2026, decide from the whole column whether the day or month comes first."""
    day_first = month_first = False
    for value in values:
        match = NUMERIC.match(str(value).strip())
        if match:
            first, second = int(match.group(1)), int(match.group(2))
            day_first = day_first or first > 12
            month_first = month_first or second > 12
    if day_first and month_first:
        raise ToolError("DATE_AMBIGUOUS", "This column mixes day-first and month-first dates.")
    return "day_first" if day_first else "month_first"


def parse_dates(values):
    """Dates as exported: ISO, 2026/03/15, 15/03/2026 or 03/15/2026 (order read from the whole column),
    15 Mar 2026, Mar 15, 2026. Returns ISO strings; rejects anything it cannot read for certain."""
    values = [str(value).strip() for value in values]
    order = date_order(values)
    result = []
    for raw in values:
        text = raw.casefold()
        if match := YMD.match(text):
            result.append(_iso(*match.groups(), raw))
        elif match := NUMERIC.match(text):
            first, second, year = match.groups()
            year = int(year) + (2000 if len(year) == 2 and int(year) < 70 else 1900 if len(year) == 2 else 0)
            day, month = (first, second) if order == "day_first" else (second, first)
            result.append(_iso(year, month, day, raw))
        elif (match := DAY_MONTH.match(text)) and match.group(2) in MONTHS:
            result.append(_iso(match.group(3), MONTHS[match.group(2)], match.group(1), raw))
        elif (match := MONTH_DAY.match(text)) and match.group(1) in MONTHS:
            result.append(_iso(match.group(3), MONTHS[match.group(1)], match.group(2), raw))
        else:
            raise ToolError("DATE_FORMAT", f"{raw!r} is not a recognizable date.", value=raw[:80])
    return result


def loose(name):
    """Header comparison that ignores case, surrounding spaces, underscores and hyphens."""
    return " ".join(str(name).casefold().replace("_", " ").replace("-", " ").split())


def resolve_column(headers, name):
    """The header a column name refers to: an exact match, else the one header that matches loosely."""
    if name in headers:
        return name
    matches = [header for header in headers if loose(header) == loose(name)]
    if len(matches) == 1:
        return matches[0]
    raise ToolError("MISSING_COLUMN", f"Column {name!r} not found. Available columns: {', '.join(headers)}.",
                    column=str(name), available=list(headers))


class Toolbox(SimpleNamespace):
    def __getattr__(self, name):
        raise AttributeError(f"The tool {name!r} is not in this skill's contract.")


def make_tools(files: dict[str, bytes], allowed) -> Toolbox:
    def read_csv(name):
        """Return (headers, rows) for a confirmed CSV input. Blank rows are skipped."""
        if name not in files:
            raise ValueError(f"No CSV input named {name!r}.")
        reader = csv.reader(io.StringIO(files[name].decode("utf-8-sig"), newline=""))
        headers = next(reader, [])
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]
        return list(headers), rows

    def column(headers, rows, name):
        """Return one column's values. Fails with the available headers if it is missing."""
        if name not in headers:
            raise ToolError("MISSING_COLUMN", f"Column {name!r} not found. Available columns: {', '.join(headers)}.",
                            column=name, available=list(headers))
        index = headers.index(name)
        return [row[index] for row in rows]

    def find_column(headers, rows, name):
        """Like column(), but also finds a header that differs only in case, spaces, underscores or hyphens."""
        index = headers.index(resolve_column(headers, name))
        return [row[index] for row in rows]

    def to_decimal(text):
        """Strict: plain decimal syntax only (e.g. 1200.50)."""
        try:
            value = Decimal(str(text).strip())
        except InvalidOperation:
            raise ToolError("BAD_NUMBER", f"{text!r} is not a plain number.", value=str(text)[:80]) from None
        if not value.is_finite():
            raise ToolError("BAD_NUMBER", f"{text!r} is not a finite number.", value=str(text)[:80])
        return value

    def parse_amount(text):
        """Money amounts as exported: $1,200.50, -€300, (1,200). Rejects ambiguous grouping."""
        raw = str(text).strip()
        try:
            return to_decimal(raw)
        except ToolError:
            pass
        value, negative = raw, False
        if value.startswith("(") and value.endswith(")"):
            value, negative = value[1:-1].strip(), True
        if value.startswith("-"):
            value, negative = value[1:].strip(), not negative
        if value[:1] and value[0] in CURRENCY_SYMBOLS:
            value = value[1:].strip()
        if value.startswith("-") and not negative:
            value, negative = value[1:].strip(), True
        if not (GROUPED.match(value) or PLAIN.match(value)):
            raise ToolError("BAD_NUMBER", f"{raw!r} is not a recognizable amount.", value=raw[:80])
        amount = Decimal(value.replace(",", ""))
        return -amount if negative else amount

    def decimal_sum(values):
        with localcontext() as context:
            context.prec = PRECISION
            return sum(values, Decimal("0"))

    def group_sum(keys, values):
        """Sum values per key: {key: {"total": Decimal, "count": int}}."""
        if len(keys) != len(values):
            raise ValueError("group_sum needs the same number of keys and values.")
        groups = {}
        with localcontext() as context:
            context.prec = PRECISION
            for key, value in zip(keys, values, strict=True):
                group = groups.setdefault(key, {"total": Decimal("0"), "count": 0})
                group["total"] += value
                group["count"] += 1
        return groups

    def format_decimal(value):
        return format(value, "f")

    def regex_findall(pattern, text):
        """All non-overlapping matches of a regular expression (groups become tuples as lists)."""
        return [list(m) if isinstance(m, tuple) else m for m in re.findall(pattern, str(text))]

    def regex_sub(pattern, replacement, text):
        return re.sub(pattern, replacement, str(text))

    def regex_split(pattern, text):
        return re.split(pattern, str(text))

    def parse_json(text):
        try:
            return json.loads(text)
        except ValueError as error:
            raise ToolError("BAD_JSON", f"Not valid JSON: {error}") from None

    def to_json(value):
        return json.dumps(value, sort_keys=True)

    available = {
        "read_csv": read_csv, "column": column, "find_column": find_column, "iso_dates": iso_dates,
        "parse_dates": parse_dates, "to_decimal": to_decimal, "parse_amount": parse_amount,
        "decimal_sum": decimal_sum, "group_sum": group_sum, "format_decimal": format_decimal,
        "regex_findall": regex_findall, "regex_sub": regex_sub, "regex_split": regex_split,
        "parse_json": parse_json, "to_json": to_json,
    }
    unknown = set(allowed) - set(available)
    if unknown:
        raise ValueError(f"Unknown tools requested: {', '.join(sorted(unknown))}.")
    return Toolbox(**{name: available[name] for name in allowed})


TOOL_NAMES = ("read_csv", "column", "find_column", "iso_dates", "parse_dates", "to_decimal", "parse_amount", "decimal_sum", "group_sum", "format_decimal",
              "regex_findall", "regex_sub", "regex_split", "parse_json", "to_json")

# One-line docs shown to SkillSmith when it writes a new skill.
TOOL_DOCS = {
    "read_csv": "read_csv(name) -> (headers, rows) for a CSV input",
    "column": "column(headers, rows, name) -> list of that column's string values",
    "find_column": "find_column(headers, rows, name) -> like column, but tolerant of case/spaces/underscores",
    "iso_dates": "iso_dates(values) -> list of ISO date strings; strict YYYY-MM-DD only",
    "parse_dates": "parse_dates(values) -> list of ISO date strings from exported formats (15/03/2026, Mar 15, 2026)",
    "to_decimal": "to_decimal(text) -> Decimal, plain numbers only",
    "parse_amount": "parse_amount(text) -> Decimal, also $1,200.50 / (300) / -€100",
    "decimal_sum": "decimal_sum(values) -> Decimal sum",
    "group_sum": "group_sum(keys, values) -> {key: {'total': Decimal, 'count': int}}",
    "format_decimal": "format_decimal(value) -> plain string of a Decimal",
    "regex_findall": "regex_findall(pattern, text) -> list of matches",
    "regex_sub": "regex_sub(pattern, replacement, text) -> str",
    "regex_split": "regex_split(pattern, text) -> list of str",
    "parse_json": "parse_json(text) -> value",
    "to_json": "to_json(value) -> str with sorted keys",
}
