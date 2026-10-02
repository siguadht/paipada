"""生图服务：阶段 2-2 接入火山即梦真实生图（正面图生图保结构 + 2.5D 文生图）。"""
import io
import os
import time
import uuid

import httpx
from PIL import Image, ImageDraw

from ..core.config import settings
from ..core.errors import ServiceError
from . import storage_service


def generate_images(front_prompt: str, isometric_prompt: str, photo_path: str, task_id: str) -> dict:
    """返回 {"front": 文件名, "iso": 文件名}。无 Key 走 mock（仅开发）。"""
    if not settings.has_ark_key:
        return _mock_generate(task_id)
    if not settings.ark_image_model:
        raise ServiceError("CONFIG_INCOMPLETE", "缺少 ARK_IMAGE_MODEL 配置")
    return _real_generate(front_prompt, isometric_prompt, photo_path, task_id)


def _real_generate(front_prompt: str, isometric_prompt: str, photo_path: str, task_id: str) -> dict:
    # 1) 照片上传 TOS 拿公开 URL（即梦图生图只认公开链接）
    local_photo = os.path.join(settings.upload_dir, photo_path)
    photo_key = f"uploads/{photo_path}"
    storage_service.upload_file(local_photo, photo_key)
    photo_url = storage_service.presigned_url(photo_key, expires=3600)

    # 2) 正面效果图：图生图（锁房间结构）
    front_name = _gen(front_prompt, task_id, "front", image_url=photo_url, strength=0.7)
    # 3) 2.5D 等距图：同源图生图（与正面图同照片、风格一致），strength 稍低以转等距视角
    iso_name = _gen(isometric_prompt, task_id, "iso", image_url=photo_url, strength=0.5)
    return {"front": front_name, "iso": iso_name}


_QUALITY_SUFFIX = "，家具比例正确，结构合理，绿植适量，画面干净，无文字无水印"
_DESIGN_QUALITY_SUFFIX = "，写实，比例自然，无文字水印"


def _gen(prompt: str, task_id: str, kind: str, image_url: str | None, strength: float = 0.7, timeout: int = 240) -> str:
    payload = {
        "model": settings.ark_image_model,
        "prompt": prompt + _QUALITY_SUFFIX,
        "size": "1024x1024",
        "response_format": "url",
    }
    if image_url:
        payload["image"] = image_url
        payload["strength"] = strength

    url = f"{settings.ark_base_url}/images/generations"
    headers = {"Authorization": f"Bearer {settings.ark_api_key}", "Content-Type": "application/json"}
    r = httpx.post(url, headers=headers, json=payload, timeout=timeout)
    if r.status_code != 200:
        err = r.json().get("error", {})
        raise ServiceError("IMAGE_GEN_FAILED", f"生图失败：{err.get('message', r.status_code)}")
    img_url = r.json()["data"][0]["url"]

    img = httpx.get(img_url, timeout=60)
    img.raise_for_status()
    os.makedirs(settings.generated_dir, exist_ok=True)
    name = f"{task_id}_{kind}.jpg"
    with open(os.path.join(settings.generated_dir, name), "wb") as f:
        f.write(img.content)
    return name


def _mock_generate(task_id: str) -> dict:
    os.makedirs(settings.generated_dir, exist_ok=True)
    front_name = f"{task_id}_front.png"
    iso_name = f"{task_id}_iso.png"
    specs = [
        (front_name, "正面效果图 (mock 占位)", (214, 190, 158)),
        (iso_name, "2.5D 等距图 (mock 占位)", (168, 196, 214)),
    ]
    for name, label, color in specs:
        img = Image.new("RGB", (1024, 768), color)
        draw = ImageDraw.Draw(img)
        draw.rectangle([24, 24, 1000, 744], outline=(255, 255, 255), width=4)
        draw.text((48, 48), label, fill=(255, 255, 255))
        img.save(os.path.join(settings.generated_dir, name))
    return {"front": front_name, "iso": iso_name}


def _output_size_for_source(width: int, height: int) -> str:
    """Choose the closest supported 1.5K aspect ratio for the room photo."""
    ratio = width / height
    choices = (
        (2048, 1152),  # 16:9
        (1872, 1248),  # 3:2
        (1792, 1344),  # 4:3
        (1536, 1536),  # 1:1
        (1344, 1792),  # 3:4
        (1248, 1872),  # 2:3
        (1152, 2048),  # 9:16
    )
    target_width, target_height = min(choices, key=lambda size: abs(size[0] / size[1] - ratio))
    return f"{target_width}x{target_height}"


def _design_image(prompt: str, source_path: str, design_id: str, kind: str, reference_names: list[str] | None = None, extra_reference_paths: list[str] | None = None) -> str:
    """从当前图生成新版本；真实请求只使用服务端上传的短时授权 URL。"""
    name = f"{design_id}_{kind}_{uuid.uuid4().hex[:8]}.jpg"
    target = os.path.join(settings.generated_dir, name)
    os.makedirs(settings.generated_dir, exist_ok=True)
    with Image.open(source_path) as source_info:
        output_size = _output_size_for_source(source_info.width, source_info.height)
    if not settings.has_ark_key:
        # 离线开发图有明显 MOCK 标记，不作为真实模型效果验收。
        with Image.open(source_path) as source:
            preview = source.convert("RGB")
            preview.thumbnail((1024, 1024))
            draw = ImageDraw.Draw(preview)
            draw.rectangle((12, 12, 250, 58), fill="#ffffff")
            draw.text((22, 25), f"MOCK {kind}", fill="#1f1f1f")
            preview.save(target, "JPEG")
        return name
    if not settings.ark_image_model:
        raise ServiceError("CONFIG_INCOMPLETE", "缺少 ARK_IMAGE_MODEL 配置")
    paths = [source_path, *(os.path.join(settings.upload_dir, item) for item in (reference_names or [])), *(extra_reference_paths or [])]
    keys = [f"designs/{name}.input{index}{os.path.splitext(path)[1].lower()}" for index, path in enumerate(paths)]
    try:
        image_urls = []
        for path, key in zip(paths, keys):
            storage_service.upload_file(path, key)
            image_urls.append(storage_service.presigned_url(key, expires=3600))
        payload = {
            "model": settings.ark_image_model,
            "prompt": prompt + _DESIGN_QUALITY_SUFFIX,
            "image": image_urls[0] if len(image_urls) == 1 else image_urls,
            "size": output_size,
            "response_format": "url",
            "watermark": False,
        }
        response = None
        for attempt in range(2):
            try:
                response = httpx.post(
                    f"{settings.ark_base_url}/images/generations",
                    headers={"Authorization": f"Bearer {settings.ark_api_key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=240,
                )
            except httpx.RequestError:
                if attempt == 0:
                    time.sleep(1)
                    continue
                raise ServiceError("IMAGE_GEN_FAILED", "图片生成超时或网络失败，请稍后重试")
            if response.status_code == 200:
                break
            if response.status_code < 500 or attempt == 1:
                raise ServiceError("IMAGE_GEN_FAILED", "图片编辑失败，请稍后重试")
            time.sleep(1)
        if response is None:
            raise ServiceError("IMAGE_GEN_FAILED", "图片生成失败，请稍后重试")
        result_url = response.json()["data"][0]["url"]
        result = None
        for attempt in range(2):
            try:
                result = httpx.get(result_url, timeout=60)
                result.raise_for_status()
                break
            except (httpx.HTTPError, httpx.TimeoutException):
                if attempt == 1:
                    raise ServiceError("IMAGE_DOWNLOAD_FAILED", "图片保存失败，请重试")
                time.sleep(1)
        if result is None:
            raise ServiceError("IMAGE_DOWNLOAD_FAILED", "图片保存失败，请重试")
        with Image.open(io.BytesIO(result.content)) as generated:
            generated.convert("RGB").save(target, "JPEG", quality=92)
        return name
    except ServiceError:
        raise
    except Exception as exc:
        raise ServiceError("IMAGE_GEN_FAILED", "图片生成失败，请稍后重试") from exc
    finally:
        for key in keys:
            try:
                storage_service.delete_object(key)
            except Exception:
                pass  # 临时对象到期后由存储生命周期规则清理，不能掩盖主请求结果。


def generate_design_front(prompt: str, photo_path: str, design_id: str, reference_names: list[str] | None = None) -> str:
    return _design_image(prompt, os.path.join(settings.upload_dir, photo_path), design_id, "front", reference_names)


def edit_design_front(source_name: str, prompt: str, design_id: str, reference_names: list[str] | None = None, extra_reference_paths: list[str] | None = None) -> str:
    return _design_image(prompt, os.path.join(settings.generated_dir, source_name), design_id, "edit", reference_names, extra_reference_paths)


def generate_design_iso(source_name: str, prompt: str, design_id: str) -> str:
    return _design_image(prompt, os.path.join(settings.generated_dir, source_name), design_id, "iso")
