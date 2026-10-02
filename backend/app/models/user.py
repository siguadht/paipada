import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    invite_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
