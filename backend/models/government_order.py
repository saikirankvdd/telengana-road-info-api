from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base

class GovernmentOrder(Base):
    __tablename__ = "government_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    go_number: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    issue_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    source_record_id: Mapped[int | None] = mapped_column(ForeignKey("source_records.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    project_associations = relationship("GovernmentOrderProject", back_populates="government_order")

class GovernmentOrderProject(Base):
    __tablename__ = "government_order_projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    government_order_id: Mapped[int] = mapped_column(ForeignKey("government_orders.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    government_order = relationship("GovernmentOrder", back_populates="project_associations")
    project = relationship("Project", back_populates="government_order_associations")
