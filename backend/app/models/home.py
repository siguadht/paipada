"""家庭项目及其空间。独立新表，旧单空间方案无需迁移。"""
import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .task import new_uuid


class Home(Base):
    __tablename__ = "homes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    style_text: Mapped[str] = mapped_column(Text, default="")
    style_photo_id: Mapped[str | None] = mapped_column(ForeignKey("photos.id"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())


class HomeSpace(Base):
    __tablename__ = "home_spaces"
    __table_args__ = (UniqueConstraint("design_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    home_id: Mapped[str] = mapped_column(ForeignKey("homes.id"), index=True)
    design_id: Mapped[str] = mapped_column(ForeignKey("designs.id"))
    name: Mapped[str] = mapped_column(String(40))
    style_snapshot: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
