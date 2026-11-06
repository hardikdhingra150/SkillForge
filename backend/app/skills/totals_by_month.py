"""Sum an amount per calendar month (YYYY-MM) from a date column. Skill source: runs in the sandbox."""


def run(inputs, tools):
    headers, rows = tools.read_csv("data_csv")
    dates = tools.iso_dates(tools.column(headers, rows, inputs["date_column"]))
    amounts = [tools.to_decimal(value) for value in tools.column(headers, rows, inputs["amount_column"])]
    groups = tools.group_sum([day[:7] for day in dates], amounts)
    return {
        "operation": "totals_by_month",
        "rows_processed": len(rows),
        "periods": [
            {"period": month, "total": tools.format_decimal(groups[month]["total"]), "row_count": groups[month]["count"]}
            for month in sorted(groups)
        ],
        "total": tools.format_decimal(tools.decimal_sum(amounts)),
    }
