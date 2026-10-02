"""带结构参照的 2.5D 验证不能因失败重复计费。"""

import pytest
from PIL import Image

from scripts import qa_iso_guided as iso


def test_failed_submission_records_attempt_and_blocks_duplicate(monkeypatch, tmp_path):
    guide, front = tmp_path / "guide.png", tmp_path / "front.jpg"
    Image.new("RGB", (64, 48), "white").save(guide)
    Image.new("RGB", (64, 48), "white").save(front)
    monkeypatch.setattr(iso, "GUIDE", guide)
    monkeypatch.setattr(iso, "FRONT", front)
    monkeypatch.setattr(iso, "OUTPUT", tmp_path / "results")
    monkeypatch.setattr(iso.settings, "ark_api_key", "test-value")
    monkeypatch.setattr(iso.settings, "ark_image_model", "test-model")
    monkeypatch.setattr(iso.storage_service, "upload_file", lambda *args: None)
    monkeypatch.setattr(iso.storage_service, "presigned_url", lambda *args, **kwargs: "https://example.test/image")
    monkeypatch.setattr(iso.storage_service, "delete_object", lambda *args: None)

    requests = []

    class Failed:
        status_code = 503

    def post(*args, **kwargs):
        requests.append(kwargs["json"])
        return Failed()

    monkeypatch.setattr(iso.httpx, "post", post)
    with pytest.raises(RuntimeError, match="不自动重试"):
        iso.submit_once(1)
    assert requests[0]["image"] == ["https://example.test/image"] * 2
    assert (iso.OUTPUT / "iso-guided-1.json").is_file()
    with pytest.raises(RuntimeError, match="不允许重复调用"):
        iso.submit_once(1)
    assert len(requests) == 1
