import uuid

from sqlalchemy import String, Boolean, DateTime, ForeignKey, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MonitoredTable(Base):
    __tablename__ = "monitored_tables"
    __table_args__ = (UniqueConstraint("connection_id", "schema_name", "table_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connections.id"), nullable=False
    )
    schema_name: Mapped[str] = mapped_column(String(255), nullable=False)
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    check_frequency: Mapped[str] = mapped_column(String(50), server_default="daily")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    connection = relationship("Connection", back_populates="monitored_tables")
    schema_snapshots = relationship("SchemaSnapshot", back_populates="monitored_table")
    check_results = relationship("CheckResult", back_populates="monitored_table")
    alerts = relationship("Alert", back_populates="monitored_table")
