"""Convert between whole numbers (1-3999) and Roman numerals, in either direction. Runs in the sandbox."""


def table():
    return [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
            (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def to_roman(number):
    if not 1 <= number <= 3999:
        raise ValueError("Roman numerals cover 1 to 3999.")
    result = ""
    for value, letters in table():
        while number >= value:
            result += letters
            number -= value
    return result


def run(inputs, tools):
    value = str(inputs["value"]).strip()
    if value.isdigit():
        number = int(value)
        return {"number": number, "roman": to_roman(number)}
    text, number, index = value.upper(), 0, 0
    for amount, letters in table():
        while text[index:index + len(letters)] == letters:
            number += amount
            index += len(letters)
    if not text or index != len(text) or to_roman(number) != text:
        raise ValueError(f"{value!r} is not a valid Roman numeral.")
    return {"number": number, "roman": text}
