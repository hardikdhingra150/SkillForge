"""Built-in skills: source files plus their contracts and fixture tests."""

from dataclasses import dataclass, field
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class BuiltinSkill:
    skill_id: str
    version: str
    source_file: str
    contract: dict
    # (name, inputs, files, expected) where expected is a dict of output fields, or None when the run must fail.
    fixtures: list = field(default_factory=list)

    @property
    def source(self) -> str:
        return (SKILLS_DIR / self.source_file).read_text()


SALES_MAPPING = {"product_column": "Product", "revenue_column": "Sales"}

REVENUE_BY_PRODUCT = BuiltinSkill(
    skill_id="revenue_by_product",
    version="1.0.0",
    source_file="revenue_by_product.py",
    contract={
        "capability": "revenue_by_product",
        "summary": "Total revenue per product from a sales CSV.",
        "entrypoint": "run",
        "inputs": [
            {"name": "sales_csv", "type": "csv", "description": "Confirmed sales export."},
            {"name": "product_column", "type": "column", "description": "Header holding the product name."},
            {"name": "revenue_column", "type": "column", "description": "Header holding the sale amount."},
        ],
        "outputs": [
            {"name": "operation", "type": "text"},
            {"name": "rows_processed", "type": "integer"},
            {"name": "products", "type": "list"},
            {"name": "total_revenue", "type": "decimal_string"},
        ],
        "tools": ["read_csv", "column", "to_decimal", "group_sum", "decimal_sum", "format_decimal"],
        "checks": ["contract_outputs", "sales_reference_totals"],
    },
    fixtures=[
        ("alias_and_grouping", SALES_MAPPING, {"sales_csv": b"Product,Sales\nPen,100\nBook,200\nPen,50\n"},
         {"totals": {"Book": "200", "Pen": "150"}, "total_revenue": "350"}),
        ("decimals_and_negative", SALES_MAPPING, {"sales_csv": b"Product,Sales\nA,0.10\nA,0.20\nB,-0.05\n"},
         {"totals": {"A": "0.30", "B": "-0.05"}, "total_revenue": "0.25"}),
        ("zero", SALES_MAPPING, {"sales_csv": b"Product,Sales\nA,0\n"},
         {"totals": {"A": "0"}, "total_revenue": "0"}),
        ("reject_invalid_revenue", SALES_MAPPING, {"sales_csv": b"Product,Sales\nA,invalid\n"}, None),
    ],
)

BUILTIN_SKILLS = [REVENUE_BY_PRODUCT]
