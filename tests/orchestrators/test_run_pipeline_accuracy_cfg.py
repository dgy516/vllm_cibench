"""Accuracy 配置加载行为测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

import vllm_cibench.orchestrators.run_pipeline as rp


def test_execute_uses_global_accuracy_cfg(monkeypatch: pytest.MonkeyPatch):
    """当场景未提供 accuracy 配置时，应读取全局 configs/tests/accuracy.yaml。"""

    # 避免真实探活
    monkeypatch.setattr(
        rp,
        "_discover_and_wait",
        lambda base, s, timeout_s=60.0: "http://127.0.0.1:9000/v1",
    )
    monkeypatch.setattr(
        rp,
        "run_smoke_suite",
        lambda base_url, model: {"choices": [{"message": {"content": "ok"}}]},
    )

    captured = {}

    def fake_acc(base_url: str, model: str, cfg=None):
        captured["cfg"] = dict(cfg or {})
        return {"task": captured["cfg"].get("task", "none"), "score": 1.0, "correct": 1, "total": 1}

    monkeypatch.setattr(rp, "run_accuracy", fake_acc)

    res = rp.execute(
        scenario_id="local_single_qwen3-32b_guided_w8a8",
        run_type="pr",
        root=str(Path.cwd()),
        timeout_s=0.1,
    )
    # 全局 configs/tests/accuracy.yaml 中默认 task 为 gpqa
    assert captured["cfg"].get("task") == "gpqa"
    assert res.get("accuracy", {}).get("task") == "gpqa"

