"""只对已生成的候选 01 做一次性改色、2.5D 和图层验证。

默认离线检查。每个付费操作必须显式指定，且任务标记先于网络请求落盘。
输出保留在隔离目录；不会覆盖正式方案或自动发布为最终产品演示。
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import time
from pathlib import Path

import httpx
from PIL import Image

from app.core.config import settings
from app.services import storage_service
from app.services.layer_service import _decompose
from scripts.qa_final_demo_candidates import OUTPUT as CANDIDATES


PROJECT = Path(__file__).resolve().parents[2]
OUTPUT = PROJECT / "data/qa-final-demo-finish-20261002"
SOURCE = CANDIDATES / "candidate-01.jpg"
RECOLOR_PROMPT = (
    "以输入的客厅效果图为唯一空间基底。只把画面左侧米白布艺三人沙发改成深橄榄绿织物沙发，"
    "保留沙发形状、靠垫数量、体积、位置与投影；窗、窗帘、电视、木柜、茶几、地毯、墙和机位保持不变。"
    "颜色要清晰可见，织物纹理和褶皱真实，不要改变整个画面的色调。无文字水印。"
)
ISO_PROMPT = (
    "参照输入的客厅效果图绘制这同一间房的 2.5D 等距轴测示意。保留浅木、米白、米灰配色，"
    "包括左侧沙发、单椅、木茶几、地毯、电视墙、落地电视柜、窗帘、落地灯和绿植。"
    "以完整房间剖开的等距俯视视角展示家具相对位置，不要文字、水印或额外房间。"
)
ISO_CORRECTION_PROMPT = (
    "参照输入客厅正面图绘制同一间现代公寓的 2.5D 正交等距剖面。"
    "这是平层房间，顶部完全敞开，只画直立的半高墙和矩形地板；绝对不要三角屋顶、斜屋顶、阁楼或房屋外立面。"
    "左墙有米白沙发与落地灯，中央是木茶几和浅色地毯，窗旁有单椅与绿植，右墙是电视、木饰面及贴地电视柜。"
    "布局和浅木米白材质来自输入图，家具完整可见。无文字水印。"
)


def validate() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError("候选 01 尚未生成")
    with Image.open(SOURCE) as image:
        image.verify()
    if not settings.ark_api_key or not settings.ark_image_model:
        raise RuntimeError("缺少真实图像模型配置，不使用 mock 图")
    if max(map(len, (RECOLOR_PROMPT, ISO_PROMPT, ISO_CORRECTION_PROMPT))) > 300:
        raise ValueError("后续提示词超出 300 字")


def one_shot(kind: str, prompt: str, size: str) -> Path:
    validate()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    marker = OUTPUT / f"{kind}.json"
    target = OUTPUT / f"{kind}.jpg"
    if marker.exists():
        raise RuntimeError("该步骤已提交或结果不明，不自动重试")
    source_key = f"qa-final-demo-20261002/{kind}-source.jpg"
    storage_service.upload_file(str(SOURCE), source_key)
    try:
        source_url = storage_service.presigned_url(source_key, expires=3600)
        with marker.open("x", encoding="utf-8") as handle:
            json.dump({"state": "submission_attempted", "created_at": int(time.time())}, handle)
        response = httpx.post(
            f"{settings.ark_base_url}/images/generations",
            headers={"Authorization": f"Bearer {settings.ark_api_key}", "Content-Type": "application/json"},
            json={
                "model": settings.ark_image_model,
                "image": source_url,
                "prompt": prompt,
                "size": size,
                "response_format": "url",
                "watermark": False,
            },
            timeout=240,
        )
        if response.status_code != 200:
            marker.write_text(json.dumps({"state": "submission_failed_or_unknown", "http_status": response.status_code}), encoding="utf-8")
            raise RuntimeError(f"{kind} 没有成功响应；不自动重试")
        data = response.json().get("data") or []
        if len(data) != 1 or not isinstance(data[0].get("url"), str):
            raise RuntimeError(f"{kind} 响应格式异常；不自动重试")
        result = httpx.get(data[0]["url"], timeout=60)
        result.raise_for_status()
        with Image.open(io.BytesIO(result.content)) as image:
            image.convert("RGB").save(target, "JPEG", quality=94)
        marker.write_text(json.dumps({"state": "completed", "result": target.name}), encoding="utf-8")
        return target
    finally:
        storage_service.delete_object(source_key)


def split_once() -> dict:
    validate()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    marker = OUTPUT / "layers.json"
    if marker.exists():
        raise RuntimeError("整件拆层已提交或结果不明，不自动重试")
    source_name = "qa-final-demo-20261002-front.jpg"
    generated_source = Path(settings.generated_dir) / source_name
    generated_source.parent.mkdir(parents=True, exist_ok=True)
    if not generated_source.exists():
        shutil.copy2(SOURCE, generated_source)
    with marker.open("x", encoding="utf-8") as handle:
        json.dump({"state": "submission_attempted", "created_at": int(time.time())}, handle)
    base, layers = _decompose(source_name, "qa-final-demo-20261002")
    record = {"state": "completed", "source": source_name, "base": base, "layers": layers}
    marker.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--recolor", action="store_true", help="可能计费的一次沙发改色")
    group.add_argument("--iso", action="store_true", help="可能计费的一次 2.5D 生成")
    group.add_argument("--fix-iso", action="store_true", help="可能计费的一次 2.5D 局部纠错")
    group.add_argument("--split", action="store_true", help="可能计费的一次家具拆层")
    args = parser.parse_args()
    if args.recolor:
        print(f"改色结果：{one_shot('recolor', RECOLOR_PROMPT, '2048x1536')}")
    elif args.iso:
        print(f"2.5D 结果：{one_shot('iso', ISO_PROMPT, '1792x1344')}")
    elif args.fix_iso:
        print(f"2.5D 纠错结果：{one_shot('iso-corrected', ISO_CORRECTION_PROMPT, '1792x1344')}")
    elif args.split:
        record = split_once()
        print(f"拆出软装件数：{len(record['layers'])}")
    else:
        validate()
        print("离线预检通过；未调用云接口")


if __name__ == "__main__":
    main()
