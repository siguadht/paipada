"""整件软装图层的费用确认、缓存、归属与版本隔离。"""
from pathlib import Path
import secrets

from PIL import Image

from app.core.config import settings
from app.db import SessionLocal
from app.models import User
from app.services import image_service, layer_service
from .test_design_editor import _photo


def test_layer_set_requires_consent_and_is_owned(client, auth_headers, monkeypatch):
    photo_id = _photo(client, auth_headers)
    design_id = client.post(
        "/api/v1/designs", json={"photo_id": photo_id, "user_input": "原木客厅"}, headers=auth_headers,
    ).json()["design_id"]
    endpoint = f"/api/v1/designs/{design_id}/layers"
    no_consent = client.post(endpoint, json={"cost_confirmed": False}, headers=auth_headers)
    assert no_consent.status_code == 400
    assert no_consent.json()["error"]["code"] == "COST_CONFIRMATION_REQUIRED"
    assert client.post(endpoint, json={"cost_confirmed": True}).status_code == 401

    monkeypatch.setattr(settings, "ark_api_key", "test-only")
    monkeypatch.setattr(settings, "ark_image_model", "test-only")
    monkeypatch.setattr(image_service, "edit_design_front", lambda source, prompt, design_id, references=None: source)
    calls = []

    def fake_decompose(source_name, layer_set_id):
        calls.append(source_name)
        base_name = f"{layer_set_id}_base.png"
        layer_name = f"{layer_set_id}_layer_0.png"
        Image.new("RGB", (512, 512), "white").save(Path(settings.generated_dir) / base_name)
        Image.new("RGBA", (100, 100), (0, 0, 0, 0)).save(Path(settings.generated_dir) / layer_name)
        return base_name, [{"name": "沙发", "description": "米色沙发", "image_path": layer_name,
                            "box": [0.1, 0.4, 0.5, 0.8], "z_index": 1}]

    monkeypatch.setattr(layer_service, "_decompose", fake_decompose)
    first = client.post(endpoint, json={"cost_confirmed": True}, headers=auth_headers)
    assert first.status_code == 202
    current = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    assert current["layer_set"]["status"] == "ready"
    assert len(current["layer_set"]["layers"]) == 1
    assert client.get(current["layer_set"]["base_image_url"], headers=auth_headers).status_code == 200
    assert client.get(current["layer_set"]["layers"][0]["image_url"], headers=auth_headers).status_code == 200
    assert client.get(current["layer_set"]["base_image_url"]).status_code == 401
    code = "LAYER-" + secrets.token_hex(4)
    with SessionLocal() as db:
        db.add(User(invite_code=code))
        db.commit()
    other_token = client.post("/api/v1/auth/login", json={"invite_code": code}).json()["token"]
    other = {"Authorization": f"Bearer {other_token}"}
    assert client.post(endpoint, json={"cost_confirmed": True}, headers=other).status_code == 404
    assert client.get(current["layer_set"]["base_image_url"], headers=other).status_code == 404
    assert client.post(endpoint, json={"cost_confirmed": False}, headers=auth_headers).status_code == 202
    assert len(calls) == 1

    edit = client.post(f"/api/v1/designs/{design_id}/edits", json={
        "operation": "recolor", "x": 0.3, "y": 0.6, "detail": "绿色", "layer_index": 0,
    }, headers=auth_headers)
    assert edit.status_code == 202
    newer = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    assert newer["current_version"] == 2
    assert newer["layer_set"] is None
    stale = client.post(f"/api/v1/designs/{design_id}/edits", json={
        "operation": "delete", "x": 0.3, "y": 0.6, "layer_index": 0,
    }, headers=auth_headers)
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "LAYER_EXPIRED"
    restored = client.post(f"/api/v1/designs/{design_id}/versions/1/restore", headers=auth_headers).json()
    assert restored["layer_set"]["status"] == "ready"


def test_layer_response_rejects_bad_boxes():
    base = {"z_index": 0, "url": "https://example.com/base.png"}
    invalid = {"z_index": 1, "url": "https://example.com/layer.png", "bounding_box": {"normalized": [900, 0, 100, 999]}}
    try:
        layer_service._validate_layers([base, invalid])
    except ValueError:
        pass
    else:
        raise AssertionError("invalid bounding box accepted")
