"""多图请求只在本地 stub 中验证，不触发付费生图。"""
import io
import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.core.errors import ServiceError
from app.services import image_service


def test_generation_sends_role_ordered_reference_images(tmp_path, monkeypatch):
    uploads = tmp_path / "uploads"
    generated = tmp_path / "generated"
    uploads.mkdir()
    for name in ("room.jpg", "style.jpg", "furniture.jpg"):
        size = (1200, 800) if name == "room.jpg" else (640, 480)
        Image.new("RGB", size, "white").save(uploads / name)
    monkeypatch.setattr(image_service.settings, "upload_dir", str(uploads))
    monkeypatch.setattr(image_service.settings, "generated_dir", str(generated))
    monkeypatch.setattr(image_service.settings, "ark_api_key", "stub-key")
    monkeypatch.setattr(image_service.settings, "ark_image_model", "stub-model")
    uploaded = []
    deleted = []
    payloads = []
    monkeypatch.setattr(image_service.storage_service, "upload_file", lambda path, key: uploaded.append((Path(path).name, key)))
    monkeypatch.setattr(image_service.storage_service, "presigned_url", lambda key, expires: f"https://example.invalid/{key}")
    monkeypatch.setattr(image_service.storage_service, "delete_object", lambda key: deleted.append(key))

    class Response:
        status_code = 200
        content = b""
        def json(self):
            return {"data": [{"url": "https://example.invalid/result"}]}
        def raise_for_status(self):
            pass

    result_image = io.BytesIO()
    Image.new("RGB", (640, 480), "white").save(result_image, "JPEG")
    def fake_post(url, headers, json, timeout):
        payloads.append(json)
        return Response()
    def fake_get(url, timeout):
        response = Response()
        response.content = result_image.getvalue()
        return response
    monkeypatch.setattr(image_service.httpx, "post", fake_post)
    monkeypatch.setattr(image_service.httpx, "get", fake_get)

    name = image_service.generate_design_front("图1原房间，图2风格，图3家具", "room.jpg", "design-id", ["style.jpg", "furniture.jpg"])
    assert name.endswith(".jpg")
    assert [item[0] for item in uploaded] == ["room.jpg", "style.jpg", "furniture.jpg"]
    assert len(payloads) == 1
    assert len(payloads[0]["image"]) == 3
    assert payloads[0]["size"] == "1872x1248"
    assert payloads[0]["prompt"].startswith("图1原房间，图2风格，图3家具")
    assert {item[1] for item in uploaded} == set(deleted)
    assert (generated / name).is_file()

    product_image = tmp_path / "selected-product.png"
    Image.new("RGB", (400, 400), "beige").save(product_image)
    edited = image_service.edit_design_front(name, "图2是选定商品", "design-id", extra_reference_paths=[str(product_image)])
    assert (generated / edited).is_file()
    assert len(payloads[1]["image"]) == 2
    assert payloads[1]["size"] == "1792x1344"
    assert "selected-product.png" in uploaded[-1][0]
    assert {item[1] for item in uploaded} == set(deleted)


def test_protocol_error_has_bounded_retry_and_cleans_temporary_images(tmp_path, monkeypatch):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    Image.new("RGB", (640, 480), "white").save(uploads / "room.jpg")
    monkeypatch.setattr(image_service.settings, "upload_dir", str(uploads))
    monkeypatch.setattr(image_service.settings, "generated_dir", str(tmp_path / "generated"))
    monkeypatch.setattr(image_service.settings, "ark_api_key", "stub-key")
    monkeypatch.setattr(image_service.settings, "ark_image_model", "stub-model")
    uploaded = []
    deleted = []
    attempts = []
    monkeypatch.setattr(image_service.storage_service, "upload_file", lambda path, key: uploaded.append(key))
    monkeypatch.setattr(image_service.storage_service, "presigned_url", lambda key, expires: f"https://example.invalid/{key}")
    monkeypatch.setattr(image_service.storage_service, "delete_object", lambda key: deleted.append(key))
    monkeypatch.setattr(image_service.time, "sleep", lambda seconds: None)

    def fail_post(url, headers, json, timeout):
        attempts.append(url)
        raise httpx.RemoteProtocolError("connection closed")

    monkeypatch.setattr(image_service.httpx, "post", fail_post)
    with pytest.raises(ServiceError) as error:
        image_service.generate_design_front("保留房间", "room.jpg", "test-id")
    assert error.value.code == "IMAGE_GEN_FAILED"
    assert error.value.message == "图片生成超时或网络失败，请稍后重试"
    assert len(attempts) == 2
    assert uploaded == deleted
