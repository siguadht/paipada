"""生成邀请码并写入数据库（邀请码只打印一次，请自行保存分发；码本身不写入项目状态文件）。

用法：cd backend && .venv/bin/python -m scripts.create_invite [数量] [前缀]
"""
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import User  # noqa: E402


def main() -> None:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    prefix = sys.argv[2] if len(sys.argv) > 2 else "PPT"

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        codes = []
        for _ in range(count):
            code = f"{prefix}-{secrets.token_urlsafe(6).upper()}"
            db.add(User(invite_code=code))
            codes.append(code)
        db.commit()
        print("已生成以下邀请码（请复制保存，仅显示一次）：")
        for c in codes:
            print(" ", c)
    finally:
        db.close()


if __name__ == "__main__":
    main()
