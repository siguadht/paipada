"""Pydantic 请求/响应结构。"""
from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    invite_code: str = Field(min_length=4, max_length=64)


class LoginResponse(BaseModel):
    token: str
    user_id: int


class MeResponse(BaseModel):
    user_id: int


class UploadResponse(BaseModel):
    photo_id: str
    url: str
    width: int
    height: int


class TaskCreateRequest(BaseModel):
    photo_id: str = Field(min_length=1, max_length=128)
    user_input: str = Field(min_length=1, max_length=200)


class TaskCreateResponse(BaseModel):
    task_id: str
    status: str
    created_at: str


class ReviewRequest(BaseModel):
    action: Literal["approve", "reject"]
    score: int | None = Field(default=None, ge=1, le=5)


class TaskResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    current_step: str
    step_details: dict
    result: dict | None
    error: dict | None
    user_input: str = ""
    photo_url: str = ""
    review_score: int | None = None
    reject_count: int = 0
    created_at: str | None = None


class HistoryResponse(BaseModel):
    tasks: list[dict]
