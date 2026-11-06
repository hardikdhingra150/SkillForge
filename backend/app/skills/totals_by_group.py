"""Sum an amount per value of a chosen column (region, category, store...). Skill source: runs in the sandbox."""


def run(inputs, tools):
    headers, rows = tools.read_csv("data_csv")
    keys = tools.column(headers, rows, inputs["group_column"])
    amounts = [tools.to_decimal(value) for value in tools.column(headers, rows, inputs["amount_column"])]
    groups = tools.group_sum(keys, amounts)
    return {
        "operation": "totals_by_group",
        "rows_processed": len(rows),
        "group_column": inputs["group_column"],
        "groups": [
            {"group": name, "total": tools.format_decimal(groups[name]["total"]), "row_count": groups[name]["count"]}
            for name in sorted(groups)
        ],
        "total": tools.format_decimal(tools.decimal_sum(amounts)),
    }
