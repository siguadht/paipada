"""全屋多空间的归属、共享风格快照和旧方案兼容。"""
import io
import secrets

from PIL import Image

from app.db import SessionLocal
from app.models import Design, User
from app.services.design_service import _image_room_brief, _room_brief


def _photo(client, headers):
    image = Image.new("RGB", (128, 96), "#c5b7a7")
    buf = io.BytesIO()
    image.save(buf, "PNG")
    response = client.post("/api/v1/uploads", files={"file": ("room.png", buf.getvalue(), "image/png")}, headers=headers)
    assert response.status_code == 201
    return response.json()["photo_id"]


def test_home_spaces_keep_own_versions_and_style_snapshot(client, auth_headers):
    style_photo = _photo(client, auth_headers)
    created = client.post("/api/v1/homes", json={"name": "我的新家", "style_text": "温暖原木风", "style_photo_id": style_photo}, headers=auth_headers)
    assert created.status_code == 201
    home_id = created.json()["id"]
    ids = []
    for room in ("客厅", "主卧"):
        result = client.post("/api/v1/designs", json={
            "photo_id": _photo(client, auth_headers), "user_input": "保留门窗，更新软装",
            "home_id": home_id, "room_name": room, "cost_confirmed": True,
        }, headers=auth_headers)
        assert result.status_code == 201
        assert result.json()["reference_ids"]["style"] == style_photo
        ids.append(result.json()["design_id"])
    home = client.get(f"/api/v1/homes/{home_id}", headers=auth_headers).json()
    assert [space["name"] for space in home["spaces"]] == ["客厅", "主卧"]
    assert [space["design"]["design_id"] for space in home["spaces"]] == ids
    assert all(space["style_snapshot"] == "温暖原木风" for space in home["spaces"])

    changed = client.put(f"/api/v1/homes/{home_id}", json={"name": "我的新家", "style_text": "现代简约"}, headers=auth_headers)
    assert changed.status_code == 200
    with SessionLocal() as db:
        assert "温暖原木风" in _room_brief(db, db.get(Design, ids[0]))
        image_brief = _image_room_brief(db, db.get(Design, ids[0]))
        assert "温暖原木风" in image_brief
        assert "保留门窗，更新软装" in image_brief
    assert client.get(f"/api/v1/homes/{home_id}", headers=auth_headers).json()["spaces"][0]["style_snapshot"] == "温暖原木风"
    third = client.post("/api/v1/designs", json={"photo_id": _photo(client, auth_headers), "user_input": "更新书房", "home_id": home_id, "room_name": "书房", "cost_confirmed": True}, headers=auth_headers)
    assert third.status_code == 201
    assert client.get(f"/api/v1/homes/{home_id}", headers=auth_headers).json()["spaces"][2]["style_snapshot"] == "现代简约"

    space_id = home["spaces"][0]["id"]
    premature = client.post(f"/api/v1/homes/{home_id}/style-from-space/{space_id}", headers=auth_headers)
    assert premature.status_code == 409
    assert client.post(f"/api/v1/designs/{ids[0]}/confirm", headers=auth_headers).status_code == 202
    chosen = client.post(f"/api/v1/homes/{home_id}/style-from-space/{space_id}", headers=auth_headers)
    assert chosen.status_code == 200
    assert chosen.json()["style_photo_id"] != style_photo
    assert client.get(chosen.json()["style_photo_url"], headers=auth_headers).status_code == 200
    fourth = client.post("/api/v1/designs", json={"photo_id": _photo(client, auth_headers), "user_input": "更新次卧", "home_id": home_id, "room_name": "次卧", "cost_confirmed": True}, headers=auth_headers)
    assert fourth.status_code == 201
    assert fourth.json()["reference_ids"]["style"] == chosen.json()["style_photo_id"]


def test_home_permission_and_legacy_design(client, auth_headers):
    home = client.post("/api/v1/homes", json={"name": "A 的家"}, headers=auth_headers).json()
    photo = _photo(client, auth_headers)
    legacy = client.post("/api/v1/designs", json={"photo_id": photo, "user_input": "旧式单房间"}, headers=auth_headers)
    assert legacy.status_code == 201
    no_cost = client.post("/api/v1/designs", json={"photo_id": photo, "user_input": "新房间", "home_id": home["id"], "room_name": "客厅"}, headers=auth_headers)
    assert no_cost.status_code == 400
    assert no_cost.json()["error"]["code"] == "COST_CONFIRMATION_REQUIRED"
    assert client.get(f"/api/v1/designs/{legacy.json()['design_id']}", headers=auth_headers).status_code == 200
    code = "HOME-" + secrets.token_hex(8)
    with SessionLocal() as db:
        db.add(User(invite_code=code))
        db.commit()
    other_token = client.post("/api/v1/auth/login", json={"invite_code": code}).json()["token"]
    other = {"Authorization": f"Bearer {other_token}"}
    assert client.get(f"/api/v1/homes/{home['id']}", headers=other).status_code == 404
    assert client.get("/api/v1/homes", headers=other).json()["homes"] == []
    assert client.put(f"/api/v1/homes/{home['id']}", json={"name": "越权"}, headers=other).status_code == 404
    assert client.post(f"/api/v1/homes/{home['id']}/style-from-space/unknown", headers=other).status_code == 404
    assert client.post("/api/v1/designs", json={"photo_id": photo, "user_input": "越权", "home_id": home["id"], "room_name": "卧室"}, headers=other).status_code == 404
