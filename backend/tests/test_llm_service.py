"""LLM 解析器与结构校验（纯函数单测，离线）。"""
import pytest

from app.core.errors import ServiceError
from app.services.llm_service import UnderstandResult, _extract_json, _system_prompt


def test_extract_json_plain():
    d = _extract_json('{"style": "cream", "colors": ["暖白"]}')
    assert d["style"] == "cream"


def test_extract_json_with_codefence():
    d = _extract_json('```json\n{"style": "cream", "colors": ["暖白", "原木"]}\n```')
    assert d["colors"] == ["暖白", "原木"]


def test_extract_json_with_prose_around():
    d = _extract_json('好的，结果如下：{"style": "cream"} 以上。')
    assert d["style"] == "cream"


def test_extract_json_invalid_raises():
    with pytest.raises(ServiceError):
        _extract_json("没有 JSON 内容")


def test_understand_result_defaults():
    r = UnderstandResult.model_validate({"style": "cream"})
    assert r.style == "cream"
    assert r.sd_prompts.front == ""
    assert r.design_notes == []


def test_understand_result_full():
    data = {
        "style": "cream",
        "colors": ["暖白", "原木"],
        "sd_prompts": {"front": "a b 真人视角、24mm 镜头、写实摄影、8k", "isometric": "c 等距视角、45 度俯视、3D 渲染、blender"},
        "design_notes": ["a", "b", "c"],
        "layout_hints": {"sofa_area": {"x": 0.3, "y": 0.5}},
    }
    r = UnderstandResult.model_validate(data)
    assert r.sd_prompts.isometric.endswith("blender")


def test_understanding_instructions_do_not_force_a_tv_wall():
    prompt = _system_prompt()
    assert "沙发必须正对电视墙" not in prompt
    assert "电视与电视背景墙只在用户要求" in prompt
    assert '"layout_hints": {}' in prompt
