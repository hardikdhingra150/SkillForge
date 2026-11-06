"""Rewrite text as upper, lower, title, sentence, snake_case, kebab-case or camelCase. Runs in the sandbox."""


def words_of(text, tools):
    spaced = tools.regex_sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", tools.regex_sub(r"([a-z0-9])([A-Z])", r"\1 \2", text))
    return [word for word in tools.regex_split(r"[^A-Za-z0-9]+", spaced) if word]


def run(inputs, tools):
    text, style = inputs["text"], inputs["style"].strip().lower().replace("-", "_").replace(" ", "_")
    if style == "upper":
        result = text.upper()
    elif style == "lower":
        result = text.lower()
    elif style == "title":
        result = " ".join(word[:1].upper() + word[1:].lower() for word in text.split())
    elif style == "sentence":
        lowered = " ".join(text.split()).lower()
        result = lowered[:1].upper() + lowered[1:]
    elif style in ("snake", "snake_case"):
        result = "_".join(word.lower() for word in words_of(text, tools))
    elif style in ("kebab", "kebab_case"):
        result = "-".join(word.lower() for word in words_of(text, tools))
    elif style in ("camel", "camel_case", "camelcase"):
        words = [word.lower() for word in words_of(text, tools)]
        result = "".join(words[:1] + [word[:1].upper() + word[1:] for word in words[1:]])
    else:
        raise ValueError("style must be upper, lower, title, sentence, snake, kebab or camel.")
    return {"text": result, "style": style}
