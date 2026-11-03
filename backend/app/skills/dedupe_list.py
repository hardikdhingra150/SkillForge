"""Remove duplicates from a list, keeping first occurrences in order. Skill source: runs in the sandbox."""


def run(inputs, tools):
    seen, unique = [], []
    for item in inputs["items"]:
        key = item.strip().lower() if isinstance(item, str) and not inputs.get("case_sensitive", False) else item
        if key not in seen:
            seen.append(key)
            unique.append(item)
    return {"items": unique, "removed": len(inputs["items"]) - len(unique)}
