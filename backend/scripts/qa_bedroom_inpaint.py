"""隔离的一次性即梦遮罩验证，不接正式生成流程。

默认只检查本地输入。只有获得单次费用授权、服务已开通后，才可显式传入
``--submit-once``。提交标记会在网络请求前落盘；结果不明时禁止重复提交。
``--poll`` 仅查询已有任务，不会创建新任务。
"""

from __future__ import annotations

import argparse
import base64
import json
import time
from pathlib import Path

import httpx
from PIL import Image

from app.core.config import settings
from scripts.prepare_bedroom_inpaint import MAX_BYTES, OUTPUT, prepare


REQUEST_KEY = "jimeng_image2image_dream_inpaint"
PROMPT = (
    "保持原照片机位、门窗、吊顶、墙体和木地板。在左侧墙与地面白色选区布置写实的低饱和现代原木卧室："
    "双人床靠左墙，搭配床头柜、浅色地毯和暖光落地灯。黑色区域保持原样，家具比例自然，光影与原房间一致。"
)
MARKER = OUTPUT / "submission.json"


def validate_inputs(photo_path: Path, mask_path: Path, prompt: str = PROMPT) -> None:
    if len(prompt) > 120:
        raise ValueError("提示词超过接口建议的 120 字")
    with Image.open(photo_path) as photo, Image.open(mask_path) as mask:
        if photo.size != mask.size or mask.mode != "L":
            raise ValueError("原图与遮罩必须同尺寸，遮罩必须是单通道灰度图")
        if max(photo.size) > 4096:
            raise ValueError("输入超出接口最大边长")
        if mask.getextrema() != (0, 255):
            raise ValueError("遮罩缺少黑色保留区或白色编辑区")
    if any(path.stat().st_size > MAX_BYTES for path in (photo_path, mask_path)):
        raise ValueError("单张输入超过 4.7 MB")


def visual_client():
    if not settings.tos_access_key or not settings.tos_secret_key:
        raise RuntimeError("缺少火山 AK/SK；不会回显凭据")
    from volcengine.visual.VisualService import VisualService

    client = VisualService()
    client.set_ak(settings.tos_access_key)
    client.set_sk(settings.tos_secret_key)
    return client


def submit_once(client, photo_path: Path, mask_path: Path, marker: Path = MARKER, prompt: str = PROMPT) -> str:
    validate_inputs(photo_path, mask_path, prompt)
    marker.parent.mkdir(parents=True, exist_ok=True)
    # 独占创建使重复执行无法重复付费；请求结果不明时也保留标记供人工核查。
    with marker.open("x", encoding="utf-8") as handle:
        json.dump({"state": "submission_attempted", "created_at": int(time.time())}, handle)
    body = {
        "req_key": REQUEST_KEY,
        "binary_data_base64": [base64.b64encode(path.read_bytes()).decode("ascii") for path in (photo_path, mask_path)],
        "prompt": prompt,
    }
    response = client.cv_sync2async_submit_task(body)
    task_id = (response.get("data") or {}).get("task_id")
    if response.get("code") != 10000 or not task_id:
        marker.write_text(json.dumps({"state": "submission_failed_or_unknown", "code": response.get("code")}), encoding="utf-8")
        raise RuntimeError("即梦任务未确认创建；一次性标记仍在，不会自动重试")
    marker.write_text(json.dumps({"state": "submitted", "task_id": str(task_id)}), encoding="utf-8")
    return str(task_id)


def poll_existing(client, marker: Path = MARKER, output: Path = OUTPUT, result_name: str = "卧室-即梦遮罩单次结果.jpg") -> str:
    record = json.loads(marker.read_text(encoding="utf-8"))
    task_id = record.get("task_id")
    if not task_id:
        raise RuntimeError("没有已确认的任务 ID，禁止新提交")
    for _ in range(40):
        response = client.cv_sync2async_get_result({
            "req_key": REQUEST_KEY,
            "task_id": task_id,
            "req_json": json.dumps({"return_url": True, "logo_info": {"add_logo": False}}),
        })
        data = response.get("data") or {}
        urls = data.get("image_urls") or []
        if response.get("code") == 10000 and urls:
            image = httpx.get(urls[0], timeout=60)
            image.raise_for_status()
            target = output / result_name
            target.write_bytes(image.content)
            with Image.open(target) as generated:
                generated.verify()
            marker.write_text(json.dumps({"state": "completed", "task_id": task_id, "result": target.name}), encoding="utf-8")
            return str(target)
        if data.get("status") in {"done", "not_found", "expired"} or response.get("code") not in {10000, None}:
            raise RuntimeError("任务已结束但没有可用图片；保留任务 ID 供人工核查")
        time.sleep(3)
    raise TimeoutError("查询超时；任务 ID 已保存，不会重新提交")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--submit-once", action="store_true", help="会创建一项可能计费的云任务；仅在明确授权后使用")
    group.add_argument("--poll", action="store_true", help="只查询此前已提交的任务")
    args = parser.parse_args()
    photo_path, mask_path = prepare()
    validate_inputs(photo_path, mask_path)
    if not args.submit_once and not args.poll:
        print("本地输入合规；没有调用云接口")
        return
    client = visual_client()
    if args.submit_once:
        print(f"任务 ID：{submit_once(client, photo_path, mask_path)}")
    else:
        print(f"结果：{poll_existing(client)}")


if __name__ == "__main__":
    main()
