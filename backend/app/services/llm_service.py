"""LLM 理解服务：火山方舟（OpenAI 兼容），无 Key 时走 mock（仅开发用，不冒充真实验收）。"""
import json
import re
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, Field

from ..core.config import settings
from ..core.errors import ServiceError

_PROMPT_PATH = Path(__file__).parent / "prompts" / "understand.txt"


class SdPrompts(BaseModel):
    front: str = ""
    isometric: str = ""


class UnderstandResult(BaseModel):
    style: str = "cream"
    colors: list[str] = Field(default_factory=list)
    mood: str = ""
    budget_level: str = "mid"
    members: list[str] = Field(default_factory=list)
    elements: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    sd_prompts: SdPrompts = Field(default_factory=SdPrompts)
    negative_prompt: str = ""
    design_notes: list[str] = Field(default_factory=list)
    layout_hints: dict = Field(default_factory=dict)


def _system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _client() -> OpenAI:
    return OpenAI(
        api_key=settings.ark_api_key,
        base_url=settings.ark_base_url,
        timeout=settings.llm_timeout_seconds,
    )


def _extract_json(text: str) -> dict:
    """宽容解析：容忍代码块标记与前后杂文，只取第一个 { 到最后一个 }。"""
    cleaned = re.sub(r"```(?:json)?", "", text or "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ServiceError("LLM_PARSE_FAILED", "模型未返回有效 JSON")
    return json.loads(cleaned[start : end + 1])


def _mock_understand(user_input: str) -> dict:
    return {
        "style": "cream",
        "colors": ["暖白", "原木", "米色"],
        "mood": "cozy, warm, minimalist",
        "budget_level": "mid",
        "members": ["couple", "cat"],
        "elements": ["软沙发", "暖光落地灯", "绿植", "原木纹理"],
        "avoid": ["冷色", "工业金属"],
        "sd_prompts": {
            "front": f"{user_input} 的客厅，奶油风，暖光，温馨，真人视角、24mm 镜头、写实摄影、8k",
            "isometric": f"{user_input} 的客厅，奶油风，等距视角、45 度俯视、3D 渲染、blender",
        },
        "negative_prompt": "ugly, distorted, low quality, perspective distortion",
        "design_notes": [
            "奶油色墙面搭配原木家具营造温暖氛围",
            "暖光落地灯弥补采光不足",
            "低矮沙发方便宠物活动",
        ],
        "layout_hints": {
            "sofa_area": {"x": 0.35, "y": 0.55},
            "tv_area": {"x": 0.3, "y": 0.1},
        },
    }


def understand_room(user_input: str, photo_url: str = "") -> dict:
    """理解用户意图，返回结构化 JSON（dict）。无 Key 走 mock；有 Key 走真实调用 + 一次纠错重试。"""
    if not settings.has_ark_key:
        return _mock_understand(user_input)
    if not settings.ark_llm_model:
        raise ServiceError("CONFIG_INCOMPLETE", "缺少 ARK_LLM_MODEL 配置")

    client = _client()
    user_msg = f"用户描述：{user_input}"
    if photo_url:
        user_msg += f"\n房间照片地址（供参考）：{photo_url}"

    last_err: Exception | None = None
    for attempt in range(2):
        try:
            resp = client.chat.completions.create(
                model=settings.ark_llm_model,
                messages=[
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.7,
            )
            content = resp.choices[0].message.content or ""
            data = _extract_json(content)
            result = UnderstandResult.model_validate(data)
            return result.model_dump()
        except ServiceError as e:
            last_err = e
        except Exception as e:  # 超时/网络/SDK 初始化失败
            last_err = ServiceError("LLM_CALL_FAILED", "AI 调用失败，请重试")
    # 重试耗尽
    if isinstance(last_err, ServiceError):
        raise last_err
    raise ServiceError("LLM_CALL_FAILED", "AI 调用失败，请重试")
