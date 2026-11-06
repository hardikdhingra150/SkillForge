"""Delete visitor workspaces nobody has used for a while (AUTH_MODE=browser).

A browser workspace is idle when its browser hasn't been seen, and it has had no new task or chat, for
WORKSPACE_RETENTION_DAYS. Everything in it goes: runs and their history, uploaded files, chats, the audit trail
and its private skills. The owner's workspace is never touched. The worker runs this about once an hour.
"""

from datetime import timedelta

from sqlalchemy import delete, func, select

from app.database.audit_models import AuditEvent
from app.database.browser_models import BrowserKey
from app.database.chat_models import Conversation
from app.database.models import Execution, ExecutionEvent, Task, Workspace
from app.database.skill_models import SkillVersion
from app.security import LOCAL_WORKSPACE_ID

BATCH = 50


def idle_workspaces(db, days: int, limit: int = BATCH) -> list:
    cutoff = func.now() - timedelta(days=days)
    recent_task = select(Task.id).where(Task.workspace_id == BrowserKey.workspace_id, Task.created_at >= cutoff)
    recent_chat = select(Conversation.id).where(Conversation.workspace_id == BrowserKey.workspace_id,
                                                Conversation.updated_at >= cutoff)
    return list(db.scalars(
        select(BrowserKey.workspace_id).where(
            BrowserKey.workspace_id != LOCAL_WORKSPACE_ID,
            func.coalesce(BrowserKey.last_seen_at, BrowserKey.created_at) < cutoff,
            ~recent_task.exists(), ~recent_chat.exists(),
        ).limit(limit)
    ))


def delete_workspaces(db, workspace_ids: list) -> int:
    """Delete these workspaces and everything in them, children first."""
    if not workspace_ids:
        return 0
    tasks = select(Task.id).where(Task.workspace_id.in_(workspace_ids))
    executions = select(Execution.id).where(Execution.task_id.in_(tasks))
    db.execute(delete(ExecutionEvent).where(ExecutionEvent.execution_id.in_(executions)))
    db.execute(delete(Execution).where(Execution.task_id.in_(tasks)))  # uploaded files cascade
    db.execute(delete(Task).where(Task.workspace_id.in_(workspace_ids)))
    db.execute(delete(Conversation).where(Conversation.workspace_id.in_(workspace_ids)))  # messages, files cascade
    db.execute(delete(AuditEvent).where(AuditEvent.workspace_id.in_(workspace_ids)))
    db.execute(delete(SkillVersion).where(SkillVersion.workspace_id.in_(workspace_ids)))
    return db.execute(delete(Workspace).where(Workspace.id.in_(workspace_ids))).rowcount  # browser keys cascade


def clean_up(session_factory, days: int) -> int:
    """Delete idle workspaces in small batches, each in its own transaction. Returns how many went."""
    total = 0
    while True:
        with session_factory.begin() as db:
            removed = delete_workspaces(db, idle_workspaces(db, days))
        total += removed
        if removed < BATCH:
            return total
