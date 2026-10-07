from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base

class ProjectStatusHistory(Base):
    __tablename__ = "project_status_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. PROPOSED, TENDERED, AWARDED, UNDER_CONSTRUCTION, COMPLETED
    progress_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    source_record_id: Mapped[int | None] = mapped_column(ForeignKey("source_records.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="status_history")

class ProjectCostHistory(Base):
    __tablename__ = "project_cost_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    cost_type: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. ESTIMATED, TENDER_VALUE, AWARDED, REVISED
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    source_record_id: Mapped[int | None] = mapped_column(ForeignKey("source_records.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="cost_history")

class ProjectIdentifier(Base):
    __tablename__ = "project_identifiers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    identifier_type: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. PROJECT_ID, TENDER_ID, TENDER_REFERENCE, AOC_ID, GO_NUMBER
    identifier_value: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    source_record_id: Mapped[int | None] = mapped_column(ForeignKey("source_records.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="identifiers")
