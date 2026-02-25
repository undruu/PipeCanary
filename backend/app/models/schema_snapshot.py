import uuid

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SchemaSnapshot(Base):
    __tablename__ = "schema_snapshots"
    __table_args__ = (Index("ix_schema_snapshots_table_captured", "table_id", "captured_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("monitored_tables.id"), nullable=False
    )
    columns_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    captured_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())

    monitored_table = relationship("MonitoredTable", back_populates="schema_snapshots")
