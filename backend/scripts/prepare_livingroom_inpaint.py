"""第二空间结构验证：只离线准备客厅原图和严格结构遮罩。"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from scripts.prepare_bedroom_inpaint import MAX_BYTES, MAX_SIDE


PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / "docs/evidence/阶段3-2/真实双空间/客厅-原图.jpg"
OUTPUT = PROJECT / "data/qa-livingroom-inpaint-20261002"
VIEW_SIZE = (1824, 1368)  # 手工标注时参考的 4:3 缩略视图


def prepare(source: Path = SOURCE, output: Path = OUTPUT) -> tuple[Path, Path]:
    with Image.open(source) as opened:
        photo = ImageOps.exif_transpose(opened).convert("RGB")
    photo.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    mask = Image.new("L", photo.size, 0)
    draw = ImageDraw.Draw(mask)

    def scaled(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
        return [(round(x * photo.width / VIEW_SIZE[0]), round(y * photo.height / VIEW_SIZE[1])) for x, y in points]

    # 可编辑左墙下半部和地面，用于摆放沙发、茶几、地毯、绿植。
    draw.polygon(scaled([(0, 600), (940, 600), (1030, 950), (1824, 1040), (1824, 1368), (0, 1368)]), fill=255)
    # 大窗及两侧垂帘区域保留，避免第二空间又发生窗框位移。
    draw.polygon(scaled([(978, 420), (1824, 405), (1824, 1090), (1000, 985)]), fill=0)

    output.mkdir(parents=True, exist_ok=True)
    photo_path = output / "客厅原图-接口尺寸.jpg"
    mask_path = output / "客厅窗墙保护-单通道遮罩.png"
    photo.save(photo_path, "JPEG", quality=88, optimize=True)
    mask.save(mask_path, "PNG", optimize=True)
    if any(path.stat().st_size > MAX_BYTES for path in (photo_path, mask_path)):
        raise ValueError("原图或遮罩超过接口 4.7 MB")
    return photo_path, mask_path


if __name__ == "__main__":
    photo_path, mask_path = prepare()
    with Image.open(photo_path) as photo, Image.open(mask_path) as mask:
        print(f"第二空间离线输入已就绪：{photo.size}，遮罩模式 {mask.mode}")
        print(f"原图：{photo_path}")
        print(f"遮罩：{mask_path}")
        print("未提交新模型任务")
