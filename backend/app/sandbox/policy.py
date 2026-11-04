"""Static checks for skill source before it is allowed to run.

Stdlib only: the sandbox child process imports this module directly.
"""

import ast

if __package__:
    from .tools import TOOL_NAMES
else:
    from tools import TOOL_NAMES

MAX_SOURCE_BYTES = 50_000
ENTRYPOINT = "run"

# Builtins a skill may call. Everything else (open, __import__, eval, getattr...) is absent.
SAFE_BUILTIN_NAMES = (
    "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float", "int",
    "isinstance", "len", "list", "map", "max", "min", "range", "reversed",
    "round", "set", "sorted", "str", "sum", "tuple", "zip",
    "Exception", "KeyError", "TypeError", "ValueError",
)

BANNED_NAMES = frozenset({
    "__import__", "breakpoint", "compile", "delattr", "dir", "eval", "exec",
    "getattr", "globals", "hasattr", "help", "input", "locals", "memoryview",
    "object", "open", "print", "setattr", "super", "type", "vars",
})

BANNED_NODES = (
    ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.ClassDef,
    ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith,
    ast.Yield, ast.YieldFrom, ast.MatchClass,
)

SAFE_ATTRIBUTES = frozenset(TOOL_NAMES) | {
    "add", "append", "capitalize", "casefold", "clear", "copy", "count",
    "difference", "discard", "endswith", "extend", "find", "get", "index",
    "insert", "intersection", "isalnum", "isalpha", "isdigit", "isfinite",
    "islower", "isspace", "isupper", "items", "join", "keys", "lower",
    "lstrip", "partition", "pop", "remove", "replace", "reverse", "rfind",
    "rpartition", "rsplit", "rstrip", "setdefault", "sort", "split",
    "splitlines", "startswith", "strip", "swapcase", "title", "union",
    "update", "upper", "values",
}


class PolicyViolation(ValueError):
    """Skill source uses something outside the sandbox policy."""


def check_source(source: str) -> ast.Module:
    if not isinstance(source, str) or not source.strip():
        raise PolicyViolation("Skill source is empty.")
    if len(source.encode()) > MAX_SOURCE_BYTES:
        raise PolicyViolation("Skill source exceeds 50 KB.")
    try:
        tree = ast.parse(source, filename="<skill>")
    except SyntaxError as error:
        raise PolicyViolation(f"Skill source has a syntax error on line {error.lineno}.") from None

    for node in ast.walk(tree):
        line = getattr(node, "lineno", "?")
        if isinstance(node, BANNED_NODES):
            raise PolicyViolation(f"{type(node).__name__} is not allowed in skills (line {line}).")
        if isinstance(node, ast.Name) and (node.id in BANNED_NAMES or node.id.startswith("__")):
            raise PolicyViolation(f"The name {node.id!r} is not allowed in skills (line {line}).")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise PolicyViolation(f"Private attribute {node.attr!r} is not allowed in skills (line {line}).")
        if isinstance(node, ast.Attribute) and node.attr not in SAFE_ATTRIBUTES:
            raise PolicyViolation(f"Attribute {node.attr!r} is not allowed in skills (line {line}).")

    # Only functions, constants and a docstring at module level: nothing runs on load.
    for node in tree.body:
        is_docstring = isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
        is_constant = isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
        if not (isinstance(node, ast.FunctionDef) or is_docstring or is_constant):
            raise PolicyViolation(f"Only function definitions and constants are allowed at module level (line {node.lineno}).")

    entry = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == ENTRYPOINT), None)
    if entry is None:
        raise PolicyViolation("Skill source must define run(inputs, tools).")
    if [a.arg for a in entry.args.args] != ["inputs", "tools"] or entry.args.vararg or entry.args.kwarg:
        raise PolicyViolation("run must take exactly (inputs, tools).")
    return tree
