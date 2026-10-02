"""API 集成测试：登录、上传、建任务、状态机、审图、数据隔离（全 mock，离线）。"""
import io
import time

from PIL import Image

from app.db import SessionLocal
from app.models import User


def make_png_bytes(color=(200, 180, 150), size=(64, 64)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def upload_photo(client, headers) -> str:
    resp = client.post(
        "/api/v1/uploads",
        files={"file": ("room.png", make_png_bytes(), "image/png")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["photo_id"]


def upload_photo_response(client, headers):
    return client.post(
        "/api/v1/uploads",
        files={"file": ("room.png", make_png_bytes(), "image/png")},
        headers=headers,
    )


def wait_status(client, headers, task_id, targets, timeout=5.0):
    targets = {targets} if isinstance(targets, str) else set(targets)
    for _ in range(int(timeout / 0.1)):
        d = client.get(f"/api/v1/tasks/{task_id}", headers=headers).json()
        if d["status"] in targets:
            return d
        time.sleep(0.1)
    return d


def test_login_success_and_fail(client, auth_headers):
    # auth_headers 已成功登录
    assert "Authorization" in auth_headers
    # 错误邀请码
    resp = client.post("/api/v1/auth/login", json={"invite_code": "NOT-EXIST"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_INVITE_CODE"


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_upload_rejects_non_image(client, auth_headers):
    resp = client.post(
        "/api/v1/uploads",
        files={"file": ("bad.txt", b"hello world", "text/plain")},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_uploaded_photo_requires_owner(client, auth_headers):
    resp = upload_photo_response(client, auth_headers)
    assert resp.status_code == 201
    url = resp.json()["url"]
    assert client.get(url).status_code == 401
    owned = client.get(url, headers=auth_headers)
    assert owned.status_code == 200
    assert owned.headers["cache-control"] == "private, no-store"


def test_create_task_requires_valid_photo(client, auth_headers):
    resp = client.post(
        "/api/v1/tasks",
        json={"photo_id": "../etc/passwd", "user_input": "奶油风"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_full_flow_to_completed(client, auth_headers):
    photo_id = upload_photo(client, auth_headers)
    resp = client.post(
        "/api/v1/tasks",
        json={"photo_id": photo_id, "user_input": "奶油风，有猫，3万预算，要温馨"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    task_id = resp.json()["task_id"]

    d = wait_status(client, auth_headers, task_id, "review")
    assert d["status"] == "review", d
    assert d["step_details"]["understanding"]["completed"] is True
    assert d["step_details"]["rendering"]["front_image_url"]
    assert d["result"]["design_notes"], "应有设计说明"

    # 审图通过
    resp = client.post(
        f"/api/v1/tasks/{task_id}/review",
        json={"action": "approve", "score": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    d = resp.json()
    assert d["status"] == "completed"
    assert d["review_score"] == 5
    assert d["result"]["front_image_url"]


def test_review_reject_then_failed(client, auth_headers):
    photo_id = upload_photo(client, auth_headers)
    task_id = client.post(
        "/api/v1/tasks",
        json={"photo_id": photo_id, "user_input": "原木日式"},
        headers=auth_headers,
    ).json()["task_id"]
    wait_status(client, auth_headers, task_id, "review")

    # 连续驳回 3 次 → failed
    for _ in range(3):
        resp = client.post(
            f"/api/v1/tasks/{task_id}/review",
            json={"action": "reject"},
            headers=auth_headers,
        )
        d = resp.json()
        if d["status"] == "failed":
            break
        wait_status(client, auth_headers, task_id, "review")
    assert d["status"] == "failed"
    assert d["error"]["code"] == "REVIEW_REJECTED"


def test_data_isolation(client):
    # 用户 A 建任务，用户 B 看不到
    db = SessionLocal()
    for code in ("ISO-A-1", "ISO-B-1"):
        db.add(User(invite_code=code))
    db.commit()
    db.close()

    a = client.post("/api/v1/auth/login", json={"invite_code": "ISO-A-1"}).json()["token"]
    b = client.post("/api/v1/auth/login", json={"invite_code": "ISO-B-1"}).json()["token"]
    ha = {"Authorization": f"Bearer {a}"}
    hb = {"Authorization": f"Bearer {b}"}

    photo_id = upload_photo(client, ha)
    photo_url = f"/api/v1/files/uploads/{photo_id}"
    assert client.get(photo_url, headers=ha).status_code == 200
    assert client.get(photo_url, headers=hb).status_code == 404

    # B 不能拿 A 的 photo_id 创建任务
    other_user_resp = client.post(
        "/api/v1/tasks", json={"photo_id": photo_id, "user_input": "现代简约"}, headers=hb
    )
    assert other_user_resp.status_code == 404

    task_id = client.post(
        "/api/v1/tasks", json={"photo_id": photo_id, "user_input": "法式复古"}, headers=ha
    ).json()["task_id"]

    # B 访问 A 的任务 → 404
    assert client.get(f"/api/v1/tasks/{task_id}", headers=hb).status_code == 404
    # B 的历史里没有 A 的任务
    b_hist = client.get("/api/v1/tasks", headers=hb).json()["tasks"]
    assert all(t["task_id"] != task_id for t in b_hist)
    # A 能看到自己的
    assert client.get(f"/api/v1/tasks/{task_id}", headers=ha).status_code == 200

    task = wait_status(client, ha, task_id, "review")
    front_url = task["result"]["front_image_url"]
    assert client.get(front_url).status_code == 401
    assert client.get(front_url, headers=hb).status_code == 404
    assert client.get(front_url, headers=ha).status_code == 200
