import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class Photo(Base):
    """上传照片的归属记录，用于后端权限校验。"""

    __tablename__ = "photos"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
