"""可编辑软装方案。与阶段 2 的 Task 分开，保留旧验收链路。"""
import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .task import new_uuid


class Design(Base):
    __tablename__ = "designs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    photo_path: Mapped[str] = mapped_column(String(512))
    user_input: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    current_step: Mapped[str] = mapped_column(String(128), default="排队中")
    front_image_path: Mapped[str] = mapped_column(String(512), default="")
    iso_image_path: Mapped[str] = mapped_column(String(512), default="")
    current_version: Mapped[int] = mapped_column(Integer, default=0)
    design_notes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    edit_history: Mapped[list | None] = mapped_column(JSON, nullable=True)
    pending_job: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str] = mapped_column(String(64), default="")
    error_message: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class DesignVersion(Base):
    __tablename__ = "design_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    design_id: Mapped[str] = mapped_column(ForeignKey("designs.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    image_path: Mapped[str] = mapped_column(String(512))
    operation: Mapped[str] = mapped_column(String(32), default="initial")
    instruction: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())


class DesignStructureReview(Base):
    """用户对某一版正面图的结构核对记录；保留历史版，不随恢复版本清除。"""
    __tablename__ = "design_structure_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    design_id: Mapped[str] = mapped_column(ForeignKey("designs.id"), index=True)
    front_version: Mapped[int] = mapped_column(Integer)
    source_image_path: Mapped[str] = mapped_column(String(512))
    mode: Mapped[str] = mapped_column(String(16))
    checks: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())


class DesignHotspot(Base):
    """明确附着在某张 2.5D 图片上的商品热点。"""
    __tablename__ = "design_hotspots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    design_id: Mapped[str] = mapped_column(ForeignKey("designs.id"), index=True)
    iso_image_path: Mapped[str] = mapped_column(String(512))
    front_version: Mapped[int] = mapped_column(Integer)
    product_id: Mapped[str] = mapped_column(String(32))
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())


class DesignReference(Base):
    """方案使用的可选参考图；新表不改变已有方案表结构。"""
    __tablename__ = "design_references"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    design_id: Mapped[str] = mapped_column(ForeignKey("designs.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    photo_id: Mapped[str] = mapped_column(ForeignKey("photos.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())


class DesignLayerSet(Base):
    """按正面图版本缓存整件软装图层；失败后需再次确认费用才可重试。"""
    __tablename__ = "design_layer_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    design_id: Mapped[str] = mapped_column(ForeignKey("designs.id"), index=True)
    front_version: Mapped[int] = mapped_column(Integer)
    source_image_path: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    base_image_path: Mapped[str] = mapped_column(String(512), default="")
    layers: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
