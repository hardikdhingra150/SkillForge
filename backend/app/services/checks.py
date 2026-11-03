"""Host-side validation checks a skill contract can require.

Checks run in the worker, outside the sandbox, against independent reference
calculations, so a skill never grades its own output.
"""

from collections.abc import Callable
from decimal import Decimal, localcontext
from itertools import groupby

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


def _sales_rows(files, inputs):
    headers, rows = csv_inputs.parse_csv(files["sales_csv"])
    product, revenue = inputs["product_column"], inputs["revenue_column"]
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


CHECKS: dict[str, Callable] = {
    "contract_outputs": contract_outputs,
    "sales_reference_totals": sales_reference_totals,
}


def run_checks(contract, files, inputs, output) -> dict:
    """Run the contract's checks (contract_outputs always runs first)."""
    passed = []
    for name in ["contract_outputs", *[c for c in contract.checks if c != "contract_outputs"]]:
        passed.extend(CHECKS[name](contract, files, inputs, output))
    return {"passed": True, "checks": passed}
