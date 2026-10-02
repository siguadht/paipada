"""拍拍搭后端入口。"""
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401  确保模型注册到 Base.metadata
from .api import auth, designs, files, homes, tasks, uploads
from .core.config import settings
from .core.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from .db import Base, SessionLocal, engine
from .models import Design, DesignLayerSet
from .services.design_service import _run_edit, _run_initial, _run_iso, _run_regenerate

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.generated_dir, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    # 意外重启后继续新编辑工作流；任务参数已先于后台执行持久化。
    with SessionLocal() as db:
        # 付费拆层任务可能在模型成功扣费后才中断；重启不自动再次调用。
        for layer_set in db.query(DesignLayerSet).filter(DesignLayerSet.status.in_(["queued", "processing"])).all():
            layer_set.status = "failed"
            layer_set.error_message = "准备过程被中断；请查看火山账单后再决定是否重新尝试"
        unfinished = db.query(Design).filter(Design.status.in_([
            "pending", "understanding", "rendering_front", "editing", "rendering_iso"
        ])).all()
        for design in unfinished:
            job = design.pending_job or {}
            if design.status in ("pending", "understanding", "rendering_front"):
                target, args = _run_initial, (design.id,)
            elif job.get("kind") == "edit":
                target, args = _run_edit, (
                    design.id, job["source_name"], job["operation"],
                    job.get("x"), job.get("y"), job.get("detail", ""), job.get("target", ""),
                    job.get("product_reference_path", ""),
                )
            elif job.get("kind") == "iso":
                target, args = _run_iso, (design.id, job["source_name"])
            elif job.get("kind") == "regenerate":
                target, args = _run_regenerate, (design.id, job["feedback"], job.get("view_mode", "original"), job.get("source_name", ""))
            else:
                design.status = "front_ready" if design.front_image_path else "failed"
                design.error_code = "INTERRUPTED"
                design.error_message = "任务被中断，请重新提交"
                continue
            threading.Thread(target=target, args=args, daemon=True).start()
        db.commit()
    yield


app = FastAPI(title="拍拍搭 API", version="0.1.0", lifespan=lifespan)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1/uploads")
app.include_router(tasks.router, prefix="/api/v1/tasks")
app.include_router(designs.router, prefix="/api/v1/designs")
app.include_router(homes.router, prefix="/api/v1/homes")
app.include_router(files.router, prefix="/api/v1/files")

app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
