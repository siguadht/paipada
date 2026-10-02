"""邀请码登录。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.errors import api_error
from ..core.security import create_token
from ..db import get_db
from ..models import User
from ..schemas import LoginRequest, LoginResponse, MeResponse
from .deps import get_current_user_id

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.invite_code == payload.invite_code.strip(), User.is_active.is_(True))
        .first()
    )
    if not user:
        raise api_error(401, "INVALID_INVITE_CODE", "邀请码无效")
    return LoginResponse(token=create_token(user.id), user_id=user.id)


@router.get("/me", response_model=MeResponse)
def me(user_id: int = Depends(get_current_user_id)):
    return MeResponse(user_id=user_id)
