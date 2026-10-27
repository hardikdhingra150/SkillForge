from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column

from app.database.models import Base


class SkillVersion(Base):
    __tablename__ = "skill_versions"

    skill_id = mapped_column(String(80), primary_key=True)
    version = mapped_column(String(32), primary_key=True)
    capability = mapped_column(String(80), nullable=False, index=True)
    status = mapped_column(String(20), nullable=False)
    implementation_hash = mapped_column(String(64), nullable=False)
    validation_json = mapped_column(JSONB, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'validated', 'retired')", name="ck_skill_versions_status"),
    )
