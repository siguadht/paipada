"""编辑工作流的持久化、版本和用户隔离。mock 图只验证流程。"""
import io
import time

from PIL import Image

from app.db import SessionLocal
from app.models import Design, DesignStructureReview, User
from app.core.config import settings


def _photo(client, headers):
    image = Image.new("RGB", (128, 96), "#c5b7a7")
    buf = io.BytesIO()
    image.save(buf, "PNG")
    response = client.post(
        "/api/v1/uploads", files={"file": ("room.png", buf.getvalue(), "image/png")}, headers=headers
    )
    assert response.status_code == 201
    return response.json()["photo_id"]


def test_front_edit_versions_then_iso(client, auth_headers):
    photo_id = _photo(client, auth_headers)
    response = client.post(
        "/api/v1/designs", json={"photo_id": photo_id, "user_input": "温暖的原木客厅"}, headers=auth_headers
    )
    assert response.status_code == 201
    design_id = response.json()["design_id"]
    current = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    assert current["status"] == "front_ready"
    assert current["front_image_url"]
    assert not current["iso_image_url"]
    assert current["current_version"] == 1

    edited = client.post(
        f"/api/v1/designs/{design_id}/edits",
        json={"operation": "recolor", "x": 0.36, "y": 0.55, "detail": "墨绿色"},
        headers=auth_headers,
    )
    assert edited.status_code == 202
    current = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    assert current["status"] == "front_ready"
    assert current["current_version"] == 2
    assert len(current["versions"]) == 2
    assert current["front_image_url"] != current["versions"][0]["image_url"]
    assert not current["iso_image_url"]

    restored = client.post(f"/api/v1/designs/{design_id}/versions/1/restore", headers=auth_headers)
    assert restored.status_code == 200
    assert restored.json()["current_version"] == 1

    confirmed = client.post(f"/api/v1/designs/{design_id}/confirm", headers=auth_headers)
    assert confirmed.status_code == 202
    current = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    assert current["status"] == "completed"
    assert current["iso_image_url"]
    assert client.get(current["iso_image_url"], headers=auth_headers).status_code == 200
    same = client.post(f"/api/v1/designs/{design_id}/versions/1/restore", headers=auth_headers)
    assert same.status_code == 200
    assert same.json()["iso_image_url"] == current["iso_image_url"]
    other = client.post(f"/api/v1/designs/{design_id}/versions/2/restore", headers=auth_headers)
    assert other.status_code == 200
    assert other.json()["current_version"] == 2
    assert not other.json()["iso_image_url"]


def test_structure_review_is_checked_and_saved_for_current_front_version(client, auth_headers):
    created = client.post(
        "/api/v1/designs", json={"photo_id": _photo(client, auth_headers), "user_input": "原木卧室"}, headers=auth_headers,
    ).json()
    design_id = created["design_id"]
    endpoint = f"/api/v1/designs/{design_id}/confirm"
    incomplete = client.post(endpoint, json={"review": {
        "mode": "original", "doors_windows": True, "walls_floor": False, "camera_layout": True,
    }}, headers=auth_headers)
    assert incomplete.status_code == 400
    assert incomplete.json()["error"]["code"] == "STRUCTURE_REVIEW_INCOMPLETE"
    current = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    assert current["status"] == "front_ready"
    reviewed = client.post(endpoint, json={"review": {
        "mode": "original", "doors_windows": True, "walls_floor": True, "camera_layout": True,
    }}, headers=auth_headers)
    assert reviewed.status_code == 202
    with SessionLocal() as db:
        rows = db.query(DesignStructureReview).filter(DesignStructureReview.design_id == design_id).all()
        assert len(rows) == 1
        assert rows[0].front_version == 1
        assert rows[0].source_image_path == current["front_image_url"].split("/")[-1]
        assert rows[0].checks["doors_windows"] is True


def test_concept_view_requires_its_own_review(client, auth_headers):
    created = client.post(
        "/api/v1/designs", json={"photo_id": _photo(client, auth_headers), "user_input": "原木客厅"}, headers=auth_headers,
    ).json()
    design_id = created["design_id"]
    result = client.post(f"/api/v1/designs/{design_id}/regenerate", json={
        "view_mode": "concept", "feedback": "转向电视墙做示意",
    }, headers=auth_headers)
    assert result.status_code == 202
    assert client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()["is_concept_view"] is True
    wrong_mode = client.post(f"/api/v1/designs/{design_id}/confirm", json={"review": {
        "mode": "original", "doors_windows": True, "walls_floor": True, "camera_layout": True,
    }}, headers=auth_headers)
    assert wrong_mode.status_code == 400
    assert wrong_mode.json()["error"]["code"] == "STRUCTURE_REVIEW_MODE_MISMATCH"
    accepted = client.post(f"/api/v1/designs/{design_id}/confirm", json={"review": {
        "mode": "concept", "concept_acknowledged": True,
    }}, headers=auth_headers)
    assert accepted.status_code == 202
    with SessionLocal() as db:
        review = db.query(DesignStructureReview).filter(DesignStructureReview.design_id == design_id).one()
        assert review.mode == "concept"


def test_initial_image_prompt_follows_user_not_llm_invented_tv(client, auth_headers, monkeypatch):
    from app.services import image_service, llm_service

    photo_id = _photo(client, auth_headers)
    monkeypatch.setattr(llm_service, "understand_room", lambda brief: {
        "design_notes": ["参考说明"],
        "sd_prompts": {"front": "沙发正对电视墙，在窗前添加电视和悬浮柜"},
    })
    original_generate = image_service.generate_design_front
    seen = []

    def record_generate(prompt, photo_path, design_id):
        seen.append(prompt)
        return original_generate(prompt, photo_path, design_id)

    monkeypatch.setattr(image_service, "generate_design_front", record_generate)
    response = client.post(
        "/api/v1/designs", json={"photo_id": photo_id, "user_input": "原木风客厅，保留现有窗户，摆放米白沙发"}, headers=auth_headers
    )
    assert response.status_code == 201
    assert len(seen) == 1
    assert "用户明确要求：原木风客厅" in seen[0]
    assert "沙发正对电视墙" not in seen[0]
    assert "未要求则不加电视" in seen[0]


def test_initial_three_image_prompt_keeps_structure_and_request_concise(client, auth_headers, monkeypatch):
    from app.services import image_service

    photo_id = _photo(client, auth_headers)
    style_id = _photo(client, auth_headers)
    furniture_id = _photo(client, auth_headers)
    request = (
        "把这间空房改成温暖、真实的原木风客厅。保留现有窗户、墙体、吊顶、地砖、机位与采光；"
        "清理地面杂物和墙上红色海报。参考风格图的浅木色与柔和光线，在左侧摆放参考图中的"
        "米白色沙发，搭配低矮木质茶几和适量绿植。家具比例自然，不要文字或水印。"
    )
    original_generate = image_service.generate_design_front
    seen = []

    def record_generate(prompt, source, design_id, references):
        seen.append((prompt, references))
        return original_generate(prompt, source, design_id, references)

    monkeypatch.setattr(image_service, "generate_design_front", record_generate)
    response = client.post(
        "/api/v1/designs",
        json={"photo_id": photo_id, "user_input": request, "style_photo_id": style_id, "furniture_photo_id": furniture_id},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert len(seen) == 1
    prompt, references = seen[0]
    assert references == [style_id, furniture_id]
    assert "门窗的数量与位置" in prompt
    assert "不要更换地面材质" in prompt
    assert request in prompt
    assert len(prompt + image_service._DESIGN_QUALITY_SUFFIX) <= 300


def test_structure_repair_uses_original_photo_and_keeps_version(client, auth_headers, monkeypatch):
    from pathlib import Path

    from app.services import image_service

    original_id = _photo(client, auth_headers)
    style_id = _photo(client, auth_headers)
    furniture_id = _photo(client, auth_headers)
    created = client.post(
        "/api/v1/designs",
        json={"photo_id": original_id, "user_input": "原木风客厅", "style_photo_id": style_id, "furniture_photo_id": furniture_id},
        headers=auth_headers,
    )
    assert created.status_code == 201
    design_id = created.json()["design_id"]
    captured = []
    actual_edit = image_service.edit_design_front

    def record_edit(source_name, prompt, request_design_id, reference_names=None, extra_reference_paths=None):
        captured.append((prompt, reference_names, extra_reference_paths))
        return actual_edit(source_name, prompt, request_design_id, reference_names, extra_reference_paths)

    monkeypatch.setattr(image_service, "edit_design_front", record_edit)
    endpoint = f"/api/v1/designs/{design_id}/edits"
    missing = client.post(endpoint, json={"operation": "restore_structure", "x": 0.52, "y": 0.44}, headers=auth_headers)
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "DETAIL_REQUIRED"
    repaired = client.post(endpoint, json={
        "operation": "restore_structure", "x": 0.52, "y": 0.44,
        "detail": "原照片左墙没有门，去掉多出的门并保留沙发",
    }, headers=auth_headers)
    assert repaired.status_code == 202
    assert len(captured) == 1
    prompt, references, extra = captured[0]
    assert "<point>519 440</point>" in prompt
    assert "原照片左墙没有门" in prompt
    assert references is None
    assert [Path(path).name for path in extra] == [original_id]
    result = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    assert result["current_version"] == 2
    assert result["versions"][-1]["operation"] == "restore_structure"
    assert result["versions"][0]["image_url"] != result["versions"][-1]["image_url"]


def test_edit_requires_point_and_owner(client, auth_headers):
    assert client.get("/api/v1/designs/products").status_code == 401
    products = client.get("/api/v1/designs/products", headers=auth_headers)
    assert products.status_code == 200
    assert len(products.json()["products"]) >= 20
    photo_id = _photo(client, auth_headers)
    design_id = client.post(
        "/api/v1/designs", json={"photo_id": photo_id, "user_input": "现代风"}, headers=auth_headers
    ).json()["design_id"]
    no_point = client.post(
        f"/api/v1/designs/{design_id}/edits",
        json={"operation": "delete"}, headers=auth_headers,
    )
    assert no_point.status_code == 400
    assert no_point.json()["error"]["code"] == "POINT_REQUIRED"

    db = SessionLocal()
    db.add(User(invite_code="EDITOR-OTHER"))
    db.commit()
    db.close()
    token = client.post("/api/v1/auth/login", json={"invite_code": "EDITOR-OTHER"}).json()["token"]
    other = {"Authorization": f"Bearer {token}"}
    assert client.get(f"/api/v1/designs/{design_id}", headers=other).status_code == 404
    owner = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    assert client.get(owner["front_image_url"], headers=other).status_code == 404
    assert client.get(owner["front_image_url"]).status_code == 401
    assert client.post(f"/api/v1/designs/{design_id}/confirm", headers=other).status_code == 404


def test_edit_cost_guard(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "max_design_edits", 1)
    photo_id = _photo(client, auth_headers)
    design_id = client.post(
        "/api/v1/designs", json={"photo_id": photo_id, "user_input": "现代风"}, headers=auth_headers
    ).json()["design_id"]
    url = f"/api/v1/designs/{design_id}/edits"
    assert client.post(url, json={"operation": "delete", "x": 0.2, "y": 0.5}, headers=auth_headers).status_code == 202
    blocked = client.post(url, json={"operation": "delete", "x": 0.3, "y": 0.5}, headers=auth_headers)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "EDIT_LIMIT"


def test_selected_demo_product_image_is_sent_as_edit_reference(client, auth_headers, monkeypatch):
    from app.services import image_service

    monkeypatch.setattr(settings, "demo_product_catalog", True)
    product = next(item for item in client.get("/api/v1/designs/products", headers=auth_headers).json()["products"] if item.get("demo_only"))
    photo_id = _photo(client, auth_headers)
    design_id = client.post(
        "/api/v1/designs", json={"photo_id": photo_id, "user_input": "简洁客厅"}, headers=auth_headers
    ).json()["design_id"]
    style_id, old_furniture_id = _photo(client, auth_headers), _photo(client, auth_headers)
    assert client.put(f"/api/v1/designs/{design_id}/references", json={"style_photo_id": style_id, "furniture_photo_id": old_furniture_id}, headers=auth_headers).status_code == 200
    endpoint = f"/api/v1/designs/{design_id}/edits"
    bad = client.post(endpoint, json={"operation": "replace", "x": 0.3, "y": 0.5, "detail": "自然融入", "product_id": "not-real"}, headers=auth_headers)
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "PRODUCT_NOT_FOUND"
    wrong_operation = client.post(endpoint, json={"operation": "recolor", "x": 0.3, "y": 0.5, "detail": "灰色", "product_id": product["id"]}, headers=auth_headers)
    assert wrong_operation.status_code == 400

    original_edit = image_service.edit_design_front
    seen = []

    def record_edit(source, prompt, design_id, references=None, extra_reference_paths=None):
        seen.append((prompt, references, extra_reference_paths))
        return original_edit(source, prompt, design_id, references, extra_reference_paths)

    monkeypatch.setattr(image_service, "edit_design_front", record_edit)
    response = client.post(endpoint, json={"operation": "replace", "x": 0.3, "y": 0.5, "detail": "自然融入", "product_id": product["id"]}, headers=auth_headers)
    assert response.status_code == 202
    assert len(seen) == 1
    assert product["name"] in seen[0][0]
    assert "图2是用户选定的商品主图" in seen[0][0]
    assert "不要只把旧物改色或保留旧物的结构" in seen[0][0]
    assert "只修改目标物品及其接触阴影" in seen[0][0]
    assert seen[0][1] == []
    assert len(seen[0][2]) == 1
    assert seen[0][2][0].endswith(product["image_url"])
    assert client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()["current_version"] == 2

    removed = client.post(endpoint, json={"operation": "delete", "x": 0.3, "y": 0.5, "detail": "删除刚换上的沙发"}, headers=auth_headers)
    assert removed.status_code == 202
    assert len(seen) == 2
    assert seen[1][1] is None
    assert seen[1][2] is None
    assert "删除刚换上的沙发" in seen[1][0]
    assert "不要生成另一件同类物品" in seen[1][0]

    recolored = client.post(endpoint, json={
        "operation": "recolor", "x": 0.48, "y": 0.38, "detail": "把整组窗帘改为浅米色",
    }, headers=auth_headers)
    assert recolored.status_code == 202
    assert seen[2][1] is None
    assert seen[2][2] is None
    assert "不要仅改变光照" in seen[2][0]
    assert "保留原有造型" in seen[2][0]

    furniture_replaced = client.post(endpoint, json={
        "operation": "replace", "x": 0.5, "y": 0.6, "detail": "换成参考家具的造型",
    }, headers=auth_headers)
    assert furniture_replaced.status_code == 202
    assert seen[3][1] == [old_furniture_id]
    assert "图2家具参考" in seen[3][0]

    restyled = client.post(endpoint, json={
        "operation": "style", "detail": "整体改为温暖原木风",
    }, headers=auth_headers)
    assert restyled.status_code == 202
    assert seen[4][1] == [style_id]
    assert "图2风格参考" in seen[4][0]


def test_regenerate_uses_original_photo_and_feedback_keeps_versions(client, auth_headers, monkeypatch):
    from app.services import image_service

    photo_id = _photo(client, auth_headers)
    design_id = client.post(
        "/api/v1/designs", json={"photo_id": photo_id, "user_input": "原木客厅"}, headers=auth_headers
    ).json()["design_id"]
    initial = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    original_generate = image_service.generate_design_front
    seen = []

    def record_generate(prompt, photo_path, target_id):
        seen.append((prompt, photo_path, target_id))
        return original_generate(prompt, photo_path, target_id)

    monkeypatch.setattr(image_service, "generate_design_front", record_generate)
    url = f"/api/v1/designs/{design_id}/regenerate"
    assert client.post(url, json={"feedback": "   "}, headers=auth_headers).json()["error"]["code"] == "FEEDBACK_REQUIRED"
    response = client.post(url, json={"feedback": "沙发太大，窗户位置错了"}, headers=auth_headers)
    assert response.status_code == 202
    assert seen and seen[0][1:] == (photo_id, design_id)
    assert "沙发太大，窗户位置错了" in seen[0][0]
    assert "门窗的数量与位置" in seen[0][0]
    assert "不要更换地面材质" in seen[0][0]
    current = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    assert current["current_version"] == 2
    assert current["versions"][0]["image_url"] == initial["front_image_url"]
    assert current["versions"][1]["operation"] == "regenerate"
    assert current["versions"][1]["instruction"] == "沙发太大，窗户位置错了"
    assert current["edit_history"][-1]["detail"] == "沙发太大，窗户位置错了"
    assert client.post(f"/api/v1/designs/{design_id}/versions/1/restore", headers=auth_headers).json()["current_version"] == 1

    monkeypatch.setattr(settings, "max_design_edits", 1)
    blocked = client.post(url, json={"feedback": "再调整"}, headers=auth_headers)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "EDIT_LIMIT"


def test_concept_view_uses_current_image_and_labels_new_camera(client, auth_headers, monkeypatch):
    from app.services import image_service

    photo_id = _photo(client, auth_headers)
    design_id = client.post(
        "/api/v1/designs", json={"photo_id": photo_id, "user_input": "原木客厅"}, headers=auth_headers
    ).json()["design_id"]
    initial = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    source_name = initial["front_image_url"].rsplit("/", 1)[-1]
    actual_edit = image_service.edit_design_front
    seen = []

    def record_edit(name, prompt, target_id):
        seen.append((name, prompt, target_id))
        return actual_edit(name, prompt, target_id)

    monkeypatch.setattr(image_service, "edit_design_front", record_edit)
    monkeypatch.setattr(image_service, "generate_design_front", lambda *args: (_ for _ in ()).throw(AssertionError("concept used original photo")))
    response = client.post(
        f"/api/v1/designs/{design_id}/regenerate",
        json={"view_mode": "concept", "feedback": "转向右侧电视墙，电视背景板悬浮，电视柜落地"},
        headers=auth_headers,
    )
    assert response.status_code == 202
    assert len(seen) == 1
    assert seen[0][0] == source_name
    assert "允许重新调整机位" in seen[0][1] or "同意改变相机机位" in seen[0][1]
    assert "电视柜落地" in seen[0][1]
    current = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    assert current["current_version"] == 2
    assert current["versions"][-1]["operation"] == "concept_view"
    assert current["versions"][0]["image_url"] == initial["front_image_url"]


def test_regenerate_failure_preserves_existing_image(client, auth_headers, monkeypatch):
    from app.services import image_service

    photo_id = _photo(client, auth_headers)
    design_id = client.post(
        "/api/v1/designs", json={"photo_id": photo_id, "user_input": "现代客厅"}, headers=auth_headers
    ).json()["design_id"]
    before = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()

    def fail_generate(*args):
        raise RuntimeError("test generation failure")

    monkeypatch.setattr(image_service, "generate_design_front", fail_generate)
    assert client.post(
        f"/api/v1/designs/{design_id}/regenerate", json={"feedback": "灯具不对"}, headers=auth_headers
    ).status_code == 202
    after = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    assert after["status"] == "front_ready"
    assert after["front_image_url"] == before["front_image_url"]
    assert after["versions"] == before["versions"]
    assert after["error"]["code"] == "REGENERATE_FAILED"


def test_interrupted_regenerate_resumes_after_startup(client, auth_headers):
    from fastapi.testclient import TestClient
    from app.main import app

    photo_id = _photo(client, auth_headers)
    design_id = client.post(
        "/api/v1/designs", json={"photo_id": photo_id, "user_input": "简洁客厅"}, headers=auth_headers
    ).json()["design_id"]
    db = SessionLocal()
    design = db.get(Design, design_id)
    design.pending_job = {"kind": "regenerate", "feedback": "窗帘颜色过深"}
    design.status = "editing"
    db.commit()
    db.close()

    with TestClient(app) as restarted:
        for _ in range(50):
            current = restarted.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
            if current["status"] == "front_ready":
                break
            time.sleep(0.05)
        assert current["status"] == "front_ready"
        assert current["current_version"] == 2
        assert current["versions"][-1]["instruction"] == "窗帘颜色过深"


def test_interrupted_edit_resumes_after_startup(client, auth_headers):
    from fastapi.testclient import TestClient
    from app.main import app

    photo_id = _photo(client, auth_headers)
    design_id = client.post(
        "/api/v1/designs", json={"photo_id": photo_id, "user_input": "原木风"}, headers=auth_headers
    ).json()["design_id"]
    db = SessionLocal()
    design = db.get(Design, design_id)
    design.pending_job = {
        "kind": "edit", "source_name": design.front_image_path, "operation": "recolor",
        "x": 0.35, "y": 0.55, "detail": "蓝色",
    }
    design.status = "editing"
    db.commit()
    db.close()

    with TestClient(app) as restarted:
        for _ in range(50):
            current = restarted.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
            if current["status"] == "front_ready":
                break
            time.sleep(0.05)
        assert current["status"] == "front_ready"
        assert current["current_version"] == 2


def test_iso_hotspots_are_owned_persisted_and_bound_to_image(client, auth_headers):
    photo_id = _photo(client, auth_headers)
    design_id = client.post(
        "/api/v1/designs", json={"photo_id": photo_id, "user_input": "原木客厅"}, headers=auth_headers
    ).json()["design_id"]
    url = f"/api/v1/designs/{design_id}/hotspots"
    before_iso = client.post(url, json={"product_id": "p001", "x": 0.3, "y": 0.5}, headers=auth_headers)
    assert before_iso.status_code == 409
    client.post(f"/api/v1/designs/{design_id}/confirm", headers=auth_headers)
    invalid = client.post(url, json={"product_id": "not-in-catalog", "x": 0.3, "y": 0.5}, headers=auth_headers)
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "PRODUCT_NOT_FOUND"
    added = client.post(url, json={"product_id": "p001", "x": 0.3, "y": 0.5}, headers=auth_headers)
    assert added.status_code == 201
    hotspot = added.json()["hotspots"][0]
    assert hotspot["product_id"] == "p001"
    assert hotspot["x"] == 0.3
    assert client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()["hotspots"] == [hotspot]

    db = SessionLocal()
    db.add(User(invite_code="HOTSPOT-OTHER"))
    db.commit()
    db.close()
    token = client.post("/api/v1/auth/login", json={"invite_code": "HOTSPOT-OTHER"}).json()["token"]
    other = {"Authorization": f"Bearer {token}"}
    assert client.post(url, json={"product_id": "p002", "x": 0.4, "y": 0.6}, headers=other).status_code == 404
    assert client.delete(f"{url}/{hotspot['id']}", headers=other).status_code == 404
    second_response = client.post(url, json={"product_id": "p002", "x": 0.6, "y": 0.4}, headers=auth_headers).json()
    second_id = second_response["added_hotspot_id"]
    removed = client.delete(f"{url}/{second_id}", headers=auth_headers)
    assert removed.status_code == 200
    assert removed.json()["hotspots"] == [hotspot]

    edited = client.post(
        f"/api/v1/designs/{design_id}/edits",
        json={"operation": "recolor", "x": 0.3, "y": 0.5, "detail": "绿色"}, headers=auth_headers,
    )
    assert edited.status_code == 202
    latest = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    assert latest["current_version"] == 2
    assert latest["hotspots"] == []
    client.post(f"/api/v1/designs/{design_id}/confirm", headers=auth_headers)
    assert client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()["hotspots"] == []


def test_local_demo_catalog_uses_real_product_ids_for_hotspots(client, auth_headers, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "demo_product_catalog", True)
    products = client.get("/api/v1/designs/products", headers=auth_headers).json()["products"]
    demo_products = [item for item in products if item.get("demo_only")]
    assert len(demo_products) >= 18
    assert all(sum(item["category"] == category for item in demo_products) >= 2 for category in ("sofa", "light", "plant", "table", "rug", "cabinet"))
    assert len(products) >= 28
    assert all(item["source_url"] and item["price"] is None for item in demo_products)

    photo_id = _photo(client, auth_headers)
    design_id = client.post(
        "/api/v1/designs", json={"photo_id": photo_id, "user_input": "原木客厅"}, headers=auth_headers
    ).json()["design_id"]
    client.post(f"/api/v1/designs/{design_id}/confirm", headers=auth_headers)
    saved = client.post(
        f"/api/v1/designs/{design_id}/hotspots",
        json={"product_id": demo_products[0]["id"], "x": 0.3, "y": 0.5}, headers=auth_headers,
    )
    assert saved.status_code == 201
    assert saved.json()["hotspots"][0]["product_id"] == demo_products[0]["id"]


def test_reference_photos_are_owned_and_saved(client, auth_headers):
    """参考图必须属于当前用户，且可在后续修改中读取。"""
    import secrets
    from app.models import DesignReference

    room = _photo(client, auth_headers)
    style = _photo(client, auth_headers)
    furniture = _photo(client, auth_headers)
    code = "REF-" + secrets.token_hex(4)
    with SessionLocal() as db:
        db.add(User(invite_code=code))
        db.commit()
    login = client.post("/api/v1/auth/login", json={"invite_code": code})
    other_headers = {"Authorization": f"Bearer {login.json()['token']}"}
    other_photo = _photo(client, other_headers)

    denied = client.post("/api/v1/designs", json={"photo_id": room, "user_input": "原木客厅", "style_photo_id": other_photo}, headers=auth_headers)
    assert denied.status_code == 404
    created = client.post("/api/v1/designs", json={"photo_id": room, "user_input": "原木客厅", "style_photo_id": style, "furniture_photo_id": furniture}, headers=auth_headers)
    assert created.status_code == 201
    design_id = created.json()["design_id"]
    result = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    assert result["references"] == {"style": f"/api/v1/files/uploads/{style}", "furniture": f"/api/v1/files/uploads/{furniture}"}
    with SessionLocal() as db:
        refs = db.query(DesignReference).filter(DesignReference.design_id == design_id).all()
        assert {(ref.kind, ref.photo_id) for ref in refs} == {("style", style), ("furniture", furniture)}

    denied_update = client.put(f"/api/v1/designs/{design_id}/references", json={"style_photo_id": other_photo}, headers=auth_headers)
    assert denied_update.status_code == 404
    unchanged = client.get(f"/api/v1/designs/{design_id}", headers=auth_headers).json()
    assert unchanged["references"] == result["references"]
    updated = client.put(f"/api/v1/designs/{design_id}/references", json={"style_photo_id": style}, headers=auth_headers)
    assert updated.status_code == 200
    assert updated.json()["references"] == {"style": f"/api/v1/files/uploads/{style}"}
