"""隔离测试脚本一次性保护；不接触火山 API。"""

import json

import pytest

from scripts.prepare_bedroom_inpaint import prepare
from scripts.qa_bedroom_inpaint import REQUEST_KEY, submit_once


def test_submit_once_persists_marker_before_call_and_refuses_second_submit(tmp_path):
    photo_path, mask_path = prepare(output=tmp_path)
    marker = tmp_path / "submission.json"

    class Client:
        calls = 0

        def cv_sync2async_submit_task(self, body):
            self.calls += 1
            assert marker.is_file()
            assert body["req_key"] == REQUEST_KEY
            assert len(body["binary_data_base64"]) == 2
            return {"code": 10000, "data": {"task_id": "isolated-stub-task"}}

    client = Client()
    assert submit_once(client, photo_path, mask_path, marker) == "isolated-stub-task"
    assert json.loads(marker.read_text())["task_id"] == "isolated-stub-task"
    with pytest.raises(FileExistsError):
        submit_once(client, photo_path, mask_path, marker)
    assert client.calls == 1
