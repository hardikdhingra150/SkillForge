from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, LargeBinary, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column

from app.database.models import Base


class ExecutionCSVInput(Base):
    __tablename__ = "execution_csv_inputs"

    execution_id = mapped_column(
        Uuid, ForeignKey("executions.id", ondelete="CASCADE"), primary_key=True,
    )
    filename = mapped_column(String(200), nullable=False)
    sha256 = mapped_column(String(64), nullable=False)
    version = mapped_column(Integer, nullable=False, server_default=text("1"))
    size_bytes = mapped_column(Integer, nullable=False)
    content_bytes = mapped_column(LargeBinary, nullable=False)
    headers_json = mapped_column(JSONB, nullable=False)
    preview_json = mapped_column(JSONB, nullable=False)
    row_count = mapped_column(Integer, nullable=False)
    mapping_json = mapped_column(JSONB(none_as_null=True), nullable=True)
    uploaded_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    confirmed_at = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("version > 0", name="ck_csv_input_version"),
        CheckConstraint("size_bytes BETWEEN 1 AND 1048576", name="ck_csv_input_size"),
        CheckConstraint("row_count BETWEEN 1 AND 10000", name="ck_csv_input_rows"),
    )
