from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base

class Authority(Base):
    __tablename__ = "authorities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    normalized_name: Mapped[str | None] = mapped_column(Text, index=True, nullable=True)
    authority_type: Mapped[str | None] = mapped_column(String(100), nullable=True) # e.g. STATE_DEPARTMENT, MUNICIPAL_CORPORATION, CENTRAL_AGENCY
    parent_authority_id: Mapped[int | None] = mapped_column(ForeignKey("authorities.id", ondelete="SET NULL"), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), default="Telangana", nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    official_website: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    official_phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    official_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Self-referential relationship for hierarchical authorities
    parent_authority = relationship("Authority", remote_side=[id], backref="child_authorities")
    project_associations = relationship("ProjectAuthority", back_populates="authority")
    projects = relationship("Project", back_populates="authority")
