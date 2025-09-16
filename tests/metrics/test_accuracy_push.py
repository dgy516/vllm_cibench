"""Accuracy 指标推送（daily-only）测试。"""

from __future__ import annotations

from pathlib import Path
from typing import List, Mapping, Tuple

import pytest

import vllm_cibench.orchestrators.run_pipeline as rp


@pytest.mark.accuracy
def test_push_accuracy_metrics_daily(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """在 daily 且非 dry-run 下，应推送 accuracy 指标到 Pushgateway。"""

    # 避免真实探活
    monkeypatch.setattr(
        rp, "_discover_and_wait", lambda *a, **k: "http://127.0.0.1:9000/v1"
    )
    monkeypatch.setattr(
        rp,
        "run_smoke_suite",
        lambda *a, **k: {"choices": [{"message": {"content": "ok"}}]},
    )

    # 固定 accuracy 结果
    monkeypatch.setattr(
        rp,
        "run_accuracy",
        lambda **kwargs: {"task": "gpqa", "score": 0.8, "correct": 8, "total": 10},
    )

    # 捕获 push_metrics 调用
    calls: List[Tuple[str, Mapping[str, float], Mapping[str, str]]] = []

    def fake_push(job: str, metrics: Mapping[str, float], *, labels: Mapping[str, str], run_type: str, dry_run: bool) -> bool:  # type: ignore[override]
        calls.append((job, metrics, labels))
        return True

    monkeypatch.setattr(rp, "push_metrics", fake_push)

    _ = rp.execute(
        scenario_id="local_single_qwen3-32b_guided_w8a8",
        run_type="daily",
        root=str(Path.cwd()),
        timeout_s=0.1,
        dry_run=False,
    )

    # 断言存在 accuracy 指标推送
    assert any("ci_accuracy_score" in m for _, m, _ in calls)
