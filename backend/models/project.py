from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from backend.models.base import Base

class ProjectAuthority(Base):
    __tablename__ = "project_authorities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    authority_id: Mapped[int] = mapped_column(ForeignKey("authorities.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(100), default="PRIMARY_AUTHORITY", nullable=False)

    project = relationship("Project", back_populates="authority_associations")
    authority = relationship("Authority", back_populates="project_associations")

class ProjectContractor(Base):
    __tablename__ = "project_contractors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    contractor_id: Mapped[int] = mapped_column(ForeignKey("contractors.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(100), default="MAIN_CONTRACTOR", nullable=False)
    award_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    contract_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)

    project = relationship("Project", back_populates="contractor_associations")
    contractor = relationship("Contractor", back_populates="project_associations")

class ProjectTender(Base):
    __tablename__ = "project_tenders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    tender_id: Mapped[int] = mapped_column(ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)

    project = relationship("Project", back_populates="tender_associations")
    tender = relationship("Tender", back_populates="project_associations")

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    project_name: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    normalized_project_name: Mapped[str | None] = mapped_column(Text, index=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    road_id: Mapped[int | None] = mapped_column(ForeignKey("roads.id"), nullable=True)
    authority_id: Mapped[int | None] = mapped_column(ForeignKey("authorities.id"), nullable=True)
    start_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    end_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    length_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    awarded_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    appointed_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expected_completion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_completion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    physical_progress: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_mode: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geometry: Mapped[Any | None] = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True)
    geometry_wkt: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    road = relationship("Road", back_populates="projects")
    authority = relationship("Authority", back_populates="projects")
    source = relationship("Source", back_populates="projects")
    locations = relationship("ProjectLocation", back_populates="project", cascade="all, delete-orphan")
    project_roads = relationship("ProjectRoad", back_populates="project", cascade="all, delete-orphan")
    tenders = relationship("Tender", back_populates="project")
    contracts = relationship("Contract", back_populates="project", cascade="all, delete-orphan")
    authority_associations = relationship("ProjectAuthority", back_populates="project", cascade="all, delete-orphan")
    contractor_associations = relationship("ProjectContractor", back_populates="project", cascade="all, delete-orphan")
    tender_associations = relationship("ProjectTender", back_populates="project", cascade="all, delete-orphan")
    status_history = relationship("ProjectStatusHistory", back_populates="project", cascade="all, delete-orphan")
    cost_history = relationship("ProjectCostHistory", back_populates="project", cascade="all, delete-orphan")
    identifiers = relationship("ProjectIdentifier", back_populates="project", cascade="all, delete-orphan")
    government_order_associations = relationship("GovernmentOrderProject", back_populates="project", cascade="all, delete-orphan")
