"""全屋项目。每个空间关联一份原有设计，权限始终按家庭所有者校验。"""
import os
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from PIL import Image

from ..core.config import settings
from ..core.errors import api_error
from ..db import get_db
from ..models import Design, Home, HomeSpace, Photo
from ..services.design_service import serialize_design
from .deps import get_current_user_id
from .designs import _owned_photo

router = APIRouter(tags=["homes"])


class HomeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    style_text: str = Field(default="", max_length=200)
    style_photo_id: str | None = None


class HomeUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    style_text: str = Field(default="", max_length=200)
    style_photo_id: str | None = None


def _owned_home(db: Session, home_id: str, user_id: int) -> Home:
    home = db.get(Home, home_id)
    if not home or home.user_id != user_id:
        raise api_error(404, "HOME_NOT_FOUND", "家庭项目不存在")
    return home


def _serialize_home(db: Session, home: Home) -> dict:
    spaces = db.query(HomeSpace).filter(HomeSpace.home_id == home.id).order_by(HomeSpace.position, HomeSpace.created_at).all()
    return {
        "id": home.id,
        "name": home.name,
        "style_text": home.style_text,
        "style_photo_id": home.style_photo_id,
        "style_photo_url": f"/api/v1/files/uploads/{home.style_photo_id}" if home.style_photo_id else "",
        "created_at": home.created_at.isoformat() if home.created_at else "",
        "spaces": [
            {"id": space.id, "name": space.name, "style_snapshot": space.style_snapshot,
             "design": serialize_design(db, db.get(Design, space.design_id))}
            for space in spaces
        ],
    }


@router.get("")
def list_homes(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    homes = db.query(Home).filter(Home.user_id == user_id).order_by(Home.created_at.desc()).all()
    return {"homes": [_serialize_home(db, home) for home in homes]}


@router.post("", status_code=201)
def create_home(payload: HomeCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    name = payload.name.strip()
    if not name:
        raise api_error(400, "HOME_NAME_REQUIRED", "请填写家的名称")
    if payload.style_photo_id:
        _owned_photo(db, payload.style_photo_id, user_id)
    home = Home(user_id=user_id, name=name, style_text=payload.style_text.strip(), style_photo_id=payload.style_photo_id)
    db.add(home)
    db.commit()
    db.refresh(home)
    return _serialize_home(db, home)


@router.get("/{home_id}")
def get_home(home_id: str, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return _serialize_home(db, _owned_home(db, home_id, user_id))


@router.put("/{home_id}")
def update_home(home_id: str, payload: HomeUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    home = _owned_home(db, home_id, user_id)
    name = payload.name.strip()
    if not name:
        raise api_error(400, "HOME_NAME_REQUIRED", "请填写家的名称")
    if payload.style_photo_id:
        _owned_photo(db, payload.style_photo_id, user_id)
    home.name = name
    home.style_text = payload.style_text.strip()
    home.style_photo_id = payload.style_photo_id
    db.commit()
    return _serialize_home(db, home)


@router.post("/{home_id}/style-from-space/{space_id}")
def style_from_space(home_id: str, space_id: str, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """用户主动将已确认房间的正面图固定为后续房间的风格参考。"""
    home = _owned_home(db, home_id, user_id)
    space = db.get(HomeSpace, space_id)
    if not space or space.home_id != home.id:
        raise api_error(404, "SPACE_NOT_FOUND", "空间不存在")
    design = db.get(Design, space.design_id)
    if not design or design.user_id != user_id or design.status != "completed" or not design.front_image_path:
        raise api_error(409, "SPACE_NOT_CONFIRMED", "请先确认这个空间的效果图并完成 2.5D")
    source = Path(settings.generated_dir) / design.front_image_path
    if not source.is_file() or source.suffix.lower() not in (".jpg", ".png", ".webp"):
        raise api_error(404, "IMAGE_NOT_FOUND", "效果图文件不存在")
    with Image.open(source) as image:
        width, height = image.size
    photo_id = f"{uuid4()}{source.suffix.lower()}"
    destination = Path(settings.upload_dir) / photo_id
    os.makedirs(settings.upload_dir, exist_ok=True)
    shutil.copyfile(source, destination)
    try:
        db.add(Photo(id=photo_id, user_id=user_id, width=width, height=height))
        home.style_photo_id = photo_id
        db.commit()
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    return _serialize_home(db, home)
