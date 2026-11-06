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



def csv_skill(skill_id, summary, columns, outputs, tools, check, fixtures):
    """A Workbench file skill. columns: [(input name, description, required)]. Fixtures: (name, inputs, csv, output)."""
    inputs = [{"name": "data_csv", "type": "csv", "description": "The confirmed file (Excel is converted to CSV)."}]
    inputs += [{"name": name, "type": "column", "description": about, "required": required}
               for name, about, required in columns]
    return BuiltinSkill(
        skill_id=skill_id, version="1.0.0", source_file=f"{skill_id}.py",
        contract={"capability": skill_id, "summary": summary, "entrypoint": "run", "inputs": inputs,
                  "outputs": [{"name": name, "type": kind} for name, kind in outputs], "tools": tools,
                  "checks": ["contract_outputs", check]},
        fixtures=[(name, values, {"data_csv": content}, None if expected is None else {"output": expected})
                  for name, values, content, expected in fixtures],
    )


GROUP = {"group_column": "Region", "amount_column": "Amount"}
MONTH = {"date_column": "Date", "amount_column": "Amount"}

FILE_SKILLS = [
    csv_skill("totals_by_group", "Sum an amount per value of a chosen column (region, category, store...).",
              [("group_column", "Header whose values become the result rows.", True),
               ("amount_column", "Header holding the number to add up.", True)],
              [("operation", "text"), ("rows_processed", "integer"), ("group_column", "text"), ("groups", "list"),
               ("total", "decimal_string")],
              ["read_csv", "column", "to_decimal", "group_sum", "decimal_sum", "format_decimal"], "group_reference_totals", [
                  ("two_regions", GROUP, b"Region,Amount\nNorth,10\nSouth,5.5\nNorth,2\n",
                   {"groups": [{"group": "North", "total": "12", "row_count": 2},
                               {"group": "South", "total": "5.5", "row_count": 1}], "total": "17.5"}),
                  ("negative", GROUP, b"Region,Amount\nEast,-3\nEast,1\n",
                   {"groups": [{"group": "East", "total": "-2", "row_count": 2}], "total": "-2"}),
                  ("reject_invalid_amount", GROUP, b"Region,Amount\nWest,lots\n", None),
              ]),
    csv_skill("totals_by_month", "Sum an amount per calendar month (YYYY-MM) from a date column.",
              [("date_column", "Header holding each row's date.", True),
               ("amount_column", "Header holding the number to add up.", True)],
              [("operation", "text"), ("rows_processed", "integer"), ("periods", "list"), ("total", "decimal_string")],
              ["read_csv", "column", "iso_dates", "to_decimal", "group_sum", "decimal_sum", "format_decimal"],
              "monthly_reference_totals", [
                  ("two_months", MONTH, b"Date,Amount\n2026-01-05,10\n2026-01-31,5\n2026-02-01,1.25\n",
                   {"periods": [{"period": "2026-01", "total": "15", "row_count": 2},
                                {"period": "2026-02", "total": "1.25", "row_count": 1}], "total": "16.25"}),
                  ("leap_day", MONTH, b"Date,Amount\n2028-02-29,7\n",
                   {"periods": [{"period": "2028-02", "total": "7", "row_count": 1}], "total": "7"}),
                  ("reject_invalid_date", MONTH, b"Date,Amount\nsoon,1\n", None),
              ]),
    csv_skill("dedupe_rows", "Remove repeated rows, keeping the first. Whole rows are compared after trimming cells; "
              "with key_column, rows sharing that key (ignoring case and spaces) are duplicates.",
              [("key_column", "Optional header to compare by, such as an id or email.", False)],
              [("operation", "text"), ("rows_processed", "integer"), ("headers", "list"), ("rows", "list"),
               ("kept", "integer"), ("removed", "integer")],
              ["read_csv", "column"], "dedupe_reference", [
                  ("whole_rows", {}, b"Name,City\nAna,Rome\nBen,Oslo\nAna, Rome\n",
                   {"rows": [["Ana", "Rome"], ["Ben", "Oslo"]], "kept": 2, "removed": 1}),
                  ("by_email", {"key_column": "Email"}, b"Email,Name\nA@x.io,Ana\na@x.io ,Ann\n,Bo\n,Cy\n",
                   {"rows": [["A@x.io", "Ana"], ["", "Bo"], ["", "Cy"]], "kept": 3, "removed": 1}),
              ]),
    csv_skill("clean_table", "Tidy a table: trim and collapse spaces, blank out placeholders (N/A, null, -) and drop "
              "rows left empty.", [],
              [("operation", "text"), ("rows_processed", "integer"), ("headers", "list"), ("rows", "list"),
               ("changes", "object")],
              ["read_csv"], "clean_reference", [
                  ("tidy", {}, b" Name , City\n  Ana   Lee ,N/A\n-,null\nBen,Oslo\n",
                   {"headers": ["Name", "City"], "rows": [["Ana Lee", ""], ["Ben", "Oslo"]],
                    "changes": {"headers_tidied": 2, "cells_trimmed": 1, "placeholders_cleared": 3,
                                "blank_rows_removed": 1}}),
              ]),
]

MORE_STARTERS = [
    text_skill("extract_urls", "Extract web links (http and https) from text, in order, without duplicates.",
               [{"name": "text", "type": "text"}], [{"name": "urls", "type": "list"}, {"name": "count", "type": "integer"}],
               ["regex_findall"], [
                   ("two", {"text": "See https://a.io/x, and http://b.org."}, {"urls": ["https://a.io/x", "http://b.org"], "count": 2}),
                   ("duplicates", {"text": "https://a.io https://a.io"}, {"urls": ["https://a.io"], "count": 1}),
                   ("none", {"text": "no links"}, {"urls": [], "count": 0}),
               ]),
    text_skill("change_case", "Rewrite text as upper, lower, title, sentence, snake_case, kebab-case or camelCase.",
               [{"name": "text", "type": "text"},
                {"name": "style", "type": "text", "description": "upper, lower, title, sentence, snake, kebab or camel."}],
               [{"name": "text", "type": "text"}, {"name": "style", "type": "text"}], ["regex_sub", "regex_split"], [
                   ("snake", {"text": "Hello World Again", "style": "snake"}, {"text": "hello_world_again"}),
                   ("camel", {"text": "user first-name", "style": "camel"}, {"text": "userFirstName"}),
                   ("title", {"text": "the QUICK fox", "style": "title"}, {"text": "The Quick Fox"}),
                   ("from_camel", {"text": "parseHTTPResponse", "style": "kebab"}, {"text": "parse-http-response"}),
                   ("bad_style", {"text": "x", "style": "zigzag"}, None),
               ]),
    text_skill("number_stats", "Summary statistics for a list of numbers: count, sum, mean, median, min and max.",
               [{"name": "numbers", "type": "list"}],
               [{"name": name, "type": "number"} for name in ("count", "sum", "mean", "median", "min", "max")], [], [
                   ("odd", {"numbers": [3, 1, 2]}, {"count": 3, "sum": 6.0, "mean": 2.0, "median": 2.0, "min": 1.0, "max": 3.0}),
                   ("even", {"numbers": [1, 2, 3, 10]}, {"median": 2.5, "mean": 4.0}),
                   ("empty", {"numbers": []}, None),
               ]),
    text_skill("percent_change", "Change and percent change from an old value to a new value.",
               [{"name": "old", "type": "number"}, {"name": "new", "type": "number"}],
               [{"name": "change", "type": "number"}, {"name": "percent", "type": "number"}, {"name": "direction", "type": "text"}],
               [], [
                   ("up", {"old": 80, "new": 100}, {"change": 20.0, "percent": 25.0, "direction": "up"}),
                   ("down_from_negative", {"old": -50, "new": -75}, {"change": -25.0, "percent": -50.0, "direction": "down"}),
                   ("from_zero", {"old": 0, "new": 5}, None),
               ]),
    text_skill("roman_numerals", "Convert between whole numbers (1 to 3999) and Roman numerals, in either direction.",
               [{"name": "value", "type": "text", "description": "A number like 2026 or a numeral like MMXXVI."}],
               [{"name": "number", "type": "integer"}, {"name": "roman", "type": "text"}], [], [
                   ("to_roman", {"value": "2026"}, {"number": 2026, "roman": "MMXXVI"}),
                   ("from_roman", {"value": "xliv"}, {"number": 44, "roman": "XLIV"}),
                   ("invalid", {"value": "IIII"}, None),
                   ("too_big", {"value": "4000"}, None),
               ]),
    text_skill("word_frequency", "The most frequent words in a text, ignoring case and common stop words.",
               [{"name": "text", "type": "text"},
                {"name": "top", "type": "integer", "required": False, "description": "How many words (default 10)."}],
               [{"name": "words", "type": "list"}, {"name": "unique", "type": "integer"}], ["regex_findall"], [
                   ("basic", {"text": "The cat and the hat. Cat!", "top": 2},
                    {"words": [{"word": "cat", "count": 2}, {"word": "hat", "count": 1}], "unique": 2}),
                   ("empty", {"text": ""}, {"words": [], "unique": 0}),
               ]),
    text_skill("loan_payment", "Fixed monthly payment, total paid and total interest for a loan.",
               [{"name": "principal", "type": "number"}, {"name": "annual_rate_percent", "type": "number"},
                {"name": "years", "type": "number"}],
               [{"name": "monthly_payment", "type": "number"}, {"name": "months", "type": "integer"},
                {"name": "total_paid", "type": "number"}, {"name": "total_interest", "type": "number"}], [], [
                   ("mortgage", {"principal": 200000, "annual_rate_percent": 6, "years": 30},
                    {"monthly_payment": 1199.1, "months": 360, "total_paid": 431676.38}),
                   ("zero_rate", {"principal": 1200, "annual_rate_percent": 0, "years": 1},
                    {"monthly_payment": 100.0, "total_interest": 0.0}),
                   ("bad", {"principal": -1, "annual_rate_percent": 5, "years": 1}, None),
               ]),
]

BUILTIN_SKILLS = [REVENUE_BY_PRODUCT, *STARTER_SKILLS, *FILE_SKILLS, *MORE_STARTERS]
