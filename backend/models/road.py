from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from backend.models.base import Base

class Road(Base):
    __tablename__ = "roads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    road_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    normalized_road_name: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    road_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    road_type: Mapped[str | None] = mapped_column(String(100), nullable=True) # e.g. NATIONAL_HIGHWAY, STATE_HIGHWAY, MAJOR_DISTRICT_ROAD, MUNICIPAL_ROAD
    authority_id: Mapped[int | None] = mapped_column(ForeignKey("authorities.id"), nullable=True)
    geometry: Mapped[Any | None] = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True)
    geometry_wkt: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    length_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    authority = relationship("Authority")
    source = relationship("Source", back_populates="roads")
    projects = relationship("Project", back_populates="road")
    project_roads = relationship("ProjectRoad", back_populates="road")

    @property
    def last_updated(self):
        return self.updated_at
