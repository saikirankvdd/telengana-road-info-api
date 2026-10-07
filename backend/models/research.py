from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base

class ResearchRun(Base):
    __tablename__ = "research_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    query_project_name: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="NOT_IMPLEMENTED", nullable=False)
    searched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    sources_checked: Mapped[int] = mapped_column(Integer, default=0)
    sources_accessed: Mapped[int] = mapped_column(Integer, default=0)
    fields_found: Mapped[int] = mapped_column(Integer, default=0)
    fields_verified: Mapped[int] = mapped_column(Integer, default=0)
    conflicts_found: Mapped[int] = mapped_column(Integer, default=0)
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("Project", backref="research_runs")
    sources = relationship("ProjectResearchSource", back_populates="research_run", cascade="all, delete-orphan")
    field_evidence = relationship("ProjectFieldEvidence", back_populates="research_run", cascade="all, delete-orphan")

class ProjectResearchSource(Base):
    __tablename__ = "project_research_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    research_run_id: Mapped[int] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="other", nullable=False)
    authority_level: Mapped[str] = mapped_column(String(20), default="SECONDARY", nullable=False)
    publisher: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    research_run = relationship("ResearchRun", back_populates="sources")
    field_evidences = relationship("ProjectFieldEvidence", back_populates="source")

class ProjectFieldEvidence(Base):
    __tablename__ = "project_field_evidences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    research_run_id: Mapped[int] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("project_research_sources.id", ondelete="SET NULL"), nullable=True)
    field_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    extracted_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(50), default="NOT_FOUND", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    research_run = relationship("ResearchRun", back_populates="field_evidence")
    source = relationship("ProjectResearchSource", back_populates="field_evidences")
