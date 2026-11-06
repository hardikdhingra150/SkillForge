"""Extract web links (http/https) from text, in order, without duplicates. Skill source: runs in the sandbox."""


def run(inputs, tools):
    found = tools.regex_findall(r"https?://[^\s<>\"')\]]+", inputs["text"])
    urls, seen = [], set()
    for url in found:
        url = url.rstrip(".,;:!?")
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return {"urls": urls, "count": len(urls)}
