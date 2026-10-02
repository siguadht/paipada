"""候选 01 的平顶 2.5D 隔离验证；默认只离线检查，不提交付费请求。

每个 --submit N 都先落盘一次性标记，再发唯一一次请求；发生网络不确定状态
绝不自动重试。旧的斜屋顶结果与正式方案不会被覆盖。
"""

import argparse
import json
import time
from pathlib import Path

import httpx
from PIL import Image

from app.core.config import settings
from app.services import storage_service
from app.services.layer_service import _download_image


PROJECT = Path(__file__).resolve().parents[2]
FRONT = PROJECT / "data/qa-final-demo-candidates-20261002/candidate-01.jpg"
GUIDE = PROJECT / "data/qa-final-demo-finish-20261002/iso-flat-structure-guide.png"
OUTPUT = PROJECT / "data/qa-final-demo-finish-20261002"
PROMPTS = {
    1: (
        "图1是必须遵守的室内空间几何参照：平层公寓，矩形地面，两面等高直立墙，"
        "整个顶部和前面完全敞开；墙的上沿为等距投影下的直线，不构成三角屋顶或山墙。"
        "保持图1的窗、沙发、单椅、茶几、地毯、电视和柜子的相对方位。"
        "图2是这间房已经确认的效果图，只取其家具造型、米白浅木色系、真实材质和柔和自然光。"
        "把图1的方块占位家具转化为图2里精致写实的家具，绘制开放式微缩室内轴测图。"
        "不要屋顶、天花板、房屋外立面、坡墙、文字或水印。"
    ),
    2: (
        "严格复现图1平顶开放式轴测模型的外轮廓与两面墙：两面墙均为长方形平墙，"
        "任何一面墙顶边不得高低起伏；没有屋顶、三角山墙或阁楼。"
        "窗口保持在左后墙，电视与落地柜在右后墙，沙发、椅子和茶几保留图1的相对位置。"
        "图2中的米白色单人扶手椅必须保留直立靠背、两个木质扶手和四条木腿，放在窗旁与沙发相邻；"
        "绝不能把单人扶手椅画成无靠背脚凳、方凳或茶几。"
        "图2只决定真实家具材质、暖白浅木配色、灯光和精致度。"
        "成品是摄影级室内沙盘轴测图，而非图1的线框、卡通或平面图。无文字水印。"
    ),
    3: (
        "以图1为完整的 3D 几何模板，仅将家具占位方块和表面材质写实化。"
        "图1从上方清楚看到整个地面，这个房间没有任何顶盖；左右两堵墙同高、直立，"
        "所有墙顶均保持图1的直线轮廓，不增添斜坡、屋脊、三角形屋顶。"
        "图2提供家具款式、浅色布艺、木纹、地砖、窗帘和自然光参考。"
        "保持沙发在左、电视柜在右、茶几在中间、窗在后方。"
        "做成真实精致的开放式 2.5D 室内模型，背景简洁，无文字水印。"
    ),
}


def validate() -> None:
    for path in (FRONT, GUIDE):
        if not path.is_file():
            raise FileNotFoundError(f"缺少离线输入：{path.name}")
        with Image.open(path) as image:
            image.verify()
    if not settings.ark_api_key or not settings.ark_image_model:
        raise RuntimeError("缺少真实图像模型配置；不会使用 mock 结果")
    for prompt in PROMPTS.values():
        if len(prompt) > 500:
            raise ValueError("提示词过长")


def submit_once(number: int) -> Path:
    validate()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    marker = OUTPUT / f"iso-guided-{number}.json"
    target = OUTPUT / f"iso-guided-{number}.jpg"
    if marker.exists():
        raise RuntimeError("本变体已提交或结果不明，不允许重复调用")
    keys = [f"qa-final-demo-20261002/iso-guided-{number}-guide.png",
            f"qa-final-demo-20261002/iso-guided-{number}-front.jpg"]
    try:
        for path, key in zip((GUIDE, FRONT), keys):
            storage_service.upload_file(str(path), key)
        urls = [storage_service.presigned_url(key, expires=3600) for key in keys]
        with marker.open("x", encoding="utf-8") as handle:
            json.dump({"state": "submission_attempted", "created_at": int(time.time())}, handle)
        response = httpx.post(
            f"{settings.ark_base_url}/images/generations",
            headers={"Authorization": f"Bearer {settings.ark_api_key}", "Content-Type": "application/json"},
            json={"model": settings.ark_image_model, "image": urls, "prompt": PROMPTS[number],
                  "size": "1792x1344", "response_format": "url", "watermark": False},
            timeout=240,
        )
        if response.status_code != 200:
            marker.write_text(json.dumps({"state": "failed_or_unknown", "http_status": response.status_code}), encoding="utf-8")
            raise RuntimeError("模型未返回成功；不自动重试")
        data = response.json().get("data") or []
        if len(data) != 1 or not isinstance(data[0].get("url"), str):
            raise ValueError("模型返回结构不符合单张图片要求；不自动重试")
        image = _download_image(data[0]["url"])
        image.convert("RGB").save(target, "JPEG", quality=94)
        marker.write_text(json.dumps({"state": "completed", "result": target.name}), encoding="utf-8")
        return target
    finally:
        for key in keys:
            try:
                storage_service.delete_object(key)
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submit", type=int, choices=tuple(PROMPTS), help="获费用授权后显式提交一次")
    args = parser.parse_args()
    if args.submit:
        print(f"隔离 2.5D 图：{submit_once(args.submit)}")
    else:
        validate()
        print(f"离线检查通过：原正面图 + 平顶结构图，{len(PROMPTS)} 个单次变体；未提交云请求")


if __name__ == "__main__":
    main()
