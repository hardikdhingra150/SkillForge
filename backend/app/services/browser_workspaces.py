"""Private workspaces without sign-in (AUTH_MODE=browser).

On its first visit a browser asks for a workspace and gets a random key (sfb_...) that it keeps in local storage
and sends as its bearer token. Only the key's SHA-256 is stored, so a database leak gives no usable keys.
Clearing the browser's data, or another device, starts a new empty workspace.
"""

import hashlib
import secrets
from uuid import UUID

from app.database.browser_models import BrowserKey
from app.database.models import Workspace

PREFIX = "sfb_"


def key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def create(db) -> str:
    workspace = Workspace(name="Browser workspace")
    db.add(workspace)
    db.flush()
    key = PREFIX + secrets.token_urlsafe(32)
    db.add(BrowserKey(key_hash=key_hash(key), workspace_id=workspace.id))
    db.flush()
    return key


def workspace_for(db, key: str) -> UUID | None:
    found = db.get(BrowserKey, key_hash(key))
    return found.workspace_id if found else None
