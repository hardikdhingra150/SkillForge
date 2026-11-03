"""In-process change notifications for live chat streams (SSE).

The agent runs inside the API process, so it can wake waiting streams the
moment it records a step. Streams also re-check on a timeout, so a change made
by another process is still picked up, just not instantly.
"""

import threading
from collections import defaultdict

_lock = threading.Condition()
_versions: dict[str, int] = defaultdict(int)


def bump(conversation_id) -> None:
    with _lock:
        _versions[str(conversation_id)] += 1
        _lock.notify_all()


def version(conversation_id) -> int:
    with _lock:
        return _versions[str(conversation_id)]


def wait_for_change(conversation_id, seen: int, timeout: float) -> int:
    """Block until the conversation's version moves past `seen` or the timeout passes."""
    key = str(conversation_id)
    with _lock:
        _lock.wait_for(lambda: _versions[key] != seen, timeout=timeout)
        return _versions[key]
