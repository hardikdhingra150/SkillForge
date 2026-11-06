"""The most frequent words in a text, ignoring case and common stop words. Skill source: runs in the sandbox."""


def run(inputs, tools):
    stop = ["the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "was", "were", "it", "this",
            "that", "with", "as", "at", "by", "be", "i", "you", "we", "they"]
    limit = int(inputs.get("top") or 10)
    counts = {}
    for word in tools.regex_findall(r"[a-z0-9']+", inputs["text"].lower()):
        word = word.strip("'")
        if word and word not in stop:
            counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:max(1, limit)]
    return {"words": [{"word": word, "count": count} for word, count in ranked], "unique": len(counts)}
