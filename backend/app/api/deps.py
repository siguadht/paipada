"""鉴权依赖：从 Bearer 头解析当前用户。"""
from fastapi import Header

from ..core.errors import api_error
from ..core.security import decode_token


def get_current_user_id(authorization: str | None = Header(default=None)) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise api_error(401, "UNAUTHORIZED", "请先登录")
    token = authorization[len("Bearer "):].strip()
    user_id = decode_token(token)
    if user_id is None:
        raise api_error(401, "UNAUTHORIZED", "登录已过期，请重新登录")
    return user_id
