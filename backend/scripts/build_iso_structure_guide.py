"""离线绘制客厅 01 的平层开放式轴测结构参照图。

这是用于约束下一次生图的几何引导图，不是产品展示图，也不声称精确户型。
无网络和模型调用。
"""

from pathlib import Path

from PIL import Image, ImageDraw


PROJECT = Path(__file__).resolve().parents[2]
OUTPUT = PROJECT / "data/qa-final-demo-finish-20261002/iso-flat-structure-guide.png"
SCALE = 2
SIZE = (1600, 1150)


def point(x: float, y: float, z: float = 0) -> tuple[int, int]:
    return (round((800 + (x - y) * 88) * SCALE), round((320 + (x + y) * 50 - z * 100) * SCALE))


def polygon(draw: ImageDraw.ImageDraw, coords: list[tuple[float, float, float]], fill: str, outline: str = "#d4cfca", width: int = 2) -> None:
    xy = [point(*item) for item in coords]
    draw.polygon(xy, fill=fill)
    draw.line(xy + xy[:1], fill=outline, width=width * SCALE, joint="curve")


def block(draw: ImageDraw.ImageDraw, x: float, y: float, z: float, dx: float, dy: float, dz: float,
          top: str, front: str, side: str, edge: str = "#b6aaa0") -> None:
    # Equal z on every top vertex: these are flat furniture surfaces, never a pitched roof.
    polygon(draw, [(x, y + dy, z), (x + dx, y + dy, z), (x + dx, y + dy, z + dz), (x, y + dy, z + dz)], front, edge)
    polygon(draw, [(x + dx, y, z), (x + dx, y + dy, z), (x + dx, y + dy, z + dz), (x + dx, y, z + dz)], side, edge)
    polygon(draw, [(x, y, z + dz), (x + dx, y, z + dz), (x + dx, y + dy, z + dz), (x, y + dy, z + dz)], top, edge)


def main() -> None:
    image = Image.new("RGB", (SIZE[0] * SCALE, SIZE[1] * SCALE), "#f5f4f1")
    draw = ImageDraw.Draw(image)

    # The original accepted front image shows a normal apartment, not an attic.
    # Two upright half-height walls have equal height at both ends; front and roof stay open.
    polygon(draw, [(0, 0, 0), (0, 6, 0), (0, 6, 2.4), (0, 0, 2.4)], "#eeeae4", "#b6aea7", 3)
    polygon(draw, [(0, 0, 0), (8, 0, 0), (8, 0, 2.4), (0, 0, 2.4)], "#e4ddd4", "#b6aea7", 3)
    polygon(draw, [(0, 0, 0), (8, 0, 0), (8, 6, 0), (0, 6, 0)], "#e7ddd0", "#bcae9e", 3)

    # Large preserved window in back-left wall. The frame is a rectangle in wall coordinates.
    polygon(draw, [(0, 1.2, .73), (0, 4.8, .73), (0, 4.8, 2.0), (0, 1.2, 2.0)], "#dcecf0", "#6f7778", 5)
    for y in (2.4, 3.6):
        draw.line([point(0, y, .73), point(0, y, 2.0)], fill="#6f7778", width=4 * SCALE)
    draw.line([point(0, 1.2, 1.36), point(0, 4.8, 1.36)], fill="#6f7778", width=4 * SCALE)

    # TV wall and a floor-standing cabinet, both on the right side of the approved image.
    polygon(draw, [(3.9, .01, .85), (6.45, .01, .85), (6.45, .01, 1.9), (3.9, .01, 1.9)], "#333537", "#474340", 5)
    block(draw, 3.85, .35, 0, 2.8, .65, .48, "#b88b63", "#9d7456", "#876349")

    # Flat rug, sofa facing the TV wall, armchair by the window, low coffee table.
    polygon(draw, [(1.7, 1.4, .012), (5.95, 1.4, .012), (5.95, 4.75, .012), (1.7, 4.75, .012)], "#eee6d8", "#d6cbbb", 3)
    block(draw, 1.35, 3.55, .03, 2.55, 1.12, .58, "#e4ddd1", "#d0c6b8", "#b9ae9f")
    block(draw, 1.32, 3.48, .59, 2.6, .32, .62, "#ebe5db", "#d0c6b8", "#b9ae9f")
    block(draw, 4.4, 1.65, .03, 1.12, 1.1, .57, "#e6ded2", "#d0c6b8", "#b9ae9f")
    block(draw, 3.1, 2.25, .02, 1.75, 1.22, .42, "#c99a6d", "#ac805d", "#936f51")

    # Lamp and plant are deliberately simple placeholders; front image controls their final styling.
    draw.line([point(1.05, 4.75, .04), point(1.05, 4.75, 1.55)], fill="#867663", width=7 * SCALE)
    cx, cy = point(1.05, 4.75, 1.68)
    draw.ellipse((cx - 37 * SCALE, cy - 22 * SCALE, cx + 37 * SCALE, cy + 22 * SCALE), fill="#ded4c7", outline="#aa9d8e", width=3 * SCALE)
    block(draw, 6.7, 1.2, .02, .45, .45, .42, "#b68b67", "#987251", "#886444")
    cx, cy = point(6.92, 1.42, 1.07)
    for ox, oy, rx, ry in [(-35, -15, 42, 68), (15, -45, 48, 70), (58, 8, 39, 60)]:
        draw.ellipse((cx + (ox-rx)*SCALE, cy + (oy-ry)*SCALE, cx + (ox+rx)*SCALE, cy + (oy+ry)*SCALE), fill="#63795b")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.resize(SIZE, Image.Resampling.LANCZOS).save(OUTPUT)
    print(f"平层结构参照：{OUTPUT}")


if __name__ == "__main__":
    main()
