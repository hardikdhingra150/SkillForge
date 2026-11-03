"""Convert a temperature between Celsius, Fahrenheit and Kelvin. Skill source: runs in the sandbox."""

def run(inputs, tools):
    units = {"c": "celsius", "celsius": "celsius", "f": "fahrenheit", "fahrenheit": "fahrenheit", "k": "kelvin", "kelvin": "kelvin"}
    source = units.get(str(inputs["from_unit"]).strip().lower())
    target = units.get(str(inputs["to_unit"]).strip().lower())
    if source is None or target is None:
        raise ValueError("Units must be celsius, fahrenheit or kelvin.")
    value = float(inputs["value"])
    celsius = value if source == "celsius" else (value - 32) * 5 / 9 if source == "fahrenheit" else value - 273.15
    result = celsius if target == "celsius" else celsius * 9 / 5 + 32 if target == "fahrenheit" else celsius + 273.15
    return {"value": round(result, 4), "unit": target}
