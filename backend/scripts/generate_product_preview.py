"""经产品经理授权的一次性六类商品示意图样稿；每个 ID 最多请求一次。"""
import io
from pathlib import Path

import httpx
from PIL import Image

from app.core.config import PROJECT_ROOT, settings


SAMPLES = (
    ("p001", "云朵布艺沙发", "米白色蓬松布艺三人沙发，柔和圆润的坐垫和扶手，完整展示沙发"),
    ("p009", "暖光落地灯", "米白色简约落地灯，细长灯杆、柔和灯罩，完整展示灯具与底座"),
    ("p017", "琴叶榕盆栽", "琴叶榕室内盆栽，深绿色自然叶片、浅色素陶花盆，完整展示整株植物"),
    ("p022", "圆形原木茶几", "浅色原木圆形低矮茶几，清楚展示桌面、桌腿与木纹"),
    ("p025", "羊毛地毯", "米白色羊毛地毯，单件平铺并略微卷起一角，清楚展示织物纹理与完整边界"),
    ("p027", "原木电视柜", "浅色原木低矮电视柜，简洁柜门与抽屉，完整展示柜体和支脚"),
)
OUTPUT = PROJECT_ROOT / "docs" / "evidence" / "阶段3-1" / "商品图样稿"


def main() -> None:
    if not settings.has_ark_key or not settings.ark_image_model:
        raise SystemExit("图片模型未配置；未发起任何生成请求")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for product_id, name, description in SAMPLES:
        target = OUTPUT / f"{product_id}.jpg"
        if target.exists():
            print(f"SKIP {product_id}: 已有样稿")
            continue
        prompt = (
            f"家居电商产品摄影风格，只拍一件独立的{description}。"
            "整件物品完整入画，三分之四视角，统一机位，居中构图，柔和真实的棚拍光线，"
            "温暖的浅米白无缝背景和很轻的接地阴影，材质细节自然，高级但克制。"
            "不要房间场景，不要其他家具或道具，不要人物，不要文字、标识、品牌、价格或水印。"
            "画面为正方形。"
        )
        try:
            response = httpx.post(
                f"{settings.ark_base_url}/images/generations",
                headers={"Authorization": f"Bearer {settings.ark_api_key}", "Content-Type": "application/json"},
                json={
                    "model": settings.ark_image_model,
                    "prompt": prompt,
                    "size": "1.5K",
                    "response_format": "url",
                    "watermark": False,
                },
                timeout=240,
            )
            response.raise_for_status()
            image_url = response.json()["data"][0]["url"]
            image_response = httpx.get(image_url, timeout=90)
            image_response.raise_for_status()
            with Image.open(io.BytesIO(image_response.content)) as image:
                image.load()
                if image.width * image.height > 2_610_000:
                    raise ValueError("输出超过预定的 1.5K 像素档位，停止后续调用")
                image.convert("RGB").save(target, "JPEG", quality=91, optimize=True)
            print(f"OK {product_id} {name} {image.width}x{image.height}", flush=True)
        except Exception as exc:
            # 失败或超时的请求可能已经计费；不自动重试，也不输出远端响应或凭据。
            raise SystemExit(f"STOP {product_id}: {type(exc).__name__}；未继续请求后续图片") from None


if __name__ == "__main__":
    main()
