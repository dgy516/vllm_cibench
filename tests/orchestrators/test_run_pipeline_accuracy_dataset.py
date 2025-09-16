"""Accuracy 从数据集文件加载（JSONL/JSON）测试。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pytest

import vllm_cibench.orchestrators.run_pipeline as rp


class _DummyClient:
    """伪 OpenAI 客户端：根据问题返回正确答案文本。"""

    def __init__(self, base_url: str, api_key: str | None = None) -> None:  # noqa: D401
        self.base_url = base_url
        self.api_key = api_key

    def chat_completions(self, model: str, messages: list[Mapping[str, Any]], temperature: float = 0.0):  # type: ignore[override]
        text = ""
        if messages:
            last = messages[-1].get("content", "")
            if "2+2" in str(last):
                text = "4"
            elif "1+1" in str(last):
                text = "2"
        return {"choices": [{"message": {"content": text}}]}


@pytest.mark.accuracy
def test_accuracy_dataset_jsonl(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """从 JSONL 数据集加载两条样本并计算分数。"""

    # 避免真实探活
    monkeypatch.setattr(
        rp, "_discover_and_wait", lambda *a, **k: "http://127.0.0.1:9000/v1"
    )
    monkeypatch.setattr(
        rp,
        "run_smoke_suite",
        lambda *a, **k: {"choices": [{"message": {"content": "ok"}}]},
    )

    # 替换 OpenAI 客户端
    import vllm_cibench.testsuites.accuracy as acc

    monkeypatch.setattr(acc, "OpenAICompatClient", _DummyClient)

    # 构造 JSONL 数据集：一条 answer 字段，一条 answer_idx 字段
    ds = tmp_path / "gpqa.jsonl"
    rows = [
        {"question": "2+2?", "choices": ["3", "4"], "answer": "4"},
        {"question": "1+1?", "choices": ["2", "3"], "answer_idx": 0},
    ]
    ds.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8"
    )

    # 通过环境变量传入 accuracy 配置路径
    cfg = tmp_path / "acc.yaml"
    cfg.write_text(
        f"""
min_score: 1.0
dataset_file: {ds}
dataset_format: jsonl
max_samples: 10
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("VLLM_CIBENCH_ACCURACY_CONFIG", str(cfg))

    res = rp.execute(
        scenario_id="local_single_qwen3-32b_guided_w8a8",
        run_type="pr",
        root=str(Path.cwd()),
        timeout_s=0.1,
        dry_run=True,
    )

    acc_res = res.get("accuracy", {})
    assert acc_res.get("score") == 1.0
    assert acc_res.get("ok") is True
