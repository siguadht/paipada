"""火山 TOS 对象存储：照片中转，供即梦图生图读取公开 URL。"""
import os

import tos

from ..core.config import settings

_client = None

_CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def _get_client():
    global _client
    if _client is None:
        _client = tos.TosClientV2(
            settings.tos_access_key,
            settings.tos_secret_key,
            settings.tos_endpoint,
            settings.tos_region,
        )
    return _client


def _ensure_bucket() -> None:
    client = _get_client()
    if not client.does_bucket_exist(settings.tos_bucket):
        client.create_bucket(settings.tos_bucket)


def upload_file(local_path: str, key: str) -> str:
    """把本地文件上传到 TOS，返回 object key。"""
    _ensure_bucket()
    ext = os.path.splitext(local_path)[1].lstrip(".").lower()
    content_type = _CONTENT_TYPES.get(ext, "image/jpeg")
    with open(local_path, "rb") as f:
        data = f.read()
    _get_client().put_object(settings.tos_bucket, key, content=data, content_type=content_type)
    return key


def presigned_url(key: str, expires: int = 3600) -> str:
    """生成临时公开链接（即梦图生图用它读照片）。"""
    out = _get_client().pre_signed_url(tos.HttpMethodType.Http_Method_Get, settings.tos_bucket, key, expires=expires)
    return out.signed_url


def delete_object(key: str) -> None:
    _get_client().delete_object(settings.tos_bucket, key)
