import hashlib
from collections import defaultdict
from decimal import Decimal, localcontext
from itertools import groupby
from pathlib import Path

from app.services import csv_inputs

SKILL_ID = "revenue_by_product"
VERSION = "1.0.0"

# Pin the code loaded by this worker, including its CSV validation dependency.
IMPLEMENTATION_HASH = hashlib.sha256(
    Path(__file__).read_bytes() + b"\0" + Path(csv_inputs.__file__).read_bytes()
).hexdigest()


def input_rows(content, mapping):
    headers, rows = csv_inputs.parse_csv(content)
    csv_inputs.validate_mapping(headers, rows, mapping["product"], mapping["revenue"])
    p = headers.index(mapping["product"])
    r = headers.index(mapping["revenue"])
    return [(row[p], Decimal(row[r].strip())) for row in rows]


def run_sales(content, mapping):
    rows = input_rows(content, mapping)
    totals = defaultdict(lambda: Decimal("0"))
    counts = defaultdict(int)
    with localcontext() as context:
        context.prec = 50
        for product, amount in rows:
            totals[product] += amount
            counts[product] += 1
        total = sum(totals.values(), Decimal("0"))
    return {
        "operation": SKILL_ID,
        "rows_processed": len(rows),
        "products": [
            {"product": name, "revenue": format(totals[name], "f"), "row_count": counts[name]}
            for name in sorted(totals)
        ],
        "total_revenue": format(total, "f"),
    }


def validate_sales_result(content, mapping, result):
    rows = input_rows(content, mapping)
    if result.get("operation") != SKILL_ID or result.get("rows_processed") != len(rows):
        raise ValueError("The result operation or row count is incorrect.")
    actual = result.get("products")
    if not isinstance(actual, list):
        raise ValueError("The result must contain a product list.")
    names = [item["product"] for item in actual]
    if len(set(names)) != len(names):
        raise ValueError("The result contains duplicate product groups.")

    # Independently check each group using a sort/group reference calculation.
    expected = {}
    with localcontext() as context:
        context.prec = 50
        for name, group in groupby(sorted(rows, key=lambda row: row[0]), key=lambda row: row[0]):
            values = [amount for _, amount in group]
            expected[name] = (sum(values, Decimal("0")), len(values))
        if set(names) != set(expected):
            raise ValueError("The result has missing or unexpected products.")
        for item in actual:
            amount, count = expected[item["product"]]
            if Decimal(item["revenue"]) != amount or item["row_count"] != count:
                raise ValueError("A product total or row count failed validation.")
        if Decimal(result["total_revenue"]) != sum((amount for _, amount in rows), Decimal("0")):
            raise ValueError("The overall revenue total failed validation.")
    return {
        "passed": True,
        "checks": ["row_count", "unique_products", "per_product_totals", "overall_total"],
    }


def run_self_tests():
    mapping = {"product": "Product", "revenue": "Sales"}
    cases = [
        ("alias_and_grouping", b"Product,Sales\nPen,100\nBook,200\nPen,50\n", {"Book": "200", "Pen": "150"}, "350"),
        ("decimals_and_negative", b"Product,Sales\nA,0.10\nA,0.20\nB,-0.05\n", {"A": "0.30", "B": "-0.05"}, "0.25"),
        ("zero", b"Product,Sales\nA,0\n", {"A": "0"}, "0"),
    ]
    evidence = []
    for name, content, expected, total in cases:
        result = run_sales(content, mapping)
        validate_sales_result(content, mapping, result)
        actual = {item["product"]: Decimal(item["revenue"]) for item in result["products"]}
        if actual != {key: Decimal(value) for key, value in expected.items()} or Decimal(result["total_revenue"]) != Decimal(total):
            raise ValueError(f"Built-in fixture failed: {name}.")
        evidence.append({"name": name, "passed": True})
    try:
        run_sales(b"Product,Sales\nA,invalid\n", mapping)
    except ValueError:
        evidence.append({"name": "reject_invalid_revenue", "passed": True})
    else:
        raise ValueError("Invalid revenue was not rejected.")
    return {"passed": True, "test_count": len(evidence), "tests": evidence}
