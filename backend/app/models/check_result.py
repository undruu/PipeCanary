import uuid

from sqlalchemy import String, Float, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CheckResult(Base):
    __tablename__ = "check_results"
    __table_args__ = (Index("ix_check_results_table_type_measured", "table_id", "check_type", "measured_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("monitored_tables.id"), nullable=False
    )
    check_type: Mapped[str] = mapped_column(String(50), nullable=False)  # row_count, null_rate, cardinality
    column_name: Mapped[str | None] = mapped_column(String(255))
    value: Mapped[float] = mapped_column(Float, nullable=False)
    measured_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())

    monitored_table = relationship("MonitoredTable", back_populates="check_results")
