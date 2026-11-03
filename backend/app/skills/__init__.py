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
    # (name, inputs, files, expected): expected is a dict of output fields, "checks" (contract checks
    # only), or None when the run must fail.
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

def text_skill(skill_id, summary, inputs, outputs, tools, fixtures, version="1.0.0"):
    """A starter skill on plain values. Fixtures are (name, inputs, expected output)."""
    return BuiltinSkill(
        skill_id=skill_id, version=version, source_file=f"{skill_id}.py",
        contract={"capability": skill_id, "summary": summary, "entrypoint": "run", "inputs": inputs, "outputs": outputs,
                  "tools": tools, "checks": ["contract_outputs"]},
        fixtures=[(name, values, {}, None if expected is None else {"output": expected}) for name, values, expected in fixtures],
    )


STARTER_SKILLS = [
    text_skill("extract_emails", "Extract email addresses from text, in order, without duplicates.",
               [{"name": "text", "type": "text", "description": "Text that may contain email addresses."}],
               [{"name": "emails", "type": "list"}, {"name": "count", "type": "integer"}], ["regex_findall"], [
                   ("two", {"text": "write a@b.co or c.d@e.org"}, {"emails": ["a@b.co", "c.d@e.org"], "count": 2}),
                   ("duplicates", {"text": "x@y.io, X@y.io and x@y.io"}, {"emails": ["x@y.io"], "count": 1}),
                   ("none", {"text": "no emails here"}, {"emails": [], "count": 0}),
               ]),
    text_skill("word_stats", "Count words, characters and sentences in a text.",
               [{"name": "text", "type": "text"}],
               [{"name": "words", "type": "integer"}, {"name": "characters", "type": "integer"},
                {"name": "characters_no_spaces", "type": "integer"}, {"name": "sentences", "type": "integer"}],
               ["regex_split"], [
                   ("two_sentences", {"text": "Hello world. How are you?"},
                    {"words": 5, "characters": 25, "characters_no_spaces": 21, "sentences": 2}),
                   ("empty", {"text": ""}, {"words": 0, "characters": 0, "characters_no_spaces": 0, "sentences": 0}),
                   ("spaces", {"text": "  a  b  "}, {"words": 2, "characters": 8, "characters_no_spaces": 2, "sentences": 1}),
               ]),
    text_skill("convert_temperature", "Convert a temperature between Celsius, Fahrenheit and Kelvin.",
               [{"name": "value", "type": "number"}, {"name": "from_unit", "type": "text"}, {"name": "to_unit", "type": "text"}],
               [{"name": "value", "type": "number"}, {"name": "unit", "type": "text"}], [], [
                   ("boiling", {"value": 100, "from_unit": "C", "to_unit": "F"}, {"value": 212.0, "unit": "fahrenheit"}),
                   ("body", {"value": 98.6, "from_unit": "fahrenheit", "to_unit": "celsius"}, {"value": 37.0, "unit": "celsius"}),
                   ("kelvin", {"value": 0, "from_unit": "c", "to_unit": "k"}, {"value": 273.15, "unit": "kelvin"}),
                   ("bad_unit", {"value": 1, "from_unit": "x", "to_unit": "c"}, None),
               ]),
    text_skill("slugify", "Turn a title into a URL slug.",
               [{"name": "text", "type": "text"}], [{"name": "slug", "type": "text"}], ["regex_sub"], [
                   ("title", {"text": "Hello, World! 2026"}, {"slug": "hello-world-2026"}),
                   ("trim", {"text": "  --Skill Forge--  "}, {"slug": "skill-forge"}),
                   ("empty", {"text": "!!!"}, {"slug": ""}),
               ]),
    # 1.1.0 documents the case-insensitive default in the contract, so verifiers judge against it.
    text_skill("dedupe_list", "Remove duplicates from a list, keeping first occurrences in order. Text is compared "
               "case-insensitively and ignoring surrounding spaces unless case_sensitive is true.",
               [{"name": "items", "type": "list", "description": "The values to de-duplicate."},
                {"name": "case_sensitive", "type": "boolean", "required": False,
                 "description": "Compare text exactly (default false: 'Apple' and 'apple' are duplicates)."}],
               [{"name": "items", "type": "list"}, {"name": "removed", "type": "integer"}], [], [
                   ("strings", {"items": ["a", "B", "b", "a", "c"]}, {"items": ["a", "B", "c"], "removed": 2}),
                   ("case_sensitive", {"items": ["a", "A"], "case_sensitive": True}, {"items": ["a", "A"], "removed": 0}),
                   ("numbers", {"items": [1, 2, 1, 3]}, {"items": [1, 2, 3], "removed": 1}),
               ], version="1.1.0"),
]

BUILTIN_SKILLS = [REVENUE_BY_PRODUCT, *STARTER_SKILLS]
