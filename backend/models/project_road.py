from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base

class ProjectRoad(Base):
    __tablename__ = "project_roads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    road_id: Mapped[int] = mapped_column(ForeignKey("roads.id", ondelete="CASCADE"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(100), default="PROJECT_ON_ROAD", nullable=False) # e.g. PROJECT_ON_ROAD, ROAD_WIDENING, FLYOVER_OVER_ROAD, CORRIDOR

    # Relationships
    project = relationship("Project", back_populates="project_roads")
    road = relationship("Road", back_populates="project_roads")
