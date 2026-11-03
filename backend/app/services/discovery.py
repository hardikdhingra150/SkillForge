"""Capability discovery: map a planned capability to an existing skill before creating a new one.

"pull_emails", "get_email_addresses" and "extract_emails" are the same operation.
Matching runs in two tiers:
  1. deterministic: normalized name tokens (synonyms, plurals, filler words) plus input-name overlap;
  2. for close calls, a model confirms "same operation?" and maps the inputs.
Only when neither finds a match does SkillSmith create a new skill.
"""

import json
from dataclasses import dataclass, field

from app.llm import LLMError, complete_json

AUTO_MATCH = 0.75   # deterministic score that reuses without asking a model
ASK_MODEL = 0.2     # scores in between are confirmed by a model
MAX_CANDIDATES = 3

SYNONYMS = {
    "pull": "extract", "get": "extract", "find": "extract", "grab": "extract", "fetch": "extract", "collect": "extract",
    "parse": "extract", "scrape": "extract", "detect": "extract",
    "sum": "total", "add": "total", "totals": "total", "aggregate": "total", "summed": "total",
    "tally": "count", "number": "count", "how_many": "count", "counts": "count",
    "deduplicate": "dedupe", "unique": "dedupe", "distinct": "dedupe", "deduplication": "dedupe",
    "transform": "convert", "change": "convert", "translate": "convert",
    "mail": "email", "address": "email", "e_mail": "email",
    "sale": "revenue", "income": "revenue", "item": "product", "products": "product", "items": "product",
    "temp": "temperature", "celsius": "temperature", "fahrenheit": "temperature", "kelvin": "temperature",
    "duplicate": "dedupe", "slug": "slugify", "url": "slugify",
    "stats": "stat", "statistic": "stat", "statistics": "stat",
}
PHRASES = {"remove_duplicate": "dedupe", "drop_duplicate": "dedupe", "how_many": "count", "e_mail": "email",
           "word_count": "count_word", "number_of": "count"}
FILLER = {"by", "of", "the", "a", "an", "from", "in", "per", "each", "list", "all", "to", "into", "and", "for", "with", "text"}

CONFIRM_SYSTEM = """You decide whether a requested operation is the SAME operation as an existing reusable skill.
Same means the existing skill, given the right inputs, returns what the request needs; differences in wording do not
matter, differences in behaviour do (e.g. "count words" is not "count sentences"; "sum" is not "average").
Reply with ONLY a JSON object:
{"same": true | false, "input_mapping": {"<requested input name>": "<existing skill input name>"}, "reason": "short"}"""


def _stem(token: str) -> str:
    if len(token) <= 3:
        return token
    if token.endswith("ies"):
        return token[:-3] + "y"
    if token.endswith("sses"):
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokens(name: str) -> frozenset[str]:
    text = "_".join(_stem(part) for part in name.lower().replace("-", "_").replace(" ", "_").split("_") if part)
    for phrase, replacement in PHRASES.items():
        text = text.replace(phrase, replacement)
    out = set()
    for raw in text.split("_"):
        if not raw:
            continue
        word = SYNONYMS.get(raw, raw)
        word = SYNONYMS.get(_stem(word), _stem(word))
        if word not in FILLER:
            out.add(word)
    return frozenset(out)


def score(planned: str, planned_inputs, existing: str, existing_inputs) -> float:
    """0..1 similarity: name-token Jaccard, nudged up by shared input names."""
    a, b = tokens(planned), tokens(existing)
    if not a or not b:
        return 0.0
    name = len(a & b) / len(a | b)
    pi, ei = {tokens(n) for n in planned_inputs}, {tokens(n) for n in existing_inputs}
    inputs = len(pi & ei) / len(pi | ei) if pi and ei else 0.0
    return round(min(1.0, name * 0.85 + inputs * 0.25), 3)


@dataclass
class Match:
    capability: str
    inputs: dict
    how: str                      # "exact", "names", "model", or "new"
    reason: str = ""
    candidates: list = field(default_factory=list)


def remap_inputs(inputs: dict, contract_inputs: list[str], mapping: dict | None = None) -> dict:
    """Rename planned inputs to the skill's input names (explicit mapping, same name, or the only one)."""
    mapping = dict(mapping or {})
    remaining = [name for name in contract_inputs if name not in inputs and name not in mapping.values()]
    if len(inputs) == 1 and len(contract_inputs) == 1 and not mapping:
        mapping = {next(iter(inputs)): contract_inputs[0]}
    out = {}
    for name, value in inputs.items():
        target = mapping.get(name) or (name if name in contract_inputs else None)
        if target is None and len(remaining) == 1:
            target = remaining.pop()
        out[target or name] = value
    return out


def discover(capability: str, inputs: dict, skills: dict, *, provider=None, model=None, request="") -> Match:
    """skills: {capability: {"summary": str, "inputs": [names]}} for validated, runnable skills."""
    if capability in skills:
        return Match(capability, inputs, "exact")
    ranked = sorted(((score(capability, inputs, cap, info["inputs"]), cap) for cap, info in skills.items()), reverse=True)
    ranked = [(s, cap) for s, cap in ranked if s >= ASK_MODEL][:MAX_CANDIDATES]
    if not ranked:
        return Match(capability, inputs, "new")
    best_score, best = ranked[0]
    if best_score >= AUTO_MATCH:
        return Match(best, remap_inputs(inputs, skills[best]["inputs"]), "names",
                     f"{capability} and {best} name the same operation (similarity {best_score}).", ranked)
    if provider is None:
        return Match(capability, inputs, "new", candidates=ranked)
    for _, cap in ranked:
        info = skills[cap]
        prompt = (f"User request: {request}\nRequested operation: {capability} with inputs {json.dumps(inputs)}\n"
                  f"Existing skill: {cap}: {info['summary']} (inputs: {', '.join(info['inputs'])})")
        try:
            verdict = complete_json(provider, prompt, system=CONFIRM_SYSTEM, model=model, timeout=90)
        except (LLMError, ValueError):
            continue
        if verdict.get("same") is True:
            mapping = verdict.get("input_mapping") if isinstance(verdict.get("input_mapping"), dict) else {}
            mapping = {k: v for k, v in mapping.items() if v in info["inputs"]}
            return Match(cap, remap_inputs(inputs, info["inputs"], mapping), "model",
                         str(verdict.get("reason") or f"{capability} is the same operation as {cap}."), ranked)
    return Match(capability, inputs, "new", candidates=ranked)
