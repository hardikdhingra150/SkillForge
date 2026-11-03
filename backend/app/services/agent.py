"""The chat agent: plan a turn, reuse or create a skill, prove it, and reply.

    user message
      -> plan (LLM): plain answer, or a reusable skill + extracted inputs
      -> answer: the model replies directly
      -> skill: latest validated version for the capability?
           yes -> run in the sandbox + contract checks
                  failed -> SkillSmith patch (LLM), proven, promoted as a repaired version
           no  -> SkillSmith create (LLM): contract + source + worked examples,
                  proven in the sandbox (examples + this input), registered as v1.0.0
      -> reply with the skill's output

Whatever the model writes is untrusted: it only becomes a skill after the
sandbox policy, the contract schema and every worked example pass.
"""

import json
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.database.chat_models import ChatMessage, Conversation
from app.database.session import SessionLocal
from app.database.skill_models import SkillVersion
from app.llm import PROVIDERS, LLMError, complete_json, get_provider
from app.sandbox import PolicyViolation, check_source, run_skill
from app.sandbox.tools import TOOL_DOCS, TOOL_NAMES
from app.schemas.skill_contract import SkillContract
from app.services.checks import CheckFailed, run_checks
from app.services.repair import encode_fixture, lineage_fixtures, promote
from app.services.skill_registry import (
    ExampleMismatch,
    implementation_hash,
    latest_validated,
    run_fixture_tests,
    verify,
    version_key,
)

MAX_HISTORY = 10
# Strongest first: used to pick an independent verifier and an escalation target.
STRENGTH_ORDER = ["codex", "claude", "ollama"]
SMITH_ATTEMPTS = 3
CHAT_TOOLS = [name for name in TOOL_NAMES if name not in ("read_csv", "column")]  # chat skills take values, not files

PLANNER_SYSTEM = """You are the planner inside SkillForge, a workspace where AI agents build reusable skills.
Decide how to handle the user's latest message.

Use "skill" ONLY when the message contains concrete input values AND asks to compute or transform them
(counting, converting units, extracting patterns, reformatting, sorting, statistics, parsing, validating),
so the same small pure-Python function could be reused later on different values.
Everything else is "answer": greetings, explanations, opinions, creative writing, advice, questions about
SkillForge, and ANY request to write, show, fix or explain code ("give me code to...", "write a function...").

For "skill":
- capability: snake_case name of the GENERAL operation, never the specific values
  (e.g. "count_words", "celsius_to_fahrenheit", "extract_emails").
- If an existing skill below does the same operation, reuse its capability and its input names exactly.
- inputs: the values taken from the message, keyed by short snake_case names.
- input_types: for each input one of text, integer, number, boolean, list, object.

Reply with ONLY a JSON object:
{"mode": "skill" | "answer", "capability": str, "summary": str, "inputs": {...}, "input_types": {...}}
For "answer" only "mode" is required."""

SMITH_SYSTEM = """You are SkillSmith, the engineer inside SkillForge. You write small, safe, reusable skills.

A skill is Python source defining exactly one entry point:
    def run(inputs, tools):
        ...
        return {...}   # a JSON-serializable dict

Hard rules (violations are rejected automatically):
- No imports, no classes, no file or network access, no print, no eval/exec/open/getattr/type.
- No names starting with "_" and no attribute names starting with "_".
- Module level may contain only function definitions and constants.
- Allowed builtins: abs all any bool dict enumerate filter float int isinstance len list map max min
  range reversed round set sorted str sum tuple zip, plus Exception, KeyError, TypeError, ValueError.
- String/list/dict methods are fine (e.g. text.split(), text.lower()).
- Extra helpers are available only through `tools` and must be listed in the contract:
{tool_docs}
- Make the skill GENERAL for the capability, not hard-coded to the example values.

Reply with ONLY a JSON object:
{
  "summary": "one line: what the skill does",
  "inputs":  [{"name": "...", "type": "text|integer|number|boolean|list|object", "description": "..."}],
  "outputs": [{"name": "...", "type": "text|integer|number|boolean|list|object|decimal_string", "description": "..."}],
  "tools":   ["tool names you use, or empty"],
  "source":  "def run(inputs, tools):\\n    ...",
  "examples": [{"name": "snake_case", "inputs": {...}, "output": {...exact expected output...}}]
}
Give at least 3 examples with exact expected outputs, including one edge case."""


VERIFIER_SYSTEM = """You are the independent verifier inside SkillForge. A skill (a small program) produced an
output for a user's request. Check whether the output is CORRECT for the request: recompute the answer yourself
from the values in the request and compare. Ignore formatting differences (6.5 vs 6.50, key order, int vs float
when equal). Reply with ONLY a JSON object: {"correct": true | false, "expected": <your answer>, "reason": "short"}"""


class SmithExhausted(ValueError):
    """SkillSmith could not produce a skill that passes its proof."""


# ---------- step log (each step is its own short transaction so the UI can poll progress) ----------

def add_step(message_id, kind, text, payload=None):
    with SessionLocal.begin() as db:
        message = db.get(ChatMessage, message_id)
        message.steps_json = [*message.steps_json, {
            "kind": kind, "text": text, "payload": payload or {}, "at": datetime.now(UTC).isoformat(),
        }]
        message.updated_at = func.now()


def finish(message_id, *, content, status="done", skill=None):
    with SessionLocal.begin() as db:
        message = db.get(ChatMessage, message_id)
        message.content, message.status, message.skill_json = content, status, skill
        message.updated_at = func.now()
        db.get(Conversation, message.conversation_id).updated_at = func.now()


# ---------- planning ----------

def history_text(db, conversation_id, before_sequence):
    rows = db.scalars(
        select(ChatMessage).where(ChatMessage.conversation_id == conversation_id, ChatMessage.sequence < before_sequence,
                                  ChatMessage.status == "done")
        .order_by(ChatMessage.sequence.desc()).limit(MAX_HISTORY)
    ).all()
    return "\n".join(f"{m.role.upper()}: {m.content[:1500]}" for m in reversed(rows))


def registry_text(db):
    rows = db.scalars(select(SkillVersion).where(SkillVersion.status == "validated", SkillVersion.contract_json.is_not(None))).all()
    seen, lines = set(), []
    for row in rows:
        if row.capability in seen or needs_files(row.contract_json):
            continue
        seen.add(row.capability)
        names = ", ".join(field["name"] for field in row.contract_json.get("inputs", []))
        lines.append(f"- {row.capability}: {row.contract_json.get('summary', '')} (inputs: {names})")
    return "\n".join(lines) or "(none yet)"


def needs_files(contract: dict) -> bool:
    """Skills that read uploaded files run from the Workbench, not from chat."""
    return any(field.get("type") in ("csv", "column") for field in contract.get("inputs", []))


def plan(provider, model, history, registry, text):
    prompt = f"Existing skills:\n{registry}\n\nConversation so far:\n{history or '(new conversation)'}\n\nLatest user message:\n{text}"
    decision = complete_json(provider, prompt, system=PLANNER_SYSTEM, model=model)
    if decision.get("mode") == "skill":
        capability = str(decision.get("capability", "")).strip().lower()
        # A skill computes from values in the message; with nothing to compute from it is just an answer.
        if not capability or not isinstance(decision.get("inputs"), dict) or not decision["inputs"]:
            return {"mode": "answer"}
        decision["capability"] = "".join(ch if ch.isalnum() else "_" for ch in capability).strip("_")[:60] or "skill"
    return decision


# ---------- SkillSmith ----------

def smith_prompt(capability, summary, inputs, input_types, feedback=None, existing=None):
    parts = [f"Capability: {capability}", f"Goal: {summary}",
             f"The user's current inputs (your skill must handle these): {json.dumps(inputs)}",
             f"Input types: {json.dumps(input_types)}"]
    if existing:
        parts.append(f"The current version fails on these inputs. Fix it while keeping the same inputs and outputs.\n"
                     f"Current source:\n{existing}")
    if feedback:
        parts.append(f"Your previous attempt was rejected:\n{feedback}\nFix exactly that and reply with the full JSON again.")
    return "\n\n".join(parts)


def build_candidate(capability, spec):
    contract = {
        "capability": capability, "summary": str(spec.get("summary") or capability)[:300], "entrypoint": "run",
        "inputs": [{"name": f["name"], "type": f.get("type", "text"), "description": str(f.get("description", ""))[:300]}
                   for f in spec.get("inputs", [])],
        "outputs": [{"name": f["name"], "type": f.get("type", "text"), "description": str(f.get("description", ""))[:300]}
                    for f in spec.get("outputs", [])],
        "tools": [t for t in spec.get("tools", []) if t in CHAT_TOOLS],
        "checks": ["contract_outputs"],
    }
    SkillContract.model_validate(contract)
    source = spec.get("source") or ""
    check_source(source)
    examples = [(str(e.get("name") or f"example_{i}"), e.get("inputs") or {}, {}, {"output": e.get("output") or {}})
                for i, e in enumerate(spec.get("examples") or [], start=1)]
    if len(examples) < 3:
        raise ValueError("Give at least 3 examples with exact expected outputs.")
    return source, contract, examples


def verify_output(provider, model, request, capability, inputs, output):
    """Ask the model to recompute the answer independently. Returns (correct, reason)."""
    prompt = (f"User request: {request}\nSkill: {capability}\nInputs it received: {json.dumps(inputs)}\n"
              f"Output it produced: {json.dumps(output)}")
    try:
        verdict = complete_json(provider, prompt, system=VERIFIER_SYSTEM, model=model, timeout=120)
    except ValueError:
        return True, "The verifier gave no usable verdict."
    if verdict.get("correct") is False:
        return False, f"{verdict.get('reason', 'judged incorrect')} (expected {json.dumps(verdict.get('expected'))})"
    return True, str(verdict.get("reason", ""))


def prove(source, contract, examples, inputs, verifier=None):
    """Every worked example must reproduce exactly, the user's input must pass the contract, and the
    independent verifier must agree with the answer."""
    evidence = run_fixture_tests(source, contract, examples)
    parsed = SkillContract.model_validate(contract)
    run = run_skill(source, inputs=inputs, files={}, tools=parsed.tools)
    if not run.ok:
        raise ValueError(f"On the user's inputs the skill raised {run.error.get('type')}: {run.error.get('message')}")
    run_checks(parsed, {}, inputs, run.output)
    if verifier:
        correct, reason = verifier(inputs, run.output)
        if not correct:
            raise ValueError(f"The verifier says the output {json.dumps(run.output)} is wrong: {reason}")
    return evidence, run.output


def prove_with_arbitration(message_id, judge, summary, capability, source, contract, examples, inputs, verifier):
    """Prove the candidate. When an example disagrees with the code, the independent verifier decides who is
    right: if it sides with the code, the example is corrected; otherwise the mismatch is a real failure."""
    corrected = set()
    while True:
        try:
            evidence, output = prove(source, contract, examples, inputs, verifier)
            return evidence, output, examples
        except ExampleMismatch as mismatch:
            if judge is None or mismatch.name in corrected:
                raise
            add_step(message_id, "arbitrating", f"Example {mismatch.name}: the code says {json.dumps(mismatch.output)}, "
                     f"the example says {json.dumps(mismatch.expected)}. Asking the verifier who is right…")
            correct, reason = judge(f"Task: {summary}", capability, mismatch.inputs, mismatch.output)
            if not correct:
                add_step(message_id, "arbitrated", f"The verifier sided with the example: {reason}")
                raise
            corrected.add(mismatch.name)
            examples = [(name, ex_inputs, files, {"output": mismatch.output, "corrected_by_verifier": True})
                        if name == mismatch.name else (name, ex_inputs, files, expected)
                        for name, ex_inputs, files, expected in examples]
            add_step(message_id, "arbitrated", f"The verifier sided with the code. Corrected example {mismatch.name}.")


def smith(message_id, provider, model, capability, summary, inputs, input_types, existing=None, verifier=None, feedback=None,
          judge=None):
    """Ask the model for a skill until it passes the proof, or attempts run out. Returns (source, contract, examples, evidence, output)."""
    for attempt in range(1, SMITH_ATTEMPTS + 1):
        verb = "fixing" if existing else "writing"
        add_step(message_id, "smith_attempt", f"SkillSmith attempt {attempt}: {verb} {capability}.")
        try:
            spec = complete_json(provider, smith_prompt(capability, summary, inputs, input_types, feedback, existing),
                                 system=SMITH_SYSTEM.replace("{tool_docs}", "\n".join(f"  - {TOOL_DOCS[t]}" for t in CHAT_TOOLS)),
                                 model=model, timeout=300)
            source, contract, examples = build_candidate(capability, spec)
            evidence, output, examples = prove_with_arbitration(message_id, judge, summary, capability,
                                                                source, contract, examples, inputs, verifier)
            return source, contract, examples, evidence, output
        except LLMError:
            raise
        except (ValueError, PolicyViolation, CheckFailed, KeyError, TypeError) as error:
            feedback = str(error)[:800]
            add_step(message_id, "smith_rejected", f"Rejected attempt {attempt}: {feedback}")
    raise SmithExhausted(f"SkillSmith could not produce a skill that passes its proof after {SMITH_ATTEMPTS} attempts.")


# ---------- the turn ----------

def bind_chat_inputs(contract, extracted):
    missing = [f.name for f in contract.inputs if f.required and f.name not in extracted]
    if missing:
        raise ValueError(f"I need a value for: {', '.join(missing)}.")
    return {f.name: extracted[f.name] for f in contract.inputs if f.name in extracted}


def run_turn(conversation_id, assistant_id, provider_id, model):
    try:
        with SessionLocal() as db:
            message = db.get(ChatMessage, assistant_id)
            user = db.scalars(select(ChatMessage).where(ChatMessage.conversation_id == conversation_id,
                                                        ChatMessage.sequence == message.sequence - 1)).one()
            history = history_text(db, conversation_id, user.sequence)
            registry = registry_text(db)
        provider = get_provider(provider_id)

        add_step(assistant_id, "planning", f"Planning with {provider.label}…")
        decision = plan(provider, model, history, registry, user.content)
        if decision.get("mode") != "skill":
            add_step(assistant_id, "answering", "This needs a direct answer, not a skill.")
            reply = provider.complete(f"Conversation so far:\n{history or '(new)'}\n\nUSER: {user.content}",
                                      system="You are SkillForge's assistant. Answer clearly and concisely in Markdown.",
                                      model=model)
            finish(assistant_id, content=reply)
            return

        capability, inputs = decision["capability"], decision["inputs"]
        summary, input_types = decision.get("summary") or capability, decision.get("input_types") or {}
        add_step(assistant_id, "planned", f"This is a reusable skill: {capability}.", {"capability": capability, "inputs": inputs})

        with SessionLocal.begin() as db:
            skill = latest_validated(db, capability)
            if skill is not None and needs_files(skill.contract_json):
                capability, skill = f"{capability}_text", latest_validated(db, f"{capability}_text")
            existing = (skill.skill_id, skill.version) if skill else None

        def attempt(author, author_id, author_model):
            if existing:
                return reuse_or_repair(assistant_id, author, author_id, author_model, existing, inputs, input_types,
                                       summary, user.content)
            return create(assistant_id, author, author_id, author_model, capability, summary, inputs, input_types, user.content)

        try:
            outcome = attempt(provider, provider_id, model)
        except SmithExhausted:
            stronger = next((p for p in STRENGTH_ORDER[:STRENGTH_ORDER.index(provider_id)]
                             if PROVIDERS[p].status().available), None)
            if stronger is None:
                raise
            add_step(assistant_id, "escalating", f"{provider.label} could not produce a proven skill. "
                     f"Escalating to {PROVIDERS[stronger].label}.")
            outcome = attempt(PROVIDERS[stronger], stronger, PROVIDERS[stronger].status().default_model)
        finish(assistant_id, content=outcome["text"], skill=outcome["skill"])
    except (LLMError, ValueError) as error:
        add_step(assistant_id, "failed", str(error))
        finish(assistant_id, content=f"I couldn't complete this: {error}", status="failed")
    except Exception as error:  # never leave a message pending
        add_step(assistant_id, "failed", "Unexpected error.", {"type": type(error).__name__})
        finish(assistant_id, content="Something went wrong while handling this message.", status="failed")
        raise


def reply_payload(skill, output, event):
    return {"skill_id": skill.skill_id, "version": skill.version, "capability": skill.capability,
            "origin": skill.origin, "parent_version": skill.parent_version, "event": event, "output": output,
            "contract": skill.contract_json}


def pick_judge(author_id, author_model):
    """Prefer a different model as the verifier, so the author never grades its own work, but never a
    weaker one: the local model does not judge Codex or Claude. Without another strong model the author
    checks itself."""
    rank = STRENGTH_ORDER.index(author_id)
    for candidate in STRENGTH_ORDER:
        if candidate != author_id and STRENGTH_ORDER.index(candidate) <= max(rank, 1) and PROVIDERS[candidate].status().available:
            return PROVIDERS[candidate], PROVIDERS[candidate].status().default_model
    return get_provider(author_id), author_model


def make_judge(author_id, author_model):
    provider, model = pick_judge(author_id, author_model)

    def judge(request, capability, inputs, output):
        return verify_output(provider, model, request, capability, inputs, output)
    judge.label = provider.label
    return judge


def make_verifier(message_id, judge, request, capability):
    def check(inputs, output):
        add_step(message_id, "verifying", f"Independent verifier ({judge.label}) is recomputing the answer…")
        correct, reason = judge(request, capability, inputs, output)
        add_step(message_id, "verified" if correct else "verify_failed",
                 "Verifier agrees with the output." if correct else f"Verifier disagrees: {reason}")
        return correct, reason
    return check


def reuse_or_repair(message_id, provider, provider_id, model, key, extracted, input_types, summary, request):
    with SessionLocal.begin() as db:
        skill = db.get(SkillVersion, key)
        contract = verify(skill)
        source = skill.source_code
    add_step(message_id, "skill_selected", f"Found {skill.skill_id} v{skill.version} in the registry. Running it in the sandbox.")
    inputs = bind_chat_inputs(contract, extracted)
    run = run_skill(source, inputs=inputs, files={}, tools=contract.tools)
    failure = None if run.ok else f"{run.error.get('type')}: {run.error.get('message')}"
    judge = make_judge(provider_id, model)
    verifier = make_verifier(message_id, judge, request, skill.capability)
    if run.ok:
        try:
            run_checks(contract, {}, inputs, run.output)
            correct, reason = verifier(inputs, run.output)
            if not correct:
                failure = f"wrong answer {json.dumps(run.output)}: {reason}"
        except CheckFailed as error:
            failure = str(error)
    if failure is None:
        add_step(message_id, "skill_ran", f"Done in {run.duration_ms:g} ms. Reused v{skill.version}, no new code needed.")
        return {"text": f"Reused **{skill.skill_id} v{skill.version}**.", "skill": reply_payload(skill, run.output, "reused")}

    add_step(message_id, "skill_failed", f"v{skill.version} failed on this input: {failure}")
    new_source, new_contract, examples, evidence, output = smith(
        message_id, provider, model, skill.capability, summary, inputs, input_types, existing=source,
        verifier=verifier, feedback=f"The current version failed: {failure}", judge=judge)
    if [f["name"] for f in new_contract["inputs"]] != [f.name for f in contract.inputs]:
        raise ValueError("The repair changed the skill's inputs, so it cannot replace this version.")
    with SessionLocal.begin() as db:
        parent = db.get(SkillVersion, key)
        regression = lineage_fixtures(db, parent)
        evidence = run_fixture_tests(new_source, new_contract, regression + examples)
        fixtures = examples + [(f"regression_input_{parent.version}", inputs, {}, "checks")]
        new = promote(db, parent, new_source, new_contract, {**evidence, "repaired_from": parent.version}, {
            "strategy": "skillsmith_llm", "summary": f"Rewritten by {provider.label} after: {failure}",
            "failure": {"code": "SKILL_ERROR", "message": failure}, "provider": provider_id, "model": model,
            "fixtures": [encode_fixture(*f) for f in fixtures],
        })
        new_key = (new.skill_id, new.version)
    add_step(message_id, "skill_promoted", f"Saved {new_key[0]} v{new_key[1]} (repaired from v{key[1]}), "
             f"proven by {evidence['test_count']} tests.")
    with SessionLocal() as db:
        new = db.get(SkillVersion, new_key)
        return {"text": f"Repaired **{new.skill_id}** and saved **v{new.version}**.", "skill": reply_payload(new, output, "repaired")}


def create(message_id, provider, provider_id, model, capability, summary, inputs, input_types, request):
    add_step(message_id, "no_skill", f"No skill can do {capability} yet. SkillSmith will create one.")
    judge = make_judge(provider_id, model)
    verifier = make_verifier(message_id, judge, request, capability)
    source, contract, examples, evidence, output = smith(message_id, provider, model, capability, summary, inputs,
                                                         input_types, verifier=verifier, judge=judge)
    skill_id = capability
    with SessionLocal.begin() as db:
        fingerprint = implementation_hash(source, contract)
        taken = db.scalars(select(SkillVersion.version).where(SkillVersion.skill_id == skill_id)).all()
        version = "1.0.0" if not taken else f"{max(version_key(v) for v in taken)[0] + 1}.0.0"
        row = db.get(SkillVersion, (skill_id, version))
        if row is None:
            row = SkillVersion(skill_id=skill_id, version=version, capability=capability, status="validated",
                               implementation_hash=fingerprint, validation_json=evidence, source_code=source,
                               contract_json=contract, origin="generated", change_json={
                                   "created_by": provider_id, "model": model, "request": request[:500],
                                   "fixtures": [encode_fixture(*e) for e in examples],
                               })
            db.add(row)
            db.flush()
        key = (row.skill_id, row.version)
    add_step(message_id, "skill_created", f"Created {key[0]} v{key[1]}: passed {evidence['test_count']} examples in the sandbox. "
             "Saved to the registry for reuse.")
    with SessionLocal() as db:
        row = db.get(SkillVersion, key)
        return {"text": f"Created a new skill, **{row.skill_id} v{row.version}**, and ran it.",
                "skill": reply_payload(row, output, "created")}
