"""Host-side validation checks a skill contract can require.

Checks run in the worker, outside the sandbox, against independent reference
calculations, so a skill never grades its own output.
"""

from collections.abc import Callable
from decimal import Decimal, localcontext
from itertools import groupby

from app.sandbox.tools import ToolError, parse_dates, resolve_column
from app.services import csv_inputs


class CheckFailed(ValueError):
    def __init__(self, check: str, message: str):
        super().__init__(message)
        self.check = check


def contract_outputs(contract, files, inputs, output):
    """Every output the contract declares is present."""
    missing = [field.name for field in contract.outputs if field.required and field.name not in output]
    if missing:
        raise CheckFailed("contract_outputs", f"The output is missing: {', '.join(missing)}.")
    return ["contract_outputs"]


def _resolve(headers, name, check="row_count"):
    try:
        return resolve_column(headers, name)
    except ToolError as error:
        raise CheckFailed(check, str(error)) from None


def _sales_rows(files, inputs):
    headers, rows = csv_inputs.parse_csv(files["sales_csv"])
    product = _resolve(headers, inputs["product_column"])
    revenue = _resolve(headers, inputs["revenue_column"])
    csv_inputs.validate_mapping(headers, rows, product, revenue)
    p, r = headers.index(product), headers.index(revenue)
    return [(row[p], csv_inputs.parse_amount(row[r])) for row in rows]


def sales_reference_totals(contract, files, inputs, output):
    """Recompute revenue per product with a sort/group reference and compare."""
    rows = _sales_rows(files, inputs)
    if output.get("operation") != contract.capability or output.get("rows_processed") != len(rows):
        raise CheckFailed("row_count", "The result operation or row count is incorrect.")
    actual = output.get("products")
    if not isinstance(actual, list):
        raise CheckFailed("row_count", "The result must contain a product list.")
    names = [item.get("product") for item in actual]
    if len(set(names)) != len(names):
        raise CheckFailed("unique_products", "The result contains duplicate product groups.")

    expected = {}
    with localcontext() as context:
        context.prec = 50
        for name, group in groupby(sorted(rows, key=lambda row: row[0]), key=lambda row: row[0]):
            values = [amount for _, amount in group]
            expected[name] = (sum(values, Decimal("0")), len(values))
        if set(names) != set(expected):
            raise CheckFailed("per_product_totals", "The result has missing or unexpected products.")
        for item in actual:
            amount, count = expected[item["product"]]
            if Decimal(item["revenue"]) != amount or item["row_count"] != count:
                raise CheckFailed("per_product_totals", "A product total or row count failed validation.")
        if Decimal(output["total_revenue"]) != sum((amount for _, amount in rows), Decimal("0")):
            raise CheckFailed("overall_total", "The overall revenue total failed validation.")
    return ["row_count", "unique_products", "per_product_totals", "overall_total"]


def _file(files):
    (content,) = files.values()
    return csv_inputs.parse_csv(content)


def _amounts(headers, rows, name):
    index = headers.index(_resolve(headers, name))
    try:
        return [csv_inputs.parse_amount(row[index]) for row in rows]
    except Exception:
        raise CheckFailed("row_count", "An amount in the file is not numeric.") from None


def _compare_groups(contract, output, keys, amounts, list_key, name_key):
    """Recompute sum and count per key independently and compare with the skill's list."""
    if output.get("operation") != contract.capability or output.get("rows_processed") != len(keys):
        raise CheckFailed("row_count", "The result operation or row count is incorrect.")
    actual = output.get(list_key)
    if not isinstance(actual, list) or not all(isinstance(item, dict) for item in actual):
        raise CheckFailed("row_count", f"The result must contain a {list_key} list.")
    names = [item.get(name_key) for item in actual]
    if len(set(names)) != len(names):
        raise CheckFailed("unique_groups", f"The result repeats a {name_key}.")
    with localcontext() as context:
        context.prec = 50
        expected = {}
        for key, amount in zip(keys, amounts, strict=True):
            total, count = expected.get(key, (Decimal("0"), 0))
            expected[key] = (total + amount, count + 1)
        if set(names) != set(expected):
            raise CheckFailed("group_totals", f"The result has missing or unexpected {name_key} values.")
        for item in actual:
            total, count = expected[item[name_key]]
            try:
                wrong = Decimal(item["total"]) != total or item["row_count"] != count
            except (KeyError, ArithmeticError, TypeError, ValueError):
                raise CheckFailed("group_totals", "A total is missing or not a number.") from None
            if wrong:
                raise CheckFailed("group_totals", f"The total or row count for {item[name_key]!r} is wrong.")
        try:
            overall = Decimal(output["total"])
        except (KeyError, ArithmeticError, TypeError, ValueError):
            raise CheckFailed("overall_total", "The overall total is missing or not a number.") from None
        if overall != sum(amounts, Decimal("0")):
            raise CheckFailed("overall_total", "The overall total failed validation.")
    return ["row_count", "unique_groups", "group_totals", "overall_total"]


def group_reference_totals(contract, files, inputs, output):
    """Totals per value of a column, recomputed on the host."""
    headers, rows = _file(files)
    index = headers.index(_resolve(headers, inputs["group_column"]))
    keys = [row[index] for row in rows]
    return _compare_groups(contract, output, keys, _amounts(headers, rows, inputs["amount_column"]), "groups", "group")


def monthly_reference_totals(contract, files, inputs, output):
    """Totals per calendar month, with dates read by the shared exported-date parser."""
    headers, rows = _file(files)
    index = headers.index(_resolve(headers, inputs["date_column"]))
    try:
        months = [day[:7] for day in parse_dates([row[index] for row in rows])]
    except ToolError as error:
        raise CheckFailed("row_count", f"The date column can't be read: {error}") from None
    return _compare_groups(contract, output, months, _amounts(headers, rows, inputs["amount_column"]),
                           "periods", "period")


def dedupe_reference(contract, files, inputs, output):
    """The kept rows are exactly the first occurrence of each row (or key), in the original order."""
    headers, rows = _file(files)
    key_column = inputs.get("key_column") or None
    index = headers.index(_resolve(headers, key_column)) if key_column else None
    seen, kept = set(), []
    for row in rows:
        key = tuple(cell.strip() for cell in row) if index is None else row[index].strip().casefold()
        if index is not None and not key:
            kept.append(row)
        elif key not in seen:
            seen.add(key)
            kept.append(row)
    if output.get("rows_processed") != len(rows) or output.get("headers") != headers:
        raise CheckFailed("row_count", "The result's row count or headers are wrong.")
    if output.get("rows") != kept:
        raise CheckFailed("kept_rows", "The kept rows are not the first occurrence of each row.")
    if output.get("kept") != len(kept) or output.get("removed") != len(rows) - len(kept):
        raise CheckFailed("counts", "The kept and removed counts don't add up.")
    return ["row_count", "kept_rows", "counts"]


def clean_reference(contract, files, inputs, output):
    """Every cell is the original with spaces tidied (or blank, for a placeholder); nothing else changed."""
    headers, rows = _file(files)
    placeholders = {"n/a", "na", "null", "none", "nil", "nan", "-", "--", "?", "#n/a"}

    def tidy(text):
        value = " ".join(text.split())
        return "" if value.casefold() in placeholders else value

    expected = [cleaned for cleaned in ([tidy(cell) for cell in row] for row in rows) if any(cleaned)]
    if output.get("rows_processed") != len(rows):
        raise CheckFailed("row_count", "The result's row count is wrong.")
    if output.get("headers") != [" ".join(header.split()) for header in headers]:
        raise CheckFailed("headers", "The cleaned headers are wrong.")
    if output.get("rows") != expected:
        raise CheckFailed("cells", "A cleaned cell differs from the expected value.")
    return ["row_count", "headers", "cells"]


CHECKS: dict[str, Callable] = {
    "contract_outputs": contract_outputs,
    "sales_reference_totals": sales_reference_totals,
    "group_reference_totals": group_reference_totals,
    "monthly_reference_totals": monthly_reference_totals,
    "dedupe_reference": dedupe_reference,
    "clean_reference": clean_reference,
}


def run_checks(contract, files, inputs, output) -> dict:
    """Run the contract's checks (contract_outputs always runs first)."""
    passed = []
    for name in ["contract_outputs", *[c for c in contract.checks if c != "contract_outputs"]]:
        passed.extend(CHECKS[name](contract, files, inputs, output))
    return {"passed": True, "checks": passed}
