import uuid

from sqlalchemy import String, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alerts_table_status", "table_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("monitored_tables.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # schema_drift, row_count, null_rate, cardinality
    severity: Mapped[str] = mapped_column(String(20), nullable=False, server_default="warning")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="open")
    details_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    acknowledged_at: Mapped[str | None] = mapped_column(DateTime)
    resolved_at: Mapped[str | None] = mapped_column(DateTime)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())

    monitored_table = relationship("MonitoredTable", back_populates="alerts")
