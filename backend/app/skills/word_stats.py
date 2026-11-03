"""Count words, characters and sentences in a text. Skill source: runs in the sandbox."""


def run(inputs, tools):
    text = inputs["text"]
    words = text.split()
    sentences = [part for part in tools.regex_split(r"[.!?]+", text) if part.strip()]
    return {"words": len(words), "characters": len(text), "characters_no_spaces": len("".join(text.split())),
            "sentences": len(sentences)}
