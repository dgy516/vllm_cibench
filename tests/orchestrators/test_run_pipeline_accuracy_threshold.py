"""Accuracy 阈值与通过判定（CI 策略）测试。

验证 `configs/tests/accuracy.yaml`（或环境变量覆盖）中的 `min_score`
会用于编排结果的通过判定：result["accuracy"]["ok"]。
"""

from __future__ import annotations

from pathlib import Path

import pytest

import vllm_cibench.orchestrators.run_pipeline as rp


@pytest.mark.accuracy
def test_accuracy_threshold_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """当精度分数低于阈值时，`ok` 应为 False。"""

    # 避免真实探活与真实功能请求
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
    # 固定精度结果为 0.5
    monkeypatch.setattr(
        rp,
        "run_accuracy",
        lambda base_url, model, cfg=None: {
            "task": "gpqa",
            "score": 0.5,
            "correct": 1,
            "total": 2,
        },
    )

    # 通过环境变量覆盖精度配置，设置 min_score=0.6
    acc_cfg = tmp_path / "acc.yaml"
    acc_cfg.write_text("min_score: 0.6\n", encoding="utf-8")
    monkeypatch.setenv("VLLM_CIBENCH_ACCURACY_CONFIG", str(acc_cfg))

    res = rp.execute(
        scenario_id="local_single_qwen3-32b_guided_w8a8",
        run_type="pr",
        root=str(Path.cwd()),
        timeout_s=0.1,
        dry_run=True,
    )
    acc = res.get("accuracy", {})
    assert isinstance(acc, dict)
    assert acc.get("score") == 0.5
    # 低于阈值 0.6，应判定为不通过
    assert acc.get("ok") is False
