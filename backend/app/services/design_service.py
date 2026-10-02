"""正面图编辑工作流：每次修改保留版本，确认后才生成 2.5D。"""
import os

from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.errors import ServiceError
from ..db import SessionLocal
from ..models import Design, DesignHotspot, DesignLayerSet, DesignReference, DesignVersion, HomeSpace
from . import image_service, llm_service


def _image_url(name: str) -> str:
    return f"/api/v1/files/generated/{name}" if name else ""


def _references(db: Session, design_id: str) -> list[DesignReference]:
    items = db.query(DesignReference).filter(DesignReference.design_id == design_id).all()
    return sorted(items, key=lambda item: 0 if item.kind == "style" else 1)


def _reference_context(db: Session, design_id: str, kinds: set[str] | None = None) -> tuple[list[str], str]:
    items = [item for item in _references(db, design_id) if kinds is None or item.kind in kinds]
    instructions = []
    for index, item in enumerate(items, start=2):
        role = "仅参考配色材质光线，不复制结构" if item.kind == "style" else "仅参考单件造型颜色"
        instructions.append(f"图{index}{'风格' if item.kind == 'style' else '家具'}参考：{role}。")
    return [item.photo_id for item in items], " ".join(instructions)


def _room_brief(db: Session, design: Design) -> str:
    """房间创建时固定共享风格；后改家庭设置不会悄悄重生旧房间。"""
    space = db.query(HomeSpace).filter(HomeSpace.design_id == design.id).first()
    return f"全屋共用风格约束：{space.style_snapshot}。本房间要求：{design.user_input}" if space and space.style_snapshot else design.user_input


def _image_room_brief(db: Session, design: Design) -> str:
    """生图保留用户原话和共享风格，只压缩固定连接词。"""
    space = db.query(HomeSpace).filter(HomeSpace.design_id == design.id).first()
    return f"全屋风格：{space.style_snapshot}。本房：{design.user_input}" if space and space.style_snapshot else design.user_input


def is_concept_view(db: Session, design: Design) -> bool:
    """局部编辑沿用当前机位；从原照片整图重做会回到原机位。"""
    marker = (db.query(DesignVersion.operation).filter(
        DesignVersion.design_id == design.id,
        DesignVersion.number <= design.current_version,
        DesignVersion.operation.in_(["initial", "regenerate", "concept_view"]),
    ).order_by(DesignVersion.number.desc()).first())
    return bool(marker and marker[0] == "concept_view")


_STRUCTURE_GUARD = (
    "图1为原房间，保留机位、墙面、门窗的数量与位置、梁柱、吊顶和地面边界；"
    "不要更换地面材质，除非用户明确要求。只改指定处，不新增门窗或挡窗；未要求则不加电视。"
)


def serialize_design(db: Session, design: Design) -> dict:
    versions = (
        db.query(DesignVersion)
        .filter(DesignVersion.design_id == design.id)
        .order_by(DesignVersion.number)
        .all()
    )
    hotspots = (
        db.query(DesignHotspot)
        .filter(
            DesignHotspot.design_id == design.id,
            DesignHotspot.iso_image_path == design.iso_image_path,
            DesignHotspot.front_version == design.current_version,
        )
        .order_by(DesignHotspot.created_at, DesignHotspot.id)
        .all()
        if design.iso_image_path and design.status == "completed" else []
    )
    layer_set = (db.query(DesignLayerSet).filter(
        DesignLayerSet.design_id == design.id,
        DesignLayerSet.front_version == design.current_version,
        DesignLayerSet.source_image_path == design.front_image_path,
    ).order_by(DesignLayerSet.created_at.desc(), DesignLayerSet.id.desc()).first())
    return {
        "design_id": design.id,
        "status": design.status,
        "current_step": design.current_step,
        "photo_url": f"/api/v1/files/uploads/{design.photo_path}",
        "references": {item.kind: f"/api/v1/files/uploads/{item.photo_id}" for item in _references(db, design.id)},
        "reference_ids": {item.kind: item.photo_id for item in _references(db, design.id)},
        "front_image_url": _image_url(design.front_image_path),
        "iso_image_url": _image_url(design.iso_image_path),
        "current_version": design.current_version,
        "is_concept_view": is_concept_view(db, design),
        "versions": [
            {
                "number": item.number,
                "image_url": _image_url(item.image_path),
                "operation": item.operation,
                "instruction": item.instruction,
            }
            for item in versions
        ],
        "hotspots": [
            {"id": item.id, "product_id": item.product_id, "x": item.x, "y": item.y}
            for item in hotspots
        ],
        "layer_set": ({
            "status": layer_set.status,
            "base_image_url": _image_url(layer_set.base_image_path) if layer_set.status == "ready" else "",
            "layers": [{
                "name": layer["name"], "description": layer["description"],
                "image_url": _image_url(layer["image_path"]),
                "box": layer["box"], "z_index": layer["z_index"],
            } for layer in (layer_set.layers or [])] if layer_set.status == "ready" else [],
            "error_message": layer_set.error_message,
        } if layer_set else None),
        "user_input": design.user_input,
        "design_notes": design.design_notes or [],
        "edit_history": design.edit_history or [],
        "error": {"code": design.error_code, "message": design.error_message} if design.error_code else None,
        "is_mock": not image_service.settings.has_ark_key,
        "created_at": design.created_at.isoformat() if design.created_at else "",
    }


def _run_initial(design_id: str) -> None:
    db = SessionLocal()
    try:
        design = db.get(Design, design_id)
        if not design:
            return
        design.status = "understanding"
        design.current_step = "AI 正在理解你的需求"
        db.commit()
        llm = llm_service.understand_room(_room_brief(db, design))
        design.design_notes = llm.get("design_notes") or []
        design.status = "rendering_front"
        design.current_step = "正在生成正面效果图"
        db.commit()
        # 生图以用户原话为准；LLM 的补充设计说明不能自行加入电视等大件。
        prompt = _STRUCTURE_GUARD + "用户明确要求：" + _image_room_brief(db, design)
        reference_names, reference_prompt = _reference_context(db, design.id)
        if reference_names:
            prompt = f"{reference_prompt} {prompt}"
            name = image_service.generate_design_front(prompt, design.photo_path, design.id, reference_names)
        else:
            name = image_service.generate_design_front(prompt, design.photo_path, design.id)
        design.front_image_path = name
        design.current_version = 1
        design.status = "front_ready"
        design.pending_job = None
        design.current_step = "正面效果图已生成，可以点选软装修改"
        db.add(DesignVersion(design_id=design.id, number=1, image_path=name))
        db.commit()
    except Exception:
        db.rollback()
        design = db.get(Design, design_id)
        if design:
            design.status = "failed"
            design.current_step = "生成失败"
            design.error_code = "DESIGN_FAILED"
            design.error_message = "正面效果图生成失败，请重新创建方案"
            design.pending_job = None
            db.commit()
    finally:
        db.close()


def edit_prompt(operation: str, x: float | None, y: float | None, detail: str, target: str = "") -> str:
    if operation == "style":
        return f"以图1为基础，将整个房间的软装风格调整为：{detail}。保留原房间结构、机位、窗户和主要建筑边界。"
    if x is None or y is None:
        raise ServiceError("POINT_REQUIRED", "请先点选要修改的物品")
    point = f"图1<point>{round(x * 999)} {round(y * 999)}</point>"
    instruction = {
        "delete": f"删除{point}处的软装物品。用户确认的删除目标：{detail or '所选软装物品'}。必须让该物品完全消失，补全它后面的墙面与地面，不要生成另一件同类物品填回原位。",
        "replace": f"将{point}处的软装物品替换为：{detail}。",
        "recolor": f"只把{point}处软装物品的颜色调整为：{detail}。目标物品本身应清楚呈现指定颜色，不要仅改变光照或让原色仍占主体；保留原有造型、材质纹理与位置。",
        "restore_structure": (
            f"修复{point}附近的房间结构错误：{detail}。"
            "图2是同一机位的原房间照片，只以图2核对墙体、门窗、梁柱、地面边界及透视。"
            "若图1出现图2没有的门窗或墙体开口，必须移除并恢复连续墙面；若原有门窗变形或移位，按图2复原。"
            "只修复用户指出的建筑结构区域，不照搬图2的旧家具、杂物、海报、窗帘或装修；保留图1现有的沙发和其他软装。"
        ),
    }.get(operation)
    if not instruction:
        raise ServiceError("INVALID_OPERATION", "不支持该修改方式")
    if operation == "restore_structure":
        return instruction + "其余区域保持图1现状，不要新增任何门窗、家具或装饰。"
    return target + instruction + "只修改目标物品及其接触阴影；保留其他家具的数量、位置、形状和颜色，保留墙体、门窗、地面、机位和光线，避免改动未选中的区域。"


def _run_edit(design_id: str, source_name: str, operation: str, x: float | None, y: float | None, detail: str, target: str = "", product_reference_path: str = "") -> None:
    db = SessionLocal()
    try:
        design = db.get(Design, design_id)
        if not design:
            return
        prompt = edit_prompt(operation, x, y, detail, target)
        if operation == "restore_structure":
            original_photo = os.path.join(settings.upload_dir, design.photo_path)
            name = image_service.edit_design_front(
                source_name, prompt, design.id, extra_reference_paths=[original_photo],
            )
        else:
            name = _edit_furnishing_image(db, design, source_name, operation, prompt, product_reference_path)
        next_version = (
            db.query(DesignVersion.number)
            .filter(DesignVersion.design_id == design.id)
            .order_by(DesignVersion.number.desc())
            .first()
        )
        number = (next_version[0] if next_version else 0) + 1
        db.add(DesignVersion(
            design_id=design.id, number=number, image_path=name,
            operation=operation, instruction=detail,
        ))
        design.front_image_path = name
        if design.iso_image_path:
            db.query(DesignHotspot).filter(DesignHotspot.design_id == design.id).delete()
        design.iso_image_path = ""
        design.current_version = number
        design.edit_history = [*(design.edit_history or []), {"version": number, "operation": operation, "detail": detail}]
        design.status = "front_ready"
        design.pending_job = None
        design.current_step = "修改已完成，可继续编辑或确认效果图"
        design.error_code = ""
        design.error_message = ""
        db.commit()
    except Exception:
        db.rollback()
        design = db.get(Design, design_id)
        if design:
            design.status = "front_ready"
            design.current_step = "修改未成功，原版本已保留"
            design.error_code = "EDIT_FAILED"
            design.error_message = "图片修改失败，原版本仍可使用，请重试"
            design.pending_job = None
            db.commit()
    finally:
        db.close()


def _edit_furnishing_image(db: Session, design: Design, source_name: str, operation: str, prompt: str, product_reference_path: str) -> str:
    """局部编辑以当前图为准；只传当前操作真正需要的参考图。"""
    if operation == "style":
        kinds = {"style"}
    elif operation == "replace" and not product_reference_path:
        kinds = {"furniture"}
    else:
        kinds = set()
    reference_names, reference_prompt = _reference_context(db, design.id, kinds=kinds)
    if product_reference_path:
        product_index = 2 + len(reference_names)
        product_prompt = (
            f"图{product_index}是用户选定的商品主图，以其轮廓、门板或扶手等可见结构、材质和颜色作为新物品依据。"
            "先移除图1所选的旧物，再把新商品以合理尺寸放回原位置；不要只把旧物改色或保留旧物的结构。"
            "其他家具不要照搬或移动。"
        )
        return image_service.edit_design_front(
            source_name, f"{reference_prompt} {product_prompt} {prompt}", design.id,
            reference_names, [product_reference_path],
        )
    if reference_names:
        return image_service.edit_design_front(source_name, f"{reference_prompt} {prompt}", design.id, reference_names)
    return image_service.edit_design_front(source_name, prompt, design.id)


def _run_regenerate(design_id: str, feedback: str, view_mode: str = "original", source_name: str = "") -> None:
    """原机位从原照片重做；概念机位从当前效果图转向新视角。"""
    db = SessionLocal()
    try:
        design = db.get(Design, design_id)
        if not design:
            return
        if view_mode == "concept":
            if not source_name:
                raise ServiceError("SOURCE_MISSING", "缺少当前效果图，不能切换示意视角")
            prompt = (
                "图1是已经生成的空间设计概念图。用户同意改变相机机位，展示原照片未完整拍到的墙面；"
                "本次输出是新视角的设计示意，不宣称与原户型和门窗位置精确一致。"
                "延续图1的沙发、茶几、地面材质和整体现代简洁气质，保持家具真实比例与空间动线。"
                f"新视角的具体设计要求：{feedback}。"
                "不要凭空添加与要求无关的门窗，不要让电视遮挡窗户。"
            )
            name = image_service.edit_design_front(source_name, prompt, design.id)
            operation = "concept_view"
        else:
            prompt = (
                _STRUCTURE_GUARD + "用户明确要求：" + _image_room_brief(db, design)
                + f"。本次修正：{feedback}。原照片决定建筑结构，旧版不作结构依据。"
            )
            reference_names, reference_prompt = _reference_context(db, design.id)
            if reference_names:
                name = image_service.generate_design_front(f"{reference_prompt} {prompt}", design.photo_path, design.id, reference_names)
            else:
                name = image_service.generate_design_front(prompt, design.photo_path, design.id)
            operation = "regenerate"
        last = db.query(DesignVersion.number).filter(
            DesignVersion.design_id == design.id
        ).order_by(DesignVersion.number.desc()).first()
        number = (last[0] if last else 0) + 1
        db.add(DesignVersion(
            design_id=design.id, number=number, image_path=name,
            operation=operation, instruction=feedback,
        ))
        if design.iso_image_path:
            db.query(DesignHotspot).filter(DesignHotspot.design_id == design.id).delete()
        design.front_image_path = name
        design.iso_image_path = ""
        design.current_version = number
        design.edit_history = [*(design.edit_history or []), {"version": number, "operation": operation, "detail": feedback}]
        design.status = "front_ready"
        design.pending_job = None
        design.current_step = "新视角示意图已生成，请核对电视墙设计" if operation == "concept_view" else "新版效果图已生成，请查看反馈是否得到修正"
        design.error_code = ""
        design.error_message = ""
        db.commit()
    except Exception:
        db.rollback()
        design = db.get(Design, design_id)
        if design:
            design.status = "completed" if design.iso_image_path else "front_ready"
            design.pending_job = None
            design.current_step = "重新生成未成功，旧版仍可使用"
            design.error_code = "REGENERATE_FAILED"
            design.error_message = "重新生成失败，旧版已保留，请稍后重试"
            db.commit()
    finally:
        db.close()


def _run_iso(design_id: str, source_name: str) -> None:
    db = SessionLocal()
    try:
        design = db.get(Design, design_id)
        if not design:
            return
        prompt = (
            "把图1当前已确认的房间重构成完整可见的微缩房间模型，采用严格的 2.5D 等距轴测投影。"
            "三维空间的平行线在画面中仍须平行，没有透视消失点，不要做室内摄影式的斜俯拍。"
            "呈现地板、两面剖开的墙和完整家具布局。沙发、灯具、绿植、柜子等的数量、颜色和材质严格沿用图1，"
            "尤其不能把已改色的家具变回原色。画面干净、结构合理。"
        )
        name = image_service.generate_design_iso(source_name, prompt, design.id)
        design.iso_image_path = name
        design.status = "completed"
        design.pending_job = None
        design.current_step = "2.5D 方案已生成"
        design.error_code = ""
        design.error_message = ""
        db.commit()
    except Exception:
        db.rollback()
        design = db.get(Design, design_id)
        if design:
            design.status = "front_ready"
            design.current_step = "2.5D 生成失败，正面图仍可编辑"
            design.error_code = "ISO_FAILED"
            design.error_message = "2.5D 生成失败，请重新确认效果图"
            design.pending_job = None
            db.commit()
    finally:
        db.close()
