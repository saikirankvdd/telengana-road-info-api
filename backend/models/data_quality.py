from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.models.base import Base


class ResearchQualityReportModel(Base):
    __tablename__ = "research_quality_reports"

    id = Column(Integer, primary_key=True, index=True)
    research_run_id = Column(Integer, ForeignKey("research_runs.id"), nullable=True, index=True)
    project_name = Column(String(255), nullable=False, index=True)
    overall_quality_score = Column(Float, nullable=False, default=0.0)
    quality_class = Column(String(50), nullable=False, default="FAIR")
    
    fields_checked = Column(Integer, default=0)
    fields_valid = Column(Integer, default=0)
    fields_suspicious = Column(Integer, default=0)
    fields_invalid = Column(Integer, default=0)
    fields_missing = Column(Integer, default=0)
    fields_unsupported = Column(Integer, default=0)
    
    cross_source_conflicts = Column(Integer, default=0)
    duplicate_candidates_count = Column(Integer, default=0)
    stale_fields_count = Column(Integer, default=0)
    
    merge_eligible = Column(Boolean, default=False)
    merge_blockers = Column(JSON, default=list)
    is_quarantined = Column(Boolean, default=False)
    
    report_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    issues = relationship("ResearchQualityIssueModel", back_populates="quality_report", cascade="all, delete-orphan")
    duplicates = relationship("ResearchDuplicateCandidateModel", back_populates="quality_report", cascade="all, delete-orphan")


class ResearchQualityIssueModel(Base):
    __tablename__ = "research_quality_issues"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("research_quality_reports.id"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    rule_name = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False, index=True) # INFO, WARNING, ERROR, CRITICAL
    description = Column(String(500), nullable=False)
    current_value = Column(String(500), nullable=True)
    source_references = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    quality_report = relationship("ResearchQualityReportModel", back_populates="issues")


class ResearchDuplicateCandidateModel(Base):
    __tablename__ = "research_duplicate_candidates"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("research_quality_reports.id"), nullable=False, index=True)
    canonical_project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    match_score = Column(Float, nullable=False)
    matching_signals = Column(JSON, default=list)
    conflicting_signals = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    quality_report = relationship("ResearchQualityReportModel", back_populates="duplicates")
