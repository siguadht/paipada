"""将已核查的真实效果图及图层装入演示用户的独立候选方案。

保留原方案和全部历史；新图标成候选，不代替产品经理审图确认。
默认只校验；--install 才会备份数据库并插入一条新方案。
"""

import argparse
import json
import shutil
import sqlite3
import uuid
from pathlib import Path

from app.core.config import settings
from app.db import SessionLocal
from app.models import Design, DesignLayerSet, DesignVersion, Photo


PROJECT = Path(__file__).resolve().parents[2]
SOURCE_PHOTO = "5dd26281-5f98-46d9-a98b-515d66f3129e.jpg"
LAYER_RECORD = PROJECT / "data/qa-final-demo-finish-20261002/layers.json"
DESIGN_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, "paipaida/local-demo-candidate/2026-10-02"))
FRONT_NAME = f"{DESIGN_ID}_front_20261002.jpg"
LAYER_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL, "paipaida/local-demo-layers/2026-10-02"))
LAYER_SET_ID = LAYER_UUID
BASE_NAME = f"{LAYER_UUID}_base.png"


def materialize(record: dict) -> list[dict]:
    """用受保护图片接口接受的文件名存放候选，不覆盖源证据。"""
    generated = Path(settings.generated_dir)
    pairs = [(record["source"], FRONT_NAME), (record["base"], BASE_NAME)]
    layers = []
    for index, layer in enumerate(record["layers"]):
        renamed = dict(layer)
        renamed["image_path"] = f"{LAYER_UUID}_layer_{index}.png"
        layers.append(renamed)
        pairs.append((layer["image_path"], renamed["image_path"]))
    for source, target in pairs:
        source_path, target_path = generated / source, generated / target
        if not target_path.exists():
            shutil.copy2(source_path, target_path)
    return layers


def validate(db) -> dict:
    record = json.loads(LAYER_RECORD.read_text(encoding="utf-8"))
    if record.get("state") != "completed" or len(record.get("layers") or []) < 5:
        raise ValueError("真实拆层未就绪，不能把候选装入项目")
    if record.get("source") != "qa-final-demo-20261002-front.jpg":
        raise ValueError("图层与候选正面图不匹配")
    photo = db.get(Photo, SOURCE_PHOTO)
    if not photo or not photo.user_id:
        raise ValueError("原房间照片或归属不存在")
    for name in [record["source"], record["base"], *(item["image_path"] for item in record["layers"])]:
        if not (Path(settings.generated_dir) / name).is_file():
            raise FileNotFoundError(f"候选文件缺失：{name}")
    return {"record": record, "user_id": photo.user_id}


def install() -> str:
    with SessionLocal() as db:
        checked = validate(db)
        db_file = PROJECT / "data/app.db"
        backup = PROJECT / "data/backup-before-demo-candidate-20261002.db"
        if not backup.exists():
            with sqlite3.connect(db_file) as source, sqlite3.connect(backup) as destination:
                source.backup(destination)
        record = checked["record"]
        layers = materialize(record)
        existing = db.get(Design, DESIGN_ID)
        if existing:
            existing.front_image_path = FRONT_NAME
            existing.design_notes = [
                "第 01 张正面图已获产品经理最终演示画质验收；第 02 张留作备选，第 03 张淘汰。",
                "画面里的 15 件软装已有独立图层，可悬停选择；修改图像会产生新的模型调用费用。",
                "这张图对应的 2.5D 尚未通过验收，不要将此前带斜屋顶的测试图当作正式方案。",
            ]
            version = db.query(DesignVersion).filter(
                DesignVersion.design_id == DESIGN_ID, DesignVersion.number == 1
            ).one()
            version.image_path = FRONT_NAME
            layer_set = db.get(DesignLayerSet, LAYER_SET_ID) or db.get(DesignLayerSet, "qa-final-demo-20261002")
            layer_set.id = LAYER_SET_ID
            layer_set.source_image_path = FRONT_NAME
            layer_set.base_image_path = BASE_NAME
            layer_set.layers = layers
            db.commit()
            return DESIGN_ID
        db.add(Design(
            id=DESIGN_ID,
            user_id=checked["user_id"],
            photo_path=SOURCE_PHOTO,
            user_input="演示候选：把原房间改成真实、精致的现代原木客厅，保留窗与机位；软装以沙发、单椅、茶几、地毯、灯和绿植为主。",
            status="front_ready",
            current_step="真实效果图候选已就绪，待产品经理核对后再确认 2.5D",
            front_image_path=FRONT_NAME,
            iso_image_path="",
            current_version=1,
            design_notes=[
                "第 01 张正面图已获产品经理最终演示画质验收；第 02 张留作备选，第 03 张淘汰。",
                "画面里的 15 件软装已有独立图层，可悬停选择；修改图像会产生新的模型调用费用。",
                "这张图对应的 2.5D 尚未通过验收，不要将此前带斜屋顶的测试图当作正式方案。",
            ],
            edit_history=[],
        ))
        db.add(DesignVersion(
            design_id=DESIGN_ID,
            number=1,
            image_path=FRONT_NAME,
            operation="initial",
            instruction="三张真实候选中选出的第 01 张，非最终确认图",
        ))
        db.add(DesignLayerSet(
            id=LAYER_SET_ID,
            design_id=DESIGN_ID,
            front_version=1,
            source_image_path=FRONT_NAME,
            status="ready",
            base_image_path=BASE_NAME,
            layers=layers,
            error_message="",
        ))
        db.commit()
    return DESIGN_ID


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true", help="备份数据库并创建独立候选方案")
    args = parser.parse_args()
    if args.install:
        print(f"独立演示候选方案：{install()}")
    else:
        with SessionLocal() as db:
            checked = validate(db)
        print(f"离线检查通过：{len(checked['record']['layers'])} 件软装；未写入数据库")


if __name__ == "__main__":
    main()
