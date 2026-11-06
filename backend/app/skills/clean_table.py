"""Tidy a table: trim and collapse spaces, blank out placeholders, drop rows left empty. Runs in the sandbox."""


def tidy(text):
    return " ".join(text.split())


def run(inputs, tools):
    headers, rows = tools.read_csv("data_csv")
    placeholders = ["n/a", "na", "null", "none", "nil", "nan", "-", "--", "?", "#n/a"]
    clean_headers = [tidy(header) for header in headers]
    trimmed = cleared = 0
    cleaned = []
    for row in rows:
        values = []
        for cell in row:
            value = tidy(cell)
            if value.casefold() in placeholders:
                value = ""
                cleared += 1
            elif value != cell:
                trimmed += 1
            values.append(value)
        cleaned.append(values)
    kept = [row for row in cleaned if any(row)]
    return {
        "operation": "clean_table",
        "rows_processed": len(rows),
        "headers": clean_headers,
        "rows": kept,
        "changes": {
            "headers_tidied": sum(1 for old, new in zip(headers, clean_headers, strict=False) if old != new),
            "cells_trimmed": trimmed,
            "placeholders_cleared": cleared,
            "blank_rows_removed": len(cleaned) - len(kept),
        },
    }
