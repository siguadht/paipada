"""仅在产品经理明确通过某张 2.5D 后，将它装入已验收正面图方案。

默认只读。--install N 是有状态写入：先备份 SQLite，再复制图并更新独立演示方案。
"""

import argparse
import json
import shutil
import sqlite3
import uuid
from pathlib import Path

from PIL import Image

from app.core.config import settings
from app.db import SessionLocal
from app.models import Design
from scripts.install_demo_candidate import DESIGN_ID, FRONT_NAME


PROJECT = Path(__file__).resolve().parents[2]
OUTPUT = PROJECT / "data/qa-final-demo-finish-20261002"


def check(number: int) -> tuple[Path, str]:
    marker = OUTPUT / f"iso-guided-{number}.json"
    source = OUTPUT / f"iso-guided-{number}.jpg"
    if not marker.exists() or json.loads(marker.read_text(encoding="utf-8")).get("state") != "completed":
        raise ValueError("该变体没有完成真实生图")
    with Image.open(source) as image:
        image.verify()
    suffix = uuid.uuid5(uuid.NAMESPACE_URL, f"paipaida/accepted-iso/{DESIGN_ID}/{number}").hex[:8]
    return source, f"{DESIGN_ID}_iso_{suffix}.jpg"


def install(number: int) -> str:
    source, filename = check(number)
    with SessionLocal() as db:
        design = db.get(Design, DESIGN_ID)
        if not design or design.front_image_path != FRONT_NAME or design.current_version != 1:
            raise ValueError("正面图版本已变化，不能安装不对应的 2.5D")
        if design.iso_image_path and design.iso_image_path != filename:
            raise ValueError("方案已有其他 2.5D，不覆盖")
        backup = PROJECT / f"data/backup-before-accepted-iso-{number}-20261002.db"
        if not backup.exists():
            with sqlite3.connect(PROJECT / "data/app.db") as origin, sqlite3.connect(backup) as target:
                origin.backup(target)
        destination = Path(settings.generated_dir) / filename
        if not destination.exists():
            shutil.copy2(source, destination)
        design.iso_image_path = filename
        design.status = "completed"
        design.current_step = "已通过验收的 2.5D 与正面图第 1 版对应"
        design.design_notes = list(design.design_notes or []) + [f"第 {number} 张结构引导 2.5D 已由产品经理验收。"]
        db.commit()
    return filename


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", type=int, choices=(1, 2, 3), help="仅在产品经理验收该变体后执行")
    args = parser.parse_args()
    if args.install:
        print(f"已接入经确认的 2.5D：{install(args.install)}")
    else:
        print("尚未安装 2.5D：等待真实生成和产品经理审图")


if __name__ == "__main__":
    main()
