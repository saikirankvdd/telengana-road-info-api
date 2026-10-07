from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from backend.models.base import Base

class ProjectLocation(Base):
    __tablename__ = "project_locations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    state: Mapped[str] = mapped_column(String(100), default="Telangana", nullable=False)
    district: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    locality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry: Mapped[Any | None] = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True)
    geometry_wkt: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, default=1.0, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    project = relationship("Project", back_populates="locations")
    location_source = relationship("Source")
