"""可编辑方案 API；图片编辑和 2.5D 生成均是持久化后台任务。"""
import os
import re
import json
import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.config import PROJECT_ROOT, settings
from ..core.errors import api_error
from ..db import get_db
from ..models import Design, DesignHotspot, DesignLayerSet, DesignReference, DesignStructureReview, DesignVersion, Home, HomeSpace, Photo
from ..services.design_service import _run_edit, _run_initial, _run_iso, _run_regenerate, is_concept_view, serialize_design
from ..services.layer_service import run_layer_set
from .deps import get_current_user_id

router = APIRouter(tags=["designs"])
_PHOTO_RE = re.compile(r"^[0-9a-f-]{36}\.(jpg|png|webp)$")
_PRODUCTS = Path(__file__).resolve().parents[1] / "data" / "products.json"
_DEMO_PRODUCTS = Path(__file__).resolve().parents[1] / "data" / "demo_products.json"


def _catalog_products() -> list[dict]:
    products = json.loads(_PRODUCTS.read_text(encoding="utf-8"))
    if settings.demo_product_catalog:
        products.extend(json.loads(_DEMO_PRODUCTS.read_text(encoding="utf-8")))
    return products


class DesignCreate(BaseModel):
    photo_id: str
    user_input: str = Field(min_length=1, max_length=200)
    style_photo_id: str | None = None
    furniture_photo_id: str | None = None
    home_id: str | None = None
    room_name: str | None = Field(default=None, min_length=1, max_length=40)
    cost_confirmed: bool = False


class ReferenceUpdate(BaseModel):
    style_photo_id: str | None = None
    furniture_photo_id: str | None = None


class EditRequest(BaseModel):
    operation: Literal["delete", "replace", "recolor", "style", "restore_structure"]
    x: float | None = Field(default=None, ge=0, le=1)
    y: float | None = Field(default=None, ge=0, le=1)
    detail: str = Field(default="", max_length=200)
    layer_index: int | None = Field(default=None, ge=0, le=15)
    product_id: str | None = Field(default=None, min_length=1, max_length=32)


class RegenerateRequest(BaseModel):
    feedback: str = Field(min_length=1, max_length=200)
    view_mode: Literal["original", "concept"] = "original"


class LayerRequest(BaseModel):
    cost_confirmed: bool = False


class StructureReview(BaseModel):
    mode: Literal["original", "concept"]
    doors_windows: bool = False
    walls_floor: bool = False
    camera_layout: bool = False
    concept_acknowledged: bool = False


class ConfirmRequest(BaseModel):
    review: StructureReview


class HotspotCreate(BaseModel):
    product_id: str = Field(min_length=1, max_length=32)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


def _owned(db: Session, design_id: str, user_id: int) -> Design:
    design = db.get(Design, design_id)
    if not design or design.user_id != user_id:
        raise api_error(404, "DESIGN_NOT_FOUND", "方案不存在")
    return design


def _owned_photo(db: Session, photo_id: str, user_id: int) -> Photo:
    if not _PHOTO_RE.fullmatch(photo_id):
        raise api_error(400, "INVALID_PHOTO", "照片标识无效")
    photo = db.get(Photo, photo_id)
    if not photo or photo.user_id != user_id or not os.path.isfile(os.path.join(settings.upload_dir, photo.id)):
        raise api_error(404, "PHOTO_NOT_FOUND", "照片不存在，请重新上传")
    return photo


def _replace_references(db: Session, design_id: str, payload: ReferenceUpdate, user_id: int) -> None:
    refs = (("style", payload.style_photo_id), ("furniture", payload.furniture_photo_id))
    for _, photo_id in refs:
        if photo_id:
            _owned_photo(db, photo_id, user_id)
    db.query(DesignReference).filter(DesignReference.design_id == design_id).delete()
    for kind, photo_id in refs:
        if photo_id:
            db.add(DesignReference(design_id=design_id, kind=kind, photo_id=photo_id))


@router.get("/products")
def list_products(user_id: int = Depends(get_current_user_id)):
    """演示模式返回经核对来源的商品；常规模式保持原有示意资料。"""
    return {"products": _catalog_products()}


@router.post("", status_code=201)
def create_design(
    payload: DesignCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    photo = _owned_photo(db, payload.photo_id, user_id)
    home = None
    room_name = (payload.room_name or "").strip()
    if payload.home_id:
        home = db.get(Home, payload.home_id)
        if not home or home.user_id != user_id:
            raise api_error(404, "HOME_NOT_FOUND", "家庭项目不存在")
        if not room_name:
            raise api_error(400, "ROOM_NAME_REQUIRED", "请填写空间名称")
        if not payload.cost_confirmed:
            raise api_error(400, "COST_CONFIRMATION_REQUIRED", "请先确认本次空间生成费用")
    elif room_name:
        raise api_error(400, "HOME_REQUIRED", "请先选择家庭项目")
    for photo_id in (payload.style_photo_id, payload.furniture_photo_id):
        if photo_id:
            _owned_photo(db, photo_id, user_id)
    design = Design(user_id=user_id, photo_path=photo.id, user_input=payload.user_input.strip())
    db.add(design)
    db.flush()
    style_photo_id = payload.style_photo_id or (home.style_photo_id if home else None)
    _replace_references(db, design.id, ReferenceUpdate(style_photo_id=style_photo_id, furniture_photo_id=payload.furniture_photo_id), user_id)
    if home:
        count = db.query(HomeSpace.id).filter(HomeSpace.home_id == home.id).count()
        db.add(HomeSpace(home_id=home.id, design_id=design.id, name=room_name, style_snapshot=home.style_text, position=count))
    db.commit()
    db.refresh(design)
    background_tasks.add_task(_run_initial, design.id)
    return serialize_design(db, design)


@router.put("/{design_id}/references")
def update_references(
    design_id: str,
    payload: ReferenceUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    design = _owned(db, design_id, user_id)
    if design.status not in ("front_ready", "completed"):
        raise api_error(409, "INVALID_STATE", "请等待当前生成结束后再更换参考图")
    _replace_references(db, design.id, payload, user_id)
    db.commit()
    return serialize_design(db, design)


@router.get("")
def list_designs(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    designs = (
        db.query(Design).filter(Design.user_id == user_id)
        .order_by(Design.created_at.desc()).limit(50).all()
    )
    return {"designs": [serialize_design(db, item) for item in designs]}


@router.get("/{design_id}")
def get_design(design_id: str, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return serialize_design(db, _owned(db, design_id, user_id))


@router.post("/{design_id}/layers", status_code=202)
def prepare_layers(
    design_id: str,
    payload: LayerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    design = _owned(db, design_id, user_id)
    if design.status not in ("front_ready", "completed") or not design.front_image_path:
        raise api_error(409, "INVALID_STATE", "请等待当前效果图生成完成")
    existing = db.query(DesignLayerSet).filter(
        DesignLayerSet.design_id == design.id,
        DesignLayerSet.front_version == design.current_version,
        DesignLayerSet.source_image_path == design.front_image_path,
    ).order_by(DesignLayerSet.created_at.desc(), DesignLayerSet.id.desc()).first()
    if existing and existing.status in ("queued", "processing", "ready"):
        return serialize_design(db, design)
    if not payload.cost_confirmed:
        raise api_error(400, "COST_CONFIRMATION_REQUIRED", "请先确认本版图层拆分可能产生的费用")
    if not settings.has_ark_key or not settings.ark_image_model:
        raise api_error(503, "MODEL_UNAVAILABLE", "图层拆分模型尚未配置")
    layer_set = DesignLayerSet(
        design_id=design.id, front_version=design.current_version,
        source_image_path=design.front_image_path, status="queued",
    )
    db.add(layer_set)
    db.commit()
    background_tasks.add_task(run_layer_set, layer_set.id)
    return serialize_design(db, design)


@router.post("/{design_id}/hotspots", status_code=201)
def add_hotspot(
    design_id: str,
    payload: HotspotCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    design = _owned(db, design_id, user_id)
    if design.status != "completed" or not design.iso_image_path:
        raise api_error(409, "INVALID_STATE", "请先生成 2.5D 图片")
    product_ids = {item["id"] for item in _catalog_products()}
    if payload.product_id not in product_ids:
        raise api_error(400, "PRODUCT_NOT_FOUND", "参考商品不存在")
    count = db.query(DesignHotspot.id).filter(
        DesignHotspot.design_id == design.id,
        DesignHotspot.iso_image_path == design.iso_image_path,
        DesignHotspot.front_version == design.current_version,
    ).count()
    if count >= 8:
        raise api_error(409, "HOTSPOT_LIMIT", "一张图最多标注 8 个商品")
    hotspot = DesignHotspot(
        design_id=design.id, iso_image_path=design.iso_image_path,
        front_version=design.current_version, product_id=payload.product_id,
        x=payload.x, y=payload.y, created_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
    )
    db.add(hotspot)
    db.commit()
    result = serialize_design(db, design)
    result["added_hotspot_id"] = hotspot.id
    return result


@router.delete("/{design_id}/hotspots/{hotspot_id}")
def delete_hotspot(
    design_id: str,
    hotspot_id: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    design = _owned(db, design_id, user_id)
    hotspot = db.get(DesignHotspot, hotspot_id)
    if not hotspot or hotspot.design_id != design.id or hotspot.iso_image_path != design.iso_image_path or hotspot.front_version != design.current_version:
        raise api_error(404, "HOTSPOT_NOT_FOUND", "热点不存在")
    db.delete(hotspot)
    db.commit()
    return serialize_design(db, design)


@router.post("/{design_id}/edits", status_code=202)
def edit_design(
    design_id: str,
    payload: EditRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    design = _owned(db, design_id, user_id)
    if design.status not in ("front_ready", "completed") or not design.front_image_path:
        raise api_error(409, "INVALID_STATE", "当前不能修改方案，请等待生成完成")
    edit_count = db.query(DesignVersion.id).filter(
        DesignVersion.design_id == design.id, DesignVersion.operation != "initial"
    ).count()
    if edit_count >= settings.max_design_edits:
        raise api_error(409, "EDIT_LIMIT", "当前方案已达到修改次数上限，请新建方案")
    detail = payload.detail.strip()
    if payload.operation != "style" and (payload.x is None or payload.y is None):
        raise api_error(400, "POINT_REQUIRED", "请先点选要修改的物品")
    if payload.operation in ("replace", "recolor", "style", "restore_structure") and not detail:
        raise api_error(400, "DETAIL_REQUIRED", "请写清要修改的地方和目标效果")
    if payload.operation == "restore_structure" and payload.layer_index is not None:
        raise api_error(400, "INVALID_LAYER_OPERATION", "房间结构修正请直接点选错误位置")
    if payload.product_id and payload.operation != "replace":
        raise api_error(400, "INVALID_PRODUCT_OPERATION", "商品参考只能用于替换软装")
    product_reference_path = ""
    if payload.product_id:
        product = next((item for item in _catalog_products() if item["id"] == payload.product_id), None)
        if not product:
            raise api_error(400, "PRODUCT_NOT_FOUND", "所选商品已不可用，请重新选择")
        detail = f"选定商品：{product['brand']} {product['name']}，颜色 {product['color']}。用户补充：{detail}"
        if product.get("demo_only"):
            image_url = product.get("image_url", "")
            if not re.fullmatch(r"/demo-products/[A-Za-z0-9_-]+\.(?:jpg|png|webp)", image_url):
                raise api_error(503, "PRODUCT_IMAGE_UNAVAILABLE", "商品参考图不可用，请重新选择")
            product_reference_path = str(PROJECT_ROOT / "frontend" / "public" / image_url.lstrip("/"))
            if not os.path.isfile(product_reference_path):
                raise api_error(503, "PRODUCT_IMAGE_UNAVAILABLE", "商品参考图不可用，请重新选择")
    target = ""
    if payload.layer_index is not None and payload.operation != "style":
        layer_set = db.query(DesignLayerSet).filter(
            DesignLayerSet.design_id == design.id,
            DesignLayerSet.front_version == design.current_version,
            DesignLayerSet.source_image_path == design.front_image_path,
            DesignLayerSet.status == "ready",
        ).order_by(DesignLayerSet.created_at.desc(), DesignLayerSet.id.desc()).first()
        if not layer_set or payload.layer_index >= len(layer_set.layers or []):
            raise api_error(409, "LAYER_EXPIRED", "家具图层与当前版本不匹配，请刷新页面")
        layer = layer_set.layers[payload.layer_index]
        box = [round(value * 999) for value in layer["box"]]
        target = f"目标是{layer['name']}的完整轮廓<bbox>{' '.join(map(str, box))}</bbox>。"
    source_name = design.front_image_path
    design.status = "editing"
    design.pending_job = {
        "kind": "edit", "source_name": source_name, "operation": payload.operation,
        "x": payload.x, "y": payload.y, "detail": detail, "target": target,
        "product_reference_path": product_reference_path,
    }
    design.current_step = "正在修改效果图，原版本已保存"
    design.error_code = ""
    design.error_message = ""
    db.commit()
    background_tasks.add_task(_run_edit, design.id, source_name, payload.operation, payload.x, payload.y, detail, target, product_reference_path)
    return serialize_design(db, design)


@router.post("/{design_id}/regenerate", status_code=202)
def regenerate_design(
    design_id: str,
    payload: RegenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    design = _owned(db, design_id, user_id)
    if design.status not in ("front_ready", "completed") or not design.front_image_path:
        raise api_error(409, "INVALID_STATE", "请等待当前生成完成")
    feedback = payload.feedback.strip()
    if not feedback:
        raise api_error(400, "FEEDBACK_REQUIRED", "请描述上一版哪里不满意")
    edit_count = db.query(DesignVersion.id).filter(
        DesignVersion.design_id == design.id, DesignVersion.operation != "initial"
    ).count()
    if edit_count >= settings.max_design_edits:
        raise api_error(409, "EDIT_LIMIT", "当前方案已达到修改次数上限，请新建方案")
    design.status = "editing"
    source_name = design.front_image_path if payload.view_mode == "concept" else ""
    design.pending_job = {"kind": "regenerate", "feedback": feedback, "view_mode": payload.view_mode, "source_name": source_name}
    design.current_step = "正在生成新机位概念效果图，旧版已保存" if payload.view_mode == "concept" else "正在根据反馈从原照片重新生成，旧版已保存"
    design.error_code = ""
    design.error_message = ""
    db.commit()
    background_tasks.add_task(_run_regenerate, design.id, feedback, payload.view_mode, source_name)
    return serialize_design(db, design)


@router.post("/{design_id}/versions/{number}/restore")
def restore_version(
    design_id: str,
    number: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    design = _owned(db, design_id, user_id)
    if design.status not in ("front_ready", "completed"):
        raise api_error(409, "INVALID_STATE", "请等待当前生成完成")
    version = (
        db.query(DesignVersion)
        .filter(DesignVersion.design_id == design.id, DesignVersion.number == number)
        .first()
    )
    if not version:
        raise api_error(404, "VERSION_NOT_FOUND", "该版本不存在")
    if design.current_version == version.number:
        # 重复选择当前版本不改变方案，尤其不能丢掉已付费生成的 2.5D。
        return serialize_design(db, design)
    design.front_image_path = version.image_path
    db.query(DesignHotspot).filter(DesignHotspot.design_id == design.id).delete()
    design.current_version = version.number
    design.iso_image_path = ""
    design.status = "front_ready"
    design.current_step = f"已恢复到第 {number} 版"
    db.commit()
    return serialize_design(db, design)


@router.post("/{design_id}/confirm", status_code=202)
def confirm_front(
    design_id: str,
    background_tasks: BackgroundTasks,
    payload: ConfirmRequest | None = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    design = _owned(db, design_id, user_id)
    if design.status != "front_ready" or not design.front_image_path:
        raise api_error(409, "INVALID_STATE", "请先完成正面效果图")
    if payload:
        review = payload.review
        expected_mode = "concept" if is_concept_view(db, design) else "original"
        if review.mode != expected_mode:
            raise api_error(400, "STRUCTURE_REVIEW_MODE_MISMATCH", "当前图片的机位已变化，请重新核对")
        if expected_mode == "original" and not (review.doors_windows and review.walls_floor and review.camera_layout):
            raise api_error(400, "STRUCTURE_REVIEW_INCOMPLETE", "请先对照原照片核对门窗、墙地面和机位")
        if expected_mode == "concept" and not review.concept_acknowledged:
            raise api_error(400, "STRUCTURE_REVIEW_INCOMPLETE", "请先确认这是新机位示意图")
        db.add(DesignStructureReview(
            design_id=design.id,
            front_version=design.current_version,
            source_image_path=design.front_image_path,
            mode=review.mode,
            checks=review.model_dump(exclude={"mode"}),
        ))
    source_name = design.front_image_path
    design.status = "rendering_iso"
    design.pending_job = {"kind": "iso", "source_name": source_name}
    design.current_step = "正在根据已确认效果图生成 2.5D 方案"
    design.error_code = ""
    design.error_message = ""
    db.commit()
    background_tasks.add_task(_run_iso, design.id, source_name)
    return serialize_design(db, design)
