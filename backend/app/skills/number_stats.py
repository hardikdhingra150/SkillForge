"""Summary statistics for a list of numbers: count, sum, mean, median, min, max. Runs in the sandbox."""


def run(inputs, tools):
    values = [float(value) for value in inputs["numbers"]]
    if not values:
        raise ValueError("Give at least one number.")
    ordered = sorted(values)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    total = sum(values)
    return {"count": len(values), "sum": round(total, 10), "mean": round(total / len(values), 10),
            "median": round(median, 10), "min": ordered[0], "max": ordered[-1]}
