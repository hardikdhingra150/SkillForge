"""Total revenue per product from a sales CSV.

This file is skill *source*: it is stored in the registry and runs inside the
sandbox, never imported by the app. It may only use the tools in its contract.
"""


def run(inputs, tools):
    headers, rows = tools.read_csv("sales_csv")
    products = tools.column(headers, rows, inputs["product_column"])
    amounts = [tools.to_decimal(value) for value in tools.column(headers, rows, inputs["revenue_column"])]
    groups = tools.group_sum(products, amounts)
    return {
        "operation": "revenue_by_product",
        "rows_processed": len(rows),
        "products": [
            {"product": name, "revenue": tools.format_decimal(groups[name]["total"]), "row_count": groups[name]["count"]}
            for name in sorted(groups)
        ],
        "total_revenue": tools.format_decimal(tools.decimal_sum(amounts)),
    }
