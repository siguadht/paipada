"""第二空间的任务保护和输入复核均在本地完成。"""

import json

import pytest

from scripts.prepare_livingroom_inpaint import prepare
from scripts.qa_bedroom_inpaint import submit_once, validate_inputs
from scripts.qa_livingroom_inpaint import PROMPT


def test_livingroom_uses_its_own_one_shot_marker(tmp_path):
    photo, mask = prepare(output=tmp_path)
    validate_inputs(photo, mask, PROMPT)
    marker = tmp_path / "livingroom-submission.json"

    class Client:
        calls = 0

        def cv_sync2async_submit_task(self, body):
            self.calls += 1
            assert marker.exists()
            assert body["prompt"] == PROMPT
            return {"code": 10000, "data": {"task_id": "local-stub"}}

    client = Client()
    assert submit_once(client, photo, mask, marker, PROMPT) == "local-stub"
    assert json.loads(marker.read_text())["task_id"] == "local-stub"
    with pytest.raises(FileExistsError):
        submit_once(client, photo, mask, marker, PROMPT)
    assert client.calls == 1
