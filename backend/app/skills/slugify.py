"""Turn a title into a URL slug. Skill source: runs in the sandbox."""


def run(inputs, tools):
    lowered = str(inputs["text"]).lower()
    slug = tools.regex_sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return {"slug": slug}
