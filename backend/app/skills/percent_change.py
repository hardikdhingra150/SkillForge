"""Change and percent change from an old value to a new one. Skill source: runs in the sandbox."""


def run(inputs, tools):
    old, new = float(inputs["old"]), float(inputs["new"])
    if old == 0:
        raise ValueError("Percent change from 0 is undefined.")
    change = new - old
    percent = round(100 * change / abs(old), 4)
    direction = "up" if change > 0 else "down" if change < 0 else "unchanged"
    return {"change": round(change, 10), "percent": percent, "direction": direction}
