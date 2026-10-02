"""JWT 会话（邀请码登录后签发）。"""
from datetime import datetime, timedelta, timezone

import jwt

from .config import settings


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> int | None:
    """返回 user_id；无效/过期返回 None。"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except Exception:
        return None
