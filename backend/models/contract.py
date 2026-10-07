from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base

class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    tender_id: Mapped[int | None] = mapped_column(ForeignKey("tenders.id", ondelete="SET NULL"), nullable=True)
    contractor_id: Mapped[int | None] = mapped_column(ForeignKey("contractors.id", ondelete="SET NULL"), nullable=True)
    contract_reference: Mapped[str | None] = mapped_column(Text, index=True, nullable=True)
    contract_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    award_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    appointed_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completion_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    contract_status: Mapped[str | None] = mapped_column(String(100), default="AWARDED", nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    source_record_id: Mapped[int | None] = mapped_column(ForeignKey("source_records.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    project = relationship("Project", back_populates="contracts")
    tender = relationship("Tender", back_populates="contracts")
    contractor = relationship("Contractor", back_populates="contracts")
    source = relationship("Source")
