"""第二空间门窗保护区格式验证。"""

from PIL import Image

from scripts.prepare_livingroom_inpaint import prepare


def test_livingroom_mask_keeps_window_and_ceiling(tmp_path):
    photo_path, mask_path = prepare(output=tmp_path)
    with Image.open(photo_path) as photo, Image.open(mask_path) as mask:
        assert photo.size == mask.size == (4096, 3072)
        assert mask.mode == "L"
        assert mask.getpixel((3000, 1300)) == 0  # 大窗保留
        assert mask.getpixel((1800, 500)) == 0  # 吊顶保留
        assert mask.getpixel((1000, 2450)) == 255  # 前景地面可摆放软装
    assert photo_path.stat().st_size < 4_700_000
    assert mask_path.stat().st_size < 4_700_000
