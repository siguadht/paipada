"""模型评测：LLM 候选 × 真实样例，测 JSON 合规率 / 字段完整 / 收尾约束 / 耗时。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import OpenAI  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.services.llm_service import UnderstandResult, _extract_json, _system_prompt  # noqa: E402

SAMPLES = [
    "奶油风，有猫，3 万预算，要温馨",
    "原木日式，采光差，要收纳",
    "现代极简，黑白灰，预算紧张",
    "法式复古，有宝宝，要安全",
    "北欧风，绿植多，要明亮",
]

LLM_CANDIDATES = [
    "doubao-seed-2-1-turbo-260628",
    "deepseek-v4-1-flash-260910",
    "glm-5-3-flash-260828",
]


def run_llm(client: OpenAI, model: str, sample: str) -> dict:
    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": f"用户描述：{sample}"},
            ],
            temperature=0.7,
            max_tokens=1200,
        )
        content = resp.choices[0].message.content or ""
        latency = round(time.time() - t0, 2)
        usage = resp.usage
        try:
            data = _extract_json(content)
            result = UnderstandResult.model_validate(data)
            return {
                "latency": latency,
                "ok": True,
                "style": result.style,
                "notes": len(result.design_notes),
                "front_ok": result.sd_prompts.front.endswith("8k"),
                "iso_ok": result.sd_prompts.isometric.endswith("blender"),
                "colors": len(result.colors),
                "prompt_tokens": usage.prompt_tokens if usage else None,
                "completion_tokens": usage.completion_tokens if usage else None,
            }
        except Exception as e:
            return {"latency": latency, "ok": False, "err": type(e).__name__, "raw": content[:200]}
    except Exception as e:
        return {"latency": round(time.time() - t0, 2), "ok": False, "err": type(e).__name__}


def main() -> None:
    client = OpenAI(api_key=settings.ark_api_key, base_url=settings.ark_base_url, timeout=60)
    for model in LLM_CANDIDATES:
        print(f"\n===== {model} =====")
        ok = 0
        total_tok = 0
        for s in SAMPLES:
            r = run_llm(client, model, s)
            if r["ok"]:
                ok += 1
                total_tok += (r["prompt_tokens"] or 0) + (r["completion_tokens"] or 0)
                print(
                    f"  [{r['style']}] 说明{r['notes']}条 正面收尾{'OK' if r['front_ok'] else 'X'} "
                    f"2.5D收尾{'OK' if r['iso_ok'] else 'X'} 色{r['colors']} {r['latency']}s"
                )
            else:
                print(f"  X {r.get('err')} {r.get('raw', '')[:120]}")
        print(f"  >> 合规 {ok}/{len(SAMPLES)}，累计 token 约 {total_tok}")


if __name__ == "__main__":
    main()
