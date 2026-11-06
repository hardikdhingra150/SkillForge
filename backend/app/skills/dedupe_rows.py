"""Drop repeated rows, keeping the first. Skill source: runs in the sandbox.

Whole rows are compared after trimming each cell. With a key column, rows with the same key (ignoring case and
surrounding spaces) are duplicates; rows with an empty key are always kept.
"""


def run(inputs, tools):
    headers, rows = tools.read_csv("data_csv")
    key_column = inputs.get("key_column") or None
    keys = tools.column(headers, rows, key_column) if key_column else None
    seen, kept, removed = set(), [], []
    for index, row in enumerate(rows):
        if keys is None:
            key = tuple(cell.strip() for cell in row)
        else:
            key = keys[index].strip().casefold()
            if not key:
                kept.append(row)
                continue
        if key in seen:
            removed.append(index + 1)
        else:
            seen.add(key)
            kept.append(row)
    return {
        "operation": "dedupe_rows",
        "rows_processed": len(rows),
        "key_column": key_column,
        "headers": headers,
        "rows": kept,
        "kept": len(kept),
        "removed": len(removed),
        "removed_rows": removed[:1000],
    }
