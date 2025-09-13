"""精度评测执行器（最小实现）。

提供基于 OpenAI 兼容接口的最小化精度评测：
- 通过提供的样本（question/choices/answer）顺序调用 `/v1/chat/completions`，
- 统计正确率并返回聚合结果。

注意：本实现用于 CI 单测与本地调试，默认不访问外网数据集；在真实集成
中，可将 `cfg` 扩展为从本地/远端加载数据集与评测参数。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from vllm_cibench.clients.openai_client import OpenAICompatClient


@dataclass
class AccuracySample:
    """单条精度样本。

    属性:
        question: 题干。
        choices: 选项列表（可为空，表示开放式回答）。
        answer: 正确答案（直接比较字符串相等）。
    """

    question: str
    choices: Sequence[str]
    answer: str


def _parse_choice_text(resp: Mapping[str, Any]) -> str:
    """从 `/v1/chat/completions` 响应中提取文本答案。

    参数:
        resp: 响应体。

    返回值:
        str: choices[0].message.content 字段；缺失时返回空字符串。

    副作用:
        无。
    """

    try:
        return str(resp.get("choices", [{}])[0].get("message", {}).get("content", ""))
    except Exception:
        return ""


def run_accuracy(
    base_url: str,
    model: str,
    cfg: Optional[Mapping[str, Any]] = None,
    *,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """运行最小化精度评测。

    参数:
        base_url: 服务基础 URL，例如 `http://127.0.0.1:9000/v1`。
        model: 模型名。
        cfg: 评测配置，支持：
            - task: 任务名（默认 "gpqa"，仅作标签使用）。
            - samples: List[dict]，每项包含 {question, choices, answer}。
        api_key: 可选 API Key。

    返回值:
        dict: {"task", "score", "correct", "total"}。

    副作用:
        发起网络请求；当服务返回 4xx/5xx 时可能抛出 HTTPError。
    """

    task = str((cfg or {}).get("task", "gpqa"))
    raw = (cfg or {}).get("samples", [])
    raw_samples: Iterable[Mapping[str, Any]] = raw if isinstance(raw, list) else []
    # 构造样本（若未提供则给出两条占位样本）
    samples: List[AccuracySample] = []
    if raw_samples:
        for s in raw_samples:
            samples.append(
                AccuracySample(
                    question=str(s.get("question", "")),
                    choices=list(s.get("choices", []) or []),
                    answer=str(s.get("answer", "")),
                )
            )
    else:
        samples = [
            AccuracySample("2+2?", ["3", "4"], "4"),
            AccuracySample("1+1?", ["2", "3"], "2"),
        ]

    # 限制评测样本数（来自 cfg.max_samples）
    try:
        max_samples = int((cfg or {}).get("max_samples", 0))
    except Exception:
        max_samples = 0
    if max_samples and max_samples > 0:
        samples = samples[:max_samples]

    client = OpenAICompatClient(base_url=base_url, api_key=api_key)
    correct = 0
    for sm in samples:
        messages: List[Mapping[str, Any]] = [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": f"Question: {sm.question}\nChoices: {', '.join(sm.choices)}\nAnswer with the choice only.",
            },
        ]
        resp = client.chat_completions(model=model, messages=messages, temperature=0)
        # chat_completions 在非 stream 情况下应返回 Dict[str, Any]
        if isinstance(resp, dict):
            pred = _parse_choice_text(resp)
        else:  # 防御式处理：若出现流模式返回 list，取首个块解析
            pred = _parse_choice_text(resp[0] if resp else {})
        if pred.strip() == sm.answer.strip():
            correct += 1

    total = len(samples)
    score = (correct / total) if total else 0.0
    return {"task": task, "score": score, "correct": correct, "total": total}
