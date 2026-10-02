import os
import secrets
import tempfile

# 必须在导入 app 之前设置环境变量，覆盖默认配置与 .env
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(tempfile.gettempdir(), 'ppd_test.db')}"
os.environ["ARK_API_KEY"] = ""  # 强制走 mock，离线可测
os.environ["JWT_SECRET"] = "test-secret-0123456789-0123456789"
os.environ["UPLOAD_DIR"] = os.path.join(tempfile.gettempdir(), "ppd_test_uploads")
os.environ["GENERATED_DIR"] = os.path.join(tempfile.gettempdir(), "ppd_test_generated")
os.environ["DEMO_PRODUCT_CATALOG"] = "0"  # 本机演示开关不能改变既有测试的默认商品库

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import User


@pytest.fixture(scope="session", autouse=True)
def _db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    code = "TEST-" + secrets.token_hex(4)
    db = SessionLocal()
    db.add(User(invite_code=code))
    db.commit()
    db.close()
    resp = client.post("/api/v1/auth/login", json={"invite_code": code})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['token']}"}
