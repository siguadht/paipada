"""受保护的图片读取：只允许登录用户读取自己的照片与生成图。"""
import os
import re

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.errors import api_error
from ..db import get_db
from ..models import Design, DesignLayerSet, DesignVersion, Photo, Task
from .deps import get_current_user_id

router = APIRouter(tags=["files"])

_UPLOAD_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(jpg|png|webp)$"
)
_GENERATED_RE = re.compile(r"^[0-9a-f-]{36}_(front|iso)\.(jpg|png|webp)$")
_DESIGN_RE = re.compile(r"^[0-9a-f-]{36}_(front|edit|iso)_[0-9a-f]{8}\.jpg$")
_LAYER_RE = re.compile(r"^[0-9a-f-]{36}_(base|layer_(?:[0-9]|1[0-5]))\.png$")


def _private_file(path: str) -> FileResponse:
    if not os.path.isfile(path):
        raise api_error(404, "FILE_NOT_FOUND", "图片不存在")
    return FileResponse(path, headers={"Cache-Control": "private, no-store"})


@router.get("/uploads/{filename}")
def uploaded_photo(
    filename: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if not _UPLOAD_RE.fullmatch(filename):
        raise api_error(404, "FILE_NOT_FOUND", "图片不存在")

    photo = db.get(Photo, filename)
    owned = photo is not None and photo.user_id == user_id
    if photo is None:
        # 兼容修复前已创建的任务，旧上传记录没有 photos 表数据。
        owned = (
            db.query(Task.id)
            .filter(Task.user_id == user_id, Task.photo_path == filename)
            .first()
            is not None
        )
    if not owned:
        raise api_error(404, "FILE_NOT_FOUND", "图片不存在")
    return _private_file(os.path.join(settings.upload_dir, filename))


@router.get("/generated/{filename}")
def generated_image(
    filename: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if not (_GENERATED_RE.fullmatch(filename) or _DESIGN_RE.fullmatch(filename) or _LAYER_RE.fullmatch(filename)):
        raise api_error(404, "FILE_NOT_FOUND", "图片不存在")
    owned = (
        db.query(Task.id)
        .filter(
            Task.user_id == user_id,
            or_(Task.front_image_path == filename, Task.iso_image_path == filename),
        )
        .first()
        is not None
    )
    if not owned and _DESIGN_RE.fullmatch(filename):
        owned = (
            db.query(Design.id)
            .filter(Design.user_id == user_id, Design.iso_image_path == filename)
            .first()
            is not None
        ) or (
            db.query(DesignVersion.id)
            .join(Design, Design.id == DesignVersion.design_id)
            .filter(Design.user_id == user_id, DesignVersion.image_path == filename)
            .first()
            is not None
        )
    if not owned and _LAYER_RE.fullmatch(filename):
        layer_id = filename.split("_", 1)[0]
        layer_set = db.get(DesignLayerSet, layer_id)
        owned = bool(
            layer_set and layer_set.status == "ready"
            and db.query(Design.id).filter(Design.id == layer_set.design_id, Design.user_id == user_id).first()
            and (filename == layer_set.base_image_path or filename in {
                layer.get("image_path") for layer in (layer_set.layers or [])
            })
        )
    if not owned:
        raise api_error(404, "FILE_NOT_FOUND", "图片不存在")
    return _private_file(os.path.join(settings.generated_dir, filename))
