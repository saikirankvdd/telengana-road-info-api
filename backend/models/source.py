from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base

class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. HISTORICAL_HF_DATASET, TELANGANA_EPROCUREMENT, TELANGANA_GIS
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    official: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    authentication_type: Mapped[str | None] = mapped_column(String(100), default="PUBLIC", nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_record_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    source_records = relationship("SourceRecord", back_populates="source")
    roads = relationship("Road", back_populates="source")
    projects = relationship("Project", back_populates="source")
    tenders = relationship("Tender", back_populates="source")

class SourceRecord(Base):
    __tablename__ = "source_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    external_record_id: Mapped[str | None] = mapped_column(Text, index=True, nullable=True)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_payload_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    source = relationship("Source", back_populates="source_records")
