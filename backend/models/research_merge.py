from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base

class ResearchMergeReview(Base):
    __tablename__ = "research_merge_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    research_run_id: Mapped[int] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    candidate_entity_type: Mapped[str] = mapped_column(String(50), default="PROJECT", nullable=False)
    candidate_entity_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    
    match_status: Mapped[str] = mapped_column(String(50), default="NO_MATCH", nullable=False)
    match_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    matching_signals: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    negative_signals: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    
    field_comparison: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    field_decisions: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    
    review_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    research_run = relationship("ResearchRun", backref="reviews")
    candidate_project = relationship("Project", backref="merge_reviews")
    merge_actions = relationship("ResearchMergeAction", back_populates="review", cascade="all, delete-orphan")


class ResearchMergeAction(Base):
    __tablename__ = "research_merge_actions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("research_merge_reviews.id", ondelete="CASCADE"), nullable=False)
    research_run_id: Mapped[int] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    
    field_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    target_table: Mapped[str] = mapped_column(String(100), nullable=False)
    target_record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_evidence_id: Mapped[int | None] = mapped_column(ForeignKey("project_field_evidences.id", ondelete="SET NULL"), nullable=True)
    
    action: Mapped[str] = mapped_column(String(50), default="NO_CHANGE", nullable=False)
    approved_by: Mapped[str] = mapped_column(String(100), default="admin", nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    review = relationship("ResearchMergeReview", back_populates="merge_actions")
    research_run = relationship("ResearchRun", backref="merge_actions")
    source_evidence = relationship("ProjectFieldEvidence", backref="merge_actions")
