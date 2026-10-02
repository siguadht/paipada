"""离线准备卧室局部重绘输入；只写本地文件，不调用云接口。

用法：cd backend && .venv/bin/python -m scripts.prepare_bedroom_inpaint
遮罩坐标直接读取已验收的 HTML 样稿，避免维护两套手绘轮廓。
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / "docs/evidence/阶段3-2/真实双空间/卧室-原图.jpg"
PROTOTYPE = PROJECT / "docs/evidence/非上线收口/卧室门窗保护遮罩原型.html"
OUTPUT = PROJECT / "data/qa-bedroom-inpaint-20261002"
MAX_SIDE = 4096
MAX_BYTES = 4_700_000
SVG_SIZE = (1920, 1280)


def polygons_from_prototype(html: str) -> list[tuple[str, list[tuple[float, float]]]]:
    matches = re.findall(r'<polygon\s+data-name="([^"]+)"\s+points="([^"]+)"', html)
    if len(matches) != 5:
        raise ValueError("门窗轮廓必须恰好有五个：房门、远窗、右墙三窗")
    result = []
    for name, raw_points in matches:
        points = [tuple(map(float, pair.split(","))) for pair in raw_points.split()]
        if len(points) < 3 or any(not 0 <= x <= SVG_SIZE[0] or not 0 <= y <= SVG_SIZE[1] for x, y in points):
            raise ValueError(f"无效的门窗轮廓：{name}")
        result.append((name, points))
    return result


def prepare(source: Path = SOURCE, prototype: Path = PROTOTYPE, output: Path = OUTPUT) -> tuple[Path, Path]:
    shapes = polygons_from_prototype(prototype.read_text(encoding="utf-8"))
    with Image.open(source) as opened:
        photo = ImageOps.exif_transpose(opened).convert("RGB")
    photo.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    if min(photo.size) < 64:
        raise ValueError("原图缩放后尺寸不足")

    # 严格结构试验：只放开床、床头柜和地毯可占的左墙下半部与地面。
    # 上部吊顶及其余墙面始终保留，降低局部重绘重新安排窗户的空间。
    mask = Image.new("L", photo.size, 0)
    draw = ImageDraw.Draw(mask)
    editable = [(285, 480), (540, 480), (560, 760), (1920, 880), (1920, 1280), (230, 1280)]
    draw.polygon([(round(x * photo.width / SVG_SIZE[0]), round(y * photo.height / SVG_SIZE[1])) for x, y in editable], fill=255)
    for _, points in shapes:
        scaled = [(round(x * photo.width / SVG_SIZE[0]), round(y * photo.height / SVG_SIZE[1])) for x, y in points]
        draw.polygon(scaled, fill=0)

    output.mkdir(parents=True, exist_ok=True)
    photo_path = output / "卧室原图-接口尺寸.jpg"
    mask_path = output / "卧室门窗保护-单通道遮罩.png"
    photo.save(photo_path, "JPEG", quality=88, optimize=True)
    mask.save(mask_path, "PNG", optimize=True)
    if any(path.stat().st_size > MAX_BYTES for path in (photo_path, mask_path)):
        raise ValueError("原图或遮罩超过接口 4.7 MB 限制")
    return photo_path, mask_path


if __name__ == "__main__":
    photo_path, mask_path = prepare()
    with Image.open(photo_path) as photo, Image.open(mask_path) as mask:
        print(f"离线输入已就绪：{photo.size}，遮罩模式 {mask.mode}")
        print(f"原图：{photo_path}")
        print(f"遮罩：{mask_path}")
        print("未提交云端任务，也未开启新服务")
