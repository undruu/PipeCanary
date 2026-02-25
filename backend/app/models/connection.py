import uuid

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # snowflake, bigquery, databricks
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    credentials_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(50), server_default="pending")
    last_tested_at: Mapped[str | None] = mapped_column(DateTime)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="connections")
    monitored_tables = relationship("MonitoredTable", back_populates="connection")
