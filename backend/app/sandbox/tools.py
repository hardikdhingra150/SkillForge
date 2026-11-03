"""The approved toolkit a skill receives as `tools`.

Stdlib only: the sandbox child process imports this module directly. A skill
sees only the tools its contract lists, as plain functions on a namespace.
"""

import csv
import io
from decimal import Decimal, InvalidOperation, localcontext
from types import SimpleNamespace

PRECISION = 50


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
            raise ValueError(f"Column {name!r} not found. Available columns: {', '.join(headers)}.")
        index = headers.index(name)
        return [row[index] for row in rows]

    def to_decimal(text):
        try:
            value = Decimal(str(text).strip())
        except InvalidOperation:
            raise ValueError(f"{text!r} is not a number.") from None
        if not value.is_finite():
            raise ValueError(f"{text!r} is not a finite number.")
        return value

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
        "read_csv": read_csv, "column": column, "to_decimal": to_decimal,
        "decimal_sum": decimal_sum, "group_sum": group_sum, "format_decimal": format_decimal,
    }
    unknown = set(allowed) - set(available)
    if unknown:
        raise ValueError(f"Unknown tools requested: {', '.join(sorted(unknown))}.")
    return Toolbox(**{name: available[name] for name in allowed})


TOOL_NAMES = ("read_csv", "column", "to_decimal", "decimal_sum", "group_sum", "format_decimal")
