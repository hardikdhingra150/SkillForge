"""The approved toolkit a skill receives as `tools`.

Stdlib only: the sandbox child process imports this module directly. A skill
sees only the tools its contract lists, as plain functions on a namespace.
"""

import csv
import io
import re
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

    available = {
        "read_csv": read_csv, "column": column, "to_decimal": to_decimal, "parse_amount": parse_amount,
        "decimal_sum": decimal_sum, "group_sum": group_sum, "format_decimal": format_decimal,
    }
    unknown = set(allowed) - set(available)
    if unknown:
        raise ValueError(f"Unknown tools requested: {', '.join(sorted(unknown))}.")
    return Toolbox(**{name: available[name] for name in allowed})


TOOL_NAMES = ("read_csv", "column", "to_decimal", "parse_amount", "decimal_sum", "group_sum", "format_decimal")
