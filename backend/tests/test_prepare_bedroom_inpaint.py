"""局部重绘输入合同测试：尺寸、遮罩通道和黑白语义。"""

from PIL import Image

from scripts.prepare_bedroom_inpaint import prepare


def test_prepare_bedroom_inpaint_matches_documented_image_contract(tmp_path):
    photo_path, mask_path = prepare(output=tmp_path)
    with Image.open(photo_path) as photo, Image.open(mask_path) as mask:
        assert photo.size == mask.size == (4096, 2731)
        assert mask.mode == "L"
        assert mask.getpixel((2500, 2100)) == 255  # 地面允许重绘
        assert mask.getpixel((3400, 950)) == 0  # 右墙窗保留
        assert mask.getpixel((120, 900)) == 0  # 左侧房门保留
        assert mask.getpixel((2000, 200)) == 0  # 吊顶保留
        assert mask.getpixel((3800, 1700)) == 0  # 右墙上半部保留
    assert photo_path.stat().st_size < 4_700_000
    assert mask_path.stat().st_size < 4_700_000
