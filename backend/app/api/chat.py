import logging
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.api.tasks import DB, DEV_WORKSPACE_ID, require_development
from app.database.chat_models import ChatMessage, Conversation
from app.database.models import Workspace
from app.llm import PROVIDERS, provider_statuses
from app.services.agent import run_turn

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/api/v1", tags=["Chat"], dependencies=[Depends(require_development)])


class ProviderOut(BaseModel):
    id: str
    label: str
    kind: str
    available: bool
    detail: str
    models: list[str]
    default_model: str | None
    setup: list[dict[str, str]]


class ConversationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = Field(pattern=r"^[a-z]+$")
    model: str | None = Field(default=None, max_length=80)


class MessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=8000)
    provider: str | None = Field(default=None, pattern=r"^[a-z]+$")
    model: str | None = Field(default=None, max_length=80)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sequence: int
    role: str
    content: str
    status: str
    provider: str | None
    model: str | None
    steps: list[dict[str, Any]] = Field(validation_alias="steps_json")
    skill: dict[str, Any] | None = Field(validation_alias="skill_json")
    created_at: datetime
    updated_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    provider: str
    model: str | None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


def unavailable(error):
    logger.error("Chat storage failed: %s", getattr(error, "orig", error))
    return HTTPException(503, "Chat storage is unavailable. Run `make migrate` and retry.")


def check_provider(provider_id):
    if provider_id not in PROVIDERS:
        raise HTTPException(422, f"Unknown provider {provider_id!r}.")
    status = PROVIDERS[provider_id].status()
    if not status.available:
        raise HTTPException(409, f"{status.label} is not ready: {status.detail}")


@router.get("/providers", response_model=list[ProviderOut])
def list_providers(refresh: bool = False):
    return [ProviderOut(**status.payload()) for status in provider_statuses(refresh)]


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: DB, limit: Annotated[int, Query(ge=1, le=100)] = 50):
    try:
        return db.scalars(select(Conversation).where(Conversation.workspace_id == DEV_WORKSPACE_ID)
                          .order_by(Conversation.updated_at.desc()).limit(limit)).all()
    except SQLAlchemyError as error:
        raise unavailable(error) from None


@router.post("/conversations", response_model=ConversationOut, status_code=201)
def create_conversation(body: ConversationIn, db: DB):
    if body.provider not in PROVIDERS:
        raise HTTPException(422, f"Unknown provider {body.provider!r}.")
    try:
        with db.begin():
            db.execute(insert(Workspace).values(id=DEV_WORKSPACE_ID, name="Local development")
                       .on_conflict_do_nothing(index_elements=["id"]))
            conversation = Conversation(workspace_id=DEV_WORKSPACE_ID, title="New chat", provider=body.provider, model=body.model)
            db.add(conversation)
            db.flush()
            db.refresh(conversation)
        return conversation
    except SQLAlchemyError as error:
        raise unavailable(error) from None


def load_conversation(db, conversation_id):
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.workspace_id != DEV_WORKSPACE_ID:
        raise HTTPException(404, "Conversation not found.")
    return conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: UUID, db: DB):
    try:
        conversation = load_conversation(db, conversation_id)
        messages = db.scalars(select(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
                              .order_by(ChatMessage.sequence)).all()
        return ConversationDetail.model_validate({**ConversationOut.model_validate(conversation).model_dump(),
                                                  "messages": [MessageOut.model_validate(m) for m in messages]})
    except SQLAlchemyError as error:
        raise unavailable(error) from None


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: UUID, db: DB):
    try:
        with db.begin():
            db.delete(load_conversation(db, conversation_id))
        return Response(status_code=204)
    except SQLAlchemyError as error:
        raise unavailable(error) from None


@router.post("/conversations/{conversation_id}/messages", response_model=list[MessageOut], status_code=202)
def send_message(conversation_id: UUID, body: MessageIn, db: DB, background: BackgroundTasks):
    try:
        with db.begin():
            conversation = db.scalars(select(Conversation).where(Conversation.id == conversation_id)
                                      .with_for_update()).first()
            if conversation is None or conversation.workspace_id != DEV_WORKSPACE_ID:
                raise HTTPException(404, "Conversation not found.")
            provider_id = body.provider or conversation.provider
            model = body.model if body.provider else (body.model or conversation.model)
            check_provider(provider_id)
            busy = db.scalar(select(func.count()).where(ChatMessage.conversation_id == conversation_id,
                                                        ChatMessage.status == "pending"))
            if busy:
                raise HTTPException(409, "Wait for the current reply to finish.")
            last = db.scalar(select(func.max(ChatMessage.sequence)).where(ChatMessage.conversation_id == conversation_id)) or 0
            user = ChatMessage(conversation_id=conversation_id, sequence=last + 1, role="user", content=body.content.strip())
            reply = ChatMessage(conversation_id=conversation_id, sequence=last + 2, role="assistant", status="pending",
                                provider=provider_id, model=model)
            db.add_all([user, reply])
            if last == 0:
                conversation.title = body.content.strip().splitlines()[0][:80]
            conversation.provider, conversation.model, conversation.updated_at = provider_id, model, func.now()
            db.flush()
            db.refresh(user)
            db.refresh(reply)
            out = [MessageOut.model_validate(user), MessageOut.model_validate(reply)]
    except SQLAlchemyError as error:
        raise unavailable(error) from None
    background.add_task(run_turn, conversation_id, reply.id, provider_id, model)
    return out


def fail_interrupted_turns(db):
    """Replies still pending at startup were interrupted by a restart; mark them failed."""
    db.execute(update(ChatMessage).where(ChatMessage.status == "pending").values(
        status="failed", content="This reply was interrupted because the server restarted. Send the message again.",
        updated_at=func.now()))
