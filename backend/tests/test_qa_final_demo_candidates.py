"""最终演示生图任务遇到未知结果时不能再次计费提交。"""

import pytest
from PIL import Image

from scripts import qa_final_demo_candidates as candidates


def test_failed_response_keeps_marker_and_blocks_repeat(monkeypatch, tmp_path):
    source = tmp_path / "room.jpg"
    Image.new("RGB", (64, 48), "white").save(source)
    monkeypatch.setattr(candidates, "SOURCE", source)
    monkeypatch.setattr(candidates, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(candidates.settings, "ark_api_key", "test-value")
    monkeypatch.setattr(candidates.settings, "ark_image_model", "test-model")
    monkeypatch.setattr(candidates.storage_service, "upload_file", lambda *args: None)
    monkeypatch.setattr(candidates.storage_service, "presigned_url", lambda *args, **kwargs: "https://example.test/room.jpg")
    monkeypatch.setattr(candidates.storage_service, "delete_object", lambda *args: None)

    calls = []

    class Failed:
        status_code = 503

    def post(*args, **kwargs):
        calls.append(kwargs["json"]["prompt"])
        return Failed()

    monkeypatch.setattr(candidates.httpx, "post", post)
    with pytest.raises(RuntimeError, match="不自动重试"):
        candidates.render()
    assert (candidates.OUTPUT / "candidate-01.json").is_file()
    with pytest.raises(RuntimeError, match="结果不明"):
        candidates.render()
    assert len(calls) == 1
