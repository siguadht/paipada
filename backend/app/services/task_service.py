"""任务编排：状态机 + 后台执行 + 审图 + 序列化。"""
import json
from pathlib import Path

from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.errors import ServiceError
from ..db import SessionLocal
from ..models import Task
from ..models.task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RENDERING,
    STATUS_REVIEW,
    STATUS_UNDERSTANDING,
)
from . import image_service, llm_service

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"

_HOTSPOT_LABELS = {
    "sofa_area": "沙发区",
    "tv_area": "电视区",
    "bed_area": "床区",
    "dining_area": "餐桌区",
    "desk_area": "书桌区",
    "plant_area": "绿植区",
    "light_area": "灯具区",
    "rug_area": "地毯区",
}

_CATEGORY_MAP = {
    "sofa_area": "sofa",
    "tv_area": "cabinet",
    "bed_area": "bed",
    "dining_area": "table",
    "desk_area": "desk",
    "plant_area": "plant",
    "light_area": "light",
    "rug_area": "rug",
}


def _set_status(task: Task, status: str, progress: int, step: str) -> None:
    task.status = status
    task.progress = progress
    task.current_step = step


def _set_failed(task: Task, code: str, message: str) -> None:
    task.status = STATUS_FAILED
    task.progress = 0
    task.current_step = "失败"
    task.error_code = code
    task.error_message = message


def _img_url(filename: str, kind: str = "generated") -> str:
    return f"/api/v1/files/{kind}/{filename}" if filename else ""


def _load_products() -> list[dict]:
    try:
        return json.loads((_DATA_DIR / "products.json").read_text(encoding="utf-8"))
    except Exception:
        return []


def _build_hotspots(layout_hints: dict, style: str = "") -> list[dict]:
    products = _load_products()
    hotspots = []
    for key, pos in (layout_hints or {}).items():
        label = _HOTSPOT_LABELS.get(key, key)
        try:
            x = float(pos.get("x", 0.3))
            y = float(pos.get("y", 0.5))
        except (AttributeError, TypeError, ValueError):
            x, y = 0.3, 0.5
        hotspot = {"id": f"h{len(hotspots) + 1}", "label": label, "x": round(x, 2), "y": round(y, 2)}
        cat = _CATEGORY_MAP.get(key, key)
        candidates = [p for p in products if p.get("category") == cat]
        match = next((p for p in candidates if p.get("style") == style), None)
        if match is None and candidates:
            match = candidates[0]
        if match:
            hotspot["product"] = {
                "name": match.get("name"),
                "brand": match.get("brand"),
                "price": match.get("price"),
                "color": match.get("color"),
                "image_url": match.get("image_url", ""),
            }
        hotspots.append(hotspot)
    return hotspots


def run_task(task_id: str) -> None:
    """后台执行：understanding → rendering → review。独立会话，失败置 failed。"""
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if not task:
            return

        _set_status(task, STATUS_UNDERSTANDING, 15, "AI 正在理解你的需求")
        db.commit()

        photo_url = _img_url(task.photo_path, "uploads")
        llm = llm_service.understand_room(task.user_input, photo_url=photo_url)
        task.llm_result = llm
        task.design_notes = llm.get("design_notes") or []
        task.layout_hints = llm.get("layout_hints") or {}
        db.commit()

        _set_status(task, STATUS_RENDERING, 55, "AI 正在生成效果图")
        db.commit()

        sd = llm.get("sd_prompts") or {}
        images = image_service.generate_images(sd.get("front", ""), sd.get("isometric", ""), task.photo_path, task.id)
        task.front_image_path = images.get("front", "")
        task.iso_image_path = images.get("iso", "")
        task.hotspots = _build_hotspots(task.layout_hints, llm.get("style", ""))
        db.commit()

        _set_status(task, STATUS_REVIEW, 90, "生成完成，请审图")
        db.commit()
    except ServiceError as e:
        task = db.get(Task, task_id)
        if task:
            _set_failed(task, e.code, e.message)
            db.commit()
    except Exception:
        task = db.get(Task, task_id)
        if task:
            _set_failed(task, "TASK_FAILED", "处理失败，请重试")
            db.commit()
    finally:
        db.close()


def review_task(db: Session, task_id: str, action: str, score: int | None) -> bool:
    """审图。返回是否需要后台重新生成（reject 且未超上限）。"""
    task = db.get(Task, task_id)
    if not task or task.status != STATUS_REVIEW:
        raise ServiceError("INVALID_STATE", "任务不在待审状态")
    regenerate = False
    if action == "approve":
        task.review_score = score
        _set_status(task, STATUS_COMPLETED, 100, "审图通过")
    else:
        task.reject_count += 1
        if task.reject_count >= settings.max_regenerate_times:
            _set_failed(task, "REVIEW_REJECTED", f"已连续驳回 {task.reject_count} 次")
        else:
            _set_status(task, STATUS_UNDERSTANDING, 15, f"换风格重新生成（第 {task.reject_count} 次）")
            regenerate = True
    db.commit()
    return regenerate


def task_to_dict(task: Task) -> dict:
    step_details = {
        "understanding": {"completed": task.llm_result is not None, "result": task.llm_result},
        "rendering": {
            "completed": bool(task.front_image_path),
            "front_image_url": _img_url(task.front_image_path),
            "isometric_image_url": _img_url(task.iso_image_path),
        },
    }
    result = None
    if task.front_image_path and task.iso_image_path:
        result = {
            "front_image_url": _img_url(task.front_image_path),
            "isometric_image_url": _img_url(task.iso_image_path),
            "design_notes": task.design_notes or [],
            "hotspots": task.hotspots or [],
            "layout_hints": task.layout_hints or {},
        }
    error = None
    if task.status == STATUS_FAILED:
        error = {"code": task.error_code or "TASK_FAILED", "message": task.error_message or "处理失败"}
    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress,
        "current_step": task.current_step,
        "step_details": step_details,
        "result": result,
        "error": error,
        "user_input": task.user_input,
        "photo_url": _img_url(task.photo_path, "uploads"),
        "review_score": task.review_score,
        "reject_count": task.reject_count,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }
