from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base

class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    tender_id: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    tender_reference_number: Mapped[str | None] = mapped_column(Text, index=True, nullable=True)
    title: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    organisation: Mapped[str | None] = mapped_column(Text, nullable=True)
    department: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closing_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    estimated_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    awarded_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    source_record_id: Mapped[int | None] = mapped_column(ForeignKey("source_records.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    project = relationship("Project", back_populates="tenders")
    source = relationship("Source", back_populates="tenders")
    contracts = relationship("Contract", back_populates="tender")
    project_associations = relationship("ProjectTender", back_populates="tender")
