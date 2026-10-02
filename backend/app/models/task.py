import datetime
import uuid

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base

# 任务状态机（枚举值受控）
STATUS_PENDING = "pending"
STATUS_UNDERSTANDING = "understanding"
STATUS_RENDERING = "rendering"
STATUS_REVIEW = "review"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

VALID_STATUSES = {
    STATUS_PENDING,
    STATUS_UNDERSTANDING,
    STATUS_RENDERING,
    STATUS_REVIEW,
    STATUS_COMPLETED,
    STATUS_FAILED,
}


def new_uuid() -> str:
    return str(uuid.uuid4())


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    photo_path: Mapped[str] = mapped_column(String(512), default="")
    user_input: Mapped[str] = mapped_column(Text, default="")

    status: Mapped[str] = mapped_column(String(32), default=STATUS_PENDING, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[str] = mapped_column(String(64), default="")

    llm_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    front_image_path: Mapped[str] = mapped_column(String(512), default="")
    iso_image_path: Mapped[str] = mapped_column(String(512), default="")
    design_notes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    hotspots: Mapped[list | None] = mapped_column(JSON, nullable=True)
    layout_hints: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    review_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reject_count: Mapped[int] = mapped_column(Integer, default=0)

    error_code: Mapped[str] = mapped_column(String(64), default="")
    error_message: Mapped[str] = mapped_column(String(512), default="")

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
