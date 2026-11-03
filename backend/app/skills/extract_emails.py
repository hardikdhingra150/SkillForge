"""Extract email addresses from text, in order, without duplicates. Skill source: runs in the sandbox."""


def run(inputs, tools):
    found = tools.regex_findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}", inputs["text"])
    emails = []
    for email in found:
        if email.lower() not in [e.lower() for e in emails]:
            emails.append(email)
    return {"emails": emails, "count": len(emails)}
