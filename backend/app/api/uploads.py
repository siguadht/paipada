"""照片上传：校验格式、真实类型、大小、安全文件名。"""
import io
import os
import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.errors import api_error
from ..db import get_db
from ..models import Photo
from ..schemas import UploadResponse
from .deps import get_current_user_id

router = APIRouter(tags=["uploads"])

_EXT_MAP = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "webp": "webp"}


@router.post("", response_model=UploadResponse, status_code=201)
async def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise api_error(413, "FILE_TOO_LARGE", f"图片不能超过 {settings.max_upload_mb}MB")

    try:
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or "").lower()
        width, height = img.size
    except Exception:
        raise api_error(400, "INVALID_IMAGE", "不是有效的图片文件")

    if fmt not in _EXT_MAP:
        raise api_error(400, "UNSUPPORTED_TYPE", "仅支持 JPG / PNG / WebP 图片")

    # 安全文件名：只存 uuid + 白名单扩展名，忽略原始文件名，防路径遍历
    ext = _EXT_MAP[fmt]
    photo_id = f"{uuid.uuid4()}.{ext}"
    os.makedirs(settings.upload_dir, exist_ok=True)
    with open(os.path.join(settings.upload_dir, photo_id), "wb") as f:
        f.write(data)

    db.add(Photo(id=photo_id, user_id=user_id, width=width, height=height))
    db.commit()

    return UploadResponse(
        photo_id=photo_id,
        url=f"/api/v1/files/uploads/{photo_id}",
        width=width,
        height=height,
    )
