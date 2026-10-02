"""任务：创建、查询（轮询）、审图、历史。"""
import os
import re

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.errors import ServiceError, api_error
from ..db import get_db
from ..models import Photo, Task
from ..models.task import STATUS_PENDING
from ..schemas import (
    HistoryResponse,
    ReviewRequest,
    TaskCreateRequest,
    TaskCreateResponse,
    TaskResponse,
)
from ..services.task_service import review_task, run_task, task_to_dict
from .deps import get_current_user_id

router = APIRouter(tags=["tasks"])

_PHOTO_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(jpg|png|webp)$")


def _owned_task(db: Session, task_id: str, user_id: int) -> Task:
    """数据隔离：只返回本人任务；他人任务一律 404，不泄露存在性。"""
    task = db.get(Task, task_id)
    if not task or task.user_id != user_id:
        raise api_error(404, "TASK_NOT_FOUND", "任务不存在")
    return task


@router.post("", response_model=TaskCreateResponse, status_code=201)
def create_task(
    payload: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if not _PHOTO_RE.match(payload.photo_id):
        raise api_error(400, "INVALID_PHOTO", "照片标识无效")
    photo = db.get(Photo, payload.photo_id)
    if not photo or photo.user_id != user_id:
        raise api_error(404, "PHOTO_NOT_FOUND", "照片不存在，请重新上传")
    if not os.path.isfile(os.path.join(settings.upload_dir, payload.photo_id)):
        raise api_error(404, "PHOTO_NOT_FOUND", "照片不存在，请重新上传")

    task = Task(
        user_id=user_id,
        photo_path=payload.photo_id,
        user_input=payload.user_input.strip(),
        status=STATUS_PENDING,
        progress=0,
        current_step="排队中",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    background_tasks.add_task(run_task, task.id)
    return TaskCreateResponse(
        task_id=task.id,
        status=task.status,
        created_at=task.created_at.isoformat() if task.created_at else "",
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    task = _owned_task(db, task_id, user_id)
    return task_to_dict(task)


@router.post("/{task_id}/review", response_model=TaskResponse)
def review(
    task_id: str,
    payload: ReviewRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _owned_task(db, task_id, user_id)
    try:
        regenerate = review_task(db, task_id, payload.action, payload.score)
    except ServiceError as e:
        raise api_error(409, e.code, e.message)
    if regenerate:
        background_tasks.add_task(run_task, task_id)
    task = _owned_task(db, task_id, user_id)
    return task_to_dict(task)


@router.get("", response_model=HistoryResponse)
def history(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    tasks = (
        db.query(Task)
        .filter(Task.user_id == user_id)
        .order_by(Task.created_at.desc())
        .limit(50)
        .all()
    )
    return HistoryResponse(tasks=[task_to_dict(t) for t in tasks])
