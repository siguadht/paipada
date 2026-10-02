"""按方案版本一次性拆出可点击软装图层；不在点选时重复计费。"""
import io
import ipaddress
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image

from ..core.config import settings
from ..db import SessionLocal
from ..models import DesignLayerSet
from . import storage_service


def _safe_result_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    if parsed.hostname in ("localhost",) or parsed.hostname.endswith((".local", ".internal")):
        return False
    try:
        return ipaddress.ip_address(parsed.hostname).is_global
    except ValueError:
        return True


def _download_image(url: str) -> Image.Image:
    if not _safe_result_url(url):
        raise ValueError("模型返回了无效图片地址")
    response = httpx.get(url, timeout=60, follow_redirects=False)
    response.raise_for_status()
    if len(response.content) > 30 * 1024 * 1024:
        raise ValueError("模型图片超出大小限制")
    with Image.open(io.BytesIO(response.content)) as image:
        image.load()
        if image.width * image.height > 36_000_000:
            raise ValueError("模型图片分辨率过高")
        return image.copy()


def _validate_layers(data: object) -> tuple[dict, list[dict]]:
    if not isinstance(data, list) or not 2 <= len(data) <= 17:
        raise ValueError("模型未返回有效的家具图层")
    bases = [item for item in data if isinstance(item, dict) and item.get("z_index") == 0]
    if len(bases) != 1:
        raise ValueError("模型底图缺失")
    layers = []
    for item in data:
        if not isinstance(item, dict) or item is bases[0]:
            continue
        box = item.get("bounding_box", {}).get("normalized")
        if (not isinstance(box, list) or len(box) != 4 or
            any(not isinstance(value, (int, float)) or not 0 <= value <= 999 for value in box) or
            box[0] >= box[2] or box[1] >= box[3] or
            not isinstance(item.get("url"), str)):
            raise ValueError("模型图层坐标无效")
        layers.append(item)
    if not layers:
        raise ValueError("未找到可交互图层")
    return bases[0], layers


def _decompose(source_name: str, layer_set_id: str) -> tuple[str, list[dict]]:
    if not settings.has_ark_key or not settings.ark_image_model:
        raise ValueError("图层拆分模型未配置")
    source = Path(settings.generated_dir) / source_name
    if not source.is_file():
        raise ValueError("当前效果图不存在")
    key = f"design-layers/{layer_set_id}.jpg"
    written: list[Path] = []
    try:
        storage_service.upload_file(str(source), key)
        payload = {
            "model": settings.ark_image_model,
            "image": storage_service.presigned_url(key, expires=3600),
            "prompt": "将图中可以移动的主要软装单件拆分为独立透明图层，例如沙发、茶几、地毯、落地灯、绿植、窗帘与柜体。每件保持完整轮廓和原位置，底图补全被遮挡背景；不要拆墙、窗、地面、天花板、文字或水印。只拆清楚可辨认的物件。",
            "layer_decomposition": True,
            "size": "1.5K",
            "response_format": "url",
            "watermark": False,
        }
        response = httpx.post(
            f"{settings.ark_base_url}/images/generations",
            headers={"Authorization": f"Bearer {settings.ark_api_key}", "Content-Type": "application/json"},
            json=payload, timeout=240,
        )
        response.raise_for_status()  # 付费调用不自动重试，避免重复计费。
        base_data, layer_data = _validate_layers(response.json().get("data"))
        base = _download_image(base_data["url"])
        if base.width < 512 or base.height < 512:
            raise ValueError("底图尺寸无效")
        base_name = f"{layer_set_id}_base.png"
        base_path = Path(settings.generated_dir) / base_name
        base.convert("RGB").save(base_path, "PNG")
        written.append(base_path)
        result = []
        for index, item in enumerate(sorted(layer_data, key=lambda layer: layer.get("z_index", 0))):
            layer = _download_image(item["url"])
            if layer.mode not in ("RGBA", "LA") or not layer.getextrema()[-1][0] < 255:
                raise ValueError("模型未返回透明家具图层")
            name = f"{layer_set_id}_layer_{index}.png"
            path = Path(settings.generated_dir) / name
            layer.convert("RGBA").save(path, "PNG")
            written.append(path)
            result.append({
                "name": str(item.get("name") or f"软装 {index + 1}")[:40],
                "description": str(item.get("description") or "")[:160],
                "image_path": name,
                "box": [round(float(value) / 999, 6) for value in item["bounding_box"]["normalized"]],
                "z_index": index + 1,
            })
        return base_name, result
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        raise
    finally:
        try:
            storage_service.delete_object(key)
        except Exception:
            pass  # TOS 生命周期规则兜底，不能覆盖拆层结果。


def run_layer_set(layer_set_id: str) -> None:
    """状态落库；中断后不自动重调有费用的模型请求。"""
    with SessionLocal() as db:
        item = db.get(DesignLayerSet, layer_set_id)
        if not item or item.status != "queued":
            return
        item.status = "processing"
        db.commit()
        try:
            base_name, layers = _decompose(item.source_image_path, item.id)
            item.base_image_path = base_name
            item.layers = layers
            item.status = "ready"
            item.error_message = ""
        except Exception:
            item.status = "failed"
            item.error_message = "整件选择准备失败，请稍后重试；本次实际费用以火山账单为准"
        db.commit()
