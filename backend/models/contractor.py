from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base

class Contractor(Base):
    __tablename__ = "contractors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    legal_name: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    normalized_name: Mapped[str | None] = mapped_column(Text, index=True, nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contractor_type: Mapped[str | None] = mapped_column(String(100), nullable=True) # e.g. COMPANY, INDIVIDUAL, JV
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    source_record_id: Mapped[int | None] = mapped_column(ForeignKey("source_records.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    project_associations = relationship("ProjectContractor", back_populates="contractor")
    contracts = relationship("Contract", back_populates="contractor")
