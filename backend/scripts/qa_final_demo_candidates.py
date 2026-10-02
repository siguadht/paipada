"""为最终演示一次性准备三张真实候选；默认仅离线预检。

只有获准一次明确的费用上限后才运行 --render。每张请求前写独占标记，
网络结果不明也不自动重试；成功图片留在隔离目录，不覆盖正式方案。
"""

from __future__ import annotations

import argparse
import io
import json
import time
from pathlib import Path

import httpx
from PIL import Image

from app.core.config import settings
from app.services import storage_service


PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / "data/uploads/5dd26281-5f98-46d9-a98b-515d66f3129e.jpg"
OUTPUT = PROJECT / "data/qa-final-demo-candidates-20261002"
SIZE = "2048x1536"
PROMPTS = {
    "01": (
        "以第一张原照片为真实房屋，保留当前机位、窗户位置和数量、墙体转角与空间尺度。"
        "设计一间真实可居住的现代原木客厅：左墙放米白布艺三人沙发、靠垫和落地灯，中央有低矮实木茶几与织物地毯，"
        "右墙为克制的木质电视背景板和贴地电视柜，加入单椅、边几、绿植与沙发墙挂画。"
        "清除原海报和杂物，换直落窗帘与简洁双眼皮吊顶。住宅实景摄影质感，自然日光、细腻材质、可信阴影和正常家具比例；无渲染塑料感、文字或水印。"
    ),
    "02": (
        "根据原照片做高品质住宅软装改造，保留拍摄机位、窗框布局、房间边界和正常动线。"
        "浅橡木、暖白墙面和少量深胡桃木构成有层次的现代客厅；米白沙发靠左墙，另一侧布置单椅，"
        "中央放原木茶几、厚实织物地毯，补充落地灯、边柜、书本、抱枕、绿植、挂画。"
        "右墙电视嵌在薄木背景板上，电视柜必须落地；清走红海报和杂物，窗帘为现代直落式。"
        "像室内设计杂志的真实照片，保留真实墙面和木材纹理，光线来自原窗，无夸张广角、文字或水印。"
    ),
    "03": (
        "把原照片中的空房改造成真实精致的居家客厅，严格沿用原机位与窗户位置，空间尺度可信。"
        "现代温暖极简风，奶油白布艺沙发、低矮深木茶几、浅灰地毯、皮革单椅、落地灯、边几、细叶绿植和抽象挂画，"
        "软装丰富但留出通道。电视墙用浅木饰面做轻薄悬浮层次，下面是贴地长电视柜，不要悬浮柜。"
        "原海报与杂物消失，窗帘改成平整纱帘加直落布帘，吊顶简洁。"
        "自然摄影，真实织物褶皱、木纹、接触阴影与层次光照，避免样板间渲染感、文字和水印。"
    ),
}


def validate() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError("演示原照不存在")
    with Image.open(SOURCE) as photo:
        photo.verify()
    if any(len(prompt) > 300 for prompt in PROMPTS.values()):
        raise ValueError("候选提示词超过 300 字")
    if not settings.ark_api_key or not settings.ark_image_model:
        raise RuntimeError("未配置方舟图片模型；不会使用 mock 图冒充真实结果")


def render() -> None:
    validate()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_key = "qa-final-demo-20261002/original-room.jpg"
    storage_service.upload_file(str(SOURCE), source_key)
    try:
        source_url = storage_service.presigned_url(source_key, expires=3600)
        for number, prompt in PROMPTS.items():
            marker = OUTPUT / f"candidate-{number}.json"
            target = OUTPUT / f"candidate-{number}.jpg"
            if marker.exists():
                if target.exists():
                    continue
                raise RuntimeError(f"候选 {number} 已尝试但结果不明，停止而不重试")
            with marker.open("x", encoding="utf-8") as handle:
                json.dump({"state": "submission_attempted", "created_at": int(time.time())}, handle)
            response = httpx.post(
                f"{settings.ark_base_url}/images/generations",
                headers={"Authorization": f"Bearer {settings.ark_api_key}", "Content-Type": "application/json"},
                json={
                    "model": settings.ark_image_model,
                    "prompt": prompt,
                    "image": source_url,
                    "size": SIZE,
                    "response_format": "url",
                    "watermark": False,
                },
                timeout=240,
            )
            if response.status_code != 200:
                marker.write_text(json.dumps({"state": "submission_failed_or_unknown", "http_status": response.status_code}), encoding="utf-8")
                raise RuntimeError(f"候选 {number} 没有成功响应；不自动重试")
            data = response.json().get("data") or []
            if len(data) != 1 or not isinstance(data[0].get("url"), str):
                marker.write_text(json.dumps({"state": "submission_failed_or_unknown"}), encoding="utf-8")
                raise RuntimeError(f"候选 {number} 响应格式异常；不自动重试")
            image_response = httpx.get(data[0]["url"], timeout=60)
            image_response.raise_for_status()
            with Image.open(io.BytesIO(image_response.content)) as generated:
                generated.convert("RGB").save(target, "JPEG", quality=94)
            marker.write_text(json.dumps({"state": "completed", "image": target.name}), encoding="utf-8")
            print(f"候选 {number} 已保存：{target}")
    finally:
        storage_service.delete_object(source_key)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true", help="会创建最多三次可能计费的生图任务，需事先授权")
    args = parser.parse_args()
    if not args.render:
        validate()
        print(f"离线预检通过：原照 1 张、候选提示词 {len(PROMPTS)} 条、输出尺寸 {SIZE}；未调用云接口")
        return
    render()


if __name__ == "__main__":
    main()
