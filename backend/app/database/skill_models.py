from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column

from app.database.models import Base


class SkillVersion(Base):
    __tablename__ = "skill_versions"

    skill_id = mapped_column(String(80), primary_key=True)
    version = mapped_column(String(32), primary_key=True)
    capability = mapped_column(String(80), nullable=False, index=True)
    status = mapped_column(String(20), nullable=False)
    # sha256 over the stored source and canonical contract (see services.skill_registry).
    implementation_hash = mapped_column(String(64), nullable=False)
    validation_json = mapped_column(JSONB, nullable=False)
    source_code = mapped_column(Text, nullable=True)
    contract_json = mapped_column(JSONB, nullable=True)
    origin = mapped_column(String(20), nullable=False, server_default="builtin")
    parent_version = mapped_column(String(32), nullable=True)
    # What changed relative to parent_version (repair diff, reason, evidence) or a backfill note.
    change_json = mapped_column(JSONB, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'validated', 'retired')", name="ck_skill_versions_status"),
        CheckConstraint("origin IN ('builtin', 'generated', 'repaired')", name="ck_skill_versions_origin"),
        CheckConstraint("(source_code IS NULL) = (contract_json IS NULL)", name="ck_skill_versions_source_contract"),
    )
